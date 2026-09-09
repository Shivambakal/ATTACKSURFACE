"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

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

interface PipelineProof {
  proof_available: boolean;
  message?: string;
  provenance_trace?: any;
  verified_end_to_end?: boolean;
}

export default function AdminPipelinePage() {
  const [pipeline, setPipeline] = useState<PipelineHealth | null>(null);
  const [proof, setProof] = useState<PipelineProof | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadPipeline = async () => {
    try {
      setLoading(true);
      const [p, prf] = await Promise.all([
        apiFetch<PipelineHealth>("/api/v1/admin/pipeline").catch(() => null),
        apiFetch<PipelineProof>("/api/v1/admin/proof").catch(() => null),
      ]);
      setPipeline(p);
      setProof(prf);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPipeline();
  }, []);

  const handleTriggerRun = async () => {
    try {
      setTriggering(true);
      setMessage("Executing synchronous verified run through all 9 stages...");
      const res = await apiFetch<any>("/api/v1/admin/trigger-proof-run", { method: "POST" });
      if (res?.success) {
        setMessage("Verified test cycle completed successfully!");
      } else {
        setMessage(`Run finished: ${res?.fetch_result?.status || "Check telemetry"}`);
      }
      loadPipeline();
    } catch (err: any) {
      setMessage(`Error: ${err.message || String(err)}`);
    } finally {
      setTriggering(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
        <Link href="/admin" className="text-amber-400 hover:underline">Admin Console</Link>
        <span>/</span>
        <span className="text-white">Pipeline</span>
      </div>

      {/* Header */}
      <div className="bg-slate-900/90 border border-amber-500/20 rounded-xl p-6 shadow-xl backdrop-blur">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </span>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">9-Stage Pipeline Architecture & Provenance Proof</h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Inspect live stage counts, drop-off filtering, and end-to-end provenance traces from raw HTTP fetch to verified research signals.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadPipeline}
              disabled={loading || triggering}
              className="px-3.5 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition"
            >
              {loading ? "Refreshing..." : "↻ Refresh"}
            </button>
            <button
              onClick={handleTriggerRun}
              disabled={triggering}
              className="px-4 py-2 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-500 rounded-lg shadow transition"
            >
              {triggering ? "Verifying..." : "▶ Run Verified Cycle"}
            </button>
          </div>
        </div>
      </div>

      {message && (
        <div className="bg-amber-950/40 border border-amber-500/30 rounded-lg p-3 text-xs text-amber-300 flex items-center justify-between">
          <span>{message}</span>
          <button onClick={() => setMessage(null)} className="text-amber-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}

      {/* 9 Stages Grid */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h3 className="text-base font-semibold text-white mb-1">Pipeline Progression by Stage</h3>
        <p className="text-xs text-slate-400 mb-4">Live items currently recorded in the persistent PostgreSQL repository.</p>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {pipeline?.stages.map((st) => (
            <div key={st.index} className="bg-slate-950/80 border border-slate-800/80 rounded-lg p-4 relative overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-amber-400 tracking-wider uppercase">Stage {st.index}</span>
                <span className="text-lg font-mono font-bold text-white">{st.count.toLocaleString()}</span>
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

      {/* Provenance Trace / Proof Inspector */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <span>Verified End-to-End Pipeline Proof</span>
              {proof?.verified_end_to_end && (
                <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                  VERIFIED E2E
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Cryptographic trace of the latest live collection run showing payload SHA-256 hash, normalization, clustering, and timeline events.
            </p>
          </div>
        </div>

        {proof?.proof_available && proof.provenance_trace ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Step 1: Source Origin</span>
                <h4 className="text-sm font-bold text-white mt-1">{proof.provenance_trace.step_1_source?.name}</h4>
                <div className="mt-2 space-y-1 text-xs text-slate-400 font-mono">
                  <div>Company: <span className="text-slate-200">{proof.provenance_trace.step_1_source?.company_name}</span></div>
                  <div>Authority: <span className="text-amber-300">{proof.provenance_trace.step_1_source?.authority_level}</span></div>
                  <div>URL: <span className="text-cyan-400 truncate block">{proof.provenance_trace.step_1_source?.url}</span></div>
                </div>
              </div>

              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Step 2: Live HTTP Response</span>
                <h4 className="text-sm font-bold text-white mt-1">Run #{proof.provenance_trace.step_2_live_http?.run_id}</h4>
                <div className="mt-2 space-y-1 text-xs text-slate-400 font-mono">
                  <div>HTTP Status: <span className="text-emerald-400 font-bold">{proof.provenance_trace.step_2_live_http?.http_status}</span></div>
                  <div>Latency: <span className="text-slate-200">{proof.provenance_trace.step_2_live_http?.duration_ms} ms</span></div>
                  <div>Payload Size: <span className="text-slate-200">{(proof.provenance_trace.step_2_live_http?.response_bytes / 1024).toFixed(1)} KB</span></div>
                </div>
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
              <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Step 3: Immutable Snapshot Hash</span>
              <div className="mt-2 text-xs font-mono text-slate-400 flex flex-wrap justify-between gap-2">
                <div>Snapshot ID: <span className="text-white font-bold">{proof.provenance_trace.step_3_raw_snapshot?.snapshot_id}</span></div>
                <div>SHA-256: <span className="text-amber-300 font-bold">{proof.provenance_trace.step_3_raw_snapshot?.content_hash_sha256}</span></div>
                <div>Size: <span className="text-slate-200">{proof.provenance_trace.step_3_raw_snapshot?.body_size_bytes} B</span></div>
              </div>
            </div>
          </div>
        ) : (
          <div className="py-12 text-center text-slate-500 font-mono text-xs">
            No pipeline proof captured yet. Click "Run Verified Cycle" above to generate a live trace.
          </div>
        )}
      </div>
    </div>
  );
}
