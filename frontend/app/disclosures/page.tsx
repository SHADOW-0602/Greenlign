"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import DisclosureEligibilityForm, {
  EntityEligibilityRequest,
} from "../../components/DisclosureEligibilityForm";
import DisclosureReportView, {
  DisclosureReportData,
} from "../../components/DisclosureReportView";

export default function DisclosuresPage() {
  const [disclosures, setDisclosures] = useState<DisclosureReportData[]>([]);
  const [selectedDisclosure, setSelectedDisclosure] =
    useState<DisclosureReportData | null>(null);
  const [loadingList, setLoadingList] = useState<boolean>(false);
  const [generating, setGenerating] = useState<boolean>(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [genSuccess, setGenSuccess] = useState<string | null>(null);

  // Form parameters for generation
  const [entityIdInput, setEntityIdInput] = useState<string>(
    "550e8400-e29b-41d4-a716-446655440000"
  );
  const [reportingPeriodInput, setReportingPeriodInput] = useState<string>("2025");
  const [selectedFramework, setSelectedFramework] = useState<string>("GHG_PROTOCOL");
  const [savedProfile, setSavedProfile] = useState<EntityEligibilityRequest | null>(
    null
  );

  const fetchDisclosures = async () => {
    setLoadingList(true);
    try {
      const res = await fetch("/api/disclosures");
      if (res.ok) {
        const data = await res.json();
        setDisclosures(data);
        if (data.length > 0 && !selectedDisclosure) {
          setSelectedDisclosure(data[0]);
        }
      }
    } catch (err) {
      console.error("Failed to load disclosures:", err);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    fetchDisclosures();
  }, []);

  const handleSelectFrameworkForGeneration = (
    framework: string,
    profile: EntityEligibilityRequest
  ) => {
    setSelectedFramework(framework);
    setSavedProfile(profile);
    setGenError(null);
    setGenSuccess(`Selected ${framework}. Review entity UUID & period, then click Generate.`);
  };

  const handleGenerateDisclosure = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!entityIdInput.trim()) {
      setGenError("Please provide a valid Entity UUID.");
      return;
    }

    setGenerating(true);
    setGenError(null);
    setGenSuccess(null);

    try {
      const payload: any = {
        entity_id: entityIdInput.trim(),
        framework: selectedFramework,
        reporting_period: reportingPeriodInput.trim(),
      };

      if (savedProfile) {
        payload.entity_profile = {
          annual_revenue_usd: savedProfile.annual_revenue_usd.toString(),
          does_business_in_california: Boolean(
            savedProfile.does_business_in_california
          ),
          eu_net_turnover_eur: savedProfile.eu_net_turnover_eur.toString(),
          balance_sheet_total_eur: savedProfile.balance_sheet_total_eur.toString(),
          employee_count: Number(savedProfile.employee_count),
          is_eu_parent: Boolean(savedProfile.is_eu_parent),
        };
      }

      const res = await fetch("/api/disclosures/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(
          errData.detail || `Generation failed with status code ${res.status}`
        );
      }

      const generatedData: DisclosureReportData = await res.json();
      setSelectedDisclosure(generatedData);
      setGenSuccess(
        `Successfully generated ${selectedFramework} disclosure report (${generatedData.total_tco2e} tCO2e)!`
      );
      fetchDisclosures();
    } catch (err: any) {
      console.error("Disclosure generation error:", err);
      setGenError(err.message || "Failed to generate disclosure report.");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-10">
        {/* Navigation & Header */}
        <header className="flex flex-col md:flex-row md:items-center md:justify-between border-b border-slate-200 pb-5 gap-4">
          <div>
            <div className="flex items-center space-x-2 text-sm text-slate-500 mb-1">
              <Link href="/" className="hover:text-emerald-600 transition">
                Greenlign
              </Link>
              <span>/</span>
              <span className="text-slate-900 font-medium">Disclosures</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Regulatory Disclosure Generator
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Statutory ESG reporting for California SB 253, EU CSRD (ESRS E1), and GHG Protocol Corporate Standard.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <Link
              href="/review"
              className="text-xs font-semibold px-3 py-2 rounded-md bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition"
            >
              Review Queue
            </Link>
            <Link
              href="/audit-trail"
              className="text-xs font-semibold px-3 py-2 rounded-md bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition"
            >
              Audit Trail
            </Link>
          </div>
        </header>

        {/* Section 1: Statutory Eligibility Evaluation */}
        <section>
          <DisclosureEligibilityForm
            onSelectFrameworkForGeneration={handleSelectFrameworkForGeneration}
          />
        </section>

        {/* Section 2: Generation Controls */}
        <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Generate Regulatory Disclosure Document
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Deterministically aggregate emissions calculations across Scopes 1, 2, and 3, apply framework citations, and produce an official audit-ready PDF report.
            </p>
          </div>

          <form onSubmit={handleGenerateDisclosure} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Reporting Framework
                </label>
                <select
                  value={selectedFramework}
                  onChange={(e) => setSelectedFramework(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none bg-white"
                >
                  <option value="GHG_PROTOCOL">GHG Protocol Corporate Standard</option>
                  <option value="CA_SB253">California SB 253 (Climate Data Act)</option>
                  <option value="CSRD_ESRS_E1">EU CSRD (ESRS E1 Climate)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Entity UUID
                </label>
                <input
                  type="text"
                  value={entityIdInput}
                  onChange={(e) => setEntityIdInput(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none font-mono"
                  placeholder="550e8400-e29b-41d4-a716-446655440000"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Reporting Period
                </label>
                <input
                  type="text"
                  value={reportingPeriodInput}
                  onChange={(e) => setReportingPeriodInput(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  placeholder="2025"
                  required
                />
              </div>
            </div>

            {genError && (
              <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
                <b>Error:</b> {genError}
              </div>
            )}

            {genSuccess && (
              <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm">
                {genSuccess}
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                disabled={generating}
                className="rounded-md bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:opacity-50 transition"
              >
                {generating ? "Aggregating & Generating..." : "Generate Disclosure & PDF"}
              </button>
            </div>
          </form>
        </section>

        {/* Section 3: Selected Disclosure Detail & Report Viewer */}
        {selectedDisclosure && (
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900">
              Active Disclosure Report Preview
            </h2>
            <DisclosureReportView disclosure={selectedDisclosure} />
          </section>
        )}

        {/* Section 4: Existing Generated Disclosures Table */}
        <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Generated Regulatory Disclosures
              </h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Archived statutory submissions with locked calculation snapshots.
              </p>
            </div>
            <button
              onClick={fetchDisclosures}
              className="text-xs font-semibold px-3 py-1.5 rounded border border-slate-200 text-slate-600 hover:bg-slate-50 transition"
            >
              Refresh
            </button>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Framework</th>
                  <th className="px-4 py-3">Period</th>
                  <th className="px-4 py-3 text-right">Total Emissions</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Entity ID</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {disclosures.map((d) => (
                  <tr
                    key={d.id}
                    className={`hover:bg-slate-50 transition cursor-pointer ${
                      selectedDisclosure?.id === d.id ? "bg-emerald-50/40" : ""
                    }`}
                    onClick={() => setSelectedDisclosure(d)}
                  >
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      {d.framework}
                    </td>
                    <td className="px-4 py-3 text-slate-600 font-medium">
                      {d.reporting_period}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-slate-900">
                      {Number(d.total_tco2e).toFixed(4)} tCO2e
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                        {d.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-slate-500">
                      {d.entity_id.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedDisclosure(d);
                        }}
                        className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 text-slate-700 hover:bg-slate-200 transition"
                      >
                        Inspect
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          window.open(`/api/disclosures/${d.id}/download-pdf`, "_blank");
                        }}
                        className="text-xs font-semibold px-2.5 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-500 transition"
                      >
                        PDF
                      </button>
                    </td>
                  </tr>
                ))}
                {disclosures.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-8 text-center text-slate-400"
                    >
                      {loadingList
                        ? "Loading disclosures..."
                        : "No disclosures generated yet. Check eligibility and generate above."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
