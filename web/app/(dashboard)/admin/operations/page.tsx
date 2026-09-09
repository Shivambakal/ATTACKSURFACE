"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Target } from "@/lib/types";

export default function AdminOperationsPage() {
  const [targetList, setTargetList] = useState<Target[]>([]);
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null);
  const [runningTarget, setRunningTarget] = useState(false);
  const [targetRunResult, setTargetRunResult] = useState<any>(null);
  const [targetRunError, setTargetRunError] = useState<string | null>(null);

  const [triggeringProof, setTriggeringProof] = useState(false);
  const [proofMessage, setProofMessage] = useState<string | null>(null);

  const [opsData, setOpsData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [targets, ops] = await Promise.all([
        apiFetch<Target[]>("/api/v1/targets").catch(() => []),
        apiFetch<any>("/api/v1/admin/operations").catch(() => null),
      ]);
      if (Array.isArray(targets) && targets.length > 0) {
        setTargetList(targets);
        if (!selectedTargetId) setSelectedTargetId(targets[0].id);
      }
      setOpsData(ops);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunTarget = async () => {
    if (!selectedTargetId) return;
    setRunningTarget(true);
    setTargetRunResult(null);
    setTargetRunError(null);
    try {
      const res = await apiFetch<any>(`/api/v1/admin/run-target/${selectedTargetId}`, {
        method: "POST",
      });
      setTargetRunResult(res);
      loadData();
    } catch (err: unknown) {
      setTargetRunError(err instanceof Error ? err.message : "Target pipeline run failed");
    } finally {
      setRunningTarget(false);
    }
  };

  const handleTriggerProofRun = async () => {
    try {
      setTriggeringProof(true);
      setProofMessage("Executing live collection through all 9 stages...");
      const res = await apiFetch<any>("/api/v1/admin/trigger-proof-run", {
        method: "POST",
      });
      if (res?.success) {
        setProofMessage("Verified live proof execution completed successfully!");
      } else {
        setProofMessage(`Completed with status: ${res?.fetch_result?.status || "Check telemetry"}`);
      }
      loadData();
    } catch (err: any) {
      setProofMessage(`Error executing verified run: ${err.message || String(err)}`);
    } finally {
      setTriggeringProof(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
        <Link href="/admin" className="text-amber-400 hover:underline">Admin Console</Link>
        <span>/</span>
        <span className="text-white">Operations</span>
      </div>

      {/* Header */}
      <div className="bg-slate-900/90 border border-amber-500/20 rounded-xl p-6 shadow-xl backdrop-blur">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </span>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Operations Control Plane</h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Manual and scheduled pipeline execution, verified proof triggers, and background job dispatch.
              </p>
            </div>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="px-3.5 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition"
          >
            {loading ? "Refreshing..." : "↻ Refresh"}
          </button>
        </div>
      </div>

      {/* Quick KPI Overview */}
      {opsData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
            <span className="text-xs text-slate-400 block mb-1">System Status</span>
            <span className="text-lg font-bold text-emerald-400 font-mono">{opsData.system_status}</span>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
            <span className="text-xs text-slate-400 block mb-1">Active Workers</span>
            <span className="text-lg font-bold text-white font-mono">{opsData.active_workers} Active</span>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
            <span className="text-xs text-slate-400 block mb-1">Queued Jobs</span>
            <span className="text-lg font-bold text-amber-400 font-mono">{opsData.total_queued_jobs}</span>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
            <span className="text-xs text-slate-400 block mb-1">Changes (24h)</span>
            <span className="text-lg font-bold text-cyan-400 font-mono">{opsData.changes_24h}</span>
          </div>
        </div>
      )}

      {/* Target Manual Pipeline Execution */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-lg">
        <h3 className="text-base font-semibold text-white mb-1">Direct Target Pipeline Execution</h3>
        <p className="text-xs text-slate-400 mb-4">
          Execute full 9-stage analysis on an authorized bug bounty target: HTTP collect, diff, correlate KEV, and synthesize signals.
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedTargetId ?? ""}
            onChange={(e) => setSelectedTargetId(Number(e.target.value))}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 outline-none focus:border-cyan-500 max-w-sm flex-1"
          >
            {targetList.map((t) => (
              <option key={t.id} value={t.id}>
                #{t.id} - {t.domain} ({t.company_name || "Public"})
              </option>
            ))}
            {targetList.length === 0 && <option value="">No targets registered</option>}
          </select>

          <button
            onClick={handleRunTarget}
            disabled={runningTarget || !selectedTargetId}
            className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-40 flex items-center gap-2"
          >
            {runningTarget ? (
              <>
                <div className="h-3 w-3 animate-spin rounded-full border border-slate-950 border-t-transparent" />
                <span>EXECUTING 9 STAGES...</span>
              </>
            ) : (
              <span>▶ RUN TARGET PIPELINE</span>
            )}
          </button>
        </div>

        {targetRunError && (
          <div className="mt-3 rounded-lg border border-red-800 bg-red-950/40 p-3 text-xs text-red-300">
            {targetRunError}
          </div>
        )}

        {targetRunResult && (
          <div className="mt-4 rounded-lg border border-cyan-500/30 bg-cyan-950/20 p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-cyan-300">
                PIPELINE EXECUTION REPORT: {targetRunResult.target_domain} (ID #{targetRunResult.target_id})
              </span>
              <span className="font-mono text-[10px] text-slate-400">
                Status: {targetRunResult.status} ({targetRunResult.duration_ms}ms)
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
              <div className="bg-slate-900/80 p-2.5 rounded border border-slate-800 font-mono">
                <span className="text-[10px] text-slate-400 block">Snapshot ID</span>
                <span className="text-white font-bold">#{targetRunResult.snapshot_id}</span>
              </div>
              <div className="bg-slate-900/80 p-2.5 rounded border border-slate-800 font-mono">
                <span className="text-[10px] text-slate-400 block">Accepted Changes</span>
                <span className="text-cyan-400 font-bold">{targetRunResult.changes_detected}</span>
              </div>
              <div className="bg-slate-900/80 p-2.5 rounded border border-slate-800 font-mono">
                <span className="text-[10px] text-slate-400 block">Gated Signals</span>
                <span className="text-amber-400 font-bold">{targetRunResult.signals_created}</span>
              </div>
              <div className="bg-slate-900/80 p-2.5 rounded border border-slate-800 font-mono">
                <span className="text-[10px] text-slate-400 block">Timeline Events</span>
                <span className="text-emerald-400 font-bold">{targetRunResult.timeline_events_created}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Verified Live Proof Run Trigger */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-white">Verified End-to-End Test Cycle</h3>
            <p className="text-xs text-slate-400 mt-1">
              Trigger a synchronous fetch of an active public source (e.g., Cloudflare Developer Changelog) through all 9 stages to generate immutable pipeline proof.
            </p>
          </div>
          <button
            onClick={handleTriggerProofRun}
            disabled={triggeringProof}
            className="px-4 py-2 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-500 active:bg-amber-700 disabled:opacity-50 rounded-lg shadow transition"
          >
            {triggeringProof ? "Running Verified Cycle..." : "▶ Trigger Verified Test Cycle"}
          </button>
        </div>

        {proofMessage && (
          <div className="mt-3 bg-amber-950/40 border border-amber-500/30 rounded-lg p-3 text-xs text-amber-300 flex items-center justify-between">
            <span>{proofMessage}</span>
            <button onClick={() => setProofMessage(null)} className="text-amber-400 hover:text-white font-bold ml-4">
              ✕
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
