"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface ErrorItem {
  run_id: number;
  source_id: number;
  source_name: string;
  status: string;
  http_status: number;
  error_message: string;
  timestamp: string;
  recommended_fix: string;
}

interface ErrorCenterData {
  failed_runs_24h_count: number;
  degraded_sources_count: number;
  recent_errors: ErrorItem[];
}

export default function AdminErrorsPage() {
  const [data, setData] = useState<ErrorCenterData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("ALL");

  const loadErrors = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiFetch<ErrorCenterData>("/api/v1/admin/errors");
      setData(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load error center telemetry");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadErrors();
  }, []);

  const errors = data?.recent_errors || [];
  const filteredErrors = filter === "ALL"
    ? errors
    : errors.filter((e) => e.status === filter);

  return (
    <div className="space-y-6">
      {/* Header */}
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
            <span className="text-xs font-mono text-cyan-400">ERRORS</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
            Error Center &amp; Source Remediation
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time collection failures, rate limiting telemetry, HTTP status anomalies, and suggested fixes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadErrors}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-xs font-mono text-slate-200 transition disabled:opacity-50 flex items-center gap-2"
          >
            <svg
              className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Refresh Errors
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300 font-mono">
          [Error Center Load Error]: {error}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Failed Runs (24h)</span>
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                (data?.failed_runs_24h_count ?? 0) > 0 ? "bg-rose-400" : "bg-emerald-400"
              }`}
            />
          </div>
          <p className="text-2xl font-bold font-mono text-white mt-2">
            {data?.failed_runs_24h_count ?? 0}
          </p>
          <span className="text-[11px] text-slate-500 font-mono">Failed snapshot collections</span>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Degraded Sources</span>
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                (data?.degraded_sources_count ?? 0) > 0 ? "bg-amber-400" : "bg-emerald-400"
              }`}
            />
          </div>
          <p className="text-2xl font-bold font-mono text-amber-400 mt-2">
            {data?.degraded_sources_count ?? 0}
          </p>
          <span className="text-[11px] text-slate-500 font-mono">Sources requiring review</span>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Logged Exceptions</span>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-500/20 text-purple-300 border border-purple-500/30">
              TRACED
            </span>
          </div>
          <p className="text-2xl font-bold font-mono text-white mt-2">
            {errors.length}
          </p>
          <span className="text-[11px] text-slate-500 font-mono">Diagnostic traces in rolling window</span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        {["ALL", "FAILED", "RATE_LIMITED"].map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono transition ${
              filter === tab
                ? "bg-slate-800 text-white border border-slate-700 font-bold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Error List */}
      <div className="space-y-3">
        {filteredErrors.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-8 text-center">
            <div className="inline-flex p-3 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mb-3">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="text-sm font-bold text-white">No Errors Recorded</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
              All passive intelligence pipelines and external connector feeds are operating cleanly without exceptions.
            </p>
          </div>
        ) : (
          filteredErrors.map((item) => (
            <div
              key={item.run_id}
              className="rounded-xl border border-rose-500/20 bg-slate-900/80 p-4 space-y-3 backdrop-blur-sm"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                      item.status === "RATE_LIMITED"
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                    }`}
                  >
                    {item.status}
                  </span>
                  <span className="text-xs font-bold text-white font-mono">
                    Run #{item.run_id}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">
                    Source #{item.source_id}: {item.source_name}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-mono text-slate-400">
                    HTTP {item.http_status || "ERR"}
                  </span>
                  <span className="text-[11px] font-mono text-slate-500">
                    {item.timestamp ? new Date(item.timestamp).toLocaleString() : "--"}
                  </span>
                </div>
              </div>

              {/* Error Detail */}
              <div className="rounded-lg bg-slate-950/80 border border-slate-800 p-3 font-mono text-xs text-rose-300 break-words">
                {item.error_message || "Unknown collection error occurred"}
              </div>

              {/* Recommended Fix */}
              <div className="flex items-center gap-2 text-xs font-mono text-cyan-300/90 bg-cyan-950/30 border border-cyan-800/40 px-3 py-2 rounded-lg">
                <svg className="w-4 h-4 shrink-0 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Recommended Action: {item.recommended_fix}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
