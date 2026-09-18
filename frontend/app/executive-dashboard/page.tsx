"use client";

import React from "react";
import Link from "next/link";

export default function ExecutiveDashboardPage() {
  return (
    <div className="min-h-screen bg-[#090D16] text-[#DFE2F2] flex flex-col">
      {/* Top Banner */}
      <header className="bg-[#0D111C]/90 border-b border-[#1E293B] px-6 py-3 flex items-center justify-between z-30 sticky top-0 backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <span className="text-xl font-bold bg-gradient-to-r from-[#10B981] to-[#34D399] bg-clip-text text-transparent">
            Greenlign
          </span>
          <span className="text-[#64748B]">|</span>
          <span className="text-xs font-mono uppercase tracking-wider text-[#34D399] bg-[#10B981]/10 px-2 py-0.5 rounded border border-[#10B981]/30">
            Stitch Executive UI
          </span>
        </div>

        <div className="flex items-center space-x-4 text-xs font-medium">
          <Link
            href="/"
            className="text-[#94A3B8] hover:text-[#F8FAFC] transition flex items-center gap-1"
          >
            &larr; Back to Overview
          </Link>
          <a
            href="/stitch_dashboard.html"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 rounded bg-[#10B981] text-[#090D16] font-semibold hover:bg-[#34D399] transition shadow-[0_0_15px_rgba(16,185,129,0.3)]"
          >
            Open Standalone Tab &nearr;
          </a>
        </div>
      </header>

      {/* Embedded Stitch Dashboard Frame */}
      <main className="flex-1 w-full">
        <iframe
          src="/stitch_dashboard.html"
          title="Greenlign Executive ESG Dashboard"
          className="w-full h-screen border-none"
        />
      </main>
    </div>
  );
}
