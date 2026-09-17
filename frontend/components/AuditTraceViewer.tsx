"use client";

import React from "react";

export interface AuditSourceDocument {
  id: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  file_hash_sha256: string;
  storage_path: string;
  created_at: string;
}

export interface AuditActivityData {
  id: string;
  raw_line_ref: string;
  supplier_ref: string;
  activity_type: string;
  quantity: string | number;
  unit: string;
  geography: string;
  period_start: string;
  period_end: string;
  scope?: number | null;
  ghg_category?: string | null;
  classification_confidence?: number | null;
  status: string;
}

export interface AuditEmissionFactor {
  id: string;
  source: string;
  source_version: string;
  activity_type: string;
  geography: string;
  unit: string;
  factor_value: string | number;
  factor_unit: string;
  published_date: string;
  effective_from: string;
  effective_to?: string | null;
}

export interface AuditCalculation {
  id: string;
  activity_data_id: string;
  emission_factor_id: string;
  formula_applied: string;
  result_tco2e: string | number;
  computed_by: string;
  computed_at: string;
}

export interface AuditLogEvent {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor: string;
  timestamp: string;
  detail: Record<string, any>;
}

export interface AuditDisclosure {
  id: string;
  framework: string;
  reporting_period: string;
  status: string;
}

export interface AuditTraceData {
  calculation: AuditCalculation;
  activity: AuditActivityData;
  source_document?: AuditSourceDocument | null;
  emission_factor: AuditEmissionFactor;
  audit_events: AuditLogEvent[];
  linked_disclosures: AuditDisclosure[];
}

interface AuditTraceViewerProps {
  trace: AuditTraceData;
}

export default function AuditTraceViewer({ trace }: AuditTraceViewerProps) {
  const {
    calculation,
    activity,
    source_document,
    emission_factor,
    audit_events,
    linked_disclosures,
  } = trace;

  return (
    <div className="space-y-8">
      {/* Overview Banner */}
      <div className="bg-emerald-900 text-white p-6 rounded-xl shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-300">
              End-to-End Audit Provenance Trace
            </span>
            <h2 className="text-2xl font-bold mt-1">
              {calculation.result_tco2e} tCO2e
            </h2>
            <p className="text-sm text-emerald-200 mt-1 font-mono">
              {calculation.formula_applied}
            </p>
          </div>
          <div className="bg-emerald-800/80 px-4 py-3 rounded-lg border border-emerald-700/50">
            <div className="text-xs text-emerald-300">Calculation ID</div>
            <div className="font-mono text-xs text-white truncate max-w-xs mt-0.5">
              {calculation.id}
            </div>
            <div className="text-xs text-emerald-300 mt-2">Computed By / At</div>
            <div className="text-xs text-white font-medium">
              {calculation.computed_by} • {new Date(calculation.computed_at).toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* Provenance Chain Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Step 1: Raw Document */}
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                1. Source Document
              </span>
              <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                {source_document?.file_type?.toUpperCase() || "N/A"}
              </span>
            </div>
            {source_document ? (
              <div className="mt-3 space-y-2">
                <div className="text-sm font-semibold text-slate-900 truncate" title={source_document.filename}>
                  {source_document.filename}
                </div>
                <div>
                  <span className="text-xs text-slate-500">SHA-256 Hash:</span>
                  <div className="font-mono text-xs bg-slate-50 p-1.5 rounded border border-slate-200 text-slate-700 break-all select-all">
                    {source_document.file_hash_sha256}
                  </div>
                </div>
                <div className="text-xs text-slate-500">
                  Size: {(source_document.file_size_bytes / 1024).toFixed(1)} KB
                </div>
              </div>
            ) : (
              <div className="mt-4 text-xs text-slate-400 italic">
                Direct ERP Line Entry (no file uploaded)
              </div>
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-400">
            Storage: {source_document?.storage_path || "Direct Database"}
          </div>
        </div>

        {/* Step 2: Activity Data */}
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                2. Normalized Activity
              </span>
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-semibold">
                Scope {activity.scope || "?"}
              </span>
            </div>
            <div className="mt-3 space-y-2">
              <div className="text-sm font-semibold text-slate-900">
                {activity.quantity} {activity.unit}
              </div>
              <div className="text-xs text-slate-600">
                Type: <span className="font-medium text-slate-800">{activity.activity_type}</span>
              </div>
              <div className="text-xs text-slate-600">
                Category: <span className="font-medium text-slate-800">{activity.ghg_category || "Uncategorized"}</span>
              </div>
              <div>
                <span className="text-xs text-slate-500">Tokenized Supplier:</span>
                <div className="font-mono text-xs bg-slate-50 p-1 rounded border border-slate-200 text-slate-700">
                  {activity.supplier_ref}
                </div>
              </div>
              <div className="text-xs text-slate-500">
                Period: {activity.period_start} to {activity.period_end} ({activity.geography})
              </div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-400">
            Source Ref: {activity.raw_line_ref}
          </div>
        </div>

        {/* Step 3: Emission Factor */}
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                3. Matched Factor
              </span>
              <span className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded font-semibold">
                {emission_factor.source}
              </span>
            </div>
            <div className="mt-3 space-y-2">
              <div className="text-sm font-semibold text-slate-900">
                {emission_factor.factor_value} {emission_factor.factor_unit}
              </div>
              <div className="text-xs text-slate-600">
                Version: <span className="font-medium text-slate-800">{emission_factor.source_version}</span>
              </div>
              <div className="text-xs text-slate-600">
                Geography: <span className="font-medium text-slate-800">{emission_factor.geography}</span>
              </div>
              <div className="text-xs text-slate-500">
                Effective: {emission_factor.effective_from} to {emission_factor.effective_to || "Indefinite"}
              </div>
              <div className="text-xs text-slate-500">
                Published: {emission_factor.published_date}
              </div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-400 font-mono truncate">
            Factor ID: {emission_factor.id}
          </div>
        </div>
      </div>

      {/* Linked Disclosures (Referential Guard) */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
          Linked Regulatory Disclosures (Referential Integrity Guard)
        </h3>
        {linked_disclosures && linked_disclosures.length > 0 ? (
          <div className="divide-y divide-slate-100">
            {linked_disclosures.map((d) => (
              <div key={d.id} className="py-2.5 flex items-center justify-between text-sm">
                <div>
                  <span className="font-semibold text-slate-900">{d.framework}</span>
                  <span className="text-slate-500 ml-2">Period: {d.reporting_period}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                    Deletion Blocked
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                    {d.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500">
            This calculation is not currently referenced by any filed disclosure (deletion is allowed if permitted by auditor role).
          </p>
        )}
      </div>

      {/* Chronological Audit Log History */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4">
          Audit Event History
        </h3>
        <div className="space-y-4">
          {audit_events.map((event, idx) => (
            <div key={event.id || idx} className="flex items-start space-x-3 text-sm">
              <div className="h-2 w-2 rounded-full bg-slate-400 mt-2"></div>
              <div className="flex-1 bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-slate-900">
                    {event.action}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    {new Date(event.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  Actor: <span className="font-medium text-slate-700">{event.actor}</span> • Target: {event.entity_type}
                </div>
                {event.detail && Object.keys(event.detail).length > 0 && (
                  <pre className="mt-2 text-xs bg-white p-2 rounded border border-slate-200 text-slate-600 font-mono overflow-x-auto">
                    {JSON.stringify(event.detail, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
