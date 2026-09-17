"use client";

import React, { useEffect, useState } from "react";
import ReviewQueueTable, {
  ReviewQueueItem,
} from "../../components/ReviewQueueTable";

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/classification/queue");
      if (!res.ok) {
        throw new Error(`Failed to load queue: ${res.statusText}`);
      }
      const data = await res.json();
      setItems(data);
    } catch (err: any) {
      console.error("Queue fetch error:", err);
      setError(err.message || "Failed to load review queue.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleReviewSubmit = async (
    id: string,
    scope: number,
    ghgCategory: string,
    notes: string
  ) => {
    const res = await fetch(`/api/classification/review/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scope,
        ghg_category: ghgCategory,
        reviewer_id: "auditor_portal_user",
        notes,
      }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Failed to submit review");
    }

    // Remove from local pending queue
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  const lowConfidenceCount = items.filter(
    (i) =>
      i.classification_confidence !== null && i.classification_confidence < 0.75
  ).length;

  return (
    <main className="min-h-screen bg-slate-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                Classification Review Queue
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                Review and override activity items flagged for human verification (&lt; 75% confidence).
              </p>
            </div>
            <button
              onClick={fetchQueue}
              disabled={loading}
              className="bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium py-2 px-4 rounded-md shadow-sm transition-colors"
            >
              {loading ? "Refreshing..." : "Refresh Queue"}
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Pending Review
              </span>
              <div className="text-2xl font-bold text-slate-900 mt-1">
                {items.length}
              </div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Low Confidence (&lt; 75%)
              </span>
              <div className="text-2xl font-bold text-amber-600 mt-1">
                {lowConfidenceCount}
              </div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Classification Engine
              </span>
              <div className="text-sm font-semibold text-slate-700 mt-1 flex items-center space-x-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block"></span>
                <span>Groq Llama-3.3-70B / Fallback</span>
              </div>
            </div>
          </div>
        </header>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-lg border border-slate-200 p-12 text-center text-slate-400">
            Loading review queue...
          </div>
        ) : (
          <ReviewQueueTable items={items} onReviewSubmit={handleReviewSubmit} />
        )}
      </div>
    </main>
  );
}
