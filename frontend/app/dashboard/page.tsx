"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import DashboardView, { DashboardSummaryData } from "../../components/DashboardView";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummaryData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [entityId, setEntityId] = useState<string>(
    "550e8400-e29b-41d4-a716-446655440000"
  );
  const [period, setPeriod] = useState<string>("2025");

  const fetchDashboardData = async () => {
    if (!entityId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/dashboard/summary?entity_id=${encodeURIComponent(
          entityId.trim()
        )}&reporting_period=${encodeURIComponent(period.trim())}`
      );
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned ${res.status}`);
      }
      const json: DashboardSummaryData = await res.json();
      setData(json);
    } catch (err: any) {
      console.error("Dashboard fetch error:", err);
      setError(err.message || "Failed to load dashboard summary.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

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
              Executive ESG Intelligence
            </span>
          </div>

          <nav className="flex space-x-4 text-xs font-medium">
            <Link href="/" className="text-slate-600 hover:text-slate-900">
              Overview
            </Link>
            <Link
              href="/dashboard"
              className="text-emerald-700 font-bold border-b-2 border-emerald-600 pb-1"
            >
              Dashboard
            </Link>
            <Link href="/simulator" className="text-slate-600 hover:text-slate-900">
              Scenario Simulator
            </Link>
            <Link href="/supplier-outreach" className="text-slate-600 hover:text-slate-900">
              Supplier Outreach
            </Link>
            <Link href="/disclosures" className="text-slate-600 hover:text-slate-900">
              Disclosures
            </Link>
            <Link href="/anomalies" className="text-slate-600 hover:text-slate-900">
              Anomalies
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-6">
        {/* Entity & Filter Selector Bar */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              Corporate Carbon Intelligence Dashboard
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Verified deterministic emissions ledger, statutory scope breakdowns, and hotspots.
            </p>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              fetchDashboardData();
            }}
            className="flex items-center space-x-3"
          >
            <input
              type="text"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              placeholder="Entity UUID"
              className="w-64 rounded-md border border-slate-300 p-2 text-xs font-mono text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              required
            />
            <input
              type="text"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              placeholder="Period"
              className="w-24 rounded-md border border-slate-300 p-2 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              required
            />
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-md text-xs font-semibold shadow-sm transition disabled:opacity-50"
            >
              {loading ? "Refreshing..." : "Load Data"}
            </button>
          </form>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-50 text-red-700 text-xs border border-red-200">
            {error}
          </div>
        )}

        {loading ? (
          <div className="p-16 text-center text-xs text-slate-400 bg-white rounded-xl border border-slate-200">
            Loading corporate emissions telemetry...
          </div>
        ) : data ? (
          <DashboardView data={data} />
        ) : (
          <div className="p-16 text-center text-xs text-slate-400 bg-white rounded-xl border border-slate-200">
            No emissions calculations found for this entity and period.
          </div>
        )}
      </main>
    </div>
  );
}
