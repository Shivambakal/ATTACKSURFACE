"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface SystemHealth {
  status: string;
  database: {
    healthy: boolean;
    latency_ms: number;
    migration_revision: string;
    error?: string;
  };
}

export default function AdminDatabasePage() {
  const [dbStats, setDbStats] = useState<Record<string, number>>({});
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchFilter, setSearchFilter] = useState("");
  const [lastRefreshed, setLastRefreshed] = useState<string>("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [stats, healthRes] = await Promise.all([
        apiFetch<Record<string, number>>("/api/v1/admin/db-stats").catch(() => ({})),
        apiFetch<SystemHealth>("/api/v1/admin/health").catch(() => null),
      ]);
      setDbStats(stats || {});
      setHealth(healthRes);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Failed to load DB stats:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const tableCategories: Record<string, { label: string; color: string; tables: string[] }> = {
    discovery: {
      label: "Discovery & Ingestion",
      color: "border-sky-500/30 text-sky-400 bg-sky-500/10",
      tables: ["companies", "company_sources", "targets", "raw_source_snapshots", "snapshots"],
    },
    normalization: {
      label: "Processing & Clustered Changes",
      color: "border-emerald-500/30 text-emerald-400 bg-emerald-500/10",
      tables: ["normalized_source_documents", "source_collection_runs", "change_clusters", "changes"],
    },
    intelligence: {
      label: "Synthesized Intelligence",
      color: "border-purple-500/30 text-purple-400 bg-purple-500/10",
      tables: ["timeline_events", "research_signals", "security_advisories", "security_intelligence_events"],
    },
    security: {
      label: "Access Control & Identity",
      color: "border-amber-500/30 text-amber-400 bg-amber-500/10",
      tables: ["users"],
    },
  };

  const totalRecords = Object.values(dbStats).reduce((sum, val) => sum + (Number(val) || 0), 0);

  const filteredEntries = Object.entries(dbStats).filter(([name]) =>
    name.toLowerCase().includes(searchFilter.toLowerCase().trim())
  );

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
            <span className="text-xs font-mono text-cyan-400">DATABASE</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
            Database Schema &amp; Storage Registry
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            PostgreSQL live table volume, query latency, schema version, and transactional records.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] font-mono text-slate-500">
            Last check: {lastRefreshed || "Checking..."}
          </span>
          <button
            onClick={loadData}
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
            Refresh
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Total Records</span>
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
          </div>
          <p className="text-2xl font-bold font-mono text-white mt-2">
            {totalRecords.toLocaleString()}
          </p>
          <span className="text-[11px] text-slate-500 font-mono">Across 14 tracked models</span>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">PostgreSQL Status</span>
            <span
              className={`h-2 w-2 rounded-full ${
                health?.database.healthy ? "bg-emerald-400" : "bg-rose-400"
              }`}
            />
          </div>
          <p className="text-2xl font-bold font-mono text-white mt-2">
            {health?.database.healthy ? "ONLINE" : "UNAVAILABLE"}
          </p>
          <span className="text-[11px] text-slate-500 font-mono">
            {health?.database.error ? health.database.error : "Connection pool active"}
          </span>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Query Ping Latency</span>
            <svg className="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-400 mt-2">
            {health?.database.latency_ms ?? "--"} ms
          </p>
          <span className="text-[11px] text-slate-500 font-mono">Direct roundtrip ping</span>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Alembic Revision</span>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-500/20 text-purple-300 border border-purple-500/30">
              SCHEMA
            </span>
          </div>
          <p className="text-lg font-bold font-mono text-slate-200 mt-2 truncate">
            {health?.database.migration_revision ?? "Unknown"}
          </p>
          <span className="text-[11px] text-slate-500 font-mono">Synchronized with migration head</span>
        </div>
      </div>

      {/* Table Registry Search & Filter */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 backdrop-blur-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-white">Database Table Row Counts</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Live cardinality and row allocation per relational entity.
            </p>
          </div>
          <div className="relative w-full sm:w-64">
            <input
              type="text"
              placeholder="Filter tables..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
            {searchFilter && (
              <button
                onClick={() => setSearchFilter("")}
                className="absolute right-2.5 top-2 text-xs text-slate-400 hover:text-white"
              >
                &times;
              </button>
            )}
          </div>
        </div>

        {/* Grouped view or flat filtered list */}
        {searchFilter ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredEntries.map(([table, count]) => (
              <div
                key={table}
                className="rounded-lg border border-slate-800 bg-slate-950/60 p-3.5 flex items-center justify-between"
              >
                <div>
                  <p className="text-xs font-mono font-medium text-slate-200">{table}</p>
                  <p className="text-[10px] font-mono text-slate-500">Relational Table</p>
                </div>
                <span className="text-base font-bold font-mono text-cyan-400">
                  {count.toLocaleString()}
                </span>
              </div>
            ))}
            {filteredEntries.length === 0 && (
              <div className="col-span-full py-8 text-center text-xs text-slate-500 font-mono">
                No tables matching &quot;{searchFilter}&quot;
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(tableCategories).map(([catKey, cat]) => {
              const catTables = Object.entries(dbStats).filter(([name]) =>
                cat.tables.includes(name)
              );
              return (
                <div key={catKey} className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-mono font-semibold border ${cat.color}`}
                    >
                      {cat.label}
                    </span>
                    <div className="h-px flex-1 bg-slate-800" />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {catTables.map(([table, count]) => {
                      const pct = totalRecords > 0 ? ((count / totalRecords) * 100).toFixed(1) : "0";
                      return (
                        <div
                          key={table}
                          className="rounded-lg border border-slate-800/80 bg-slate-950/50 p-3 hover:border-slate-700 transition"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-mono text-slate-300 truncate" title={table}>
                              {table}
                            </span>
                            <span className="text-xs font-mono font-bold text-white">
                              {count.toLocaleString()}
                            </span>
                          </div>
                          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-cyan-500 h-1.5 rounded-full transition-all duration-500"
                              style={{ width: `${Math.max(Number(pct), count > 0 ? 3 : 0)}%` }}
                            />
                          </div>
                          <div className="flex justify-between items-center mt-1.5 text-[10px] font-mono text-slate-500">
                            <span>{pct}% share</span>
                            <span>rows</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Relational Integrity Note */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 flex items-start gap-3">
        <svg className="w-5 h-5 text-cyan-400 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div className="text-xs text-slate-400 space-y-1">
          <p className="font-semibold text-slate-200">Database Consistency Model</p>
          <p>
            AttackSurface Timeline isolates immutable raw snapshots from normalized documents and timeline events.
            Row counts reflect direct row queries to PostgreSQL without heuristic estimation.
          </p>
        </div>
      </div>
    </div>
  );
}
