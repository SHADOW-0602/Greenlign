"use client";

import React, { useState } from "react";

export interface LeverDefinition {
  lever_id: string;
  title: string;
  description: string;
  target_scope: number;
  target_activity_type: string;
  default_capex_usd: number;
  default_annual_opex_delta_usd: number;
}

export interface LeverImpactResult {
  lever_id: string;
  title: string;
  scope: number;
  baseline_emissions_tco2e: number;
  simulated_emissions_tco2e: number;
  reduction_tco2e: number;
  reduction_percent: number;
  annualized_net_cost_usd: number;
  marginal_abatement_cost_usd_per_tco2e: number;
  roi_rank: number;
}

export interface SimulationResponse {
  entity_id: string;
  reporting_period: string;
  baseline_gross_tco2e: number;
  simulated_gross_tco2e: number;
  total_reduction_tco2e: number;
  total_reduction_percent: number;
  net_annual_cost_usd: number;
  target_met: boolean | null;
  ranked_levers: LeverImpactResult[];
}

interface ScenarioSimulatorViewProps {
  catalog: LeverDefinition[];
  entityId: string;
  reportingPeriod: string;
}

export default function ScenarioSimulatorView({
  catalog,
  entityId,
  reportingPeriod,
}: ScenarioSimulatorViewProps) {
  // Rates state: map lever_id -> 0.0 .. 1.0
  const [rates, setRates] = useState<Record<string, number>>(() => {
    const init: Record<string, number> = {};
    catalog.forEach((l) => {
      init[l.lever_id] = l.lever_id === "SOLAR_PPA_GRID_ELEC" ? 0.5 : 0.0;
    });
    return init;
  });

  const [targetPercent, setTargetPercent] = useState<number>(30.0);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [simError, setSimError] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationResponse | null>(null);

  const handleRateChange = (leverId: string, val: number) => {
    setRates((prev) => ({ ...prev, [leverId]: val }));
  };

  const runSimulation = async () => {
    setSimulating(true);
    setSimError(null);
    try {
      const appliedLevers = Object.entries(rates)
        .filter(([_, rate]) => rate > 0)
        .map(([lever_id, rate]) => ({
          lever_id,
          implementation_rate: rate,
        }));

      const res = await fetch("/api/simulator/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entity_id: entityId,
          reporting_period: reportingPeriod,
          applied_levers: appliedLevers,
          target_reduction_percent: targetPercent,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error ${res.status}`);
      }

      const data: SimulationResponse = await res.json();
      setResult(data);
    } catch (err: any) {
      console.error("Simulation error:", err);
      setSimError(err.message || "Failed to execute simulation.");
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Simulation Controls & Target Setting */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <h2 className="text-base font-bold text-slate-900 uppercase tracking-wider">
              Decarbonization Abatement Lever Selection
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Adjust implementation scale for each intervention to evaluate emissions reduction and abatement costs.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 text-xs">
              <span className="font-semibold text-slate-600">SBTi Target:</span>
              <input
                type="number"
                min="0"
                max="100"
                value={targetPercent}
                onChange={(e) => setTargetPercent(parseFloat(e.target.value) || 0)}
                className="w-16 rounded-md border border-slate-300 p-1.5 font-mono text-center text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
              <span className="font-semibold text-slate-600">%</span>
            </div>

            <button
              onClick={runSimulation}
              disabled={simulating}
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
            >
              {simulating ? "Calculating Abatement..." : "⚡ Run Simulation"}
            </button>
          </div>
        </div>

        {simError && (
          <div className="p-3 rounded-lg bg-red-50 text-red-700 text-xs border border-red-200">
            {simError}
          </div>
        )}

        {/* Levers List */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {catalog.map((l) => {
            const currentRate = rates[l.lever_id] || 0.0;
            const pct = Math.round(currentRate * 100);

            return (
              <div
                key={l.lever_id}
                className="rounded-xl border border-slate-200 p-5 space-y-4 hover:border-slate-300 transition bg-slate-50/40"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200/80 text-slate-700 border border-slate-300 uppercase tracking-wider">
                      Scope {l.target_scope}
                    </span>
                    <h3 className="font-bold text-sm text-slate-900 mt-1">{l.title}</h3>
                  </div>
                  <span className="font-mono font-bold text-sm text-emerald-600">
                    {pct}%
                  </span>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">{l.description}</p>

                {/* Slider */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] text-slate-400 font-semibold uppercase">
                    <span>Inactive (0%)</span>
                    <span>Full Scale (100%)</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={currentRate}
                    onChange={(e) => handleRateChange(l.lever_id, parseFloat(e.target.value))}
                    className="w-full accent-emerald-600 cursor-pointer"
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Results Section */}
      {result && (
        <div className="space-y-6">
          {/* Top Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <span className="text-[11px] uppercase font-bold text-slate-400 block tracking-wider">
                Baseline Footprint
              </span>
              <span className="text-2xl font-black text-slate-900 font-mono mt-1 block">
                {result.baseline_gross_tco2e.toFixed(2)}{" "}
                <span className="text-xs font-normal text-slate-500">tCO₂e</span>
              </span>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <span className="text-[11px] uppercase font-bold text-emerald-600 block tracking-wider">
                Total Abatement
              </span>
              <span className="text-2xl font-black text-emerald-600 font-mono mt-1 block">
                -{result.total_reduction_tco2e.toFixed(2)}{" "}
                <span className="text-xs font-normal text-emerald-700">
                  (-{result.total_reduction_percent.toFixed(1)}%)
                </span>
              </span>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <span className="text-[11px] uppercase font-bold text-slate-400 block tracking-wider">
                Simulated Footprint
              </span>
              <span className="text-2xl font-black text-slate-900 font-mono mt-1 block">
                {result.simulated_gross_tco2e.toFixed(2)}{" "}
                <span className="text-xs font-normal text-slate-500">tCO₂e</span>
              </span>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col justify-between">
              <div>
                <span className="text-[11px] uppercase font-bold text-slate-400 block tracking-wider">
                  Target Status
                </span>
                <span
                  className={`mt-1 inline-flex items-center px-2.5 py-0.5 rounded text-xs font-bold ${
                    result.target_met
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : "bg-amber-100 text-amber-800 border border-amber-300"
                  }`}
                >
                  {result.target_met ? "✓ Target Met" : "Target Not Met"}
                </span>
              </div>
              <span className="text-[10px] text-slate-400 mt-2 block font-mono">
                Target: {targetPercent}% | Achieved: {result.total_reduction_percent.toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Marginal Abatement Cost Curve (MACC) Ranked Table */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                  Marginal Abatement Cost Curve (MACC) Rankings
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Levers ranked by cost-efficiency ($/tCO₂e abated). Negative costs represent net economic savings.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-y border-slate-200 text-slate-600 uppercase font-bold text-[10px] tracking-wider">
                  <tr>
                    <th className="py-2.5 px-3">ROI Rank</th>
                    <th className="py-2.5 px-3">Decarbonization Lever</th>
                    <th className="py-2.5 px-3 text-right">Scope</th>
                    <th className="py-2.5 px-3 text-right">Abated (tCO₂e)</th>
                    <th className="py-2.5 px-3 text-right">Annual Cost ($/yr)</th>
                    <th className="py-2.5 px-3 text-right">MAC ($/tCO₂e)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.ranked_levers.map((lev) => {
                    const isSaving = lev.marginal_abatement_cost_usd_per_tco2e < 0;
                    return (
                      <tr key={lev.lever_id} className="hover:bg-slate-50/50 transition">
                        <td className="py-3 px-3">
                          <span className="w-6 h-6 rounded-full bg-slate-100 border border-slate-200 inline-flex items-center justify-center font-bold text-slate-700 font-mono text-xs">
                            {lev.roi_rank}
                          </span>
                        </td>
                        <td className="py-3 px-3 font-semibold text-slate-900">
                          {lev.title}
                        </td>
                        <td className="py-3 px-3 text-right font-semibold text-slate-600">
                          Scope {lev.scope}
                        </td>
                        <td className="py-3 px-3 text-right font-mono font-bold text-emerald-600">
                          -{lev.reduction_tco2e.toFixed(2)}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-700">
                          ${lev.annualized_net_cost_usd.toLocaleString(undefined, {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                          })}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                              isSaving
                                ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                                : "bg-purple-100 text-purple-800 border border-purple-200"
                            }`}
                          >
                            ${lev.marginal_abatement_cost_usd_per_tco2e.toFixed(2)}/t
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
