"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface HealthData {
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
  scheduler: {
    active: boolean;
    type: string;
  };
  collections: {
    last_successful: string | null;
    last_failed: string | null;
  };
  timestamp?: string;
}

export default function AdminHealthPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastCheck, setLastCheck] = useState<string>("");

  const loadHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiFetch<HealthData>("/api/v1/admin/health");
      setHealth(data);
      setLastCheck(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to retrieve health metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHealth();
    const interval = setInterval(loadHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hrs = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (days > 0) return `${days}d ${hrs}h ${mins}m`;
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
    return `${mins}m ${secs}s`;
  };

  const getStatusBadge = (status: string) => {
    switch (status?.toUpperCase()) {
      case "HEALTHY":
        return "border-emerald-500/30 text-emerald-400 bg-emerald-500/10";
      case "DEGRADED":
        return "border-amber-500/30 text-amber-400 bg-amber-500/10";
      default:
        return "border-rose-500/30 text-rose-400 bg-rose-500/10";
    }
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Title */}
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
            <span className="text-xs font-mono text-cyan-400">HEALTH</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
            System Health &amp; Subsystem Runtime
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            End-to-end dependency verification, process telemetry, queue workers, and latency metrics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] font-mono text-slate-500">
            Updated: {lastCheck || "--"}
          </span>
          <button
            onClick={loadHealth}
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
            Refresh Now
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300 font-mono">
          [System Health Query Error]: {error}
        </div>
      )}

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Core Status */}
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">System State</span>
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                health?.status === "HEALTHY" ? "bg-emerald-400 animate-pulse" : "bg-rose-400"
              }`}
            />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">
              {health?.status || "CHECKING"}
            </span>
          </div>
          <span
            className={`inline-block mt-2 px-2 py-0.5 rounded text-[10px] font-mono border ${getStatusBadge(
              health?.status || ""
            )}`}
          >
            {health?.status === "HEALTHY" ? "All Subsystems Nominal" : "Attention Required"}
          </span>
        </div>

        {/* Uptime */}
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Uptime</span>
            <svg className="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-2xl font-bold font-mono text-white mt-2">
            {health ? formatUptime(health.uptime_seconds) : "--"}
          </p>
          <span className="text-[11px] text-slate-500 font-mono">
            {health ? `${health.uptime_seconds} continuous seconds` : ""}
          </span>
        </div>

        {/* PostgreSQL Ping */}
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">PostgreSQL Ping</span>
            <span
              className={`h-2 w-2 rounded-full ${
                health?.database.healthy ? "bg-emerald-400" : "bg-rose-400"
              }`}
            />
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-bold font-mono text-emerald-400">
              {health?.database.latency_ms ?? "--"}
            </span>
            <span className="text-xs text-slate-500 font-mono">ms</span>
          </div>
          <span className="text-[11px] text-slate-500 font-mono">
            Revision: {health?.database.migration_revision ?? "unknown"}
          </span>
        </div>

        {/* Redis Ping */}
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Redis Ping</span>
            <span
              className={`h-2 w-2 rounded-full ${
                health?.redis.healthy ? "bg-emerald-400" : "bg-rose-400"
              }`}
            />
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-bold font-mono text-emerald-400">
              {health?.redis.latency_ms ?? "--"}
            </span>
            <span className="text-xs text-slate-500 font-mono">ms</span>
          </div>
          <span className="text-[11px] text-slate-500 font-mono">Broker &amp; Session Store</span>
        </div>
      </div>

      {/* Detailed Subsystems Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Workers & RQ Diagnostics */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 backdrop-blur-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
                </svg>
              </div>
              <h2 className="text-sm font-bold text-white">Active Background Workers</h2>
            </div>
            <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-800 text-cyan-300">
              {health?.workers.active_count ?? 0} Running
            </span>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Scheduler Daemon</span>
              <span className="text-emerald-400 font-bold">
                {health?.scheduler.active ? "ONLINE" : "OFFLINE"} ({health?.scheduler.type})
              </span>
            </div>

            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Registered Worker Instances</span>
              <span className="text-white font-bold">{health?.workers.active_count ?? 0}</span>
            </div>

            <div className="mt-3 rounded-lg border border-slate-800/80 bg-slate-950/60 p-3">
              <p className="text-[11px] font-mono text-slate-500 uppercase tracking-wider mb-2">
                Worker Identifiers
              </p>
              {health?.workers.worker_names && health.workers.worker_names.length > 0 ? (
                <div className="space-y-1.5">
                  {health.workers.worker_names.map((wName, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between text-xs font-mono text-slate-300 bg-slate-900/80 px-2.5 py-1.5 rounded border border-slate-800"
                    >
                      <span className="truncate">{wName}</span>
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shrink-0" />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-amber-400/80 font-mono py-2">
                  No registered standalone workers detected in Redis registry.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Ingestion & Collection Health */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 backdrop-blur-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="text-sm font-bold text-white">Ingestion Provenance Status</h2>
            </div>
            <span className="px-2 py-0.5 rounded text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              AUDITED
            </span>
          </div>

          <div className="space-y-3">
            <div className="p-3 rounded-lg border border-slate-800/80 bg-slate-950/60 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-slate-300">Last Successful Snapshot</p>
                <p className="text-[11px] font-mono text-slate-500 mt-0.5">
                  {health?.collections.last_successful
                    ? new Date(health.collections.last_successful).toLocaleString()
                    : "No successful collections recorded yet"}
                </p>
              </div>
              <span
                className={`px-2 py-1 rounded text-[10px] font-mono font-bold ${
                  health?.collections.last_successful
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "bg-slate-800 text-slate-400"
                }`}
              >
                {health?.collections.last_successful ? "VALIDATED" : "NONE"}
              </span>
            </div>

            <div className="p-3 rounded-lg border border-slate-800/80 bg-slate-950/60 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-slate-300">Last Collection Exception</p>
                <p className="text-[11px] font-mono text-slate-500 mt-0.5">
                  {health?.collections.last_failed
                    ? new Date(health.collections.last_failed).toLocaleString()
                    : "Zero collection errors recorded"}
                </p>
              </div>
              <span
                className={`px-2 py-1 rounded text-[10px] font-mono font-bold ${
                  health?.collections.last_failed
                    ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                    : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                }`}
              >
                {health?.collections.last_failed ? "RECORDED" : "CLEAN"}
              </span>
            </div>

            <div className="pt-2 flex justify-end">
              <Link
                href="/admin/queues"
                className="text-xs font-mono text-cyan-400 hover:text-cyan-300 transition flex items-center gap-1"
              >
                Inspect 9 Priority RQ Queues &rarr;
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
