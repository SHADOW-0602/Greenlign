"use client";

import React from "react";
import Link from "next/link";

export interface ScopeMetric {
  scope: number;
  total_tco2e: number;
  share_percentage: number;
}

export interface CategoryHotspot {
  ghg_category: string;
  scope: number;
  total_tco2e: number;
  share_percentage: number;
  activity_count: number;
}

export interface PeriodicTrendPoint {
  reporting_period: string;
  scope1_tco2e: number;
  scope2_tco2e: number;
  scope3_tco2e: number;
  total_tco2e: number;
}

export interface DashboardSummaryData {
  entity_id: string;
  reporting_period: string;
  gross_emissions_tco2e: number;
  scope_breakdown: ScopeMetric[];
  top_hotspots: CategoryHotspot[];
  historical_trends: PeriodicTrendPoint[];
  total_calculations: number;
  open_anomalies_count: number;
  critical_anomalies_count: number;
}

interface DashboardViewProps {
  data: DashboardSummaryData;
}

export default function DashboardView({ data }: DashboardViewProps) {
  const getScopeColor = (scope: number) => {
    switch (scope) {
      case 1:
        return {
          bg: "bg-blue-500",
          text: "text-blue-700",
          border: "border-blue-200",
          light: "bg-blue-50",
        };
      case 2:
        return {
          bg: "bg-emerald-500",
          text: "text-emerald-700",
          border: "border-emerald-200",
          light: "bg-emerald-50",
        };
      case 3:
      default:
        return {
          bg: "bg-purple-500",
          text: "text-purple-700",
          border: "border-purple-200",
          light: "bg-purple-50",
        };
    }
  };

  return (
    <div className="space-y-8">
      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <span className="text-[11px] uppercase font-bold text-slate-400 block tracking-wider">
            Gross Emissions
          </span>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-slate-900 font-mono">
              {data.gross_emissions_tco2e.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </span>
            <span className="text-xs font-semibold text-slate-500">tCO₂e</span>
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block">
            {data.total_calculations} audited calculations in FY{data.reporting_period}
          </span>
        </div>

        {data.scope_breakdown.map((s) => {
          const colors = getScopeColor(s.scope);
          return (
            <div
              key={s.scope}
              className={`rounded-xl shadow-sm border ${colors.border} ${colors.light} p-5`}
            >
              <div className="flex items-center justify-between">
                <span className={`text-[11px] uppercase font-bold ${colors.text} tracking-wider`}>
                  Scope {s.scope}
                </span>
                <span className="text-xs font-bold text-slate-600 font-mono">
                  {s.share_percentage.toFixed(1)}%
                </span>
              </div>
              <div className="mt-2 flex items-baseline space-x-1">
                <span className="text-2xl font-black text-slate-900 font-mono">
                  {s.total_tco2e.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </span>
                <span className="text-xs font-semibold text-slate-500">tCO₂e</span>
              </div>
              {/* Progress bar */}
              <div className="w-full bg-slate-200/80 rounded-full h-1.5 mt-3 overflow-hidden">
                <div
                  className={`h-1.5 rounded-full ${colors.bg}`}
                  style={{ width: `${Math.min(s.share_percentage, 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Anomaly Alerts Banner if active */}
      {data.open_anomalies_count > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-xl">⚠️</span>
            <div>
              <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider">
                Auditor Attention Required ({data.open_anomalies_count} Open Flags)
              </h4>
              <p className="text-xs text-amber-700 mt-0.5">
                {data.critical_anomalies_count} critical statistical anomaly flags pending human verification.
              </p>
            </div>
          </div>
          <Link
            href="/anomalies"
            className="px-4 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold shadow-sm transition"
          >
            Review Anomaly Flags →
          </Link>
        </div>
      )}

      {/* Hotspots & Emissions Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Top Emission Hotspots Table */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Top Carbon Emission Hotspots
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Highest contributing GHG categories ranked by absolute footprint.
              </p>
            </div>
            <span className="text-xs font-semibold text-slate-400">
              Top {data.top_hotspots.length} categories
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-y border-slate-200 text-slate-600 uppercase font-bold text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">GHG Category</th>
                  <th className="py-2.5 px-3">Scope</th>
                  <th className="py-2.5 px-3 text-right">Emissions (tCO₂e)</th>
                  <th className="py-2.5 px-3 text-right">Share</th>
                  <th className="py-2.5 px-3 text-right">Activity Lines</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-sans">
                {data.top_hotspots.map((h, i) => {
                  const colors = getScopeColor(h.scope);
                  return (
                    <tr key={i} className="hover:bg-slate-50/50 transition">
                      <td className="py-3 px-3 font-semibold text-slate-800">
                        {h.ghg_category}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border ${colors.border} ${colors.light} ${colors.text}`}
                        >
                          Scope {h.scope}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right font-mono font-bold text-slate-900">
                        {h.total_tco2e.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </td>
                      <td className="py-3 px-3 text-right font-mono font-semibold text-slate-600">
                        {h.share_percentage.toFixed(1)}%
                      </td>
                      <td className="py-3 px-3 text-right font-mono text-slate-400">
                        {h.activity_count}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Scope Distribution Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-5 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Scope Composition
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Proportionate carbon intensity distribution.
            </p>

            <div className="mt-6 space-y-4">
              {data.scope_breakdown.map((s) => {
                const colors = getScopeColor(s.scope);
                return (
                  <div key={s.scope} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className={colors.text}>Scope {s.scope}</span>
                      <span className="font-mono text-slate-800">
                        {s.share_percentage.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-2 rounded-full ${colors.bg}`}
                        style={{ width: `${Math.min(s.share_percentage, 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="bg-slate-50 rounded-lg p-4 border border-slate-200 text-xs space-y-2">
            <span className="font-bold text-slate-800 block text-[11px] uppercase tracking-wider">
              Strategic Levers
            </span>
            <p className="text-slate-600 text-[11px]">
              Ready to evaluate emissions abatement scenarios and calculate Marginal Abatement Costs?
            </p>
            <Link
              href="/simulator"
              className="inline-block text-emerald-600 hover:text-emerald-700 font-bold text-xs pt-1"
            >
              Open Scenario Simulator →
            </Link>
          </div>
        </div>
      </div>

      {/* Multi-Year Emissions Trajectory */}
      {data.historical_trends.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Emissions Trajectory by Reporting Period
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Audited multi-year emissions trends across Scopes 1, 2, and 3.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-y border-slate-200 text-slate-600 uppercase font-bold text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Period</th>
                  <th className="py-2.5 px-3 text-right">Scope 1 (tCO₂e)</th>
                  <th className="py-2.5 px-3 text-right">Scope 2 (tCO₂e)</th>
                  <th className="py-2.5 px-3 text-right">Scope 3 (tCO₂e)</th>
                  <th className="py-2.5 px-3 text-right font-black">Gross Total (tCO₂e)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {data.historical_trends.map((p) => (
                  <tr key={p.reporting_period} className="hover:bg-slate-50/50 transition">
                    <td className="py-3 px-3 font-sans font-bold text-slate-800">
                      FY{p.reporting_period}
                    </td>
                    <td className="py-3 px-3 text-right text-blue-700">
                      {p.scope1_tco2e.toFixed(2)}
                    </td>
                    <td className="py-3 px-3 text-right text-emerald-700">
                      {p.scope2_tco2e.toFixed(2)}
                    </td>
                    <td className="py-3 px-3 text-right text-purple-700">
                      {p.scope3_tco2e.toFixed(2)}
                    </td>
                    <td className="py-3 px-3 text-right font-bold text-slate-900">
                      {p.total_tco2e.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
