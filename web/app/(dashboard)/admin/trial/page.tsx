"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
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
  target_status?: Array<{
    company: string;
    domain: string;
    scope: string[];
    source: string;
    authorization_source: string;
    collection_status: string;
    last_successful_collection?: string | null;
  }>;
}

const metricCards = [
  ["targets", "TARGETS", "Explicit registry"],
  ["collection_cycles", "COLLECTION CYCLES", "24 hour window"],
  ["success", "SUCCESS", "Completed or empty"],
  ["failed", "FAILED", "Needs review"],
  ["assets_discovered", "ASSETS DISCOVERED", "Observed assets"],
  ["real_changes", "REAL CHANGES", "After dedup + noise"],
  ["duplicates", "DUPLICATES", "Collapsed records"],
  ["noise_rejected", "NOISE REJECTED", "Quality gate"],
  ["security_correlations", "SECURITY CORRELATIONS", "Context only"],
  ["research_signals", "RESEARCH SIGNALS", "Prioritized leads"],
  ["high_value_findings", "HIGH-VALUE FINDINGS", "Signals, not claims"],
  ["evidence_records", "EVIDENCE RECORDS", "Source-backed"],
] as const;

export default function AdminTrialPage() {
  const [metrics, setMetrics] = useState<TrialMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadMetrics = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<TrialMetrics>("/api/v1/trial/metrics");
      setMetrics(data);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Trial metrics unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMetrics();
    const timer = setInterval(loadMetrics, 20000);
    return () => clearInterval(timer);
  }, [loadMetrics]);

  const startTrial = async () => {
    setStarting(true);
    setMessage(null);
    try {
      await apiFetch("/api/v1/trial/start", { method: "POST" });
      setMessage("Trial queued successfully. Existing passive snapshot workers are processing the 50 authorized targets.");
      await loadMetrics();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not start trial");
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Link
              href="/admin"
              className="text-xs font-mono text-slate-400 hover:text-slate-200 transition"
            >
              ADMIN
            </Link>
            <span className="text-xs text-slate-600">/</span>
            <span className="text-xs font-mono text-cyan-400">50 TARGET TRIAL</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
            50 Target Controlled Evaluation
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Measure useful, source-backed intelligence across an explicit authorized registry over a 24-hour evaluation window.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={startTrial}
            disabled={starting}
            className="rounded-lg bg-cyan-500 hover:bg-cyan-400 px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-slate-950 transition disabled:opacity-50 flex items-center gap-2"
          >
            {starting ? (
              <>
                <svg className="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Queuing Trial...
              </>
            ) : (
              "Start 24H Trial"
            )}
          </button>
          <button
            onClick={loadMetrics}
            disabled={loading}
            className="px-3 py-2 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-xs font-mono text-slate-200 transition disabled:opacity-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {message && (
        <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-4 text-xs font-mono text-cyan-300">
          {message}
        </div>
      )}

      {/* 12 Metrics KPI Grid */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
        {metricCards.map(([key, label, hint]) => (
          <div
            key={key}
            className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-3.5 backdrop-blur-sm"
          >
            <p className="font-mono text-[9px] uppercase tracking-wider text-slate-500 truncate">
              {label}
            </p>
            <p className="mt-2 text-2xl font-bold font-mono tracking-tight text-white">
              {loading ? "--" : (metrics?.[key as keyof TrialMetrics] as number) ?? 0}
            </p>
            <p className="mt-1 text-[10px] text-slate-500 font-mono truncate">{hint}</p>
          </div>
        ))}
      </div>

      {/* Target Status Ledger */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 overflow-hidden backdrop-blur-sm">
        <div className="flex flex-col gap-2 border-b border-slate-800 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white">Trial Target Ledger</h3>
            <p className="text-xs text-slate-500">
              Scope and source attribution are verified and retained for every target.
            </p>
          </div>
          <span className="font-mono text-xs uppercase tracking-widest text-cyan-400 bg-cyan-500/10 px-2.5 py-1 rounded border border-cyan-500/20">
            {metrics?.status || "NOT STARTED"}
          </span>
        </div>

        {!metrics?.target_status?.length ? (
          <div className="py-16 text-center font-mono text-xs text-slate-500">
            No trial run in progress. Click &quot;Start 24H Trial&quot; to queue passive collection across the authorized registry.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="border-b border-slate-800 bg-slate-950/60 text-slate-400">
                <tr>
                  <th className="py-3 px-4 font-semibold">Company</th>
                  <th className="py-3 px-4 font-semibold">Domain</th>
                  <th className="py-3 px-4 font-semibold">Scope</th>
                  <th className="py-3 px-4 font-semibold">Source</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Last Success</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {metrics.target_status.map((target) => (
                  <tr key={target.domain} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4 text-white font-medium">{target.company}</td>
                    <td className="py-3 px-4 text-cyan-300">{target.domain}</td>
                    <td className="py-3 px-4 text-slate-400 max-w-[200px] truncate">
                      {target.scope.join(", ")}
                    </td>
                    <td className="py-3 px-4 text-slate-500">{target.source}</td>
                    <td className="py-3 px-4">
                      <span className="rounded px-2 py-0.5 text-[10px] font-bold border border-cyan-500/30 bg-cyan-500/10 text-cyan-300">
                        {target.collection_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500 text-[11px]">
                      {target.last_successful_collection
                        ? new Date(target.last_successful_collection).toLocaleString()
                        : "--"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
