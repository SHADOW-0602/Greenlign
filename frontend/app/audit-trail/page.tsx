"use client";

import React, { useState } from "react";
import AuditTraceViewer, { AuditTraceData } from "../../components/AuditTraceViewer";

export default function AuditTrailPage() {
  const [calculationIdInput, setCalculationIdInput] = useState<string>("");
  const [trace, setTrace] = useState<AuditTraceData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTrace = async (idToFetch: string) => {
    if (!idToFetch.trim()) {
      setError("Please enter a valid calculation UUID.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/audit/trace/${idToFetch.trim()}`);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to fetch trace (status ${res.status})`);
      }
      const data: AuditTraceData = await res.json();
      setTrace(data);
    } catch (err: any) {
      console.error("Trace fetch error:", err);
      setError(err.message || "Failed to load calculation provenance trace.");
      setTrace(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchTrace(calculationIdInput);
  };

  return (
    <main className="min-h-screen bg-slate-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <header>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Audit Trail & Provenance Viewer
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Inspect end-to-end evidence chains for emissions figures: from raw file hashes and activity line items to factor tables, formulas, and disclosure citations.
          </p>

          {/* Search Bar */}
          <form onSubmit={handleSubmit} className="mt-6 flex max-w-2xl gap-3">
            <input
              type="text"
              value={calculationIdInput}
              onChange={(e) => setCalculationIdInput(e.target.value)}
              placeholder="Enter Calculation UUID (e.g. 550e8400-e29b-41d4-a716-446655440000)"
              className="flex-1 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-600 font-mono"
            />
            <button
              type="submit"
              disabled={loading}
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:opacity-50"
            >
              {loading ? "Tracing..." : "Inspect Provenance"}
            </button>
          </form>
        </header>

        {error && (
          <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}

        {loading && (
          <div className="bg-white rounded-lg border border-slate-200 p-12 text-center text-slate-400">
            Assembling end-to-end audit provenance chain...
          </div>
        )}

        {!loading && trace && <AuditTraceViewer trace={trace} />}

        {!loading && !trace && !error && (
          <div className="bg-white rounded-lg border border-slate-200 p-12 text-center text-slate-400">
            Enter a calculation UUID above to inspect its cryptographic and regulatory audit trail.
          </div>
        )}
      </div>
    </main>
  );
}
