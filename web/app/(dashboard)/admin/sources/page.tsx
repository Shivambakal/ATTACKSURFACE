"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface ProviderSource {
  id: string;
  name: string;
  category: string;
  feed_url: string;
  configured: boolean;
  status: string;
  freshness: string;
  last_successful_fetch: string | null;
  total_records: number | null;
  catalog_version: string | null;
  content_sha256: string | null;
  latency_ms: number;
  error: string | null;
  detail_url: string | null;
}

interface AdminCompanySource {
  id: number;
  company_id: number;
  company_name: string;
  name: string;
  source_url: string;
  feed_url?: string;
  source_type: string;
  authority_level: string;
  parser_strategy: string;
  enabled: boolean;
  status: string;
  health_state: string;
  last_checked_at?: string;
  last_changed_at?: string;
  consecutive_failures: number;
}

export default function AdminSourcesPage() {
  const [providerSources, setProviderSources] = useState<ProviderSource[]>([]);
  const [companySources, setCompanySources] = useState<AdminCompanySource[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingCisa, setSyncingCisa] = useState(false);
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<"providers" | "company_feeds">("providers");

  const loadData = async () => {
    try {
      setLoading(true);
      const [providers, feeds] = await Promise.all([
        apiFetch<ProviderSource[]>("/api/v1/admin/sources/overview"),
        apiFetch<AdminCompanySource[]>("/api/v1/admin/sources"),
      ]);
      setProviderSources(providers || []);
      setCompanySources(feeds || []);
    } catch (err) {
      console.error("Failed to load sources overview:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSyncCisa = async () => {
    setSyncingCisa(true);
    try {
      await apiFetch("/api/v1/admin/sources/cisa-kev/sync", { method: "POST" });
      loadData();
    } catch (err) {
      console.error("CISA sync trigger failed:", err);
    } finally {
      setSyncingCisa(false);
    }
  };

  const filteredCompanyFeeds = companySources.filter((s) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return s.name.toLowerCase().includes(q) || s.company_name.toLowerCase().includes(q) || s.source_type.toLowerCase().includes(q);
  });

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16 font-sans">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
        <Link href="/admin" className="text-amber-400 hover:underline">Admin Console</Link>
        <span>/</span>
        <span className="text-white">Intelligence Sources Registry</span>
      </div>

      {/* Header Banner */}
      <div className="bg-slate-900/90 border border-amber-500/20 rounded-2xl p-6 shadow-2xl backdrop-blur">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" />
              </svg>
            </span>
            <div>
              <h1 className="text-2xl font-extrabold text-white tracking-tight">Intelligence Sources & Provider Operations</h1>
              <p className="text-xs text-slate-400 mt-1">
                Real connection states, official government machine feeds, cryptographic hashes, and health telemetry. Zero synthetic health claims.
              </p>
            </div>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="px-4 py-2 text-xs font-mono font-medium text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl transition"
          >
            {loading ? "Refreshing..." : "↻ Refresh Status"}
          </button>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex items-center gap-3 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("providers")}
          className={`px-4 py-2 rounded-lg text-xs font-mono font-semibold transition ${
            activeTab === "providers"
              ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
              : "text-slate-400 hover:text-white"
          }`}
        >
          External Threat & Intelligence Providers ({providerSources.length})
        </button>
        <button
          onClick={() => setActiveTab("company_feeds")}
          className={`px-4 py-2 rounded-lg text-xs font-mono font-semibold transition ${
            activeTab === "company_feeds"
              ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
              : "text-slate-400 hover:text-white"
          }`}
        >
          Company Monitoring Feeds ({companySources.length})
        </button>
      </div>

      {activeTab === "providers" ? (
        /* External Provider Cards */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {providerSources.map((prov) => {
            const isConnected = prov.status === "CONNECTED" || prov.status === "CONFIGURED";
            return (
              <div
                key={prov.id}
                className="rounded-2xl bg-slate-950/80 border border-slate-800 p-6 flex flex-col justify-between shadow-xl relative overflow-hidden group hover:border-slate-700 transition"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="px-2.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider font-bold bg-slate-900 border border-slate-800 text-slate-400">
                      {prov.category}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                      prov.status === "CONNECTED"
                        ? "bg-emerald-950/60 text-emerald-400 border border-emerald-500/30"
                        : prov.status === "CONFIGURED"
                        ? "bg-cyan-950/60 text-cyan-400 border border-cyan-500/30"
                        : "bg-slate-900 text-slate-500 border border-slate-800"
                    }`}>
                      {prov.status}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-white tracking-tight">{prov.name}</h3>
                  <p className="text-xs text-slate-500 font-mono mt-1 truncate">{prov.feed_url}</p>

                  <div className="mt-4 pt-4 border-t border-slate-900 space-y-2 text-xs font-mono">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Freshness:</span>
                      <span className="text-slate-300 font-bold">{prov.freshness}</span>
                    </div>
                    {prov.total_records !== null && (
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Records Stored:</span>
                        <span className="text-cyan-400 font-bold">{prov.total_records.toLocaleString()}</span>
                      </div>
                    )}
                    {prov.catalog_version && (
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Catalog Version:</span>
                        <span className="text-slate-300">{prov.catalog_version}</span>
                      </div>
                    )}
                    {prov.last_successful_fetch && (
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Last Sync:</span>
                        <span className="text-slate-400">{new Date(prov.last_successful_fetch).toLocaleDateString()}</span>
                      </div>
                    )}
                    {prov.content_sha256 && (
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">SHA-256:</span>
                        <span className="text-slate-400 truncate max-w-[140px]" title={prov.content_sha256}>
                          {prov.content_sha256.substring(0, 8)}...{prov.content_sha256.substring(56)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-900 flex items-center justify-between gap-3">
                  {prov.id === "cisa_kev" ? (
                    <>
                      <Link
                        href="/admin/sources/cisa-kev"
                        className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-medium transition"
                      >
                        Inspect Catalog →
                      </Link>
                      <button
                        onClick={handleSyncCisa}
                        disabled={syncingCisa}
                        className="px-3.5 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 text-xs font-mono font-bold transition disabled:opacity-50"
                      >
                        {syncingCisa ? "Syncing..." : "⚡ Sync Now"}
                      </button>
                    </>
                  ) : (
                    <span className="text-xs font-mono text-slate-500">
                      {prov.configured ? "Configured server-side" : "Unconfigured credentials"}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Company Feeds Table */
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search company or feed name..."
              className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-500 text-xs font-mono focus:border-amber-500 focus:outline-none w-full sm:w-80"
            />
            <span className="text-xs font-mono text-slate-500">{filteredCompanyFeeds.length} feeds found</span>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/90 text-slate-400 font-mono uppercase tracking-wider text-[11px] border-b border-slate-800">
                  <tr>
                    <th className="px-5 py-3.5">Company</th>
                    <th className="px-5 py-3.5">Feed / Source</th>
                    <th className="px-5 py-3.5">Type</th>
                    <th className="px-5 py-3.5">Authority</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5">Health</th>
                    <th className="px-5 py-3.5 text-right">Consecutive Errors</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {filteredCompanyFeeds.map((s) => (
                    <tr key={s.id} className="hover:bg-slate-900/40 transition">
                      <td className="px-5 py-4 font-sans font-semibold text-white">{s.company_name}</td>
                      <td className="px-5 py-4">
                        <span className="text-slate-300 font-medium">{s.name}</span>
                        <p className="text-[11px] text-slate-500 truncate max-w-xs">{s.source_url}</p>
                      </td>
                      <td className="px-5 py-4 text-slate-400 text-[11px]">{s.source_type}</td>
                      <td className="px-5 py-4 text-slate-400 text-[11px]">{s.authority_level}</td>
                      <td className="px-5 py-4">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                          {s.status}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          s.health_state === "HEALTHY"
                            ? "bg-emerald-950/60 text-emerald-400 border border-emerald-500/30"
                            : "bg-amber-950/60 text-amber-400 border border-amber-500/30"
                        }`}>
                          {s.health_state}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-right text-slate-400">{s.consecutive_failures}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
