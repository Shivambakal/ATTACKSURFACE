"use client";

import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Target } from "@/lib/types";

interface SystemHealth {
  status: string;
  uptime_seconds: number;
  database: {
    healthy: boolean;
    latency_ms: number;
    migration_revision: string;
    error?: string;
  };
  redis: {
    healthy: boolean;
    latency_ms: number;
    error?: string;
  };
  workers: {
    active_count: number;
    worker_names: string[];
  };
  timestamp: string;
}

interface PipelineStage {
  index: number;
  name: string;
  key: string;
  count: number;
  description: string;
}

interface PipelineHealth {
  stages: PipelineStage[];
  pipeline_operational: boolean;
  last_evaluated: string;
}

interface ProviderOp {
  name: string;
  category: string;
  auth_required: boolean;
  auth_configured: boolean;
  status: string;
  last_success_at: string | null;
  records_ingested: number;
  quota_info: string;
  recommended_action: string;
}

interface QueueInfo {
  name: string;
  length: number;
  failed_count: number;
  is_empty: boolean;
}

interface QueueTelemetry {
  total_queued: number;
  queues: QueueInfo[];
  redis_connected: boolean;
}

interface ChangeCounters {
  today: number;
  last_24h: number;
  last_7d: number;
  last_30d: number;
}

interface ActivityItem {
  id: number;
  type: string;
  source_id: number;
  source_name: string;
  company_name: string;
  status: string;
  http_status: number;
  items_found: number;
  items_changed: number;
  duration_ms: number;
  response_bytes: number;
  error_message: string | null;
  timestamp: string;
}

interface ErrorCenter {
  failed_runs_24h_count: number;
  degraded_sources_count: number;
  recent_errors: Array<{
    run_id: number;
    source_name: string;
    status: string;
    http_status: number;
    error_message: string;
    timestamp: string;
    recommended_fix: string;
  }>;
}

interface PipelineProof {
  proof_available: boolean;
  message?: string;
  provenance_trace?: {
    step_1_source: {
      source_id: number;
      name: string;
      company_name: string;
      url: string;
      authority_level: string;
      parser_strategy: string;
    };
    step_2_live_http: {
      run_id: number;
      http_status: number;
      duration_ms: number;
      response_bytes: number;
      status: string;
      executed_at: string;
    };
    step_3_raw_snapshot: {
      snapshot_id: number;
      content_hash_sha256: string;
      body_size_bytes: number;
      retrieved_at: string;
      body_raw_preview: string;
    };
    step_4_normalized_document: {
      norm_doc_id: number;
      items_extracted_count: number;
      parser_name: string;
      parser_version: string;
      sample_item: any;
    };
    step_5_change_clusters: Array<{
      id: number;
      title: string;
      primary_category: string;
      source_count: number;
      fingerprint: string;
      created_at: string;
    }>;
    step_6_timeline_events: Array<{
      id: number;
      title: string;
      event_type: string;
      priority: string;
      confidence: number;
      relevance_score: number;
      observed_at: string;
    }>;
    step_7_research_signals: Array<{
      id: number;
      title: string;
      signal_type: string;
      priority: string;
      why_it_matters: string;
      relevance_score: number;
      created_at: string;
    }>;
  };
  verified_end_to_end?: boolean;
}

