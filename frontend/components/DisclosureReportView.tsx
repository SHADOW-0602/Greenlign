"use client";

import React from "react";
import Link from "next/link";

export interface CategorySummary {
  ghg_category: string;
  scope: number;
  total_tco2e: number | string;
  line_item_count: number;
  calculation_ids: string[];
}

export interface ScopeSummary {
  scope: number;
  total_tco2e: number | string;
  categories: CategorySummary[];
}

export interface DisclosureReportData {
  id: string;
  entity_id: string;
  framework: string;
  reporting_period: string;
  status: string;
  generated_document_ref?: string | null;
  total_tco2e: number | string;
  scope_1_tco2e: number | string;
  scope_2_tco2e: number | string;
  scope_3_tco2e: number | string;
  scope_breakdown: ScopeSummary[];
  line_item_refs: string[];
  created_at?: string;
}

interface DisclosureReportViewProps {
  disclosure: DisclosureReportData;
}

export default function DisclosureReportView({ disclosure }: DisclosureReportViewProps) {
  const total = Number(disclosure.total_tco2e) || 0;
  const s1 = Number(disclosure.scope_1_tco2e) || 0;
  const s2 = Number(disclosure.scope_2_tco2e) || 0;
  const s3 = Number(disclosure.scope_3_tco2e) || 0;

  const s1Pct = total > 0 ? ((s1 / total) * 100).toFixed(1) : "0.0";
  const s2Pct = total > 0 ? ((s2 / total) * 100).toFixed(1) : "0.0";
  const s3Pct = total > 0 ? ((s3 / total) * 100).toFixed(1) : "0.0";

  const frameworkNames: Record<string, string> = {
    CA_SB253: "California Senate Bill 253 (Climate Corporate Data Accountability Act)",
    CSRD_ESRS_E1: "EU Corporate Sustainability Reporting Directive — ESRS E1 Climate Change",
    GHG_PROTOCOL: "GHG Protocol Corporate Accounting and Reporting Standard",
  };

  const handleDownloadPDF = () => {
    window.open(`/api/disclosures/${disclosure.id}/download-pdf`, "_blank");
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
      {/* Report Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-100 pb-5 gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
              {disclosure.status}
            </span>
            <span className="text-xs font-mono text-slate-400">
              ID: {disclosure.id}
            </span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-2">
            {frameworkNames[disclosure.framework] || disclosure.framework}
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Reporting Entity: <span className="font-mono text-slate-700">{disclosure.entity_id}</span> | Period: <span className="font-semibold text-slate-700">{disclosure.reporting_period}</span>
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleDownloadPDF}
            className="inline-flex items-center rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 transition"
          >
            <svg
              className="mr-2 -ml-1 h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            Download Statutory PDF Report
          </button>
        </div>
      </div>

      {/* Executive Summary Metrics */}
      <div>
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-3">
          1. Executive Emissions Summary
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg bg-emerald-50/50 border border-emerald-200">
            <span className="text-xs font-medium text-emerald-800">Total Gross Emissions</span>
            <div className="mt-1 text-2xl font-bold text-emerald-950 font-mono">
              {total.toFixed(4)} <span className="text-sm font-normal text-emerald-700">tCO2e</span>
            </div>
            <span className="text-[11px] text-emerald-600">100.0% of inventory</span>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-xs font-medium text-slate-600">Scope 1 (Direct)</span>
            <div className="mt-1 text-2xl font-bold text-slate-900 font-mono">
              {s1.toFixed(4)} <span className="text-sm font-normal text-slate-500">tCO2e</span>
            </div>
            <span className="text-[11px] text-slate-500">{s1Pct}% of total</span>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-xs font-medium text-slate-600">Scope 2 (Energy Indirect)</span>
            <div className="mt-1 text-2xl font-bold text-slate-900 font-mono">
              {s2.toFixed(4)} <span className="text-sm font-normal text-slate-500">tCO2e</span>
            </div>
            <span className="text-[11px] text-slate-500">{s2Pct}% of total</span>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
            <span className="text-xs font-medium text-slate-600">Scope 3 (Value Chain)</span>
            <div className="mt-1 text-2xl font-bold text-slate-900 font-mono">
              {s3.toFixed(4)} <span className="text-sm font-normal text-slate-500">tCO2e</span>
            </div>
            <span className="text-[11px] text-slate-500">{s3Pct}% of total</span>
          </div>
        </div>
      </div>

      {/* Scope and Category Breakdown Table */}
      <div>
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-3">
          2. Scope & Category Breakdown with Calculation Citations
        </h3>
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Scope</th>
                <th className="px-4 py-3 text-right">Emissions (tCO2e)</th>
                <th className="px-4 py-3 text-right">Items</th>
                <th className="px-4 py-3">Audit Citations (Calculation ID)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {disclosure.scope_breakdown.flatMap((sc) =>
                sc.categories.map((cat, idx) => (
                  <tr key={`${sc.scope}-${cat.ghg_category}-${idx}`} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {cat.ghg_category}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
                        Scope {cat.scope}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-medium text-slate-900">
                      {Number(cat.total_tco2e).toFixed(4)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-600">
                      {cat.line_item_count}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1.5 max-w-md">
                        {cat.calculation_ids.slice(0, 3).map((cid) => (
                          <Link
                            key={cid}
                            href={`/audit-trail?id=${cid}`}
                            className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition"
                            title={`Inspect Calculation ${cid}`}
                          >
                            {cid.slice(0, 8)}...
                          </Link>
                        ))}
                        {cat.calculation_ids.length > 3 && (
                          <span className="text-[11px] text-slate-400 self-center">
                            +{cat.calculation_ids.length - 3} more
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
              {disclosure.scope_breakdown.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-slate-400">
                    No category breakdown available for this disclosure.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Regulatory Attestation Notice */}
      <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1">
        <div className="font-semibold text-slate-800 flex items-center gap-1.5">
          <svg className="h-4 w-4 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          Audit Provenance & Cryptographic Assurance
        </div>
        <p>
          All emissions quantities are computed via pure deterministic Decimal arithmetic without generative AI approximation in final results. Supporting calculations are cryptographically indexed with sha256 file references and protected against cascading deletion.
        </p>
      </div>
    </div>
  );
}
