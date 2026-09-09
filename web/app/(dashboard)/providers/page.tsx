"use client";

import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ProviderMetadata, ProviderUsage } from "@/lib/types";

export default function ProviderExplorerPage() {
  const { user } = useAuth();
  const isAuthorizedAdmin = user?.role === "OWNER" || user?.role === "ADMIN" || Boolean(user?.is_admin);

  const [providers, setProviders] = useState<ProviderMetadata[]>([]);
  const [usages, setUsages] = useState<Record<string, ProviderUsage>>({});
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedMethod, setSelectedMethod] = useState<string>("ALL");

  useEffect(() => {
    if (!isAuthorizedAdmin) {
      setLoading(false);
      return;
    }
    const loadProviders = async () => {
      setLoading(true);
      try {
        const [provList, costSummary] = await Promise.all([
          apiFetch<ProviderMetadata[]>("/api/v1/providers"),
          apiFetch<Record<string, ProviderUsage>>("/api/v1/intelligence/health").then(
            (res: any) => res.provider_usage || {}
          ).catch(() => ({})),
        ]);
        setProviders(provList || []);
        setUsages(costSummary || {});
      } catch (err) {
        console.error("Failed to load providers:", err);
      } finally {
        setLoading(false);
      }
    };
    loadProviders();
  }, [isAuthorizedAdmin]);

  if (user && !isAuthorizedAdmin) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-4">
        <div className="rounded-full bg-rose-500/10 p-4 border border-rose-500/20 text-rose-400">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-white">403 Forbidden - Access Denied</h2>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Provider telemetry, licensing, and operational adapter controls require an <span className="font-semibold text-slate-200">OWNER</span> or <span className="font-semibold text-slate-200">ADMIN</span> role.
        </p>
        <div className="inline-block rounded-lg border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono text-slate-300">
          Current Session: <span className="text-amber-400 font-bold">{user.role || "RESEARCHER"}</span> ({user.email})
        </div>
      </div>
    );
  }

  const filtered = providers.filter((p) => {
    if (selectedMethod !== "ALL" && p.method !== selectedMethod) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return p.name.toLowerCase().includes(q) || p.provider_id.toLowerCase().includes(q) || p.notes.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="font-mono text-xs text-cyan-400 tracking-wider uppercase">
              EXTERNAL INTELLIGENCE ADAPTERS
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mt-1">
            Provider Architecture &amp; Telemetry
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Catalog of verified data providers, licensing boundaries, rate limiting, and live operational telemetry.
          </p>
        </div>
      </div>

      {/* KPI Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <span className="text-xs text-slate-400 font-medium">Registered Providers</span>
          <p className="text-2xl font-bold text-white font-mono mt-1">{providers.length}</p>
        </div>
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <span className="text-xs text-slate-400 font-medium">Free / Public Tier</span>
          <p className="text-2xl font-bold text-emerald-400 font-mono mt-1">
            {providers.filter((p) => !p.license_required).length}
          </p>
        </div>
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <span className="text-xs text-slate-400 font-medium">Commercial / Keyed</span>
          <p className="text-2xl font-bold text-cyan-400 font-mono mt-1">
            {providers.filter((p) => p.license_required).length}
          </p>
        </div>
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <span className="text-xs text-slate-400 font-medium">Temporal / Change Aware</span>
          <p className="text-2xl font-bold text-purple-400 font-mono mt-1">
            {providers.filter((p) => p.change_capable).length}
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <input
          type="text"
          placeholder="Filter providers by name, ID, or keywords..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 rounded-lg border border-slate-800 bg-slate-900/90 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
        />
        <select
          value={selectedMethod}
          onChange={(e) => setSelectedMethod(e.target.value)}
          className="rounded-lg border border-slate-800 bg-slate-900/90 px-3 py-2 text-sm text-slate-300 focus:border-cyan-500 focus:outline-none"
        >
          <option value="ALL">All Methods</option>
          <option value="REST">REST API</option>
          <option value="GRAPHQL">GraphQL</option>
          <option value="WEBHOOK">Webhook / Callback</option>
          <option value="JSON">JSON Feed</option>
          <option value="HOURLY_FILES">Hourly Dumps</option>
        </select>
      </div>

      {/* Provider Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 font-mono text-sm">
          Loading provider registry and telemetry...
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-12 text-center text-slate-500 font-mono text-sm">
          No providers matched your filter criteria.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((p) => {
            const usage = usages[p.provider_id] || { requests: 0, credits: 0, errors: 0 };
            return (
              <div
                key={p.provider_id}
                className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 flex flex-col justify-between hover:border-slate-700 transition-colors"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="text-base font-bold text-white tracking-tight">{p.name}</h3>
                      <span className="font-mono text-[10px] text-cyan-400">{p.provider_id}</span>
                    </div>
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-mono font-semibold uppercase ${
                        p.license_required
                          ? "bg-amber-950/60 text-amber-300 border border-amber-800/40"
                          : "bg-emerald-950/60 text-emerald-300 border border-emerald-800/40"
                      }`}
                    >
                      {p.license_required ? "Commercial / Keyed" : "Public / Free"}
                    </span>
                  </div>

                  <p className="mt-3 text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {p.notes || "Enterprise external intelligence integration."}
                  </p>

                  <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] font-mono border-t border-slate-800/80 pt-3">
                    <div>
                      <span className="text-slate-500 block">Method</span>
                      <span className="text-slate-300">{p.method}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Rate Limit</span>
                      <span className="text-slate-300">{p.rate_limit_per_min} req/min</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Auth Mechanism</span>
                      <span className="text-slate-300">{p.auth_type}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Capabilities</span>
                      <span className="text-slate-300">
                        {p.change_capable ? "Temporal" : "Point-in-time"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Telemetry / Footer */}
                <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                  <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
                    <span>Calls: <b className="text-white">{usage.requests}</b></span>
                    <span>Errors: <b className={usage.errors > 0 ? "text-rose-400" : "text-slate-400"}>{usage.errors}</b></span>
                  </div>
                  <a
                    href={p.official_docs_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-cyan-400 hover:text-cyan-300 font-mono underline inline-flex items-center gap-1"
                  >
                    Docs &rarr;
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
