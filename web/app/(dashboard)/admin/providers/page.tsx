"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

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

interface ProviderMeta {
  provider_id: string;
  name: string;
  notes: string;
  license_required: boolean;
  rate_limit_per_min: number;
  auth_type: string;
  method: string;
  change_capable: boolean;
  official_docs_url: string;
}

export default function AdminProvidersPage() {
  const [operations, setOperations] = useState<ProviderOp[]>([]);
  const [metadata, setMetadata] = useState<ProviderMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  const loadProviders = async () => {
    try {
      setLoading(true);
      setError(null);
      const [opsRes, metaRes] = await Promise.all([
        apiFetch<ProviderOp[]>("/api/v1/admin/providers").catch(() => []),
        apiFetch<ProviderMeta[]>("/api/v1/providers").catch(() => []),
      ]);
      setOperations(Array.isArray(opsRes) ? opsRes : []);
      setMetadata(Array.isArray(metaRes) ? metaRes : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load provider telemetry");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProviders();
  }, []);

  const filteredOps = operations.filter((op) => {
    if (selectedCategory !== "ALL" && op.category !== selectedCategory) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        op.name.toLowerCase().includes(q) ||
        op.category.toLowerCase().includes(q) ||
        op.recommended_action.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const categories = Array.from(new Set(operations.map((o) => o.category)));

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
            <span className="text-xs font-mono text-cyan-400">PROVIDERS</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
            External Intelligence Providers &amp; Adapters
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Strict-truth operations status, authentication configuration, quota boundaries, and ingestion telemetry.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadProviders}
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
            Refresh Providers
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300 font-mono">
          [Provider Telemetry Error]: {error}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Total Providers</span>
          <p className="text-2xl font-bold font-mono text-white mt-2">{operations.length}</p>
          <span className="text-[11px] text-slate-500 font-mono">Integrated intelligence adapters</span>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Configured Auth</span>
          <p className="text-2xl font-bold font-mono text-emerald-400 mt-2">
            {operations.filter((o) => o.auth_configured).length}
          </p>
          <span className="text-[11px] text-slate-500 font-mono">Keys &amp; tokens verified</span>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Public / Free</span>
          <p className="text-2xl font-bold font-mono text-cyan-400 mt-2">
            {operations.filter((o) => !o.auth_required).length}
          </p>
          <span className="text-[11px] text-slate-500 font-mono">No credentials required</span>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 backdrop-blur-sm">
          <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Total Records</span>
          <p className="text-2xl font-bold font-mono text-purple-400 mt-2">
            {operations.reduce((sum, o) => sum + (o.records_ingested || 0), 0).toLocaleString()}
          </p>
          <span className="text-[11px] text-slate-500 font-mono">Ingested through external feeds</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
          <button
            onClick={() => setSelectedCategory("ALL")}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono whitespace-nowrap transition ${
              selectedCategory === "ALL"
                ? "bg-slate-800 text-white border border-slate-700 font-bold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            All Categories
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono whitespace-nowrap transition ${
                selectedCategory === cat
                  ? "bg-slate-800 text-white border border-slate-700 font-bold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <input
            type="text"
            placeholder="Search providers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2.5 top-2 text-xs text-slate-400 hover:text-white"
            >
              &times;
            </button>
          )}
        </div>
      </div>

      {/* Provider Operations Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 overflow-hidden backdrop-blur-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="border-b border-slate-800 bg-slate-950/60 text-slate-400">
              <tr>
                <th className="py-3 px-4 font-semibold">Provider / Name</th>
                <th className="py-3 px-4 font-semibold">Category</th>
                <th className="py-3 px-4 font-semibold">Auth State</th>
                <th className="py-3 px-4 font-semibold">Operational Status</th>
                <th className="py-3 px-4 font-semibold">Quota Telemetry</th>
                <th className="py-3 px-4 font-semibold">Ingested Records</th>
                <th className="py-3 px-4 font-semibold">Action / Guidance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {filteredOps.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No providers matching criteria.
                  </td>
                </tr>
              ) : (
                filteredOps.map((op) => (
                  <tr key={op.name} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4">
                      <div className="font-medium text-white">{op.name}</div>
                      <span className="text-[10px] text-slate-500">
                        {op.auth_required ? "Requires API Key" : "Open Public Access"}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700/60">
                        {op.category}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      {op.auth_configured ? (
                        <span className="text-emerald-400 font-semibold flex items-center gap-1.5">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                          Configured
                        </span>
                      ) : op.auth_required ? (
                        <span className="text-amber-400 flex items-center gap-1.5">
                          <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                          Missing Key
                        </span>
                      ) : (
                        <span className="text-slate-500 flex items-center gap-1.5">
                          <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
                          Public / None
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${
                          op.status === "OPERATIONAL"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : op.status === "DEGRADED"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : "bg-slate-800 text-slate-400 border-slate-700"
                        }`}
                      >
                        {op.status}
                      </span>
                    </td>

                    <td className="py-3 px-4 text-slate-400">
                      <span className="text-[11px]">{op.quota_info}</span>
                    </td>

                    <td className="py-3 px-4 font-bold text-white">
                      {op.records_ingested.toLocaleString()}
                    </td>

                    <td className="py-3 px-4 text-slate-400">
                      <span className="text-[11px] text-cyan-300 font-mono">
                        {op.recommended_action}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
