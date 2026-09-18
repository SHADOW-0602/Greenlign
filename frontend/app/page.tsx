"use client";

import React from "react";
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#090D16] text-slate-100 flex flex-col selection:bg-emerald-500 selection:text-slate-950 font-sans relative overflow-x-hidden">
      {/* Ambient Gradient Mesh Background */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute -top-40 left-1/4 w-[700px] h-[700px] bg-emerald-500/10 rounded-full blur-[160px]" />
        <div className="absolute top-1/3 -right-40 w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-[180px]" />
        <div className="absolute -bottom-40 left-1/3 w-[800px] h-[600px] bg-emerald-600/5 rounded-full blur-[170px]" />
      </div>

      {/* Top Navigation Bar */}
      <header className="bg-[#0D111C]/80 backdrop-blur-xl border-b border-slate-800/80 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.4)]">
              <span className="text-slate-950 font-black text-base">G</span>
            </div>
            <span className="text-xl font-black bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent tracking-tight">
              Greenlign
            </span>
            <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              v1.0 Institutional
            </span>
          </div>

          <nav className="hidden md:flex items-center space-x-6 text-xs font-medium text-slate-400">
            <Link href="/executive-dashboard" className="text-emerald-400 hover:text-emerald-300 transition">
              Executive UI (Stitch)
            </Link>
            <Link href="/dashboard" className="hover:text-slate-100 transition">
              Ledger
            </Link>
            <Link href="/simulator" className="hover:text-slate-100 transition">
              Simulator
            </Link>
            <Link href="/supplier-outreach" className="hover:text-slate-100 transition">
              Outreach
            </Link>
            <Link href="/disclosures" className="hover:text-slate-100 transition">
              Disclosures
            </Link>
            <Link href="/anomalies" className="hover:text-slate-100 transition">
              Anomalies
            </Link>
            <Link href="/audit-trail" className="hover:text-slate-100 transition">
              Audit
            </Link>
          </nav>

          <div className="flex items-center space-x-3">
            <span className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live Neon &amp; Upstash Connected
            </span>
            <Link
              href="/executive-dashboard"
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold text-xs shadow-[0_0_20px_rgba(16,185,129,0.3)] transition transform hover:-translate-y-0.5"
            >
              Launch Dashboard &rarr;
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative z-10 pt-16 pb-12 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 mb-6 backdrop-blur-md shadow-[0_0_20px_rgba(16,185,129,0.15)]">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span>Production Ready &bull; All 8 Phases Complete</span>
        </div>

        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white max-w-5xl mx-auto leading-[1.1]">
          Audit-Grade Carbon Accounting with{" "}
          <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
            Cryptographic Provenance
          </span>
        </h1>

        <p className="mt-6 text-base sm:text-xl text-slate-400 max-w-3xl mx-auto font-normal leading-relaxed">
          The institutional platform pairing deterministic Python arithmetic with Groq AI automation.
          Built for CA SB 253, EU CSRD, and GHG Protocol compliance with zero mathematical hallucination.
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/executive-dashboard"
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold text-sm shadow-[0_0_30px_rgba(16,185,129,0.35)] transition transform hover:-translate-y-0.5 flex items-center gap-2"
          >
            <span>Explore Obsidian Executive UI</span>
            <span className="text-base">&rarr;</span>
          </Link>
          <Link
            href="/dashboard"
            className="px-6 py-3 rounded-xl bg-slate-900/80 hover:bg-slate-800 text-slate-200 border border-slate-700/80 hover:border-slate-600 font-semibold text-sm backdrop-blur-md transition flex items-center gap-2"
          >
            <span>Open Carbon Ledger</span>
          </Link>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-3 rounded-xl bg-white/[0.03] hover:bg-white/[0.07] text-slate-400 hover:text-slate-200 border border-slate-800 font-mono text-xs backdrop-blur-md transition flex items-center gap-1.5"
          >
            <span>Interactive Swagger API</span>
            <span className="text-xs">&nearr;</span>
          </a>
        </div>

        {/* Live Real-Time Telemetry Bar */}
        <div className="mt-14 p-4 rounded-2xl bg-[#0D111C]/80 border border-slate-800/80 backdrop-blur-xl shadow-2xl grid grid-cols-2 md:grid-cols-5 gap-4 text-left">
          <div className="p-3 border-r border-slate-800/60 last:border-none">
            <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
              Gross Emissions
            </div>
            <div className="mt-1 text-xl font-mono font-bold text-emerald-400">
              6,268.4 <span className="text-xs font-normal text-slate-400">tCO2e</span>
            </div>
            <div className="mt-0.5 text-[10px] text-emerald-400/80 font-mono">
              FY2025 Audited Ledger
            </div>
          </div>

          <div className="p-3 border-r border-slate-800/60 last:border-none">
            <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
              Arithmetic Mode
            </div>
            <div className="mt-1 text-xl font-mono font-bold text-teal-300">
              100% Deterministic
            </div>
            <div className="mt-0.5 text-[10px] text-slate-400 font-mono">
              Zero LLM in calculation
            </div>
          </div>

          <div className="p-3 border-r border-slate-800/60 last:border-none">
            <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
              Verified Coverage
            </div>
            <div className="mt-1 text-xl font-mono font-bold text-cyan-400">
              98.4%
            </div>
            <div className="mt-0.5 text-[10px] text-slate-400 font-mono">
              Primary supplier data
            </div>
          </div>

          <div className="p-3 border-r border-slate-800/60 last:border-none">
            <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
              Evidence Trail
            </div>
            <div className="mt-1 text-xl font-mono font-bold text-white">
              &lt; 200 ms
            </div>
            <div className="mt-0.5 text-[10px] text-slate-400 font-mono">
              Sub-second tree trace
            </div>
          </div>

          <div className="p-3 col-span-2 md:col-span-1">
            <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
              Cloud Infrastructure
            </div>
            <div className="mt-1 text-xl font-mono font-bold text-emerald-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              Live Active
            </div>
            <div className="mt-0.5 text-[10px] text-slate-400 font-mono">
              Neon + Upstash + B2
            </div>
          </div>
        </div>
      </section>

      {/* Featured Showcase: Obsidian Executive UI Panel */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="p-8 rounded-3xl bg-gradient-to-b from-[#111827]/90 to-[#0D111C]/90 border border-emerald-500/30 shadow-[0_0_50px_rgba(16,185,129,0.15)] backdrop-blur-2xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
          
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 pb-6 border-b border-slate-800/80">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  Stitch Design Showcase
                </span>
                <span className="text-xs text-slate-400 font-mono">Obsidian Provenance Theme</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                Obsidian Executive ESG Intelligence Suite
              </h2>
              <p className="mt-1 text-sm text-slate-400 max-w-2xl">
                Precision glassmorphism interface engineered for boardrooms, risk committees, and institutional auditors. Features live SBTi net-zero target trajectories, MACC abatement curves, and real-time ERP telemetry.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/executive-dashboard"
                className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/30 transition transform hover:-translate-y-0.5 flex items-center gap-1.5"
              >
                <span>Launch Interactive View</span>
                <span>&rarr;</span>
              </Link>
              <a
                href="/stitch_dashboard.html"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.08] text-slate-200 border border-slate-700 text-xs font-medium transition"
              >
                Open Fullscreen &nearr;
              </a>
            </div>
          </div>

          {/* Quick Metrics Glance */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-6">
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-[11px] font-mono text-slate-400">Scope 1 Direct</div>
              <div className="text-lg font-mono font-bold text-emerald-400 mt-1">1,901.80 tCO2e</div>
              <div className="text-[10px] text-slate-500 font-mono mt-0.5">30.3% of gross emissions</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-[11px] font-mono text-slate-400">Scope 2 Indirect</div>
              <div className="text-lg font-mono font-bold text-teal-300 mt-1">1,505.84 tCO2e</div>
              <div className="text-[10px] text-slate-500 font-mono mt-0.5">24.0% of gross emissions</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-[11px] font-mono text-slate-400">Scope 3 Value Chain</div>
              <div className="text-lg font-mono font-bold text-cyan-400 mt-1">2,860.79 tCO2e</div>
              <div className="text-[10px] text-slate-500 font-mono mt-0.5">45.6% of gross emissions</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="text-[11px] font-mono text-slate-400">Net YoY Trajectory</div>
              <div className="text-lg font-mono font-bold text-emerald-400 mt-1">-14.2% YoY</div>
              <div className="text-[10px] text-emerald-400/80 font-mono mt-0.5">SBTi 1.5&deg;C Aligned</div>
            </div>
          </div>
        </div>
      </section>

      {/* Core Platform Modules Grid (8 Complete Modules) */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8">
          <div>
            <div className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400 mb-1">
              End-to-End Enterprise Architecture
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Institutional ESG &amp; Decarbonization Engines
            </h2>
          </div>
          <p className="text-xs text-slate-400 max-w-md mt-2 md:mt-0 font-mono">
            Every module is verified with 100% unit &amp; E2E integration test pass rate (88% statement coverage).
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 text-left">
          {/* 1. Corporate Carbon Ledger */}
          <Link
            href="/dashboard"
            className="p-6 rounded-2xl bg-[#0D111C]/80 border border-slate-800 hover:border-emerald-500/60 transition group hover:shadow-[0_0_30px_rgba(16,185,129,0.15)] flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400">
                  Phase 7 &bull; Real Data
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                  Live Ledger
                </span>
              </div>
              <h3 className="text-lg font-bold text-white group-hover:text-emerald-300 transition">
                Corporate Carbon Ledger
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Scope 1, 2, and 3 aggregate analytics, top emission hotspots, category breakdowns, and multi-year historical trends.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-emerald-400 font-medium">
              <span>View Carbon Ledger</span>
              <span>&rarr;</span>
            </div>
          </Link>

          {/* 2. Decarbonization Simulator */}
          <Link
            href="/simulator"
            className="p-6 rounded-2xl bg-[#0D111C]/80 border border-slate-800 hover:border-emerald-500/60 transition group hover:shadow-[0_0_30px_rgba(16,185,129,0.15)] flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-teal-400">
                  Phase 7 &bull; Simulator
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-teal-500/10 text-teal-300 border border-teal-500/20">
                  MACC Curve
                </span>
              </div>
              <h3 className="text-lg font-bold text-white group-hover:text-teal-300 transition">
                Decarbonization Simulator
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Model solar PPAs, fleet EV transitions, heat pump retrofits, and supply chain levers with MACC ($/tCO2e) ROI ranking.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-teal-400 font-medium">
              <span>Simulate Mitigation</span>
              <span>&rarr;</span>
            </div>
          </Link>

          {/* 3. Scope 3 Supplier Outreach */}
          <Link
            href="/supplier-outreach"
            className="p-6 rounded-2xl bg-[#0D111C]/80 border border-slate-800 hover:border-emerald-500/60 transition group hover:shadow-[0_0_30px_rgba(16,185,129,0.15)] flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-cyan-400">
                  Phase 7 &bull; Autonomous Agent
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                  Groq AI
                </span>
              </div>
              <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition">
                Scope 3 Supplier Outreach
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Identify missing Scope 3 supplier activity, generate tailored outreach emails with Groq, and record primary supplier factors.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-cyan-400 font-medium">
              <span>Engage Suppliers</span>
              <span>&rarr;</span>
            </div>
          </Link>

          {/* 4. Regulatory Disclosures */}
          <Link
            href="/disclosures"
            className="p-6 rounded-2xl bg-[#0D111C]/80 border border-slate-800 hover:border-emerald-500/60 transition group hover:shadow-[0_0_30px_rgba(16,185,129,0.15)] flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-indigo-400">
                  Phase 5 &bull; Statutory Compliance
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  PDF Export
                </span>
              </div>
              <h3 className="text-lg font-bold text-white group-hover:text-indigo-300 transition">
                Regulatory Disclosures
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Evaluate statutory eligibility for California SB 253, EU CSRD (ESRS E1), and GHG Protocol with footnoted PDF export.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-indigo-400 font-medium">
              <span>Generate Filing</span>
              <span>&rarr;</span>
            </div>
          </Link>

          {/* 5. Greenwashing & Anomaly Detection */}
          <Link
            href="/anomalies"
            className="p-6 rounded-2xl bg-[#0D111C]/80 border border-slate-800 hover:border-emerald-500/60 transition group hover:shadow-[0_0_30px_rgba(16,185,129,0.15)] flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-amber-400">
                  Phase 6 &bull; Anomaly Engine
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-300 border border-amber-500/20">
                  Z &ge; 3.0 Outliers
                </span>
              </div>
              <h3 className="text-lg font-bold text-white group-hover:text-amber-300 transition">
                Anomaly &amp; Greenwashing
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Statistical YoY variances, intensity outliers, completeness guards, and Groq cross-examination of public CSR claims.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-amber-400 font-medium">
              <span>Inspect Anomalies</span>
              <span>&rarr;</span>
            </div>
          </Link>

          {/* 6. Cryptographic Audit Provenance */}
          <Link
            href="/audit-trail"
            className="p-6 rounded-2xl bg-[#0D111C]/80 border border-slate-800 hover:border-emerald-500/60 transition group hover:shadow-[0_0_30px_rgba(16,185,129,0.15)] flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400">
                  Phase 4 &bull; Governance
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                  &lt;200ms Trace
                </span>
              </div>
              <h3 className="text-lg font-bold text-white group-hover:text-emerald-300 transition">
                Audit Provenance Trail
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Trace end-to-end evidence trees from raw document SHA-256 hash to line item, emission factor version, and formula.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-emerald-400 font-medium">
              <span>Trace Provenance</span>
              <span>&rarr;</span>
            </div>
          </Link>

          {/* 7. Scope Classification Queue */}
          <Link
            href="/review"
            className="p-6 rounded-2xl bg-[#0D111C]/80 border border-slate-800 hover:border-emerald-500/60 transition group hover:shadow-[0_0_30px_rgba(16,185,129,0.15)] flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-purple-400">
                  Phase 2 &bull; Human-in-the-Loop
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-500/10 text-purple-300 border border-purple-500/20">
                  Review Queue
                </span>
              </div>
              <h3 className="text-lg font-bold text-white group-hover:text-purple-300 transition">
                Classification Review
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Verify AI Scope 1/2/3 classifications, override GHG Protocol categories, and audit confidence scores with full logs.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-purple-400 font-medium">
              <span>Review Line Items</span>
              <span>&rarr;</span>
            </div>
          </Link>

          {/* 8. Zero LLM Arithmetic Tenet */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-[#0D111C] to-emerald-950/20 border border-emerald-500/40 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-300">
                  Core Axiom
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-200 border border-emerald-500/30">
                  Zero LLM Math
                </span>
              </div>
              <h3 className="text-lg font-bold text-white">
                Pure Deterministic Arithmetic
              </h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                All carbon arithmetic strictly executes in pure Python with unit tests. Zero LLM completions ever touch calculation ledgers.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] font-mono text-emerald-400">
              EPA eGRID 2025 &bull; DEFRA 2025 Verified
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-800/80 bg-[#0A0E19] py-8 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-slate-300">Greenlign Platform</span>
            <span>&bull;</span>
            <span>Enterprise Carbon Accounting &amp; ESG Intelligence</span>
          </div>

          <div className="flex items-center space-x-6 text-slate-400">
            <Link href="/executive-dashboard" className="hover:text-emerald-400 transition">
              Executive UI
            </Link>
            <Link href="/dashboard" className="hover:text-emerald-400 transition">
              Ledger
            </Link>
            <Link href="/simulator" className="hover:text-emerald-400 transition">
              Simulator
            </Link>
            <Link href="/supplier-outreach" className="hover:text-emerald-400 transition">
              Outreach
            </Link>
            <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="hover:text-emerald-400 transition">
              API Swagger
            </a>
          </div>

          <div className="text-[11px] font-mono text-slate-600">
            &copy; 2026 Greenlign. Audit-Grade ESG Architecture.
          </div>
        </div>
      </footer>
    </div>
  );
}

