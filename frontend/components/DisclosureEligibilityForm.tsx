"use client";

import React, { useState } from "react";

export interface EntityEligibilityRequest {
  annual_revenue_usd: number | string;
  does_business_in_california: boolean;
  eu_net_turnover_eur: number | string;
  balance_sheet_total_eur: number | string;
  employee_count: number;
  is_eu_parent: boolean;
}

export interface FrameworkEligibilityStatus {
  framework: "CA_SB253" | "CSRD_ESRS_E1" | "GHG_PROTOCOL" | string;
  is_eligible: boolean;
  reason: string;
  mandatory_scopes: number[];
  reporting_deadline_notes?: string | null;
}

export interface EntityEligibilityResponse {
  ca_sb253: FrameworkEligibilityStatus;
  csrd_esrs_e1: FrameworkEligibilityStatus;
  ghg_protocol: FrameworkEligibilityStatus;
}

interface DisclosureEligibilityFormProps {
  onEligibilityChecked?: (results: EntityEligibilityResponse) => void;
  onSelectFrameworkForGeneration?: (
    framework: string,
    profile: EntityEligibilityRequest
  ) => void;
}

export default function DisclosureEligibilityForm({
  onEligibilityChecked,
  onSelectFrameworkForGeneration,
}: DisclosureEligibilityFormProps) {
  const [profile, setProfile] = useState<EntityEligibilityRequest>({
    annual_revenue_usd: "1200000000",
    does_business_in_california: true,
    eu_net_turnover_eur: "60000000",
    balance_sheet_total_eur: "30000000",
    employee_count: 350,
    is_eu_parent: true,
  });

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<EntityEligibilityResponse | null>(null);

  const handleCheckEligibility = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        annual_revenue_usd: profile.annual_revenue_usd.toString(),
        does_business_in_california: Boolean(profile.does_business_in_california),
        eu_net_turnover_eur: profile.eu_net_turnover_eur.toString(),
        balance_sheet_total_eur: profile.balance_sheet_total_eur.toString(),
        employee_count: Number(profile.employee_count),
        is_eu_parent: Boolean(profile.is_eu_parent),
      };

      const res = await fetch("/api/disclosures/check-eligibility", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Eligibility check failed (${res.status})`);
      }

      const data: EntityEligibilityResponse = await res.json();
      setResults(data);
      if (onEligibilityChecked) {
        onEligibilityChecked(data);
      }
    } catch (err: any) {
      console.error("Eligibility check error:", err);
      setError(err.message || "Failed to check eligibility");
    } finally {
      setLoading(false);
    }
  };

  const getFrameworkBadge = (frameworkStatus: FrameworkEligibilityStatus) => {
    if (frameworkStatus.is_eligible) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
          ✓ Mandatory / Eligible
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-300">
        ✕ Ineligible
      </span>
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-900">
          Corporate Statutory Reporting Eligibility Check
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          Evaluate entity operations against California SB 253, EU CSRD (ESRS E1), and GHG Protocol applicability thresholds.
        </p>
      </div>

      <form onSubmit={handleCheckEligibility} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Annual Revenue (USD)
            </label>
            <input
              type="text"
              value={profile.annual_revenue_usd}
              onChange={(e) =>
                setProfile({ ...profile, annual_revenue_usd: e.target.value })
              }
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              placeholder="1000000000"
              required
            />
            <span className="text-[11px] text-slate-400 mt-0.5 block">
              CA SB 253 threshold: &gt; $1,000,000,000
            </span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              EU Net Turnover (EUR)
            </label>
            <input
              type="text"
              value={profile.eu_net_turnover_eur}
              onChange={(e) =>
                setProfile({ ...profile, eu_net_turnover_eur: e.target.value })
              }
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              placeholder="50000000"
              required
            />
            <span className="text-[11px] text-slate-400 mt-0.5 block">
              CSRD large threshold: &gt; €50,000,000
            </span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              EU Balance Sheet Total (EUR)
            </label>
            <input
              type="text"
              value={profile.balance_sheet_total_eur}
              onChange={(e) =>
                setProfile({ ...profile, balance_sheet_total_eur: e.target.value })
              }
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              placeholder="25000000"
              required
            />
            <span className="text-[11px] text-slate-400 mt-0.5 block">
              CSRD large threshold: &gt; €25,000,000
            </span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Employee Count
            </label>
            <input
              type="number"
              value={profile.employee_count}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  employee_count: parseInt(e.target.value) || 0,
                })
              }
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              placeholder="250"
              required
            />
            <span className="text-[11px] text-slate-400 mt-0.5 block">
              CSRD threshold: &gt; 250 employees
            </span>
          </div>

          <div className="flex items-center space-x-3 pt-6">
            <input
              type="checkbox"
              id="ca_nexus"
              checked={profile.does_business_in_california}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  does_business_in_california: e.target.checked,
                })
              }
              className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
            />
            <label htmlFor="ca_nexus" className="text-sm font-medium text-slate-700">
              Conducts Business in California
            </label>
          </div>

          <div className="flex items-center space-x-3 pt-6">
            <input
              type="checkbox"
              id="eu_parent"
              checked={profile.is_eu_parent}
              onChange={(e) =>
                setProfile({ ...profile, is_eu_parent: e.target.checked })
              }
              className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
            />
            <label htmlFor="eu_parent" className="text-sm font-medium text-slate-700">
              EU Parent / Undertaking
            </label>
          </div>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:opacity-50 transition"
          >
            {loading ? "Checking Eligibility..." : "Evaluate Reporting Eligibility"}
          </button>
        </div>
      </form>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      {results && (
        <div className="mt-6 space-y-4 border-t border-slate-100 pt-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-800">
            Eligibility Determination Results
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* California SB 253 */}
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-slate-900 text-sm">
                    California SB 253
                  </h4>
                  {getFrameworkBadge(results.ca_sb253)}
                </div>
                <p className="text-xs text-slate-600 leading-relaxed mb-3">
                  {results.ca_sb253.reason}
                </p>
                {results.ca_sb253.reporting_deadline_notes && (
                  <p className="text-[11px] text-slate-500 italic">
                    {results.ca_sb253.reporting_deadline_notes}
                  </p>
                )}
              </div>
              {results.ca_sb253.is_eligible && onSelectFrameworkForGeneration && (
                <button
                  type="button"
                  onClick={() =>
                    onSelectFrameworkForGeneration("CA_SB253", profile)
                  }
                  className="mt-4 w-full text-xs font-semibold py-1.5 px-3 rounded bg-emerald-600 text-white hover:bg-emerald-500 transition"
                >
                  Select CA SB 253
                </button>
              )}
            </div>

            {/* EU CSRD ESRS E1 */}
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-slate-900 text-sm">
                    EU CSRD (ESRS E1)
                  </h4>
                  {getFrameworkBadge(results.csrd_esrs_e1)}
                </div>
                <p className="text-xs text-slate-600 leading-relaxed mb-3">
                  {results.csrd_esrs_e1.reason}
                </p>
                {results.csrd_esrs_e1.reporting_deadline_notes && (
                  <p className="text-[11px] text-slate-500 italic">
                    {results.csrd_esrs_e1.reporting_deadline_notes}
                  </p>
                )}
              </div>
              {results.csrd_esrs_e1.is_eligible && onSelectFrameworkForGeneration && (
                <button
                  type="button"
                  onClick={() =>
                    onSelectFrameworkForGeneration("CSRD_ESRS_E1", profile)
                  }
                  className="mt-4 w-full text-xs font-semibold py-1.5 px-3 rounded bg-emerald-600 text-white hover:bg-emerald-500 transition"
                >
                  Select CSRD ESRS E1
                </button>
              )}
            </div>

            {/* GHG Protocol */}
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-slate-900 text-sm">
                    GHG Protocol Corporate
                  </h4>
                  {getFrameworkBadge(results.ghg_protocol)}
                </div>
                <p className="text-xs text-slate-600 leading-relaxed mb-3">
                  {results.ghg_protocol.reason}
                </p>
                {results.ghg_protocol.reporting_deadline_notes && (
                  <p className="text-[11px] text-slate-500 italic">
                    {results.ghg_protocol.reporting_deadline_notes}
                  </p>
                )}
              </div>
              {results.ghg_protocol.is_eligible && onSelectFrameworkForGeneration && (
                <button
                  type="button"
                  onClick={() =>
                    onSelectFrameworkForGeneration("GHG_PROTOCOL", profile)
                  }
                  className="mt-4 w-full text-xs font-semibold py-1.5 px-3 rounded bg-emerald-600 text-white hover:bg-emerald-500 transition"
                >
                  Select GHG Protocol
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
