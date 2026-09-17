# Greenlign — Build Roadmap
### For use with an AI coding IDE (Cursor / Windsurf / Claude Code / etc.)

This document is written to be pasted directly into an AI IDE as a build brief. It specifies the tech stack, repo structure, data models, and a phase-by-phase task list with concrete acceptance criteria. Each phase is designed to be handed to the AI IDE as its own prompt/session once the prior phase is merged.

---

## 0. Tech Stack (concrete, opinionated)

| Layer | Choice | Why |
|---|---|---|
| Language (backend) | **Python 3.12** | Best ecosystem for data parsing (pandas), OCR, and agent orchestration |
| Backend framework | **FastAPI** | Async, typed, auto-generates OpenAPI docs — good for an AI IDE to reason about |
| LLM provider | **Groq API** (`llama-3.3-70b-versatile` via `groq` Python SDK) | Used for classification/narrative steps only — never final arithmetic |
| Database | **Neon Serverless PostgreSQL** (PostgreSQL 16 compatible) | Relational integrity for the audit ledger; connection pooling and SSL (`sslmode=require`); JSONB columns for flexible line-item metadata |
| ORM | **SQLAlchemy 2.0 + Alembic** | Migrations needed since factor tables and schemas will evolve |
| Object storage | **Backblaze B2 (production) / MinIO (local dev)** | S3-compatible via `boto3`; raw source documents (PDFs, CSVs) stored immutably, referenced by hash |
| Task queue | **Celery + Redis** | Async ingestion/OCR jobs shouldn't block API requests |
| OCR/document parsing | **`unstructured` library + `pytesseract`** (or AWS Textract if cloud budget allows) | Utility bill PDFs, freight logs |
| Tabular parsing | **pandas + openpyxl** | CSV/XLSX ERP exports |
| Frontend | **Next.js 14 (App Router) + TypeScript + Tailwind CSS** | Matches the stack already used in the org's other project (voice agents); reuse patterns |
| Frontend state/data | **TanStack Query** | Server-state caching for dashboard views |
| Auth | **Auth.js (NextAuth) or Clerk** | Fast to stand up; role-based access needed (analyst / auditor / admin) |
| PII redaction | **Presidio (Microsoft)** or custom regex+NER pipeline | Detect and tokenize supplier names, contract values, account numbers before any LLM call |
| Testing | **pytest (backend), Vitest + Playwright (frontend)** | Standard |
| Infra/deploy | **Docker Compose for local dev; Terraform + AWS ECS/Fargate for prod** | Keep it boring and reproducible |
| CI | **GitHub Actions** | Lint, type-check, test, migration-check on every PR |

**Non-negotiable architectural rule to give the AI IDE up front:**
> All arithmetic that produces a final tCO2e figure MUST be executed by a deterministic Python function with unit tests, never by an LLM completion. LLM calls are only permitted for: (a) classifying a line item into a Scope/category, (b) drafting narrative text for disclosures, (c) detecting anomalies as a first-pass flag that a human then confirms. Any PR that has an LLM call producing a number that lands directly in the audit ledger should be rejected.

---

## 1. Repository Structure

```
greenlign/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI entrypoint
│   │   ├── api/
│   │   │   ├── ingestion.py            # upload endpoints
│   │   │   ├── classification.py
│   │   │   ├── calculations.py
│   │   │   ├── disclosures.py
│   │   │   └── audit.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── models/                     # SQLAlchemy models
│   │   │   ├── activity_data.py
│   │   │   ├── emission_factor.py
│   │   │   ├── calculation.py
│   │   │   ├── disclosure.py
│   │   │   └── audit_log.py
│   │   ├── schemas/                    # Pydantic schemas
│   │   ├── services/
│   │   │   ├── ingestion_service.py
│   │   │   ├── pii_redaction.py
│   │   │   ├── scope_classifier.py     # LLM-assisted, confidence-scored
│   │   │   ├── factor_matcher.py       # deterministic lookup
│   │   │   ├── calc_engine.py          # deterministic arithmetic
│   │   │   ├── anomaly_detector.py
│   │   │   └── disclosure_generator.py
│   │   ├── factor_tables/              # versioned data, not code
│   │   │   ├── epa_egrid_2025.json
│   │   │   ├── epa_ghg_factors_2025.json
│   │   │   └── defra_2025.json
│   │   ├── workers/                    # Celery tasks
│   │   └── tests/
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── dashboard/
│   │   ├── ingestion/
│   │   ├── review-queue/
│   │   ├── disclosures/
│   │   └── audit-trail/
│   ├── components/
│   ├── lib/
│   └── package.json
├── infra/
│   ├── docker-compose.yml
│   └── terraform/
└── docs/
    └── plan.md                          # (the strategic plan doc)
```

