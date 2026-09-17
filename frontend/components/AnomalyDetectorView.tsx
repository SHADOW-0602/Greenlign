"use client";

import React, { useState } from "react";
import Link from "next/link";

export interface AnomalyFlagData {
  id: string;
  entity_id: string;
  reporting_period: string;
  flag_type: string;
  severity: "CRITICAL" | "WARNING" | "INFO" | string;
  title: string;
  description: string;
  status: "OPEN" | "CONFIRMED" | "DISMISSED" | string;
  details_json: Record<string, any>;
  resolution_notes?: string | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
  created_at: string;
}

interface AnomalyDetectorViewProps {
  flags: AnomalyFlagData[];
  onFlagResolved?: () => void;
}

export default function AnomalyDetectorView({
  flags,
  onFlagResolved,
}: AnomalyDetectorViewProps) {
  const [selectedFlag, setSelectedFlag] = useState<AnomalyFlagData | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [resolutionStatus, setResolutionStatus] = useState<"CONFIRMED" | "DISMISSED">("CONFIRMED");
  const [resolutionNotes, setResolutionNotes] = useState<string>("");
  const [resolving, setResolving] = useState<boolean>(false);
  const [resolveError, setResolveError] = useState<string | null>(null);

  const filteredFlags = flags.filter((f) => {
    if (statusFilter === "ALL") return true;
    return f.status === statusFilter;
  });

  const handleResolve = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFlag) return;
    if (resolutionNotes.trim().length < 5) {
      setResolveError("Please provide resolution rationale (minimum 5 characters).");
      return;
    }

    setResolving(true);
    setResolveError(null);

    try {
      const res = await fetch(`/api/anomalies/${selectedFlag.id}/resolve`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: resolutionStatus,
          notes: resolutionNotes.trim(),
          actor: "auditor",
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to resolve anomaly flag.");
      }

      setSelectedFlag(null);
      setResolutionNotes("");
      if (onFlagResolved) {
        onFlagResolved();
      }
    } catch (err: any) {
      console.error("Resolution error:", err);
      setResolveError(err.message || "Failed to resolve flag.");
    } finally {
      setResolving(false);
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
        return (
          <span className="px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-800 border border-red-200">
            CRITICAL
          </span>
        );
      case "WARNING":
        return (
          <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
            WARNING
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
            INFO
          </span>
        );
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CONFIRMED":
        return (
          <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-200">
            Confirmed Issue
          </span>
        );
      case "DISMISSED":
        return (
          <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200">
            Dismissed
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
            Open / Active
          </span>
        );
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-4 gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">
            Anomaly & Outlier Flags Ledger
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Statistical variance flags, $Z$-score intensity outliers, and scope omission alerts requiring auditor review.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-xs font-medium text-slate-500">Filter:</span>
          {["ALL", "OPEN", "CONFIRMED", "DISMISSED"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition ${
                statusFilter === st
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Anomaly Flags Table */}
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Title & Summary</th>
              <th className="px-4 py-3">Period</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            {filteredFlags.map((flag) => (
              <tr key={flag.id} className="hover:bg-slate-50 transition">
                <td className="px-4 py-3 whitespace-nowrap">
                  {getSeverityBadge(flag.severity)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap font-mono text-xs font-bold text-slate-700">
                  {flag.flag_type}
                </td>
                <td className="px-4 py-3 max-w-md">
                  <div className="font-semibold text-slate-900 text-xs">
                    {flag.title}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5 line-clamp-2">
                    {flag.description}
                  </div>
                  {flag.details_json?.calculation_id && (
                    <div className="mt-1">
                      <Link
                        href={`/audit-trail?id=${flag.details_json.calculation_id}`}
                        className="text-[11px] font-mono text-emerald-600 hover:underline"
                      >
                        Inspect Calculation: {flag.details_json.calculation_id.slice(0, 8)}...
                      </Link>
                    </div>
                  )}
                  {flag.resolution_notes && (
                    <div className="mt-1.5 p-1.5 rounded bg-slate-100 text-[11px] text-slate-700">
                      <span className="font-semibold">Auditor ({flag.resolved_by}):</span>{" "}
                      {flag.resolution_notes}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 whitespace-nowrap font-medium text-slate-700 text-xs">
                  {flag.reporting_period}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {getStatusBadge(flag.status)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  {flag.status === "OPEN" ? (
                    <button
                      onClick={() => {
                        setSelectedFlag(flag);
                        setResolutionNotes("");
                        setResolveError(null);
                      }}
                      className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 text-white hover:bg-emerald-500 transition"
                    >
                      Resolve
                    </button>
                  ) : (
                    <span className="text-xs text-slate-400">Resolved</span>
                  )}
                </td>
              </tr>
            ))}
            {filteredFlags.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                  No anomaly flags found for filter &quot;{statusFilter}&quot;.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Resolution Modal / Form */}
      {selectedFlag && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900">
                Resolve Anomaly Flag
              </h3>
              <button
                onClick={() => setSelectedFlag(null)}
                className="text-slate-400 hover:text-slate-600 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <div className="space-y-1">
              <span className="text-xs font-mono text-slate-400">
                Flag ID: {selectedFlag.id}
              </span>
              <h4 className="text-sm font-semibold text-slate-900">
                {selectedFlag.title}
              </h4>
              <p className="text-xs text-slate-600">{selectedFlag.description}</p>
            </div>

            <form onSubmit={handleResolve} className="space-y-4 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Resolution Decision
                </label>
                <div className="flex space-x-4">
                  <label className="flex items-center space-x-2 text-xs font-medium text-slate-800 cursor-pointer">
                    <input
                      type="radio"
                      name="decision"
                      value="CONFIRMED"
                      checked={resolutionStatus === "CONFIRMED"}
                      onChange={() => setResolutionStatus("CONFIRMED")}
                      className="text-red-600 focus:ring-red-500"
                    />
                    <span>Confirm as Genuine Anomaly / Error</span>
                  </label>
                  <label className="flex items-center space-x-2 text-xs font-medium text-slate-800 cursor-pointer">
                    <input
                      type="radio"
                      name="decision"
                      value="DISMISSED"
                      checked={resolutionStatus === "DISMISSED"}
                      onChange={() => setResolutionStatus("DISMISSED")}
                      className="text-slate-600 focus:ring-slate-500"
                    />
                    <span>Dismiss as False Positive</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Auditor Resolution Rationale
                </label>
                <textarea
                  rows={3}
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="Explain why this anomaly was confirmed or dismissed (e.g. verified with supplier invoice, facility shutdown, etc.)."
                  className="w-full rounded-md border border-slate-300 p-2.5 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  required
                />
              </div>

              {resolveError && (
                <div className="p-3 rounded bg-red-50 text-red-700 text-xs border border-red-200">
                  {resolveError}
                </div>
              )}

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedFlag(null)}
                  className="px-3 py-1.5 rounded-md text-xs font-semibold border border-slate-200 text-slate-600 hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={resolving}
                  className="px-4 py-1.5 rounded-md text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-500 transition disabled:opacity-50"
                >
                  {resolving ? "Recording Decision..." : "Submit Resolution"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