export default function AdminControlCenterPage() {
  const { user } = useAuth();
  const isAuthorizedAdmin = user?.role === "OWNER" || user?.role === "ADMIN" || Boolean(user?.is_admin);

  const [activeTab, setActiveTab] = useState<"pipeline" | "providers" | "queues" | "proof" | "health">("pipeline");
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [triggerMessage, setTriggerMessage] = useState<string | null>(null);

  // Target run state
  const [targetList, setTargetList] = useState<Target[]>([]);
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null);
  const [runningTarget, setRunningTarget] = useState(false);
  const [targetRunResult, setTargetRunResult] = useState<any>(null);
  const [targetRunError, setTargetRunError] = useState<string | null>(null);

  // Data states
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [pipeline, setPipeline] = useState<PipelineHealth | null>(null);
  const [providers, setProviders] = useState<ProviderOp[]>([]);
  const [queues, setQueues] = useState<QueueTelemetry | null>(null);
  const [counters, setCounters] = useState<ChangeCounters | null>(null);
  const [dbStats, setDbStats] = useState<Record<string, number>>({});
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [errors, setErrors] = useState<ErrorCenter | null>(null);
  const [proof, setProof] = useState<PipelineProof | null>(null);

  const fetchAllTelemetry = async () => {
    if (!isAuthorizedAdmin) return;
    try {
      setLoading(true);
      const [h, p, prov, q, c, db, act, err, prf] = await Promise.all([
        apiFetch<SystemHealth>("/api/v1/admin/health").catch(() => null),
        apiFetch<PipelineHealth>("/api/v1/admin/pipeline").catch(() => null),
        apiFetch<ProviderOp[]>("/api/v1/admin/providers").catch(() => []),
        apiFetch<QueueTelemetry>("/api/v1/admin/queues").catch(() => null),
        apiFetch<ChangeCounters>("/api/v1/admin/change-counters").catch(() => null),
        apiFetch<Record<string, number>>("/api/v1/admin/db-stats").catch(() => ({})),
        apiFetch<ActivityItem[]>("/api/v1/admin/activity?limit=15").catch(() => []),
        apiFetch<ErrorCenter>("/api/v1/admin/errors").catch(() => null),
        apiFetch<PipelineProof>("/api/v1/admin/proof").catch(() => null),
      ]);

      setHealth(h);
      setPipeline(p);
      setProviders(prov || []);
      setQueues(q);
      setCounters(c);
      setDbStats(db || {});
      setActivity(act || []);
      setErrors(err);
      setProof(prf);
    } catch (err) {
      console.error("Telemetry fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthorizedAdmin) {
      fetchAllTelemetry();
      apiFetch<Target[]>("/api/v1/targets")
        .then((targets) => {
          if (Array.isArray(targets) && targets.length > 0) {
            setTargetList(targets);
            setSelectedTargetId(targets[0].id);
          }
        })
        .catch(() => {});
    } else {
      setLoading(false);
    }
  }, [isAuthorizedAdmin]);

  const handleRunTargetPipeline = async () => {
    if (!selectedTargetId) return;
    setRunningTarget(true);
    setTargetRunResult(null);
    setTargetRunError(null);
    try {
      const res = await apiFetch<any>(`/api/v1/admin/run-target/${selectedTargetId}`, {
        method: "POST",
      });
      setTargetRunResult(res);
      fetchAllTelemetry();
    } catch (err: unknown) {
      setTargetRunError(err instanceof Error ? err.message : "Target pipeline run failed");
    } finally {
      setRunningTarget(false);
    }
  };

  const handleTriggerProofRun = async () => {
    try {
      setTriggering(true);
      setTriggerMessage("Executing live collection through all 9 stages...");
      const res = await apiFetch<any>("/api/v1/admin/trigger-proof-run", {
        method: "POST",
      });

      if (res?.success) {
        setTriggerMessage("Verified live proof execution completed successfully!");
      } else {
        setTriggerMessage(`Execution completed: ${res?.fetch_result?.status || "Check telemetry"}`);
      }

      // Re-fetch all and switch to proof tab
      await fetchAllTelemetry();
      setActiveTab("proof");
    } catch (err: any) {
      setTriggerMessage(`Error executing verified run: ${err.message || String(err)}`);
    } finally {
      setTriggering(false);
    }
  };

  const formatUptime = (secs: number) => {
    const hours = Math.floor(secs / 3600);
    const mins = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    return `${hours}h ${mins}m ${s}s`;
  };

  if (user && !isAuthorizedAdmin) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
        <div className="inline-flex p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 font-mono text-xl">
          403 FORBIDDEN
        </div>
        <h2 className="text-xl font-bold text-white">Administrative Access Restricted</h2>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          The Admin Control Center and operational pipeline controls require an <span className="font-semibold text-slate-200">OWNER</span> or <span className="font-semibold text-slate-200">ADMIN</span> role.
        </p>
        <div className="inline-block rounded-lg border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono text-slate-300">
          Current Session: <span className="text-amber-400 font-bold">{user.role || "RESEARCHER"}</span> ({user.email})
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header & Mission Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xl backdrop-blur">
        <div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center justify-center p-2 bg-cyan-500/10 text-cyan-400 rounded-lg border border-cyan-500/20">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </span>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Admin Control Center</h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Reality-First Pipeline Observability & End-to-End Data Flow Proof
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={fetchAllTelemetry}
            disabled={loading || triggering}
            className="px-3.5 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition"
          >
            {loading ? "Refreshing..." : "↻ Refresh Telemetry"}
          </button>
          <button
            onClick={handleTriggerProofRun}
            disabled={triggering}
            className="px-4 py-2 text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 active:bg-cyan-700 disabled:opacity-50 rounded-lg shadow-lg shadow-cyan-600/20 transition flex items-center gap-2"
          >
            {triggering ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Verifying Live Pipeline...</span>
              </>
            ) : (
              <>
                <span>▶ Trigger Verified Live Run</span>
              </>
            )}
          </button>
        </div>
      </div>

      {triggerMessage && (
        <div className="bg-cyan-950/40 border border-cyan-500/30 rounded-lg p-3 text-xs text-cyan-300 flex items-center justify-between">
          <span>{triggerMessage}</span>
          <button onClick={() => setTriggerMessage(null)} className="text-cyan-400 hover:text-white font-bold ml-4">
            ✕
          </button>
        </div>
      )}

      {/* Target Manual Pipeline Execution Control */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-cyan-400" />
              <h3 className="text-sm font-semibold text-white">Target Pipeline Direct Execution</h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Execute collection, differential fingerprinting, security correlation, and signal quality gating on an authorized target.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedTargetId ?? ""}
              onChange={(e) => setSelectedTargetId(Number(e.target.value))}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 outline-none focus:border-cyan-500 max-w-xs"
            >
              {targetList.map((t) => (
                <option key={t.id} value={t.id}>
                  #{t.id} - {t.domain} ({t.company_name || "Public"})
                </option>
              ))}
              {targetList.length === 0 && <option value="">No targets registered</option>}
            </select>

            <button
              onClick={handleRunTargetPipeline}
              disabled={runningTarget || !selectedTargetId}
              className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-40 flex items-center gap-2"
            >
              {runningTarget ? (
                <>
                  <div className="h-3 w-3 animate-spin rounded-full border border-slate-950 border-t-transparent" />
                  <span>RUNNING PIPELINE...</span>
                </>
              ) : (
                <>
                  <span>▶</span>
                  <span>RUN NOW</span>
                </>
              )}
            </button>
          </div>
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
                Status: {targetRunResult.status}
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

      {/* Quick Status Cards (Section A & E) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Postgres */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>PostgreSQL Engine</span>
            <span className={`w-2 h-2 rounded-full ${health?.database.healthy ? "bg-emerald-400" : "bg-rose-400 animate-ping"}`} />
          </div>
          <div className="text-lg font-bold text-white">
            {health?.database.healthy ? "CONNECTED" : "DISCONNECTED"}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Latency: {health?.database.latency_ms ?? "--"} ms</span>
            <span className="font-mono text-cyan-400">Rev: {health?.database.migration_revision?.slice(0, 8)}</span>
          </div>
        </div>

        {/* Redis & RQ Workers */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Redis & RQ Workers</span>
            <span className={`w-2 h-2 rounded-full ${health?.redis.healthy ? "bg-emerald-400" : "bg-rose-400"}`} />
          </div>
          <div className="text-lg font-bold text-white">
            {health?.workers.active_count ?? 0} Active Worker{(health?.workers.active_count ?? 0) !== 1 ? "s" : ""}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Redis: {health?.redis.latency_ms ?? "--"} ms</span>
            <span className="text-amber-400 font-semibold">{queues?.total_queued ?? 0} Queued</span>
          </div>
        </div>

        {/* Changes Detected */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Changes (24h / 7d)</span>
            <span className="text-[10px] text-cyan-400 font-mono">Today: {counters?.today ?? 0}</span>
          </div>
          <div className="text-lg font-bold text-white">
            {counters?.last_24h ?? 0} <span className="text-xs font-normal text-slate-400">/ {counters?.last_7d ?? 0}</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            <span>30-Day Window: {counters?.last_30d ?? 0} clusters</span>
          </div>
        </div>

        {/* System Uptime */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>System State</span>
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
              health?.status === "HEALTHY" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" : "bg-amber-500/10 text-amber-400 border border-amber-500/30"
            }`}>
              {health?.status ?? "CHECKING"}
            </span>
          </div>
          <div className="text-lg font-bold text-white font-mono">
            {health ? formatUptime(health.uptime_seconds) : "--"}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            <span>Process Uptime</span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-800 flex items-center gap-6 text-sm font-medium">
        <button
          onClick={() => setActiveTab("pipeline")}
          className={`pb-3 border-b-2 transition ${
            activeTab === "pipeline"
              ? "border-cyan-400 text-cyan-400 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          9-Stage Pipeline Flow
        </button>
        <button
          onClick={() => setActiveTab("providers")}
          className={`pb-3 border-b-2 transition ${
            activeTab === "providers"
              ? "border-cyan-400 text-cyan-400 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Provider Operations ({providers.length})
        </button>
        <button
          onClick={() => setActiveTab("proof")}
          className={`pb-3 border-b-2 transition flex items-center gap-2 ${
            activeTab === "proof"
              ? "border-emerald-400 text-emerald-400 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>Pipeline Proof Inspector</span>
          {proof?.verified_end_to_end && (
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
          )}
        </button>
        <button
          onClick={() => setActiveTab("queues")}
          className={`pb-3 border-b-2 transition ${
            activeTab === "queues"
              ? "border-cyan-400 text-cyan-400 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Live Queues & Activity
        </button>
        <button
          onClick={() => setActiveTab("health")}
          className={`pb-3 border-b-2 transition ${
            activeTab === "health"
              ? "border-cyan-400 text-cyan-400 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Database & Health
        </button>
      </div>

      {/* TAB 1: 9-Stage Pipeline Flow (Section B) */}
      {activeTab === "pipeline" && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-semibold text-white">Full Intelligence Pipeline Architecture</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Chronological progression of data from external world fetch to prioritized security signals.
                </p>
              </div>
              <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                pipeline?.pipeline_operational ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" : "bg-slate-800 text-slate-400"
              }`}>
                {pipeline?.pipeline_operational ? "PIPELINE OPERATIONAL" : "IDLE"}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {pipeline?.stages.map((st) => (
                <div key={st.index} className="bg-slate-950/80 border border-slate-800/80 rounded-lg p-4 relative overflow-hidden">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-cyan-400 tracking-wider uppercase">
                      Stage {st.index}
                    </span>
                    <span className="text-lg font-mono font-bold text-white">
                      {st.count.toLocaleString()}
                    </span>
                  </div>
                  <h4 className="text-sm font-semibold text-slate-200 mt-1">{st.name}</h4>
                  <p className="text-xs text-slate-400 mt-1">{st.description}</p>
                  <div className="mt-3 flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${st.count > 0 ? "bg-emerald-400" : "bg-slate-600"}`} />
                    <span className="text-[10px] text-slate-400 font-mono">
                      {st.count > 0 ? "Observed In Database" : "Pending Ingest"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Error Center (Section H) */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-white">Error Center & Degraded Sources</h3>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                (errors?.failed_runs_24h_count ?? 0) > 0 ? "bg-rose-500/10 text-rose-400 border border-rose-500/30" : "bg-emerald-500/10 text-emerald-400"
              }`}>
                {errors?.failed_runs_24h_count ?? 0} Failures (24h)
              </span>
            </div>

            {errors?.recent_errors && errors.recent_errors.length > 0 ? (
              <div className="divide-y divide-slate-800">
                {errors.recent_errors.map((err, i) => (
                  <div key={i} className="py-3 flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs">
                    <div>
                      <span className="font-semibold text-rose-400">[{err.status}]</span>{" "}
                      <span className="text-slate-200 font-medium">{err.source_name}</span>:{" "}
                      <span className="text-slate-400">{err.error_message || "Unknown error"}</span>
                    </div>
                    <div className="text-slate-400 text-[11px] flex items-center gap-3">
                      <span>Rec: {err.recommended_fix}</span>
                      <span className="font-mono">{new Date(err.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400">No collection failures or rate limits recorded in the last 24 hours.</p>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: Provider Operations (Section C) */}
      {activeTab === "providers" && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-5 border-b border-slate-800">
            <h3 className="text-base font-semibold text-white">External Intelligence Provider Registry</h3>
            <p className="text-xs text-slate-400 mt-1">
              Strict truth operations table. Healthy requires verified request execution. Quota unknown indicates no public quota API exists.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Provider</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Authentication</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Records Ingested</th>
                  <th className="py-3 px-4">Quota Information</th>
                  <th className="py-3 px-4">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {providers.map((p, idx) => (
                  <tr key={idx} className="hover:bg-slate-850/50 transition">
                    <td className="py-3 px-4 font-semibold text-slate-200">{p.name}</td>
                    <td className="py-3 px-4 text-slate-400">{p.category}</td>
                    <td className="py-3 px-4">
                      {!p.auth_required ? (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/30">
                          Public Feed
                        </span>
                      ) : p.auth_configured ? (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                          Key Configured
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/30">
                          Key Missing
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold">
                      <span className={`px-2 py-0.5 rounded text-[10px] ${
                        p.status === "HEALTHY" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" :
                        p.status === "CONFIGURED" || p.status === "AVAILABLE" ? "bg-cyan-500/10 text-cyan-400" :
                        p.status === "NEVER_RUN" ? "bg-slate-800 text-slate-400" : "bg-rose-500/10 text-rose-400"
                      }`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300">
                      {p.records_ingested > 0 ? p.records_ingested.toLocaleString() : "--"}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400 text-[11px]">
                      {p.quota_info}
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px]">
                      {p.recommended_action}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: Pipeline Proof Inspector (Section I & J) */}
      {activeTab === "proof" && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-6">
              <div>
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <span>Verified End-to-End Pipeline Proof</span>
                  {proof?.verified_end_to_end && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                      VERIFIED E2E PROVENANCE
                    </span>
                  )}
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Complete immutable trace showing how a real external change enters through HTTP, gets hashed, normalized, clustered, and surfaces on the timeline.
                </p>
              </div>

              <button
                onClick={handleTriggerProofRun}
                disabled={triggering}
                className="px-3.5 py-1.5 text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg shadow transition"
              >
                {triggering ? "Executing..." : "Run Verified Test Cycle"}
              </button>
            </div>

            {proof?.proof_available && proof.provenance_trace ? (
              <div className="space-y-6">
                {/* Step 1 & 2 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Step 1: Source */}
                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                    <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Step 1: Source Origin</span>
                    <h4 className="text-sm font-bold text-white mt-1">{proof.provenance_trace.step_1_source.name}</h4>
                    <div className="mt-2 space-y-1 text-xs text-slate-400 font-mono">
                      <div>Company: <span className="text-slate-200">{proof.provenance_trace.step_1_source.company_name}</span></div>
                      <div>Authority: <span className="text-cyan-300">{proof.provenance_trace.step_1_source.authority_level}</span></div>
                      <div>Strategy: <span className="text-slate-300">{proof.provenance_trace.step_1_source.parser_strategy}</span></div>
                      <div className="truncate">URL: <a href={proof.provenance_trace.step_1_source.url} target="_blank" rel="noreferrer" className="text-cyan-400 hover:underline">{proof.provenance_trace.step_1_source.url}</a></div>
                    </div>
                  </div>

                  {/* Step 2: Live HTTP */}
                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                    <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Step 2: Live HTTP Response</span>
                    <h4 className="text-sm font-bold text-white mt-1">Run #{proof.provenance_trace.step_2_live_http.run_id} — {proof.provenance_trace.step_2_live_http.status}</h4>
                    <div className="mt-2 space-y-1 text-xs text-slate-400 font-mono">
                      <div>HTTP Status: <span className="text-emerald-400 font-bold">{proof.provenance_trace.step_2_live_http.http_status}</span></div>
                      <div>Roundtrip Latency: <span className="text-slate-200">{proof.provenance_trace.step_2_live_http.duration_ms} ms</span></div>
                      <div>Payload Received: <span className="text-slate-200">{(proof.provenance_trace.step_2_live_http.response_bytes / 1024).toFixed(1)} KB</span></div>
                      <div>Timestamp: <span className="text-slate-400">{new Date(proof.provenance_trace.step_2_live_http.executed_at).toLocaleString()}</span></div>
                    </div>
                  </div>
                </div>

                {/* Step 3: Raw Snapshot */}
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                  <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Step 3: Immutable Raw Snapshot (PostgreSQL)</span>
                  <div className="mt-2 flex flex-col md:flex-row md:items-center justify-between text-xs font-mono text-slate-400 gap-2">
                    <div>Snapshot ID: <span className="text-white font-bold">{proof.provenance_trace.step_3_raw_snapshot.snapshot_id}</span></div>
                    <div>SHA-256: <span className="text-cyan-400 font-bold">{proof.provenance_trace.step_3_raw_snapshot.content_hash_sha256}</span></div>
                    <div>Stored Size: <span className="text-slate-200">{proof.provenance_trace.step_3_raw_snapshot.body_size_bytes} bytes</span></div>
                  </div>
                  <div className="mt-3 bg-slate-900 border border-slate-800/80 rounded p-3 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-36">
                    {proof.provenance_trace.step_3_raw_snapshot.body_raw_preview}
                  </div>
                </div>

                {/* Step 4: Normalized Document */}
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                  <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider">Step 4: Normalized Structured Document</span>
                  <div className="mt-2 flex items-center justify-between text-xs font-mono text-slate-400">
                    <div>Document ID: <span className="text-white font-bold">{proof.provenance_trace.step_4_normalized_document.norm_doc_id}</span></div>
                    <div>Extracted Items: <span className="text-emerald-400 font-bold">{proof.provenance_trace.step_4_normalized_document.items_extracted_count} items</span></div>
                    <div>Parser: <span className="text-slate-300">{proof.provenance_trace.step_4_normalized_document.parser_name} v{proof.provenance_trace.step_4_normalized_document.parser_version}</span></div>
                  </div>
                  {proof.provenance_trace.step_4_normalized_document.sample_item && (
                    <div className="mt-3 bg-slate-900 border border-slate-800/80 rounded p-3 text-[11px] font-mono text-slate-300 overflow-x-auto">
                      <pre>{JSON.stringify(proof.provenance_trace.step_4_normalized_document.sample_item, null, 2)}</pre>
                    </div>
                  )}
                </div>

                {/* Step 5 & 6 & 7: Clustered Entities, Timeline & Signals */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Step 5: Change Cluster */}
                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                    <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Step 5: Change Cluster</span>
                    <div className="mt-2 space-y-2">
                      {proof.provenance_trace.step_5_change_clusters.map((c) => (
                        <div key={c.id} className="text-xs bg-slate-900 p-2.5 rounded border border-slate-800">
                          <div className="font-semibold text-slate-200">{c.title}</div>
                          <div className="text-[11px] text-cyan-400 font-mono mt-0.5">{c.primary_category}</div>
                          <div className="text-[10px] text-slate-400 font-mono truncate mt-1">fp: {c.fingerprint}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Step 6: Timeline Event */}
                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                    <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Step 6: Timeline Events</span>
                    <div className="mt-2 space-y-2">
                      {proof.provenance_trace.step_6_timeline_events.map((e) => (
                        <div key={e.id} className="text-xs bg-slate-900 p-2.5 rounded border border-slate-800">
                          <div className="font-semibold text-slate-200">{e.title}</div>
                          <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                            <span className="text-emerald-400 font-mono">{e.event_type}</span>
                            <span className="font-bold text-amber-300">Score: {e.relevance_score}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Step 7: Research Signal */}
                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                    <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Step 7: Research Signal</span>
                    <div className="mt-2 space-y-2">
                      {proof.provenance_trace.step_7_research_signals.map((s) => (
                        <div key={s.id} className="text-xs bg-slate-900 p-2.5 rounded border border-slate-800">
                          <div className="font-semibold text-slate-200">{s.title}</div>
                          <div className="text-[11px] text-amber-300 font-mono mt-0.5">{s.signal_type} ({s.priority})</div>
                          <p className="text-[10px] text-slate-400 mt-1 line-clamp-2">{s.why_it_matters}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 bg-slate-950 rounded-lg border border-slate-800/80">
                <svg className="w-12 h-12 text-slate-600 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h4 className="text-sm font-semibold text-slate-300">No Verified Live Proof Recorded Yet</h4>
                <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                  Click the "Run Verified Test Cycle" button above to execute a real live fetch of a registered public source through all 9 pipeline stages.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: Live Queues & Activity (Section D & F) */}
      {activeTab === "queues" && (
        <div className="space-y-6">
          {/* RQ Priority Queues */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-white">RQ Priority Queue Depths</h3>
              <span className="text-xs text-slate-400 font-mono">Total Queued: {queues?.total_queued ?? 0}</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
              {queues?.queues.map((q) => (
                <div key={q.name} className="bg-slate-950 border border-slate-800/80 rounded-lg p-3">
                  <div className="text-[11px] font-mono text-slate-400 truncate">{q.name}</div>
                  <div className="text-lg font-mono font-bold text-white mt-1">{q.length}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5 flex items-center justify-between">
                    <span>Failed: {q.failed_count}</span>
                    <span className={`w-1.5 h-1.5 rounded-full ${q.is_empty ? "bg-slate-600" : "bg-cyan-400 animate-pulse"}`} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Live Activity Feed */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="p-5 border-b border-slate-800">
              <h3 className="text-base font-semibold text-white">Live Collection Runs</h3>
              <p className="text-xs text-slate-400 mt-1">Chronological record of recent source fetches and status returns.</p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Time</th>
                    <th className="py-3 px-4">Source</th>
                    <th className="py-3 px-4">Company</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">HTTP Status</th>
                    <th className="py-3 px-4">Items (Found / Changed)</th>
                    <th className="py-3 px-4">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {activity.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-850/50">
                      <td className="py-3 px-4 font-mono text-slate-400">{new Date(a.timestamp).toLocaleTimeString()}</td>
                      <td className="py-3 px-4 font-semibold text-slate-200">{a.source_name}</td>
                      <td className="py-3 px-4 text-slate-400">{a.company_name}</td>
                      <td className="py-3 px-4 font-mono font-bold">
                        <span className={`px-2 py-0.5 rounded text-[10px] ${
                          a.status === "SUCCESS_CHANGED" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" :
                          a.status === "SUCCESS_UNCHANGED" ? "bg-slate-800 text-slate-400" : "bg-rose-500/10 text-rose-400"
                        }`}>
                          {a.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">{a.http_status || "--"}</td>
                      <td className="py-3 px-4 font-mono text-slate-300">{a.items_found} / {a.items_changed}</td>
                      <td className="py-3 px-4 font-mono text-slate-400">{a.duration_ms} ms</td>
                    </tr>
                  ))}
                  {activity.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-400">
                        No collection runs recorded yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: Database & Health (Section G) */}
      {activeTab === "health" && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="text-base font-semibold text-white mb-4">PostgreSQL Table Registry</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {Object.entries(dbStats).map(([table, count]) => (
                <div key={table} className="bg-slate-950 border border-slate-800/80 rounded-lg p-3">
                  <div className="text-[11px] font-mono text-slate-400">{table}</div>
                  <div className="text-xl font-mono font-bold text-cyan-400 mt-1">
                    {count.toLocaleString()}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">Rows in database</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
