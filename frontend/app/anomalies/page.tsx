"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import AnomalyDetectorView, { AnomalyFlagData } from "../../components/AnomalyDetectorView";
import NarrativeClaimChecker from "../../components/NarrativeClaimChecker";

interface ScanSummary {
  entity_id: string;
  reporting_period: string;
  baseline_period?: string | null;
  total_activity_lines_checked: number;
  yoy_flags_raised: number;
  intensity_flags_raised: number;
  completeness_flags_raised: number;
  total_new_flags: number;
}

export default function AnomaliesPage() {
  const [flags, setFlags] = useState<AnomalyFlagData[]>([]);
  const [loadingFlags, setLoadingFlags] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"flags" | "narrative">("flags");

  // Scan trigger form state
  const [entityIdInput, setEntityIdInput] = useState<string>("550e8400-e29b-41d4-a716-446655440000");
  const [currentPeriodInput, setCurrentPeriodInput] = useState<string>("2025");
  const [baselinePeriodInput, setBaselinePeriodInput] = useState<string>("2024");
  const [scanning, setScanning] = useState<boolean>(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [scanSummary, setScanSummary] = useState<ScanSummary | null>(null);

  const fetchFlags = async () => {
    setLoadingFlags(true);
    try {
      const url = entityIdInput.trim()
        ? `/api/anomalies?entity_id=${encodeURIComponent(entityIdInput.trim())}`
        : "/api/anomalies";
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setFlags(data);
      }
    } catch (err) {
      console.error("Failed to fetch anomaly flags:", err);
    } finally {
      setLoadingFlags(false);
    }
  };

  useEffect(() => {
    fetchFlags();
  }, []);

  const handleRunScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!entityIdInput.trim()) {
      setScanError("Please provide an Entity UUID.");
      return;
    }

    setScanning(true);
    setScanError(null);
    setScanSummary(null);

    try {
      const res = await fetch("/api/anomalies/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entity_id: entityIdInput.trim(),
          reporting_period: currentPeriodInput.trim(),
          baseline_period: baselinePeriodInput.trim() || undefined,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Scan failed with status ${res.status}`);
      }

      const summary: ScanSummary = await res.json();
      setScanSummary(summary);
      await fetchFlags();
      setActiveTab("flags");
    } catch (err: any) {
      console.error("Scan error:", err);
      setScanError(err.message || "Failed to run statistical anomaly scan.");
    } finally {
      setScanning(false);
    }
  };

  const openFlagsCount = flags.filter((f) => f.status === "OPEN").length;
  const criticalCount = flags.filter((f) => f.severity === "CRITICAL" && f.status === "OPEN").length;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-16">
      {/* Top Navbar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-2xl font-black bg-gradient-to-r from-emerald-600 to-teal-500 bg-clip-text text-transparent">
              Greenlign
            </span>
            <span className="text-slate-300">|</span>
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-500">
              Audit & Governance
            </span>
          </div>

          <nav className="flex space-x-4 text-xs font-medium">
            <Link href="/" className="text-slate-600 hover:text-slate-900">
              Overview
            </Link>
            <Link href="/review" className="text-slate-600 hover:text-slate-900">
              Review Queue
            </Link>
            <Link href="/audit-trail" className="text-slate-600 hover:text-slate-900">
              Audit Trail
            </Link>
            <Link href="/disclosures" className="text-slate-600 hover:text-slate-900">
              Disclosures
            </Link>
            <Link
              href="/anomalies"
              className="text-emerald-700 font-bold border-b-2 border-emerald-600 pb-1"
            >
              Anomalies & Greenwashing
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        {/* Page Title & KPI Bar */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              Greenwashing & Anomaly Detection Center
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Multi-layer detection: YoY variance checks, cohort emission intensity outliers (Z ≥ 3.0),
              mandatory scope completeness, and LLM narrative consistency cross-examination.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <div className="px-3 py-2 bg-white rounded-lg border border-slate-200 shadow-sm text-center">
              <span className="block text-[10px] uppercase font-bold text-slate-400">
                Open Flags
              </span>
              <span className="text-sm font-bold text-slate-900">{openFlagsCount}</span>
            </div>
            <div className="px-3 py-2 bg-white rounded-lg border border-red-200 shadow-sm text-center">
              <span className="block text-[10px] uppercase font-bold text-red-500">
                Critical
              </span>
              <span className="text-sm font-bold text-red-600">{criticalCount}</span>
            </div>
            <button
              onClick={fetchFlags}
              disabled={loadingFlags}
              className="px-3 py-2 text-xs font-semibold bg-white border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-700 transition shadow-sm"
            >
              {loadingFlags ? "Refreshing..." : "↻ Refresh"}
            </button>
          </div>
        </div>

        {/* Scan Trigger Bar */}
        <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <form onSubmit={handleRunScan} className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                Run Statistical Audit Scan
              </h2>
              <span className="text-[11px] text-slate-400">
                Rule-based + statistical detection engine (no LLM in arithmetic)
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="md:col-span-2">
                <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Target Entity UUID
                </label>
                <input
                  type="text"
                  value={entityIdInput}
                  onChange={(e) => setEntityIdInput(e.target.value)}
                  placeholder="Entity UUID"
                  className="w-full rounded-md border border-slate-300 p-2 text-xs font-mono text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Current Period
                </label>
                <input
                  type="text"
                  value={currentPeriodInput}
                  onChange={(e) => setCurrentPeriodInput(e.target.value)}
                  placeholder="e.g. 2025"
                  className="w-full rounded-md border border-slate-300 p-2 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Baseline Period (Optional)
                </label>
                <input
                  type="text"
                  value={baselinePeriodInput}
                  onChange={(e) => setBaselinePeriodInput(e.target.value)}
                  placeholder="e.g. 2024"
                  className="w-full rounded-md border border-slate-300 p-2 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>
            </div>

            {scanError && (
              <div className="p-3 rounded-lg bg-red-50 text-red-700 text-xs border border-red-200">
                {scanError}
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={scanning}
                className="px-5 py-2 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-500 transition shadow-sm disabled:opacity-50 flex items-center space-x-2"
              >
                {scanning ? (
                  <>
                    <svg className="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    <span>Executing Statistical Tests...</span>
                  </>
                ) : (
                  <span>Trigger Comprehensive Scan</span>
                )}
              </button>
            </div>
          </form>

          {/* Scan Summary Banner */}
          {scanSummary && (
            <div className="mt-4 pt-4 border-t border-slate-200 grid grid-cols-2 md:grid-cols-5 gap-3 bg-slate-50 p-3 rounded-lg text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Checked Lines</span>
                <span className="font-bold text-slate-800">{scanSummary.total_activity_lines_checked}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">YoY Discrepancies</span>
                <span className="font-bold text-amber-700">{scanSummary.yoy_flags_raised}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Intensity Outliers</span>
                <span className="font-bold text-purple-700">{scanSummary.intensity_flags_raised}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Scope Incomplete</span>
                <span className="font-bold text-red-700">{scanSummary.completeness_flags_raised}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">New Flags Created</span>
                <span className="font-bold text-emerald-700">{scanSummary.total_new_flags}</span>
              </div>
            </div>
          )}
        </section>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 space-x-6">
          <button
            onClick={() => setActiveTab("flags")}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition ${
              activeTab === "flags"
                ? "text-emerald-700 border-b-2 border-emerald-600"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Audit Flags & Anomaly Resolution ({flags.length})
          </button>
          <button
            onClick={() => setActiveTab("narrative")}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition ${
              activeTab === "narrative"
                ? "text-emerald-700 border-b-2 border-emerald-600"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Corporate Narrative Cross-Examiner
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === "flags" ? (
          <AnomalyDetectorView flags={flags} onFlagResolved={fetchFlags} />
        ) : (
          <NarrativeClaimChecker
            entityId={entityIdInput}
            reportingPeriod={currentPeriodInput}
            onScanTriggered={fetchFlags}
          />
        )}
      </main>
    </div>
  );
}
