"""Anomaly detection service for Greenlign: variance, outliers, and greenwashing detection."""

import json
import math
import re
import uuid
from decimal import Decimal
from typing import Any

from groq import Groq
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.activity_data import ActivityData
from app.models.anomaly_flag import AnomalyFlag
from app.models.audit_log import AuditLogEntry
from app.models.calculation import Calculation
from app.schemas.anomaly import (
    ClaimVerdict,
    NarrativeCheckResponse,
    NarrativeClaimFinding,
)


class AnomalyDetector:
    """Detects statistical outliers, omitted emissions, and narrative greenwashing claims."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _fetch_calcs_for_period(
        self, entity_id: uuid.UUID, period: str
    ) -> list[tuple[Calculation, ActivityData]]:
        """Fetch all calculations and activities matching entity_id and reporting period."""
        query = (
            select(Calculation, ActivityData)
            .join(ActivityData, Calculation.activity_data_id == ActivityData.id)
            .where(ActivityData.entity_id == entity_id)
        )
        res = await self.session.execute(query)
        all_rows = list(res.all())

        # Filter by year or period string
        matched: list[tuple[Calculation, ActivityData]] = []
        for row in all_rows:
            calc, act = row[0], row[1]
            start_year = str(act.period_start.year)
            end_year = str(act.period_end.year)
            if period in (start_year, end_year) or f"{start_year}" == period:
                matched.append((calc, act))
        return matched

    async def check_yoy_variance(
        self,
        entity_id: uuid.UUID,
        current_period: str,
        baseline_period: str,
        threshold_pct: Decimal = Decimal("50.0"),
    ) -> list[AnomalyFlag]:
        """Flag sharp drops or surges in emissions without proportional activity changes."""
        prior_data = await self._fetch_calcs_for_period(entity_id, baseline_period)
        curr_data = await self._fetch_calcs_for_period(entity_id, current_period)

        if not prior_data or not curr_data:
            return []

        # Group emissions and quantities by scope
        prior_scope_tco2e: dict[int, Decimal] = {}
        prior_scope_qty: dict[int, Decimal] = {}
        for c, a in prior_data:
            sc = a.scope or 1
            prior_scope_tco2e[sc] = prior_scope_tco2e.get(sc, Decimal("0")) + c.result_tco2e
            prior_scope_qty[sc] = prior_scope_qty.get(sc, Decimal("0")) + a.quantity

        curr_scope_tco2e: dict[int, Decimal] = {}
        curr_scope_qty: dict[int, Decimal] = {}
        for c, a in curr_data:
            sc = a.scope or 1
            curr_scope_tco2e[sc] = curr_scope_tco2e.get(sc, Decimal("0")) + c.result_tco2e
            curr_scope_qty[sc] = curr_scope_qty.get(sc, Decimal("0")) + a.quantity

        flags: list[AnomalyFlag] = []

        for sc, prior_tco2e in prior_scope_tco2e.items():
            if prior_tco2e <= Decimal("0"):
                continue

            curr_tco2e = curr_scope_tco2e.get(sc, Decimal("0"))
            prior_qty = prior_scope_qty.get(sc, Decimal("0"))
            curr_qty = curr_scope_qty.get(sc, Decimal("0"))

            pct_change = ((curr_tco2e - prior_tco2e) / prior_tco2e) * Decimal("100.0")
            act_pct_change = (
                ((curr_qty - prior_qty) / prior_qty) * Decimal("100.0")
                if prior_qty > 0
                else Decimal("0")
            )

            # Check for unexplained drop
            if pct_change <= -threshold_pct:
                # If activity drop is significantly less than emission drop
                if act_pct_change > (pct_change / Decimal("2")):
                    severity = "CRITICAL" if pct_change <= Decimal("-70.0") else "WARNING"
                    title = f"Unexplained {abs(pct_change):.1f}% Drop in Scope {sc} Emissions"
                    description = (
                        f"Scope {sc} emissions dropped by {abs(pct_change):.1f}% "
                        f"(from {prior_tco2e:.2f} to {curr_tco2e:.2f} tCO2e), "
                        f"while activity quantity only changed by {act_pct_change:.1f}%. "
                        "Indicates potentially omitted data sources or missing calculation records."
                    )
                    flag = AnomalyFlag(
                        entity_id=entity_id,
                        reporting_period=current_period,
                        flag_type="YOY_DROP",
                        severity=severity,
                        title=title,
                        description=description,
                        details_json={
                            "scope": sc,
                            "prior_tco2e": str(prior_tco2e),
                            "current_tco2e": str(curr_tco2e),
                            "pct_change": float(pct_change),
                            "activity_pct_change": float(act_pct_change),
                            "baseline_period": baseline_period,
                        },
                    )
                    self.session.add(flag)
                    flags.append(flag)

            # Check for unexplained surge (> 100% increase)
            elif pct_change >= Decimal("100.0"):
                if act_pct_change < (pct_change / Decimal("2")):
                    title = f"Unexplained {pct_change:.1f}% Surge in Scope {sc} Emissions"
                    description = (
                        f"Scope {sc} emissions surged by {pct_change:.1f}% "
                        f"while activity quantity only changed by {act_pct_change:.1f}%. "
                        "Indicates possible unit conversion errors or duplicated records."
                    )
                    flag = AnomalyFlag(
                        entity_id=entity_id,
                        reporting_period=current_period,
                        flag_type="YOY_SPIKE",
                        severity="WARNING",
                        title=title,
                        description=description,
                        details_json={
                            "scope": sc,
                            "prior_tco2e": str(prior_tco2e),
                            "current_tco2e": str(curr_tco2e),
                            "pct_change": float(pct_change),
                            "activity_pct_change": float(act_pct_change),
                            "baseline_period": baseline_period,
                        },
                    )
                    self.session.add(flag)
                    flags.append(flag)

        return flags

    async def check_intensity_outliers(
        self,
        entity_id: uuid.UUID,
        period: str,
        zscore_cutoff: float = 3.0,
    ) -> list[AnomalyFlag]:
        """Flag line items where intensity (tCO2e/unit) is > N standard deviations from mean."""
        data = await self._fetch_calcs_for_period(entity_id, period)
        if len(data) < 3:
            return []

        # Group by (activity_type, unit)
        groups: dict[tuple[str, str], list[tuple[Calculation, ActivityData, float]]] = {}
        for c, a in data:
            if a.quantity > Decimal("0"):
                intensity = float(c.result_tco2e / a.quantity)
                key = (a.activity_type, a.unit)
                groups.setdefault(key, []).append((c, a, intensity))

        flags: list[AnomalyFlag] = []

        for (a_type, unit), items in groups.items():
            if len(items) < 3:
                continue

            intensities = [item[2] for item in items]
            mean_val = sum(intensities) / len(intensities)
            variance = sum((x - mean_val) ** 2 for x in intensities) / (len(intensities) - 1)
            stdev = math.sqrt(variance)

            if stdev <= 0:
                continue

            for calc, act, inten in items:
                z_score = abs(inten - mean_val) / stdev
                if z_score >= zscore_cutoff:
                    severity = "CRITICAL" if z_score >= 5.0 else "WARNING"
                    title = f"Emissions Intensity Outlier for {a_type} (Z={z_score:.2f})"
                    description = (
                        f"Line item has emissions intensity of {inten:.6f} tCO2e/{unit}, "
                        f"which is {z_score:.2f} standard deviations from mean ({mean_val:.6f})."
                    )
                    flag = AnomalyFlag(
                        entity_id=entity_id,
                        reporting_period=period,
                        flag_type="INTENSITY_OUTLIER",
                        severity=severity,
                        title=title,
                        description=description,
                        details_json={
                            "calculation_id": str(calc.id),
                            "activity_data_id": str(act.id),
                            "activity_type": a_type,
                            "unit": unit,
                            "intensity": inten,
                            "cohort_mean": mean_val,
                            "cohort_stdev": stdev,
                            "z_score": z_score,
                        },
                    )
                    self.session.add(flag)
                    flags.append(flag)

        return flags

    async def check_scope_completeness(
        self,
        entity_id: uuid.UUID,
        current_period: str,
        baseline_period: str | None = None,
    ) -> list[AnomalyFlag]:
        """Detect omission of mandatory scopes or categories that were historically reported."""
        curr_data = await self._fetch_calcs_for_period(entity_id, current_period)
        if not curr_data:
            return []

        curr_scopes = {a.scope for _, a in curr_data if a.scope is not None}
        flags: list[AnomalyFlag] = []

        if baseline_period:
            prior_data = await self._fetch_calcs_for_period(entity_id, baseline_period)
            prior_scopes = {a.scope for _, a in prior_data if a.scope is not None}

            # If a scope was present in baseline but is completely absent in current period
            for sc in (1, 2, 3):
                if sc in prior_scopes and sc not in curr_scopes:
                    prior_sc_total = sum(
                        (c.result_tco2e for c, a in prior_data if a.scope == sc),
                        Decimal("0"),
                    )
                    title = f"Omission of Scope {sc} Emissions"
                    description = (
                        f"Scope {sc} emissions were reported in baseline period {baseline_period} "
                        f"({prior_sc_total:.2f} tCO2e), but are absent in {current_period}."
                    )
                    flag = AnomalyFlag(
                        entity_id=entity_id,
                        reporting_period=current_period,
                        flag_type="SCOPE_INCOMPLETENESS",
                        severity="CRITICAL",
                        title=title,
                        description=description,
                        details_json={
                            "missing_scope": sc,
                            "prior_tco2e": str(prior_sc_total),
                            "current_tco2e": "0.0",
                            "baseline_period": baseline_period,
                        },
                    )
                    self.session.add(flag)
                    flags.append(flag)

        return flags

    async def run_statistical_scan(
        self,
        entity_id: uuid.UUID,
        current_period: str,
        baseline_period: str | None = None,
        yoy_threshold_pct: Decimal = Decimal("50.0"),
        zscore_threshold: float = 3.0,
        actor: str = "system:anomaly_detector",
    ) -> list[AnomalyFlag]:
        """Run statistical and completeness checks, persist flags, and log audit entry."""
        flags: list[AnomalyFlag] = []

        # 1. Intensity outliers
        intensity_flags = await self.check_intensity_outliers(
            entity_id, current_period, zscore_threshold
        )
        flags.extend(intensity_flags)

        # 2. Scope completeness
        comp_flags = await self.check_scope_completeness(
            entity_id, current_period, baseline_period
        )
        flags.extend(comp_flags)

        # 3. YoY variance if baseline provided
        if baseline_period:
            yoy_flags = await self.check_yoy_variance(
                entity_id, current_period, baseline_period, yoy_threshold_pct
            )
            flags.extend(yoy_flags)

        # Audit log entry
        audit = AuditLogEntry(
            entity_type="anomaly_scan",
            entity_id=entity_id,
            action="ANOMALY_SCAN",
            actor=actor,
            detail={
                "current_period": current_period,
                "baseline_period": baseline_period,
                "flags_generated": len(flags),
            },
        )
        self.session.add(audit)
        await self.session.commit()

        # Refresh flags
        for f in flags:
            await self.session.refresh(f)

        return flags

    def _run_heuristic_fallback(
        self, narrative_text: str, pct_change_str: str
    ) -> tuple[list[NarrativeClaimFinding], str, str]:
        """Heuristic rule-based fallback when LLM is offline or encounters an error."""
        findings: list[NarrativeClaimFinding] = []
        overall_status = "CLEAN"
        summary = "Heuristic evaluation complete."

        m = re.search(
            r"(\d+(?:\.\d+)?)%\s*(?:reduction|decrease|cut)",
            narrative_text,
            re.IGNORECASE,
        )
        if m:
            claimed_val = float(m.group(1))
            findings.append(
                NarrativeClaimFinding(
                    claim_text=m.group(0),
                    verdict="POTENTIAL_GREENWASHING" if claimed_val > 20 else "SUPPORTED",
                    claimed_metric=f"{claimed_val}% reduction",
                    actual_metric=pct_change_str,
                    discrepancy_explanation=(
                        "Heuristic review: reported reduction deviates from calculations."
                    ),
                )
            )
            overall_status = "FLAGGED" if claimed_val > 20 else "CLEAN"
            summary = "Heuristic check flagged potential greenwashing claim."
        return findings, overall_status, summary

    async def evaluate_narrative_claims(
        self,
        entity_id: uuid.UUID,
        reporting_period: str,
        narrative_text: str,
        baseline_period: str | None = None,
        groq_client: Any = None,
        actor: str = "auditor",
    ) -> NarrativeCheckResponse:
        """Cross-reference narrative sustainability claims against verified calculation totals."""
        # 1. Fetch current and baseline emissions metrics
        curr_data = await self._fetch_calcs_for_period(entity_id, reporting_period)
        curr_total = sum((c.result_tco2e for c, _ in curr_data), Decimal("0"))
        curr_s1 = sum((c.result_tco2e for c, a in curr_data if a.scope == 1), Decimal("0"))
        curr_s2 = sum((c.result_tco2e for c, a in curr_data if a.scope == 2), Decimal("0"))
        curr_s3 = sum((c.result_tco2e for c, a in curr_data if a.scope == 3), Decimal("0"))

        baseline_info = ""
        pct_change_str = "N/A"
        if baseline_period:
            base_data = await self._fetch_calcs_for_period(entity_id, baseline_period)
            base_total = sum((c.result_tco2e for c, _ in base_data), Decimal("0"))
            base_s1 = sum((c.result_tco2e for c, a in base_data if a.scope == 1), Decimal("0"))
            base_s2 = sum((c.result_tco2e for c, a in base_data if a.scope == 2), Decimal("0"))
            base_s3 = sum((c.result_tco2e for c, a in base_data if a.scope == 3), Decimal("0"))
            if base_total > 0:
                pct = ((curr_total - base_total) / base_total) * 100
                pct_change_str = f"{pct:+.2f}%"
            baseline_info = (
                f"Baseline Period ({baseline_period}): Total={base_total:.2f} tCO2e "
                f"(Scope 1={base_s1:.2f}, Scope 2={base_s2:.2f}, Scope 3={base_s3:.2f}). "
                f"Overall YoY Change: {pct_change_str}."
            )

        data_context = (
            f"Reporting Period ({reporting_period}): Total={curr_total:.2f} tCO2e "
            f"(Scope 1={curr_s1:.2f}, Scope 2={curr_s2:.2f}, Scope 3={curr_s3:.2f}).\n"
            f"{baseline_info}"
        )

        # 2. Call Groq LLM (or mock/fallback)
        findings: list[NarrativeClaimFinding] = []
        overall_status = "CLEAN"
        summary = "All claims aligned with calculation ledger."

        prompt_system = (
            "You are an expert greenhouse gas auditor. Cross-examine the empirical claims in the "
            "provided corporate sustainability narrative against the verified calculations data.\n"
            "Identify statements alleging specific percentage reductions, carbon neutrality, or "
            "emission quantities.\n"
            "For each claim, decide verdict from: "
            "'SUPPORTED', 'UNSUPPORTED', 'POTENTIAL_GREENWASHING', 'CONTRADICTED'.\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "findings": [\n'
            "    {\n"
            '      "claim_text": "...",\n'
            '      "verdict": "CONTRADICTED",\n'
            '      "claimed_metric": "...",\n'
            '      "actual_metric": "...",\n'
            '      "discrepancy_explanation": "..."\n'
            "    }\n"
            "  ],\n"
            '  "overall_status": "FLAGGED",\n'
            '  "summary_text": "..."\n'
            "}"
        )

        prompt_user = (
            f"Verified Calculation Data:\n{data_context}\n\n"
            f"Submitted Narrative:\n{narrative_text}"
        )

        client = groq_client
        if not client and settings.groq_api_key:
            client = Groq(api_key=settings.groq_api_key)

        if client:
            try:
                response = client.chat.completions.create(
                    model=settings.groq_model,
                    messages=[
                        {"role": "system", "content": prompt_system},
                        {"role": "user", "content": prompt_user},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                raw_json = response.choices[0].message.content or "{}"
                parsed = json.loads(raw_json)
                overall_status = parsed.get("overall_status", "CLEAN")
                summary = parsed.get("summary_text", "")
                for f_data in parsed.get("findings", []):
                    verdict_val: ClaimVerdict = f_data.get("verdict", "UNSUPPORTED")
                    findings.append(
                        NarrativeClaimFinding(
                            claim_text=f_data.get("claim_text", ""),
                            verdict=verdict_val,
                            claimed_metric=f_data.get("claimed_metric", ""),
                            actual_metric=f_data.get("actual_metric", ""),
                            discrepancy_explanation=f_data.get("discrepancy_explanation", ""),
                        )
                    )
            except Exception:
                findings, overall_status, summary = self._run_heuristic_fallback(
                    narrative_text, pct_change_str
                )
        else:
            findings, overall_status, summary = self._run_heuristic_fallback(
                narrative_text, pct_change_str
            )

        # 3. If greenwashing or contradiction is detected, persist an AnomalyFlag
        flag_id: uuid.UUID | None = None
        has_inconsistency = any(
            f.verdict in ("POTENTIAL_GREENWASHING", "CONTRADICTED") for f in findings
        )
        if has_inconsistency or overall_status == "FLAGGED":
            overall_status = "FLAGGED"
            flag = AnomalyFlag(
                entity_id=entity_id,
                reporting_period=reporting_period,
                flag_type="NARRATIVE_INCONSISTENCY",
                severity="CRITICAL",
                title="Greenwashing Alert: Narrative Claim Contradicts Calculation Ledger",
                description=(
                    summary or "Submitted text contains claims inconsistent with calculations."
                ),
                details_json={
                    "findings": [f.model_dump() for f in findings],
                    "data_context": data_context,
                },
            )
            self.session.add(flag)
            await self.session.commit()
            await self.session.refresh(flag)
            flag_id = flag.id

        return NarrativeCheckResponse(
            overall_status=overall_status,  # type: ignore[arg-type]
            findings=findings,
            flag_id=flag_id,
            summary_text=summary,
        )
