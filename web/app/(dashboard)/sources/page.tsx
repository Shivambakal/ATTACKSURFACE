"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { CompanySource } from "@/lib/types";

export default function SourceExplorerPage() {
  const [sources, setSources] = useState<CompanySource[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [selectedHealth, setSelectedHealth] = useState<string>("ALL");
  const [totalCount, setTotalCount] = useState(0);
  const [checkingId, setCheckingId] = useState<number | null>(null);

  const fetchSources = async () => {
    setLoading(true);
    try {
      let url = `/api/v1/sources?limit=200`;
      if (searchQuery.trim()) {
        url += `&q=${encodeURIComponent(searchQuery.trim())}`;
      }
      if (selectedType !== "ALL") {
        url += `&source_type=${encodeURIComponent(selectedType)}`;
      }
      if (selectedHealth !== "ALL") {
        url += `&health=${encodeURIComponent(selectedHealth)}`;
      }
      const data = await apiFetch<{ total: number; items: CompanySource[] }>(url);
      setSources(data.items || []);
      setTotalCount(data.total || 0);
    } catch (err) {
      console.error("Failed to load sources:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSources();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery, selectedType, selectedHealth]);

  const handleManualCheck = async (sourceId: number) => {
    setCheckingId(sourceId);
    try {
      await apiFetch(`/api/v1/sources/${sourceId}/check`, { method: "POST" });
      await fetchSources();
    } catch (err) {
      console.error("Manual check failed:", err);
    } finally {
      setCheckingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 border-b border-slate-800 pb-5 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">Source Explorer</h1>
            <span className="rounded border border-cyan-500/30 bg-cyan-950/40 px-2 py-0.5 font-mono text-xs font-semibold text-cyan-400">
              {totalCount} FEEDS
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Multi-source continuous corporate intelligence registry, conditional polling status, and health telemetry.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/60 p-3.5 backdrop-blur-sm">
        <div className="relative min-w-[240px] flex-1">
          <input
            type="text"
            placeholder="Search by feed name, URL, or scope..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-slate-400">Type:</span>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="rounded border border-slate-700 bg-slate-950 px-2.5 py-1.5 font-mono text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
          >
            <option value="ALL">All Types</option>
            <option value="OFFICIAL_PRODUCT_CHANGE">Official Product Change</option>
            <option value="OFFICIAL_RELEASE">Official Release</option>
            <option value="OFFICIAL_API_CHANGELOG">Official API Changelog</option>
            <option value="OFFICIAL_SECURITY_ADVISORY">Security Advisory</option>
            <option value="OFFICIAL_BLOG">Official Blog</option>
            <option value="OFFICIAL_GITHUB">Official GitHub</option>
            <option value="OFFICIAL_ROADMAP">Roadmap</option>
            <option value="COMMUNITY">Community</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-slate-400">Health:</span>
          <select
            value={selectedHealth}
            onChange={(e) => setSelectedHealth(e.target.value)}
            className="rounded border border-slate-700 bg-slate-950 px-2.5 py-1.5 font-mono text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
          >
            <option value="ALL">All States</option>
            <option value="HEALTHY">Healthy</option>
            <option value="DEGRADED">Degraded</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </div>

      {/* Sources Table */}
      <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/70 shadow-lg">
        {loading ? (
          <div className="p-12 text-center text-sm font-mono text-slate-400">
            Scanning source telemetry...
          </div>
        ) : sources.length === 0 ? (
          <div className="p-12 text-center text-sm text-slate-500">
            No sources match the selected filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-950/70 font-mono text-[11px] text-slate-400 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Company / Source</th>
                  <th className="px-4 py-3">Type & Authority</th>
                  <th className="px-4 py-3">Product Scope</th>
                  <th className="px-4 py-3">Cadence</th>
                  <th className="px-4 py-3">Health & Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans text-slate-200">
                {sources.map((src) => {
                  const isHealthy = src.health_state === "HEALTHY";
                  const isDegraded = src.health_state === "DEGRADED";
                  return (
                    <tr key={src.id} className="transition hover:bg-slate-800/40">
                      <td className="px-4 py-3.5">
                        <div className="font-semibold text-slate-100 flex items-center gap-2">
                          <Link href={`/companies/${src.company_id}`} className="text-cyan-400 hover:underline">
                            {src.company_name}
                          </Link>
                          <span className="text-slate-500">›</span>
                          <span>{src.name}</span>
                        </div>
                        <div className="mt-0.5 truncate font-mono text-[11px] text-slate-400 max-w-sm">
                          <a href={src.source_url} target="_blank" rel="noreferrer" className="hover:text-slate-300">
                            {src.source_url}
                          </a>
                        </div>
                      </td>

                      <td className="px-4 py-3.5 font-mono text-[11px]">
                        <div className="font-medium text-slate-200">{src.source_type}</div>
                        <div className="mt-0.5 text-[10px] text-slate-400">{src.authority_level}</div>
                      </td>

                      <td className="px-4 py-3.5 font-mono text-[11px]">
                        {src.product_scope ? (
                          <span className="rounded bg-slate-800 px-1.5 py-0.5 text-slate-300">
                            {src.product_scope}
                          </span>
                        ) : (
                          <span className="text-slate-500">Corporate Global</span>
                        )}
                        {src.platform_scope && (
                          <div className="mt-1 text-[10px] text-slate-400">{src.platform_scope}</div>
                        )}
                      </td>

                      <td className="px-4 py-3.5 font-mono text-[11px]">
                        <div className="text-slate-300">{Math.round(src.poll_interval_seconds / 60)} min</div>
                        <div className="mt-0.5 text-[10px] text-slate-500">{src.priority} Queue</div>
                      </td>

                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold ${
                              isHealthy
                                ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/60"
                                : isDegraded
                                ? "bg-amber-950/60 text-amber-400 border border-amber-800/60"
                                : "bg-rose-950/60 text-rose-400 border border-rose-800/60"
                            }`}
                          >
                            <span className={`h-1.5 w-1.5 rounded-full ${isHealthy ? "bg-emerald-400" : isDegraded ? "bg-amber-400" : "bg-rose-400"}`} />
                            {src.health_state}
                          </span>
                          <span className="font-mono text-[10px] text-slate-400">{src.status}</span>
                        </div>
                        {src.last_checked_at && (
                          <div className="mt-1 font-mono text-[10px] text-slate-500">
                            Checked: {new Date(src.last_checked_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </div>
                        )}
                      </td>

                      <td className="px-4 py-3.5 text-right font-mono text-[11px]">
                        <button
                          onClick={() => handleManualCheck(src.id)}
                          disabled={checkingId === src.id}
                          className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-slate-300 hover:border-cyan-500 hover:text-white transition disabled:opacity-50"
                        >
                          {checkingId === src.id ? "Checking..." : "Poll Now"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
