"use client";

import React, { useState } from "react";

export interface NarrativeClaimFinding {
  claim_text: string;
  verdict: "SUPPORTED" | "POTENTIAL_GREENWASHING" | "CONTRADICTED" | "UNSUPPORTED" | string;
  confidence: number;
  rationale: string;
  claimed_metric?: string | null;
  verified_metric?: string | null;
  ledger_diff_percent?: number | null;
}

export interface NarrativeCheckResponse {
  entity_id: string;
  reporting_period: string;
  narrative_text: string;
  findings: NarrativeClaimFinding[];
  overall_status: "CLEAN" | "FLAGGED" | string;
}

interface NarrativeClaimCheckerProps {
  entityId?: string;
  reportingPeriod?: string;
  onScanTriggered?: () => void;
}

export default function NarrativeClaimChecker({
  entityId = "",
  reportingPeriod = "2025",
  onScanTriggered,
}: NarrativeClaimCheckerProps) {
  const [activeEntityId, setActiveEntityId] = useState<string>(entityId);
  const [period, setPeriod] = useState<string>(reportingPeriod);
  const [narrativeText, setNarrativeText] = useState<string>(
    "In 2025, through our aggressive sustainability initiative, we achieved an 80% reduction in total corporate emissions across all facilities."
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<NarrativeCheckResponse | null>(null);

  const handleCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeEntityId.trim()) {
      setError("Please specify a valid Entity UUID.");
      return;
    }
    if (!narrativeText.trim()) {
      setError("Please provide narrative text to cross-examine.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/anomalies/check-narrative", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entity_id: activeEntityId.trim(),
          reporting_period: period.trim(),
          narrative_text: narrativeText.trim(),
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned HTTP ${res.status}`);
      }

      const data: NarrativeCheckResponse = await res.json();
      setResult(data);
      if (onScanTriggered) {
        onScanTriggered();
      }
    } catch (err: any) {
      console.error("Narrative check error:", err);
      setError(err.message || "Failed to analyze narrative claims.");
    } finally {
      setLoading(false);
    }
  };

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case "SUPPORTED":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
            ✓ SUPPORTED BY LEDGER
          </span>
        );
      case "POTENTIAL_GREENWASHING":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
            ⚠ POTENTIAL GREENWASHING
          </span>
        );
      case "CONTRADICTED":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-red-100 text-red-800 border border-red-200">
            ✗ CONTRADICTED BY DATA
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            UNSUPPORTED / UNVERIFIABLE
          </span>
        );
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
      <div>
        <div className="flex items-center space-x-2">
          <span className="text-xl">🔍</span>
          <h2 className="text-lg font-bold text-slate-900">
            Corporate Narrative & Greenwashing Cross-Examiner
          </h2>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Groq LLM extracts empirical environmental claims from CSR reports or press releases and
          strictly verifies them against deterministically calculated ledger totals.
        </p>
      </div>

      <form onSubmit={handleCheck} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Entity UUID
            </label>
            <input
              type="text"
              value={activeEntityId}
              onChange={(e) => setActiveEntityId(e.target.value)}
              placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
              className="w-full rounded-md border border-slate-300 p-2 text-xs font-mono text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Reporting Period
            </label>
            <input
              type="text"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              placeholder="e.g. 2025"
              className="w-full rounded-md border border-slate-300 p-2 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
            Disclosure Text / Public Statement
          </label>
          <textarea
            rows={4}
            value={narrativeText}
            onChange={(e) => setNarrativeText(e.target.value)}
            placeholder="Paste public ESG claims, press releases, or annual disclosure text here..."
            className="w-full rounded-md border border-slate-300 p-3 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none leading-relaxed"
            required
          />
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-50 text-red-700 text-xs border border-red-200">
            {error}
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-500 transition shadow-sm disabled:opacity-50 flex items-center space-x-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Cross-Examining Claims...</span>
              </>
            ) : (
              <span>Verify Against Audit Ledger</span>
            )}
          </button>
        </div>
      </form>

      {result && (
        <div className="border-t border-slate-200 pt-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Analysis Results ({result.findings.length} claims extracted)
            </h3>
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                result.overall_status === "CLEAN"
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                  : "bg-red-100 text-red-800 border border-red-200"
              }`}
            >
              Overall: {result.overall_status}
            </span>
          </div>

          {result.findings.length === 0 ? (
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 text-center">
              No empirical sustainability or quantitative reduction claims were detected in the provided text.
            </div>
          ) : (
            <div className="space-y-3">
              {result.findings.map((f, idx) => (
                <div
                  key={idx}
                  className={`p-4 rounded-lg border text-xs space-y-3 ${
                    f.verdict === "SUPPORTED"
                      ? "bg-emerald-50/50 border-emerald-200"
                      : f.verdict === "POTENTIAL_GREENWASHING"
                      ? "bg-amber-50/50 border-amber-200"
                      : "bg-red-50/50 border-red-200"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-semibold text-slate-900 italic">
                      &ldquo;{f.claim_text}&rdquo;
                    </p>
                    {getVerdictBadge(f.verdict)}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2 bg-white/70 p-2.5 rounded border border-slate-200/60 font-mono text-[11px]">
                    <div>
                      <span className="text-slate-500 block">Claimed Metric:</span>
                      <span className="font-bold text-slate-800">
                        {f.claimed_metric || "None"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Ledger Verified Metric:</span>
                      <span className="font-bold text-slate-800">
                        {f.verified_metric || "N/A"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Variance / Diff:</span>
                      <span
                        className={`font-bold ${
                          f.ledger_diff_percent && Math.abs(f.ledger_diff_percent) > 5
                            ? "text-red-600"
                            : "text-emerald-700"
                        }`}
                      >
                        {f.ledger_diff_percent != null
                          ? `${f.ledger_diff_percent.toFixed(1)}%`
                          : "N/A"}
                      </span>
                    </div>
                  </div>

                  <p className="text-slate-700 leading-relaxed font-sans">
                    <span className="font-semibold text-slate-900">Auditor Notes: </span>
                    {f.rationale}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