---

## 2. Core Data Models (give these to the AI IDE verbatim as a starting schema)

```python
# activity_data.py — canonical normalized record from ANY source
class ActivityData(Base):
    id: UUID
    source_document_id: UUID          # FK to raw uploaded file
    raw_line_ref: str                 # e.g. row number / page number in source
    entity_id: UUID                   # which company/subsidiary this belongs to
    activity_type: str                # e.g. "electricity_purchase", "freight_road", "flight"
    quantity: Decimal
    unit: str                         # "kWh", "liters", "km", "USD" etc.
    geography: str                    # ISO country/region code, needed for factor matching
    period_start: date
    period_end: date
    supplier_ref: str                 # TOKENIZED reference, not raw supplier name
    scope: Optional[int]              # 1, 2, or 3 — filled by classifier
    ghg_category: Optional[str]       # GHG Protocol category, e.g. "Scope 3.6 Business Travel"
    classification_confidence: Optional[float]
    status: str                       # "pending_review" | "classified" | "calculated" | "flagged"
    created_at: datetime

# emission_factor.py — versioned, sourced, never hardcoded in application code
class EmissionFactor(Base):
    id: UUID
    source: str                       # "EPA_eGRID" | "EPA_GHG_Hub" | "DEFRA"
    source_version: str               # e.g. "2025", must be tracked
    activity_type: str
    geography: str
    unit: str
    factor_value: Decimal
    factor_unit: str                  # e.g. "kgCO2e/kWh"
    published_date: date
    effective_from: date
    effective_to: Optional[date]

# calculation.py — the deterministic output, fully traceable
class Calculation(Base):
    id: UUID
    activity_data_id: UUID            # FK
    emission_factor_id: UUID          # FK
    formula_applied: str              # human-readable, e.g. "quantity * factor_value * unit_conversion"
    result_tco2e: Decimal
    computed_by: str                  # "calc_engine_v1" — always deterministic code, never "llm"
    computed_at: datetime

# audit_log.py — AIMS-style governance log
class AuditLogEntry(Base):
    id: UUID
    entity_type: str                  # "activity_data" | "calculation" | "disclosure"
    entity_id: UUID
    action: str                       # "created" | "reviewed" | "approved" | "flagged"
    actor: str                        # user id or "system:classifier_v1"
    timestamp: datetime
    detail: JSONB                     # before/after values, reviewer notes, etc.

# disclosure.py
class Disclosure(Base):
    id: UUID
    entity_id: UUID
    framework: str                    # "CA_SB253" | "CSRD_ESRS_E1" | "GHG_PROTOCOL"
    reporting_period: str
    status: str                       # "draft" | "reviewed" | "filed"
    generated_document_ref: str       # S3 ref to generated PDF/DOCX
    line_item_refs: list[UUID]        # every Calculation.id that feeds this disclosure
```

---

## 3. Phase-by-Phase Build Plan

Each phase below is scoped to be a self-contained prompt for an AI IDE session. Give it the phase goal, the "must include" list, and the acceptance criteria — let the IDE propose file-level implementation.

### Phase 0 — Scaffolding & Data Model (est. 1–2 sessions)
**Goal:** Repo skeleton, Postgres schema, Docker Compose dev environment.
**Must include:**
- FastAPI app boots with `/health` endpoint
- SQLAlchemy models above, with Alembic migration generating the tables
- Docker Compose with Postgres + Redis + backend + frontend services
- Seed script loading a small sample of EPA/DEFRA factors into `emission_factor` table
**Acceptance criteria:**
- `docker compose up` brings up a working stack
- `alembic upgrade head` creates all tables cleanly
- A pytest smoke test inserts and reads back one `ActivityData` row

### Phase 1 — Ingestion Pipeline
**Goal:** Upload CSV/XLSX + PDF, normalize into `ActivityData`.
**Must include:**
- `/api/ingestion/upload` endpoint accepting file upload, storing raw file in S3/MinIO, creating a `source_document` record
- CSV/XLSX parser mapping arbitrary ERP export columns to canonical schema (start with a configurable column-mapping step — don't hardcode one ERP's format)
- PDF parser (unstructured + pytesseract) extracting line items from utility bills
- PII redaction step: supplier names/account numbers tokenized before anything touches an LLM
- Celery task for async processing of larger files
**Acceptance criteria:**
- Uploading a sample utility PDF produces `ActivityData` rows with `status = "pending_review"`
- Uploading a sample ERP CSV produces correctly mapped rows
- No raw supplier name or account number appears in any LLM prompt log

