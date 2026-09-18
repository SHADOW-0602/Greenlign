import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 py-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto text-center space-y-8">
        <div>
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300 mb-4">
            Phase 7 Complete: Executive Dashboard, Simulator &amp; Supplier Outreach
          </span>
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight sm:text-5xl">
            Greenlign
          </h1>
          <p className="mt-3 text-lg text-slate-600 max-w-2xl mx-auto">
            Audit-grade, AI-assisted greenhouse gas accounting platform with deterministic calculation provenance, referential integrity guards, statutory ESG disclosures, decarbonization simulations, and autonomous Scope 3 supplier outreach.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-4 text-left">
          {/* Executive Dashboard */}
          <Link
            href="/dashboard"
            className="p-6 rounded-xl bg-white border border-slate-200 shadow-sm hover:shadow-md hover:border-emerald-500 transition group"
          >
            <div className="text-emerald-600 font-bold text-sm uppercase tracking-wider mb-2">
              Phase 7
            </div>
            <h2 className="text-lg font-bold text-slate-900 group-hover:text-emerald-600 transition">
              Executive ESG Dashboard
            </h2>
            <p className="mt-2 text-xs text-slate-500 leading-relaxed">
              Scope 1, 2, and 3 aggregate analytics, top emission hotspots, category breakdowns, and multi-year historical trends.
            </p>
          </Link>

          {/* Scenario Simulator */}
          <Link
            href="/simulator"
            className="p-6 rounded-xl bg-white border border-slate-200 shadow-sm hover:shadow-md hover:border-emerald-500 transition group"
          >
            <div className="text-emerald-600 font-bold text-sm uppercase tracking-wider mb-2">
              Phase 7
            </div>
            <h2 className="text-lg font-bold text-slate-900 group-hover:text-emerald-600 transition">
              Decarbonization Simulator
            </h2>
            <p className="mt-2 text-xs text-slate-500 leading-relaxed">
              Model solar PPAs, fleet EV transitions, heat pump retrofits, and supply chain levers with MACC ($/tCO2e) ROI ranking.
            </p>
          </Link>

          {/* Supplier Outreach */}
          <Link
            href="/supplier-outreach"
            className="p-6 rounded-xl bg-white border border-slate-200 shadow-sm hover:shadow-md hover:border-emerald-500 transition group"
          >
            <div className="text-emerald-600 font-bold text-sm uppercase tracking-wider mb-2">
              Phase 7
            </div>
            <h2 className="text-lg font-bold text-slate-900 group-hover:text-emerald-600 transition">
              Scope 3 Supplier Outreach
            </h2>
            <p className="mt-2 text-xs text-slate-500 leading-relaxed">
              Identify missing Scope 3 supplier activity, generate tailored outreach emails with Groq, and record primary supplier factors.
            </p>
          </Link>

          {/* Review Queue */}
          <Link
            href="/review"
            className="p-6 rounded-xl bg-white border border-slate-200 shadow-sm hover:shadow-md hover:border-emerald-500 transition group"
          >
            <div className="text-emerald-600 font-bold text-sm uppercase tracking-wider mb-2">
              Phase 2
            </div>
            <h2 className="text-lg font-bold text-slate-900 group-hover:text-emerald-600 transition">
              Classification Review
            </h2>
            <p className="mt-2 text-xs text-slate-500 leading-relaxed">
              Verify LLM Scope 1, 2, and 3 classifications, override GHG Protocol categories, and validate confidence scores.
            </p>
          </Link>

          {/* Audit Trail */}
          <Link
            href="/audit-trail"
            className="p-6 rounded-xl bg-white border border-slate-200 shadow-sm hover:shadow-md hover:border-emerald-500 transition group"
          >
            <div className="text-emerald-600 font-bold text-sm uppercase tracking-wider mb-2">
              Phase 4
            </div>
            <h2 className="text-lg font-bold text-slate-900 group-hover:text-emerald-600 transition">
              Audit Provenance Trail
            </h2>
            <p className="mt-2 text-xs text-slate-500 leading-relaxed">
              Trace end-to-end evidence trees from raw files to activity lines, emission factor tables, and mathematical formulas.
            </p>
          </Link>

          {/* Regulatory Disclosures */}
          <Link
            href="/disclosures"
            className="p-6 rounded-xl bg-white border border-slate-200 shadow-sm hover:shadow-md hover:border-emerald-500 transition group"
          >
            <div className="text-emerald-600 font-bold text-sm uppercase tracking-wider mb-2">
              Phase 5
            </div>
            <h2 className="text-lg font-bold text-slate-900 group-hover:text-emerald-600 transition">
              Regulatory Disclosures
            </h2>
            <p className="mt-2 text-xs text-slate-500 leading-relaxed">
              Evaluate eligibility for CA SB 253, EU CSRD, and GHG Protocol. Deterministically generate PDF reports with audit citations.
            </p>
          </Link>

          {/* Anomalies & Greenwashing */}
          <Link
            href="/anomalies"
            className="p-6 rounded-xl bg-white border border-slate-200 shadow-sm hover:shadow-md hover:border-emerald-500 transition group"
          >
            <div className="text-emerald-600 font-bold text-sm uppercase tracking-wider mb-2">
              Phase 6
            </div>
            <h2 className="text-lg font-bold text-slate-900 group-hover:text-emerald-600 transition">
              Anomaly &amp; Greenwashing
            </h2>
            <p className="mt-2 text-xs text-slate-500 leading-relaxed">
              YoY variances, intensity outliers (Z ≥ 3.0), scope completeness, and LLM narrative consistency cross-examination.
            </p>
          </Link>
        </div>
      </div>
    </main>
  );
}
