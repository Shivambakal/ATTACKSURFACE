"use client";

import React, { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface TrialMetrics {
  status: string;
  trial_run_id?: number;
  started_at?: string;
  window_hours: number;
  targets: number;
  collection_cycles?: number;
  success?: number;
  failed?: number;
  assets_discovered?: number;
  real_changes?: number;
  duplicates?: number;
  noise_rejected?: number;
  security_correlations?: number;
  research_signals?: number;
  high_value_findings?: number;
  evidence_records?: number;
  target_status?: Array<{ company: string; domain: string; scope: string[]; source: string; authorization_source: string; collection_status: string; last_successful_collection?: string | null }>;
}

const metricCards = [
  ["targets", "TARGETS", "Explicit registry"], ["collection_cycles", "COLLECTION CYCLES", "24 hour window"], ["success", "SUCCESS", "Completed or empty"], ["failed", "FAILED", "Needs review"],
  ["assets_discovered", "ASSETS DISCOVERED", "Observed assets"], ["real_changes", "REAL CHANGES", "After dedup + noise"], ["duplicates", "DUPLICATES", "Collapsed records"], ["noise_rejected", "NOISE REJECTED", "Quality gate"],
  ["security_correlations", "SECURITY CORRELATIONS", "Context only"], ["research_signals", "RESEARCH SIGNALS", "Prioritized leads"], ["high_value_findings", "HIGH-VALUE FINDINGS", "Signals, not claims"], ["evidence_records", "EVIDENCE RECORDS", "Source-backed"],
] as const;

export default function TrialDashboardPage() {
  const [metrics, setMetrics] = useState<TrialMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadMetrics = useCallback(async () => {
    setLoading(true);
    try { setMetrics(await apiFetch<TrialMetrics>("/api/v1/trial/metrics")); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Trial metrics unavailable"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadMetrics(); const timer = setInterval(loadMetrics, 30000); return () => clearInterval(timer); }, [loadMetrics]);

  const startTrial = async () => {
    setStarting(true); setMessage(null);
    try { await apiFetch("/api/v1/trial/start", { method: "POST" }); setMessage("Trial queued. Existing passive snapshot workers are processing the authorized registry."); await loadMetrics(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Could not start trial"); }
    finally { setStarting(false); }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[.2em] text-cyan-300">CONTROLLED EVALUATION / 24 HOURS</p>
          <h2 className="mt-2 max-w-3xl text-4xl font-bold tracking-[-.04em] text-white sm:text-6xl">50 Target Trial</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Measure useful, source-backed intelligence across an explicit authorized registry. Observations, changes, security context, possible risk, and research signals remain separate.</p>
        </div>
        <button onClick={startTrial} disabled={starting} className="rounded-full bg-cyan-500 px-5 py-3 font-mono text-xs font-bold uppercase tracking-wider text-slate-950 disabled:opacity-50">{starting ? "QUEUING TRIAL..." : "START 24H TRIAL"}</button>
      </div>

      {message && <div className="glass-surface rounded-2xl border p-4 text-xs text-slate-300">{message}</div>}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
        {metricCards.map(([key, label, hint]) => (
          <div key={key} className="glass-surface rounded-2xl border p-4">
            <p className="font-mono text-[9px] uppercase tracking-wider text-slate-500">{label}</p>
            <p className="mt-3 text-3xl font-semibold tracking-tight text-white">{loading ? "..." : metrics?.[key] ?? 0}</p>
            <p className="mt-2 text-[10px] text-slate-500">{hint}</p>
          </div>
        ))}
      </div>

      <div className="glass-surface rounded-3xl border p-5 sm:p-6">
        <div className="flex flex-col gap-2 border-b border-white/10 pb-4 sm:flex-row sm:items-center sm:justify-between"><div><h3 className="text-lg font-semibold text-white">Trial target ledger</h3><p className="text-xs text-slate-500">Scope and source attribution are retained for every target.</p></div><span className="font-mono text-[10px] uppercase tracking-widest text-cyan-300">{metrics?.status || "NOT STARTED"}</span></div>
        {!metrics?.target_status?.length ? <div className="py-16 text-center font-mono text-xs text-slate-500">No trial started. An explicit 50-entry authorized registry is required.</div> : <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[900px] text-left"><thead><tr><th className="px-4 py-3">Company</th><th className="px-4 py-3">Domain</th><th className="px-4 py-3">Scope</th><th className="px-4 py-3">Source</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Last success</th></tr></thead><tbody>{metrics.target_status.map((target) => <tr key={target.domain} className="border-t"><td className="px-4 py-3 text-sm text-slate-200">{target.company}</td><td className="px-4 py-3 font-mono text-xs text-cyan-200">{target.domain}</td><td className="max-w-[240px] px-4 py-3 text-xs text-slate-400">{target.scope.join(", ")}</td><td className="px-4 py-3 font-mono text-[10px] text-slate-400">{target.source}</td><td className="px-4 py-3"><span className="rounded-full border border-white/10 px-2 py-1 font-mono text-[10px] text-cyan-200">{target.collection_status}</span></td><td className="px-4 py-3 font-mono text-[10px] text-slate-500">{target.last_successful_collection ? new Date(target.last_successful_collection).toLocaleString() : "--"}</td></tr>)}</tbody></table></div>}
      </div>
    </div>
  );
}