### Phase 2 — Scope Classification
**Goal:** LLM-assisted classification of each `ActivityData` row into Scope 1/2/3 + GHG Protocol category, with confidence scoring.
**Must include:**
- `scope_classifier.py` calling Groq API (`llama-3.3-70b-versatile`) with a structured-output prompt (JSON schema for scope + category + confidence)
- Confidence threshold config (e.g. <0.75 → `status = "pending_review"` for human queue)
- Review queue API + minimal frontend page to approve/correct classifications
**Acceptance criteria:**
- A batch of 50 mixed sample line items classifies with >80% matching a hand-labeled test set
- Every classification writes an `AuditLogEntry`
- Human corrections in the review queue update `ActivityData` and log the correction

### Phase 3 — Emission Factor Matching + Deterministic Calculation Engine
**Goal:** Match each classified activity to the correct versioned emission factor and compute tCO2e via pure deterministic code.
**Must include:**
- `factor_matcher.py`: pure function, no LLM call, matches on `(activity_type, geography, effective date range)`
- `calc_engine.py`: pure function performing unit conversion + multiplication, fully unit-tested with known EPA/DEFRA examples
- Every `Calculation` row stores `formula_applied` as a human-readable string
- Missing-factor case handled explicitly (flagged for manual factor addition, never silently estimated by an LLM)
**Acceptance criteria:**
- Given a known input (e.g. "1,000 kWh, US grid, 2025"), the engine produces the correct tCO2e matching a manually verified EPA eGRID calculation, to the decimal
- 100% unit test coverage on `calc_engine.py`
- No LLM call appears anywhere in the call stack of this phase

### Phase 4 — Audit Trail & Governance Log
**Goal:** Make every number traceable end-to-end: disclosure figure → calculation → factor → raw source document.
**Must include:**
- `/api/audit/trace/{calculation_id}` endpoint returning the full chain (activity data → source document link → factor used → formula → result)
- Frontend audit-trail viewer page showing this chain visually
**Acceptance criteria:**
- For any `Calculation`, the trace endpoint returns a complete, correct chain in under 200ms
- Attempting to delete a `Calculation` or `EmissionFactor` referenced by a `Disclosure` is blocked (referential integrity enforced)

### Phase 5 — Disclosure Generator
**Goal:** Generate jurisdiction-specific draft disclosures from approved calculations.
**Must include:**
- Template system parameterized by `framework` (start with CA SB 253, then GHG Protocol summary, then CSRD ESRS E1 subset)
- `disclosure_generator.py` aggregates `Calculation` rows into the required categories per framework, generates a PDF/DOCX with citations back to source calculations
- Explicit "entity eligibility" check (e.g. does this entity meet the CSRD €450M/1,000-employee threshold?) before offering that framework
**Acceptance criteria:**
- Given a fully calculated dataset, generates a CA SB 253-formatted draft report with every figure hyperlinked/footnoted to its `Calculation.id`
- Ineligible frameworks are hidden/warned, not silently generated

### Phase 6 — Greenwashing / Anomaly Detection
**Goal:** Flag statistical outliers and narrative-vs-data inconsistencies.
**Must include:**
- `anomaly_detector.py`: rule-based + statistical checks (e.g. year-over-year change beyond N standard deviations, reported reduction claims not supported by underlying activity data)
- Flags surfaced in a dedicated review UI, never auto-blocking without human sign-off
**Acceptance criteria:**
- Injecting a synthetic anomalous data point (e.g. a 90% YoY drop with no corresponding activity change) triggers a flag
- False-positive rate on a clean sample dataset stays low enough to be usable (tune threshold, document the tuning)

### Phase 7 (stretch) — Dashboard, Simulator, Supplier Outreach
Build only after Phases 0–6 are solid. Each is a separate module:
- **Dashboard:** Next.js pages consuming aggregate APIs, charts via Recharts/D3
- **Scenario simulator:** what-if engine reusing `calc_engine.py` with modified activity assumptions, ranks levers by ROI
- **Supplier outreach agent:** templated email generation + tracking table for missing Scope 3 supplier data

---

## 4. Prompting Notes for the AI IDE

When handing each phase to the AI IDE, include:
1. The relevant data model section above (don't make it re-derive schema from scratch)
2. The non-negotiable rule about deterministic arithmetic (Section 0)
3. The specific acceptance criteria for that phase
4. A reminder to write tests alongside implementation, not after

Suggested first prompt to paste into the IDE:
> "Build Phase 0 of the Greenlign project as specified in this roadmap: FastAPI + Postgres + Docker Compose scaffolding with the data models in Section 2. Use SQLAlchemy 2.0 + Alembic. Do not implement any business logic yet — this phase is scaffolding and schema only."
