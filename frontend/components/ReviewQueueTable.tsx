"use client";

import React, { useState } from "react";

export interface ReviewQueueItem {
  id: string;
  entity_id: string;
  source_document_id?: string;
  raw_line_ref: string;
  activity_type: string;
  quantity: string | number;
  unit: string;
  geography: string;
  supplier_ref: string;
  scope: number | null;
  ghg_category: string | null;
  classification_confidence: number | null;
  status: string;
}

const CATEGORIES_BY_SCOPE: Record<number, string[]> = {
  1: [
    "stationary_combustion",
    "mobile_combustion",
    "process_emissions",
    "fugitive_emissions",
  ],
  2: [
    "purchased_electricity",
    "purchased_steam",
    "purchased_heating",
    "purchased_cooling",
  ],
  3: [
    "purchased_goods_services",
    "capital_goods",
    "fuel_and_energy_related_activities",
    "upstream_transportation_distribution",
    "waste_generated_in_operations",
    "business_travel",
    "employee_commuting",
    "upstream_leased_assets",
    "downstream_transportation_distribution",
    "processing_of_sold_products",
    "use_of_sold_products",
    "end_of_life_treatment_of_sold_products",
    "downstream_leased_assets",
    "franchises",
    "investments",
  ],
};

interface ReviewRowProps {
  item: ReviewQueueItem;
  onReviewSubmit: (
    id: string,
    scope: number,
    ghgCategory: string,
    notes: string
  ) => Promise<void>;
}

function ReviewRow({ item, onReviewSubmit }: ReviewRowProps) {
  const [scope, setScope] = useState<number>(item.scope || 3);
  const [ghgCategory, setGhgCategory] = useState<string>(
    item.ghg_category || CATEGORIES_BY_SCOPE[item.scope || 3][0]
  );
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitted, setSubmitted] = useState<boolean>(false);

  const handleScopeChange = (newScope: number) => {
    setScope(newScope);
    const available = CATEGORIES_BY_SCOPE[newScope];
    if (!available.includes(ghgCategory)) {
      setGhgCategory(available[0]);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onReviewSubmit(item.id, scope, ghgCategory, notes);
      setSubmitted(true);
    } catch (err) {
      console.error("Failed to submit review:", err);
      alert("Failed to submit review. See console for details.");
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <tr className="bg-emerald-50 text-emerald-900 border-b border-emerald-200">
        <td colSpan={7} className="px-4 py-3 text-sm font-medium">
          &#10003; Activity {item.raw_line_ref} classified as Scope {scope} ({ghgCategory})
        </td>
      </tr>
    );
  }

  const confidencePct =
    item.classification_confidence !== null
      ? Math.round(item.classification_confidence * 100)
      : null;

  return (
    <tr className="border-b hover:bg-slate-50 transition-colors">
      <td className="px-4 py-3 text-sm font-mono text-slate-600">
        {item.raw_line_ref}
      </td>
      <td className="px-4 py-3 text-sm font-medium text-slate-900">
        {item.activity_type}
        <div className="text-xs text-slate-400 font-mono mt-0.5">
          {item.supplier_ref}
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-slate-700">
        {item.quantity} <span className="text-slate-500 text-xs">{item.unit}</span>
      </td>
      <td className="px-4 py-3 text-sm">
        {confidencePct !== null ? (
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
              confidencePct >= 75
                ? "bg-emerald-100 text-emerald-800"
                : "bg-amber-100 text-amber-800"
            }`}
          >
            {confidencePct}%
          </span>
        ) : (
          <span className="text-xs text-slate-400">N/A</span>
        )}
      </td>
      <td className="px-4 py-3 text-sm">
        <div className="flex space-x-2">
          <select
            value={scope}
            onChange={(e) => handleScopeChange(Number(e.target.value))}
            className="rounded border-slate-300 text-sm py-1 px-2 focus:ring-emerald-500 focus:border-emerald-500 border bg-white"
          >
            <option value={1}>Scope 1</option>
            <option value={2}>Scope 2</option>
            <option value={3}>Scope 3</option>
          </select>
          <select
            value={ghgCategory}
            onChange={(e) => setGhgCategory(e.target.value)}
            className="rounded border-slate-300 text-sm py-1 px-2 focus:ring-emerald-500 focus:border-emerald-500 border bg-white max-w-[220px]"
          >
            {CATEGORIES_BY_SCOPE[scope].map((cat) => (
              <option key={cat} value={cat}>
                {cat.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
      </td>
      <td className="px-4 py-3 text-sm">
        <input
          type="text"
          placeholder="Notes (optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="rounded border-slate-300 text-sm py-1 px-2 w-full border focus:ring-emerald-500 focus:border-emerald-500"
        />
      </td>
      <td className="px-4 py-3 text-sm text-right">
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-medium py-1 px-3 rounded text-sm transition-colors shadow-sm"
        >
          {submitting ? "Saving..." : "Approve"}
        </button>
      </td>
    </tr>
  );
}

interface ReviewQueueTableProps {
  items: ReviewQueueItem[];
  onReviewSubmit: (
    id: string,
    scope: number,
    ghgCategory: string,
    notes: string
  ) => Promise<void>;
}

export default function ReviewQueueTable({
  items,
  onReviewSubmit,
}: ReviewQueueTableProps) {
  if (items.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-8 text-center text-slate-500">
        No pending items in the classification review queue.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto bg-white rounded-lg border border-slate-200 shadow-sm">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
          <tr>
            <th className="px-4 py-3">Line Ref</th>
            <th className="px-4 py-3">Activity / Supplier</th>
            <th className="px-4 py-3">Quantity</th>
            <th className="px-4 py-3">Confidence</th>
            <th className="px-4 py-3">Scope & Category</th>
            <th className="px-4 py-3">Notes</th>
            <th className="px-4 py-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white">
          {items.map((item) => (
            <ReviewRow
              key={item.id}
              item={item}
              onReviewSubmit={onReviewSubmit}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
