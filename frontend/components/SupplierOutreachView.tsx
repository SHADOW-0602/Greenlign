"use client";

import React, { useState } from "react";

export interface MissingScope3SupplierItem {
  supplier_ref: string;
  activity_type: string;
  reporting_period: string;
  current_factor_source: string;
  estimated_tco2e: number;
  line_item_count: number;
}

export interface SupplierOutreachItem {
  id: string;
  entity_id: string;
  supplier_ref: string;
  supplier_name: string | null;
  supplier_email: string;
  contact_name: string;
  activity_type: string;
  reporting_period: string;
  status: "DRAFT" | "SENT" | "RECEIVED" | string;
  template_type: string;
  generated_email_subject: string;
  generated_email_body: string;
  response_data_json: Record<string, any>;
  sent_at: string | null;
  responded_at: string | null;
  created_at: string;
}

interface SupplierOutreachViewProps {
  missingSuppliers: MissingScope3SupplierItem[];
  outreachList: SupplierOutreachItem[];
  entityId: string;
  reportingPeriod: string;
  onRefresh: () => void;
}

export default function SupplierOutreachView({
  missingSuppliers,
  outreachList,
  entityId,
  reportingPeriod,
  onRefresh,
}: SupplierOutreachViewProps) {
  // Modal states
  const [draftModalOpen, setDraftModalOpen] = useState<boolean>(false);
  const [responseModalOpen, setResponseModalOpen] = useState<boolean>(false);
  const [activeOutreach, setActiveOutreach] = useState<SupplierOutreachItem | null>(null);

  // Form states for Email Draft
  const [suppRef, setSuppRef] = useState<string>("");
  const [suppName, setSuppName] = useState<string>("");
  const [suppEmail, setSuppEmail] = useState<string>("");
  const [contactName, setContactName] = useState<string>("");
  const [activityType, setActivityType] = useState<string>("");
  const [templateType, setTemplateType] = useState<string>("PRIMARY_EMISSION_FACTOR");
  const [emailSubject, setEmailSubject] = useState<string>("");
  const [emailBody, setEmailBody] = useState<string>("");
  const [generating, setGenerating] = useState<boolean>(false);
  const [savingOutreach, setSavingOutreach] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Form states for Recording Response
  const [factorVal, setFactorVal] = useState<string>("");
  const [factorUnit, setFactorUnit] = useState<string>("kgCO2e/kg");
  const [verifiedQty, setVerifiedQty] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [savingResponse, setSavingResponse] = useState<boolean>(false);
  const [responseError, setResponseError] = useState<string | null>(null);

  const openDraftForMissing = (item: MissingScope3SupplierItem) => {
    setSuppRef(item.supplier_ref);
    setSuppName(item.supplier_ref.replace("SUPP_", "").replace(/_/g, " "));
    setSuppEmail("sustainability@" + item.supplier_ref.toLowerCase() + ".com");
    setContactName("ESG Coordinator");
    setActivityType(item.activity_type);
    setTemplateType("PRIMARY_EMISSION_FACTOR");
    setEmailSubject("");
    setEmailBody("");
    setFormError(null);
    setDraftModalOpen(true);
  };

  const handleGenerateEmail = async () => {
    setGenerating(true);
    setFormError(null);
    try {
      const res = await fetch("/api/outreach/generate-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supplier_name: suppName || suppRef,
          supplier_ref: suppRef,
          activity_type: activityType,
          reporting_period: reportingPeriod,
          template_type: templateType,
        }),
      });
      if (!res.ok) throw new Error("Failed to generate email draft.");
      const data = await res.json();
      setEmailSubject(data.subject);
      setEmailBody(data.body);
    } catch (err: any) {
      setFormError(err.message || "Failed to generate email.");
    } finally {
      setGenerating(false);
    }
  };

  const handleCreateOutreach = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingOutreach(true);
    setFormError(null);
    try {
      const res = await fetch("/api/outreach", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entity_id: entityId,
          supplier_ref: suppRef,
          supplier_name: suppName,
          supplier_email: suppEmail,
          contact_name: contactName,
          activity_type: activityType,
          reporting_period: reportingPeriod,
          template_type: templateType,
          custom_subject: emailSubject || undefined,
          custom_body: emailBody || undefined,
        }),
      });
      if (!res.ok) throw new Error("Failed to create outreach campaign.");
      setDraftModalOpen(false);
      onRefresh();
    } catch (err: any) {
      setFormError(err.message || "Failed to save outreach.");
    } finally {
      setSavingOutreach(false);
    }
  };

  const handleSendOutreach = async (id: string) => {
    try {
      const res = await fetch(`/api/outreach/${id}/send`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to dispatch outreach.");
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRecordResponseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeOutreach) return;
    setSavingResponse(true);
    setResponseError(null);
    try {
      const res = await fetch(`/api/outreach/${activeOutreach.id}/record-response`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          primary_factor_value: factorVal ? parseFloat(factorVal) : null,
          primary_factor_unit: factorUnit || null,
          verified_quantity: verifiedQty ? parseFloat(verifiedQty) : null,
          response_notes: notes || null,
        }),
      });
      if (!res.ok) throw new Error("Failed to record supplier response.");
      setResponseModalOpen(false);
      setActiveOutreach(null);
      onRefresh();
    } catch (err: any) {
      setResponseError(err.message || "Failed to record response.");
    } finally {
      setSavingResponse(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Section 1: Missing Scope 3 Primary Data */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Scope 3 Suppliers Requiring Primary Data
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Activity data currently calculated using industry-average secondary proxy factors (DEFRA/EPA).
            </p>
          </div>
          <span className="text-xs font-semibold text-slate-500 font-mono">
            {missingSuppliers.length} suppliers identified
          </span>
        </div>

        {missingSuppliers.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400 bg-slate-50 rounded-lg border border-slate-200">
            No Scope 3 suppliers currently require primary data outreach.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-y border-slate-200 text-slate-600 uppercase font-bold text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Supplier Reference</th>
                  <th className="py-2.5 px-3">Activity Type</th>
                  <th className="py-2.5 px-3">Current Factor Proxy</th>
                  <th className="py-2.5 px-3 text-right">Estimated Footprint</th>
                  <th className="py-2.5 px-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {missingSuppliers.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50 transition">
                    <td className="py-3 px-3 font-semibold text-slate-900 font-mono">
                      {item.supplier_ref}
                    </td>
                    <td className="py-3 px-3 text-slate-700">{item.activity_type}</td>
                    <td className="py-3 px-3 text-slate-500">{item.current_factor_source}</td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-slate-900">
                      {item.estimated_tco2e.toFixed(2)} tCO₂e
                    </td>
                    <td className="py-3 px-3 text-center">
                      <button
                        onClick={() => openDraftForMissing(item)}
                        className="px-3 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded text-xs font-semibold transition"
                      >
                        Draft Inquiry →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Section 2: Active Outreach Campaigns */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Supplier Outreach Campaigns &amp; Response Intake
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Track communications lifecycle from draft to dispatched inquiries and verified primary intake.
            </p>
          </div>
          <button
            onClick={() => {
              setSuppRef("");
              setSuppName("");
              setSuppEmail("");
              setContactName("");
              setActivityType("");
              setEmailSubject("");
              setEmailBody("");
              setFormError(null);
              setDraftModalOpen(true);
            }}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-sm transition"
          >
            + New Supplier Campaign
          </button>
        </div>

        {outreachList.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400 bg-slate-50 rounded-lg border border-slate-200">
            No outreach campaigns have been initiated yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-y border-slate-200 text-slate-600 uppercase font-bold text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Supplier</th>
                  <th className="py-2.5 px-3">Contact</th>
                  <th className="py-2.5 px-3">Commodity</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Timeline</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {outreachList.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/50 transition">
                    <td className="py-3 px-3">
                      <div className="font-bold text-slate-900">
                        {item.supplier_name || item.supplier_ref}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {item.supplier_ref}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-slate-700">
                      <div>{item.contact_name}</div>
                      <div className="text-[10px] text-slate-400">{item.supplier_email}</div>
                    </td>
                    <td className="py-3 px-3 text-slate-600 font-mono text-[11px]">
                      {item.activity_type}
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          item.status === "RECEIVED"
                            ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                            : item.status === "SENT"
                            ? "bg-blue-100 text-blue-800 border border-blue-300"
                            : "bg-slate-100 text-slate-700 border border-slate-300"
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-[11px] text-slate-500">
                      {item.status === "RECEIVED" ? (
                        <span className="text-emerald-700 font-semibold">
                          Received {new Date(item.responded_at || "").toLocaleDateString()}
                        </span>
                      ) : item.status === "SENT" ? (
                        <span>Sent {new Date(item.sent_at || "").toLocaleDateString()}</span>
                      ) : (
                        <span>Draft</span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-right space-x-2">
                      {item.status === "DRAFT" && (
                        <button
                          onClick={() => handleSendOutreach(item.id)}
                          className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[11px] font-semibold transition shadow-sm"
                        >
                          Dispatch
                        </button>
                      )}
                      {item.status === "SENT" && (
                        <button
                          onClick={() => {
                            setActiveOutreach(item);
                            setFactorVal("");
                            setNotes("");
                            setResponseError(null);
                            setResponseModalOpen(true);
                          }}
                          className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[11px] font-semibold transition shadow-sm"
                        >
                          Record Data
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal 1: Create & Draft Outreach */}
      {draftModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-2xl w-full p-6 space-y-5 my-8">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Draft Scope 3 Supplier Inquiry
              </h3>
              <button
                onClick={() => setDraftModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateOutreach} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                    Supplier Ref
                  </label>
                  <input
                    type="text"
                    value={suppRef}
                    onChange={(e) => setSuppRef(e.target.value)}
                    required
                    className="w-full rounded border border-slate-300 p-2 text-xs font-mono focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                    Supplier Name
                  </label>
                  <input
                    type="text"
                    value={suppName}
                    onChange={(e) => setSuppName(e.target.value)}
                    required
                    className="w-full rounded border border-slate-300 p-2 text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                    Contact Email
                  </label>
                  <input
                    type="email"
                    value={suppEmail}
                    onChange={(e) => setSuppEmail(e.target.value)}
                    required
                    className="w-full rounded border border-slate-300 p-2 text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                    Contact Name
                  </label>
                  <input
                    type="text"
                    value={contactName}
                    onChange={(e) => setContactName(e.target.value)}
                    required
                    className="w-full rounded border border-slate-300 p-2 text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                    Activity / Procured Category
                  </label>
                  <input
                    type="text"
                    value={activityType}
                    onChange={(e) => setActivityType(e.target.value)}
                    required
                    className="w-full rounded border border-slate-300 p-2 text-xs font-mono focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                    Template Type
                  </label>
                  <select
                    value={templateType}
                    onChange={(e) => setTemplateType(e.target.value)}
                    className="w-full rounded border border-slate-300 p-2 text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  >
                    <option value="PRIMARY_EMISSION_FACTOR">Primary Emission Factor</option>
                    <option value="ACTIVITY_DATA_VERIFICATION">Activity Data Verification</option>
                    <option value="REDUCTION_PLEDGE">Decarbonization Pledge</option>
                  </select>
                </div>
              </div>

              <div className="pt-2 flex justify-between items-center">
                <button
                  type="button"
                  onClick={handleGenerateEmail}
                  disabled={generating}
                  className="px-3 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded text-xs font-semibold transition"
                >
                  {generating ? "Drafting with Groq AI..." : "✨ Generate AI Email Draft"}
                </button>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                  Subject Line
                </label>
                <input
                  type="text"
                  value={emailSubject}
                  onChange={(e) => setEmailSubject(e.target.value)}
                  placeholder="Subject line..."
                  className="w-full rounded border border-slate-300 p-2 text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                  Email Body
                </label>
                <textarea
                  rows={6}
                  value={emailBody}
                  onChange={(e) => setEmailBody(e.target.value)}
                  placeholder="Draft email content..."
                  className="w-full rounded border border-slate-300 p-2 text-xs font-sans focus:ring-2 focus:ring-emerald-500 focus:outline-none leading-relaxed"
                  required
                />
              </div>

              {formError && (
                <div className="p-3 bg-red-50 text-red-700 text-xs rounded border border-red-200">
                  {formError}
                </div>
              )}

              <div className="flex justify-end space-x-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setDraftModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-md text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingOutreach}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-md text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {savingOutreach ? "Saving..." : "Save Outreach Campaign"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 2: Record Supplier Response Data */}
      {responseModalOpen && activeOutreach && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Record Verified Primary Supplier Data
              </h3>
              <button
                onClick={() => setResponseModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleRecordResponseSubmit} className="space-y-4">
              <div className="p-3 bg-slate-50 rounded border border-slate-200 text-xs">
                <span className="font-bold text-slate-800">
                  {activeOutreach.supplier_name || activeOutreach.supplier_ref}
                </span>{" "}
                ({activeOutreach.activity_type})
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                    Primary Factor Value
                  </label>
                  <input
                    type="number"
                    step="0.000001"
                    value={factorVal}
                    onChange={(e) => setFactorVal(e.target.value)}
                    placeholder="e.g. 0.142"
                    required
                    className="w-full rounded border border-slate-300 p-2 text-xs font-mono focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                    Unit
                  </label>
                  <input
                    type="text"
                    value={factorUnit}
                    onChange={(e) => setFactorUnit(e.target.value)}
                    placeholder="e.g. kgCO2e/kg"
                    required
                    className="w-full rounded border border-slate-300 p-2 text-xs font-mono focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                  Verified Activity Quantity (Optional)
                </label>
                <input
                  type="number"
                  step="any"
                  value={verifiedQty}
                  onChange={(e) => setVerifiedQty(e.target.value)}
                  placeholder="Reconciled delivered quantity"
                  className="w-full rounded border border-slate-300 p-2 text-xs font-mono focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                  Audit Notes / Verification Standard
                </label>
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Verified via ISO 14064 or Supplier EPD Report..."
                  className="w-full rounded border border-slate-300 p-2 text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              {responseError && (
                <div className="p-3 bg-red-50 text-red-700 text-xs rounded border border-red-200">
                  {responseError}
                </div>
              )}

              <div className="flex justify-end space-x-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setResponseModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-md text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingResponse}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-md text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {savingResponse ? "Recording..." : "Record Primary Factor"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
