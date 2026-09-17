import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 py-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto text-center space-y-8">
        <div>
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300 mb-4">
            Phase 5 Complete: Regulatory Disclosures
          </span>
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight sm:text-5xl">
            Greenlign
          </h1>
          <p className="mt-3 text-lg text-slate-600 max-w-2xl mx-auto">
            Audit-grade, AI-assisted greenhouse gas accounting platform with deterministic calculation provenance, referential integrity guards, and statutory ESG disclosures.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4 text-left">
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
              Trace end-to-end evidence trees from raw files to activity lines, emission factor tables, and mathematical formulas in &lt;200ms.
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
              Evaluate eligibility for CA SB 253, EU CSRD (ESRS E1), and GHG Protocol. Deterministically generate PDF reports with audit citations.
            </p>
          </Link>
        </div>
      </div>
    </main>
  );
}
