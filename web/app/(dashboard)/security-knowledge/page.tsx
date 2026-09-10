"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface Advisory {
  id: number;
  canonical_id: string;
  provider: string;
  cve_id: string | null;
  ghsa_id: string | null;
  title: string;
  summary: string | null;
  vendor: string | null;
  product: string | null;
  severity: string | null;
  cvss_score: number | null;
  known_ransomware_use: string | null;
  forensic_triage: string | null;
  date_added: string | null;
  due_date: string | null;
  published_at: string | null;
  source_url: string | null;
  confidence: number;
  cwes: string[];
  owasp_categories: string[];
}

interface AdvisoryDetail {
  id: number;
  canonical_id: string;
  provider: string;
  cve_id: string | null;
  ghsa_id: string | null;
  title: string;
  summary: string | null;
  description: string | null;
  vendor: string | null;
  product: string | null;
  affected_versions: string[] | null;
  severity: string | null;
  cvss_score: number | null;
  known_ransomware_use: string | null;
  forensic_triage: string | null;
  date_added: string | null;
  due_date: string | null;
  published_at: string | null;
  source_url: string | null;
  confidence: number;
  consensus?: {
    consensus_label: string;
    source_count: number;
    sources: Array<{
      source: string;
      authority: string;
      kev_status?: string;
      evidence?: string;
      date_added?: string;
      ransomware_use?: string;
      required_action?: string;
    }>;
    has_conflict: boolean;
    conflict_details?: string | null;
  };
  vulnerability_class?: string;
  why_worth_researching?: {
    vulnerability_class: string;
    class_impact: string;
    is_actively_exploited: boolean;
    exploitation_context: string;
    grounding_disclaimer: string;
    truth_classification: string;
    matching_company: {
      id: number;
      name: string;
      domain: string;
    } | null;
  };
  cwes: string[];
  owasp_categories: string[];
}

interface BountyRecord {
  id: number;
  program_name: string;
  program_url: string | null;
  award_amount: number;
  currency: string;
  source: string;
  source_url: string;
  published_at: string | null;
  measurement_type: string;
  notes: string | null;
}

interface BountyIntelligence {
  status: "available" | "unavailable";
  vulnerability_class: string;
  message: string | null;
  records: BountyRecord[];
  verified_count: number;
  range: { min: number; max: number } | null;
  median: number | null;
  average: number | null;
  currency: string;
  methodology: string;
  sources: string[];
}

interface KBStats {
  total_advisories: number;
  by_provider: Record<string, number>;
  cwe_count: number;
  owasp_count: number;
}

interface KnowledgeSource {
  id: number;
  source_type: string;
  name: string;
  version: string | null;
  source_url: string | null;
  retrieved_at: string | null;
  record_count: number;
  status: string;
}

interface KnowledgeSyncRun {
  id: number;
  started_at: string;
  completed_at: string | null;
  status: string;
  records_seen: number;
  records_created: number;
  records_updated: number;
  records_skipped: number;
  records_failed: number;
  error_count: number;
}

export default function SecurityKnowledgePage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<KBStats | null>(null);
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [syncRuns, setSyncRuns] = useState<KnowledgeSyncRun[]>([]);
  const [advisories, setAdvisories] = useState<Advisory[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const limit = 25;

  // Search and filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProvider, setSelectedProvider] = useState<string>("ALL");
  const [activeTab, setActiveTab] = useState<"advisories" | "sources" | "sync_runs">("advisories");

  // Modal inspection state
  const [selectedAdvisoryId, setSelectedAdvisoryId] = useState<number | null>(null);
  const [advisoryDetail, setAdvisoryDetail] = useState<AdvisoryDetail | null>(null);
  const [bountyIntel, setBountyIntel] = useState<BountyIntelligence | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Dedicated ref to ensure the modal body owns vertical scroll
  const modalBodyRef = useRef<HTMLDivElement>(null);

  const fetchStatsAndSources = async () => {
    try {
      const [statsData, sourcesData, runsData] = await Promise.all([
        apiFetch<KBStats>("/api/v1/security-knowledge/stats").catch(() => null),
        apiFetch<KnowledgeSource[]>("/api/v1/security-knowledge/sources").catch(() => []),
        apiFetch<KnowledgeSyncRun[]>("/api/v1/security-knowledge/sync-runs").catch(() => []),
      ]);
      if (statsData) setStats(statsData);
      if (sourcesData) setSources(sourcesData);
      if (runsData) setSyncRuns(runsData);
    } catch (err) {
      console.error("Failed to load knowledge telemetry:", err);
    }
  };

  const fetchAdvisories = async () => {
    setLoading(true);
    try {
      const offset = (page - 1) * limit;
      let url = `/api/v1/security-knowledge?limit=${limit}&offset=${offset}`;
      if (searchQuery.trim()) {
        url += `&q=${encodeURIComponent(searchQuery.trim())}`;
      }
      if (selectedProvider !== "ALL") {
        url += `&provider=${encodeURIComponent(selectedProvider)}`;
      }
      const data = await apiFetch<{ total: number; limit: number; offset: number; items: Advisory[] }>(url);
      setAdvisories(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error("Failed to fetch advisories:", err);
      setAdvisories([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatsAndSources();
  }, []);

  useEffect(() => {
    fetchAdvisories();
  }, [page, selectedProvider]);

  // Handle modal detail fetching when an advisory is selected
  useEffect(() => {
    if (!selectedAdvisoryId) {
      setAdvisoryDetail(null);
      setBountyIntel(null);
      return;
    }

    let isMounted = true;
    setDetailLoading(true);

    Promise.all([
      apiFetch<AdvisoryDetail>(`/api/v1/security-knowledge/${selectedAdvisoryId}`).catch(() => null),
      apiFetch<BountyIntelligence>(`/api/v1/security-knowledge/${selectedAdvisoryId}/bounty-intelligence`).catch(() => null),
    ]).then(([detail, bounty]) => {
      if (!isMounted) return;
      if (detail) setAdvisoryDetail(detail);
      if (bounty) setBountyIntel(bounty);
      setDetailLoading(false);
    });

    return () => {
      isMounted = false;
    };
  }, [selectedAdvisoryId]);

  // Lock background body scroll and bind ESC key listener
  useEffect(() => {
    if (!selectedAdvisoryId) return;

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelectedAdvisoryId(null);
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [selectedAdvisoryId]);

  // Guarantee modal content starts at top when opened or changed
  useEffect(() => {
    if (selectedAdvisoryId && modalBodyRef.current) {
      modalBodyRef.current.scrollTop = 0;
    }
  }, [selectedAdvisoryId, advisoryDetail]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchAdvisories();
  };

  const totalPages = Math.ceil(total / limit) || 1;

  const formatCurrency = (val: number, curr = "USD") => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: curr,
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Page Title & Status Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="font-mono text-xs uppercase tracking-widest text-cyan-400">
              Global Intelligence Repository
            </span>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Security Knowledge Base
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Vulnerability advisories, weakness taxonomies, and exploit mappings.
          </p>
        </div>
      </div>

      {/* High-Level Metric Tiles */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="font-mono text-[11px] font-medium uppercase tracking-wider text-slate-400">Total Advisories</div>
          <div className="mt-2 font-mono text-2xl font-bold text-white">
            {stats ? stats.total_advisories.toLocaleString() : "..."}
          </div>
          <div className="mt-1 text-[11px] text-slate-500">Cross-source catalog records</div>
        </div>

        <div className="rounded-xl border border-rose-900/30 bg-rose-950/10 p-4 backdrop-blur-sm">
          <div className="font-mono text-[11px] font-medium uppercase tracking-wider text-rose-400">CISA KEV Catalog</div>
          <div className="mt-2 font-mono text-2xl font-bold text-rose-300">
            {stats?.by_provider?.["CISA_KEV"] ? stats.by_provider["CISA_KEV"].toLocaleString() : "..."}
          </div>
          <div className="mt-1 text-[11px] text-rose-500/80">Known Exploited Vulnerabilities</div>
        </div>

        <div className="rounded-xl border border-cyan-900/30 bg-cyan-950/10 p-4 backdrop-blur-sm">
          <div className="font-mono text-[11px] font-medium uppercase tracking-wider text-cyan-400">CWE Weaknesses</div>
          <div className="mt-2 font-mono text-2xl font-bold text-cyan-300">
            {stats ? stats.cwe_count.toLocaleString() : "..."}
          </div>
          <div className="mt-1 text-[11px] text-cyan-500/80">MITRE Weakness Classifications</div>
        </div>

        <div className="rounded-xl border border-amber-900/30 bg-amber-950/10 p-4 backdrop-blur-sm">
          <div className="font-mono text-[11px] font-medium uppercase tracking-wider text-amber-400">OWASP Categories</div>
          <div className="mt-2 font-mono text-2xl font-bold text-amber-300">
            {stats ? stats.owasp_count.toLocaleString() : "..."}
          </div>
          <div className="mt-1 text-[11px] text-amber-500/80">Top 10 Security Taxonomy Map</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 font-mono text-xs">
        <button
          onClick={() => setActiveTab("advisories")}
          className={`px-4 py-2.5 font-bold transition border-b-2 -mb-px ${
            activeTab === "advisories"
              ? "border-cyan-400 text-cyan-300 bg-cyan-950/20"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          SECURITY ADVISORIES ({total.toLocaleString()})
        </button>
        <button
          onClick={() => setActiveTab("sources")}
          className={`px-4 py-2.5 font-bold transition border-b-2 -mb-px ${
            activeTab === "sources"
              ? "border-cyan-400 text-cyan-300 bg-cyan-950/20"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          DATA SOURCES ({sources.length})
        </button>
        <button
          onClick={() => setActiveTab("sync_runs")}
          className={`px-4 py-2.5 font-bold transition border-b-2 -mb-px ${
            activeTab === "sync_runs"
              ? "border-cyan-400 text-cyan-300 bg-cyan-950/20"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          INGESTION TELEMETRY ({syncRuns.length})
        </button>
      </div>

      {/* Main Tab Content */}
      {activeTab === "advisories" && (
        <div className="space-y-4">
          {/* Search & Provider Filter Bar */}
          <form onSubmit={handleSearchSubmit} className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[260px]">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by CVE (e.g. CVE-2026-85046), vendor (e.g. Google), product (e.g. Chromium V8), or keyword..."
                className="w-full rounded-lg border border-slate-800 bg-slate-900/90 px-4 py-2 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery("");
                    setPage(1);
                  }}
                  className="absolute right-3 top-2.5 text-xs text-slate-400 hover:text-white"
                >
                  Clear
                </button>
              )}
            </div>

            <select
              value={selectedProvider}
              onChange={(e) => {
                setSelectedProvider(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 font-mono text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
            >
              <option value="ALL">All Providers</option>
              <option value="CISA_KEV">CISA KEV</option>
              <option value="NVD">NVD (National Vulnerability Database)</option>
              <option value="OSV">OSV (Open Source Vulnerabilities)</option>
              <option value="GHSA">GitHub Security Advisories</option>
            </select>

            <button
              type="submit"
              className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-bold text-slate-950 hover:bg-cyan-400 transition"
            >
              SEARCH
            </button>
          </form>

          {/* Results Summary Bar */}
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <div>
              Showing {advisories.length > 0 ? (page - 1) * limit + 1 : 0} -{" "}
              {Math.min(page * limit, total)} of {total.toLocaleString()} records
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
              >
                Previous
              </button>
              <span>
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>

          {/* Advisories Grid */}
          {loading ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center">
              <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent mb-3" />
              <div className="font-mono text-xs text-slate-400">Loading knowledge records...</div>
            </div>
          ) : advisories.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center">
              <div className="font-mono text-sm font-semibold text-slate-300">No security advisories match your query</div>
              <div className="mt-1 text-xs text-slate-500">Try adjusting your keyword search or provider filter.</div>
            </div>
          ) : (
            <div className="space-y-3">
              {advisories.map((adv) => {
                const isRansomware = adv.known_ransomware_use?.toLowerCase() === "known";
                return (
                  <div
                    key={adv.id}
                    onClick={() => setSelectedAdvisoryId(adv.id)}
                    className="cursor-pointer rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition hover:border-cyan-700/60 hover:bg-slate-900/90 shadow-sm"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        {adv.cve_id && (
                          <span className="rounded border border-cyan-800/60 bg-cyan-950/40 px-2 py-0.5 font-mono text-xs font-bold text-cyan-300">
                            {adv.cve_id}
                          </span>
                        )}
                        <span className="rounded border border-slate-800 bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-400 uppercase">
                          {adv.provider}
                        </span>
                        {adv.provider === "CISA_KEV" && (
                          <span className="rounded border border-rose-900/60 bg-rose-950/40 px-1.5 py-0.5 font-mono text-[10px] font-bold text-rose-300 flex items-center gap-1">
                            <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
                            ACTIVELY EXPLOITED
                          </span>
                        )}
                        {isRansomware && (
                          <span className="rounded border border-rose-800/80 bg-rose-950/60 px-1.5 py-0.5 font-mono text-[10px] font-bold text-rose-300">
                            RANSOMWARE USE
                          </span>
                        )}
                      </div>

                      <div className="font-mono text-xs text-slate-500">
                        Added: {adv.date_added ? new Date(adv.date_added).toLocaleDateString() : "N/A"}
                      </div>
                    </div>

                    <h3 className="mt-2 text-sm font-semibold text-white leading-snug">
                      {adv.title}
                    </h3>

                    {adv.summary && (
                      <p className="mt-1 text-xs text-slate-400 line-clamp-2 leading-relaxed">
                        {adv.summary}
                      </p>
                    )}

                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800/60 pt-2.5 text-[11px] font-mono text-slate-400">
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500">AFFECTED:</span>
                        <span className="text-slate-200 font-semibold">{adv.vendor || "Unknown Vendor"}</span>
                        <span className="text-slate-600">/</span>
                        <span className="text-cyan-300">{adv.product || "Unknown Product"}</span>
                      </div>

                      <div className="flex items-center gap-1.5 flex-wrap">
                        {adv.cwes.map((cwe) => (
                          <span key={cwe} className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-amber-300">
                            {cwe}
                          </span>
                        ))}
                        {adv.owasp_categories.map((owasp) => (
                          <span key={owasp} className="rounded bg-purple-950/50 border border-purple-800/50 px-1.5 py-0.5 text-[10px] text-purple-300">
                            OWASP {owasp}
                          </span>
                        ))}
                        <span className="text-cyan-400 hover:text-cyan-300 font-semibold pl-2">
                          Inspect Details →
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Pagination Footer */}
          {total > limit && (
            <div className="flex items-center justify-between border-t border-slate-800 pt-4 font-mono text-xs text-slate-400">
              <div>
                Page {page} of {totalPages} ({total.toLocaleString()} total advisories)
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(1)}
                  disabled={page <= 1}
                  className="rounded border border-slate-800 bg-slate-900 px-2 py-1 hover:bg-slate-800 disabled:opacity-40"
                >
                  First
                </button>
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="rounded border border-slate-800 bg-slate-900 px-2.5 py-1 hover:bg-slate-800 disabled:opacity-40"
                >
                  Prev
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="rounded border border-slate-800 bg-slate-900 px-2.5 py-1 hover:bg-slate-800 disabled:opacity-40"
                >
                  Next
                </button>
                <button
                  onClick={() => setPage(totalPages)}
                  disabled={page >= totalPages}
                  className="rounded border border-slate-800 bg-slate-900 px-2 py-1 hover:bg-slate-800 disabled:opacity-40"
                >
                  Last
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sources Tab */}
      {activeTab === "sources" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="font-mono text-xs font-bold uppercase tracking-wider text-slate-300">Registered Knowledge Sources</h3>
            <p className="mt-1 text-xs text-slate-400">Authoritative global security feeds and catalog sources used for ingestion.</p>

            <div className="mt-4 divide-y divide-slate-800">
              {sources.map((s) => (
                <div key={s.id} className="py-3 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white text-sm">{s.name}</span>
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-cyan-300">{s.source_type}</span>
                      <span className="rounded border border-emerald-800 bg-emerald-950/40 px-1.5 py-0.5 font-mono text-[10px] text-emerald-400">{s.status}</span>
                    </div>
                    <div className="mt-1 text-xs text-slate-400 font-mono">
                      Catalog Version: <span className="text-slate-200">{s.version || "N/A"}</span> | Records Ingested: <span className="text-cyan-300 font-bold">{s.record_count.toLocaleString()}</span>
                    </div>
                    {s.source_url && (
                      <a href={s.source_url} target="_blank" rel="noopener noreferrer" className="mt-1 block text-[11px] text-slate-500 hover:text-cyan-400 truncate max-w-xl">
                        {s.source_url}
                      </a>
                    )}
                  </div>

                  <div className="font-mono text-xs text-slate-500 text-right">
                    Last sync: {s.retrieved_at ? new Date(s.retrieved_at).toLocaleString() : "N/A"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Ingestion Telemetry Tab */}
      {activeTab === "sync_runs" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="font-mono text-xs font-bold uppercase tracking-wider text-slate-300">Ingestion Execution Telemetry</h3>
            <p className="mt-1 text-xs text-slate-400">Audit trail of knowledge synchronization runs and delta statistics.</p>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left font-mono text-xs text-slate-300">
                <thead className="border-b border-slate-800 text-[10px] uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="py-2.5">Run ID</th>
                    <th className="py-2.5">Started</th>
                    <th className="py-2.5">Status</th>
                    <th className="py-2.5 text-right">Seen</th>
                    <th className="py-2.5 text-right">Created</th>
                    <th className="py-2.5 text-right">Updated</th>
                    <th className="py-2.5 text-right">Skipped</th>
                    <th className="py-2.5 text-right">Failed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {syncRuns.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-800/30">
                      <td className="py-2.5 text-cyan-400">#{r.id}</td>
                      <td className="py-2.5 text-slate-400">{new Date(r.started_at).toLocaleString()}</td>
                      <td className="py-2.5">
                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                          r.status === "COMPLETED"
                            ? "bg-emerald-950/40 text-emerald-400 border border-emerald-800/60"
                            : r.status === "RUNNING"
                            ? "bg-cyan-950/40 text-cyan-300 border border-cyan-800/60"
                            : "bg-rose-950/40 text-rose-300 border border-rose-800/60"
                        }`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="py-2.5 text-right">{r.records_seen.toLocaleString()}</td>
                      <td className="py-2.5 text-right text-emerald-400 font-bold">{r.records_created.toLocaleString()}</td>
                      <td className="py-2.5 text-right text-cyan-300">{r.records_updated.toLocaleString()}</td>
                      <td className="py-2.5 text-right text-slate-500">{r.records_skipped.toLocaleString()}</td>
                      <td className="py-2.5 text-right text-rose-400">{r.records_failed.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* REPAIRED VULNERABILITY DETAIL MODAL */}
      {selectedAdvisoryId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/80 backdrop-blur-md"
          onClick={(e) => {
            if (e.target === e.currentTarget) setSelectedAdvisoryId(null);
          }}
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-3xl max-h-[88vh] flex flex-col rounded-2xl border border-slate-700/80 bg-slate-900 shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* STICKY HEADER */}
            <div className="shrink-0 flex items-start justify-between gap-4 border-b border-slate-800/90 bg-slate-900/95 px-6 py-4 backdrop-blur-md z-10">
              <div className="space-y-1.5 min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  {advisoryDetail?.cve_id ? (
                    <span className="rounded border border-cyan-800/80 bg-cyan-950/60 px-2.5 py-0.5 font-mono text-xs font-bold text-cyan-300">
                      {advisoryDetail.cve_id}
                    </span>
                  ) : (
                    <span className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 font-mono text-xs text-slate-300">
                      {advisoryDetail?.canonical_id || "VULNERABILITY"}
                    </span>
                  )}
                  <span className="rounded border border-slate-800 bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-slate-300 uppercase">
                    {advisoryDetail?.provider || "CATALOG"}
                  </span>
                  {advisoryDetail?.vulnerability_class && (
                    <span className="rounded border border-amber-900/60 bg-amber-950/40 px-2 py-0.5 font-mono text-[10px] font-semibold text-amber-300">
                      {advisoryDetail.vulnerability_class}
                    </span>
                  )}
                  {advisoryDetail?.provider === "CISA_KEV" && (
                    <span className="rounded border border-rose-900/80 bg-rose-950/60 px-2 py-0.5 font-mono text-[10px] font-bold text-rose-300 flex items-center gap-1">
                      <span className="h-1.5 w-1.5 rounded-full bg-rose-400 animate-pulse" />
                      KEV ACTIVELY EXPLOITED
                    </span>
                  )}
                </div>
                <h2 className="text-base sm:text-lg font-bold text-white leading-snug">
                  {advisoryDetail?.title || (detailLoading ? "Loading advisory..." : "Vulnerability Detail")}
                </h2>
              </div>
              <button
                onClick={() => setSelectedAdvisoryId(null)}
                className="rounded-lg border border-slate-700/80 bg-slate-800/60 p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition shrink-0"
                title="Close (Esc)"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* SCROLLABLE BODY (Only this container owns vertical scroll) */}
            <div
              ref={modalBodyRef}
              className="flex-1 overflow-y-auto overscroll-contain px-6 py-5 space-y-6 text-xs"
            >
              {detailLoading && !advisoryDetail ? (
                <div className="py-16 text-center">
                  <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent mb-3" />
                  <div className="font-mono text-xs text-slate-400">Loading comprehensive vulnerability intelligence...</div>
                </div>
              ) : advisoryDetail ? (
                <>
                  {/* SECTION A: Description & Attacker Capabilities */}
                  <div>
                    <h3 className="font-mono text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                      Vulnerability Summary & Attacker Capabilities
                    </h3>
                    <p className="text-slate-300 text-xs leading-relaxed font-sans bg-slate-950/40 border border-slate-800/80 rounded-xl p-3.5">
                      {advisoryDetail.summary || "No detailed summary provided in catalog record."}
                    </p>
                  </div>

                  {/* SECTION B: Key Security Metrics Grid */}
                  <div>
                    <h3 className="font-mono text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
                      Key Security Attributes
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 font-mono">
                      <div className="space-y-0.5">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider">Vendor</div>
                        <div className="text-slate-200 font-semibold truncate">{advisoryDetail.vendor || "N/A"}</div>
                      </div>
                      <div className="space-y-0.5">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider">Product</div>
                        <div className="text-cyan-300 font-semibold truncate">{advisoryDetail.product || "N/A"}</div>
                      </div>
                      <div className="space-y-0.5">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider">Date Added to KEV</div>
                        <div className="text-slate-200">
                          {advisoryDetail.date_added ? new Date(advisoryDetail.date_added).toLocaleDateString() : "N/A"}
                        </div>
                      </div>
                      <div className="space-y-0.5">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider">Remediation Due Date</div>
                        <div className="text-amber-400 font-bold">
                          {advisoryDetail.due_date ? new Date(advisoryDetail.due_date).toLocaleDateString() : "N/A"}
                        </div>
                      </div>
                      <div className="space-y-0.5">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider">Ransomware Campaign Use</div>
                        <div className={advisoryDetail.known_ransomware_use?.toLowerCase() === "known" ? "text-rose-400 font-bold" : "text-slate-400"}>
                          {advisoryDetail.known_ransomware_use || "Unknown"}
                        </div>
                      </div>
                      <div className="space-y-0.5">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider">Source Confidence</div>
                        <div className="text-emerald-400 font-bold">{Math.round(advisoryDetail.confidence * 100)}% Verified</div>
                      </div>
                    </div>
                  </div>

                  {/* SECTION C: Forensic Triage & Remediation Guidance */}
                  {advisoryDetail.description && (
                    <div>
                      <h3 className="font-mono text-[11px] font-bold uppercase tracking-wider text-amber-400 mb-1.5 flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                        Remediation Directive & Action Required
                      </h3>
                      <div className="rounded-xl border border-amber-900/40 bg-amber-950/15 p-3.5 text-xs text-amber-200/90 leading-relaxed font-sans">
                        {advisoryDetail.description}
                      </div>
                    </div>
                  )}

                  {/* SECTION D: Weakness Taxonomy & Classifications */}
                  <div>
                    <h3 className="font-mono text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-purple-400" />
                      Weakness Classifications & Taxonomy
                    </h3>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3.5 space-y-2.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[11px] text-slate-400 font-mono">Vulnerability Class:</span>
                        <span className="rounded border border-amber-800/60 bg-amber-950/40 px-2 py-0.5 font-mono text-xs font-bold text-amber-300">
                          {advisoryDetail.vulnerability_class || "General Weakness"}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/60">
                        <span className="text-[11px] text-slate-400 font-mono">MITRE CWEs:</span>
                        {advisoryDetail.cwes && advisoryDetail.cwes.length > 0 ? (
                          advisoryDetail.cwes.map((cwe) => (
                            <span key={cwe} className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[11px] text-amber-300 border border-amber-800/40">
                              {cwe}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-500 font-mono text-[11px]">Class derived via catalog pattern</span>
                        )}
                      </div>
                      {advisoryDetail.owasp_categories && advisoryDetail.owasp_categories.length > 0 && (
                        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/60">
                          <span className="text-[11px] text-slate-400 font-mono">OWASP Top 10:</span>
                          {advisoryDetail.owasp_categories.map((owasp) => (
                            <span key={owasp} className="rounded bg-purple-950/60 border border-purple-800 px-2 py-0.5 font-mono text-[11px] text-purple-300">
                              OWASP {owasp}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* SECTION E: Authoritative Evidence & Multi-Source Consensus */}
                  <div>
                    <h3 className="font-mono text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      Authoritative Evidence & Consensus
                    </h3>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3.5 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-emerald-950/60 border border-emerald-800/80 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-300">
                            {advisoryDetail.consensus?.consensus_label || "OFFICIAL SOURCE VERIFIED"}
                          </span>
                          <span className="font-mono text-slate-400 text-[11px]">
                            ({advisoryDetail.consensus?.source_count || 1} Authoritative Source)
                          </span>
                        </div>
                        {advisoryDetail.source_url && (
                          <a
                            href={advisoryDetail.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-mono text-[11px] text-cyan-400 hover:text-cyan-300 underline"
                          >
                            Catalog Source Link ↗
                          </a>
                        )}
                      </div>
                      <div className="text-slate-400 text-[11px] leading-relaxed pt-1">
                        Ingested directly from authoritative government catalog ({advisoryDetail.provider}) with cryptographic record validation and unmitigated exploitation evidence.
                      </div>
                    </div>
                  </div>

                  {/* SECTION F: "Why This May Be Worth Researching" */}
                  {advisoryDetail.why_worth_researching && (
                    <div className="rounded-xl border border-cyan-900/50 bg-cyan-950/20 p-4 space-y-3">
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="font-mono text-xs font-bold text-cyan-300 uppercase tracking-wider flex items-center gap-2">
                          <svg className="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                          </svg>
                          Why This May Be Worth Researching
                        </div>
                        <span className="rounded border border-cyan-800/80 bg-cyan-900/40 px-2 py-0.5 font-mono text-[10px] font-bold text-cyan-300">
                          {advisoryDetail.why_worth_researching.truth_classification}
                        </span>
                      </div>

                      <div className="text-slate-300 text-xs leading-relaxed">
                        {advisoryDetail.why_worth_researching.class_impact}
                      </div>

                      <div className="rounded-lg border border-cyan-900/40 bg-slate-900/60 p-2.5 text-[11px] text-slate-400 flex items-start gap-2">
                        <svg className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>{advisoryDetail.why_worth_researching.grounding_disclaimer}</span>
                      </div>
                    </div>
                  )}

                  {/* SECTION G: "Verified Bounty Intelligence" */}
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="font-mono text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                        <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Verified Bounty Intelligence ({advisoryDetail.vulnerability_class || "Class"})
                      </div>
                      <span className="font-mono text-[10px] text-slate-500 uppercase">
                        {bountyIntel?.status === "available" ? "Public Evidence Verified" : "Data Grounded"}
                      </span>
                    </div>

                    {bountyIntel?.status === "available" ? (
                      <div className="space-y-3">
                        <div className="grid grid-cols-3 gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-center font-mono">
                          <div>
                            <div className="text-[10px] text-slate-500 uppercase">Award Range</div>
                            <div className="text-sm font-bold text-emerald-400">
                              {formatCurrency(bountyIntel.range?.min || 0)} - {formatCurrency(bountyIntel.range?.max || 0)}
                            </div>
                          </div>
                          <div>
                            <div className="text-[10px] text-slate-500 uppercase">Median Award</div>
                            <div className="text-sm font-bold text-white">
                              {formatCurrency(bountyIntel.median || 0)}
                            </div>
                          </div>
                          <div>
                            <div className="text-[10px] text-slate-500 uppercase">Verified Records</div>
                            <div className="text-sm font-bold text-cyan-300">
                              {bountyIntel.verified_count} Disclosures
                            </div>
                          </div>
                        </div>

                        <div className="divide-y divide-slate-800/80 border border-slate-800 rounded-lg overflow-hidden font-mono text-[11px]">
                          {bountyIntel.records.map((r) => (
                            <div key={r.id} className="p-2.5 bg-slate-900/40 flex items-center justify-between">
                              <div>
                                <span className="font-bold text-slate-200">{r.program_name}</span>
                                <span className="text-slate-500 ml-2">via {r.source}</span>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className="text-emerald-400 font-bold">{formatCurrency(r.award_amount, r.currency)}</span>
                                {r.source_url && (
                                  <a href={r.source_url} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:text-cyan-300 underline">
                                    Evidence ↗
                                  </a>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>

                        <p className="text-[10px] text-slate-500 italic font-mono">
                          Methodology: {bountyIntel.methodology}
                        </p>
                      </div>
                    ) : (
                      <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-4 text-center space-y-1.5">
                        <div className="flex justify-center text-slate-500 mb-1">
                          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        </div>
                        <div className="font-mono text-xs font-semibold text-slate-300">
                          No verified public award data available for this vulnerability class.
                        </div>
                        <div className="text-[11px] text-slate-500 max-w-lg mx-auto leading-relaxed">
                          We strictly present verified public bug bounty awards and audited writeups. No synthetic or extrapolated payout statistics are generated.
                        </div>
                      </div>
                    )}
                  </div>

                  {/* SECTION H: Monitored Workspace Target Correlation CTA */}
                  {advisoryDetail.why_worth_researching?.matching_company ? (
                    <div className="rounded-xl border border-emerald-900/50 bg-emerald-950/20 p-4 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <div className="font-mono text-xs font-bold text-emerald-300 uppercase tracking-wider flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full bg-emerald-400" />
                          Monitored Organization Correlation
                        </div>
                        <span className="rounded border border-emerald-800 bg-emerald-900/40 px-2 py-0.5 font-mono text-[10px] text-emerald-300">
                          Workspace Target Active
                        </span>
                      </div>
                      <p className="text-slate-300 text-xs leading-relaxed">
                        <strong className="text-white">{advisoryDetail.why_worth_researching.matching_company.name}</strong> ({advisoryDetail.why_worth_researching.matching_company.domain}) is an active enrolled company in your workspace. You can inspect enrolled assets, subdomains, and attack surface diffs for this organization.
                      </p>
                      <div className="pt-1 flex items-center gap-3">
                        <Link
                          href={`/companies/${advisoryDetail.why_worth_researching.matching_company.id}`}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 px-3.5 py-1.5 font-mono text-xs font-bold text-slate-950 transition"
                        >
                          <span>Inspect {advisoryDetail.why_worth_researching.matching_company.name} Attack Surface</span>
                          <span>→</span>
                        </Link>
                        <Link
                          href="/targets"
                          className="font-mono text-xs text-slate-400 hover:text-slate-200 transition"
                        >
                          View Workspace Scope
                        </Link>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3.5 flex items-center justify-between text-xs">
                      <div className="text-slate-400 font-mono">
                        Want to correlate this vulnerability against monitored company targets?
                      </div>
                      <Link
                        href="/targets"
                        className="font-mono text-cyan-400 hover:text-cyan-300 font-bold transition"
                      >
                        Explore Monitored Targets →
                      </Link>
                    </div>
                  )}
                </>
              ) : (
                <div className="py-12 text-center font-mono text-xs text-rose-400">
                  Failed to load advisory details. Please try again.
                </div>
              )}
            </div>

            {/* STICKY FOOTER */}
            <div className="shrink-0 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 bg-slate-900/95 px-6 py-3.5 backdrop-blur-md z-10">
              <div className="flex items-center gap-3">
                {advisoryDetail?.source_url && (
                  <a
                    href={advisoryDetail.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 font-mono text-xs text-cyan-400 hover:text-cyan-300 transition underline underline-offset-4"
                  >
                    <span>Official Source Advisory</span>
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                )}
              </div>
              <div className="flex items-center gap-3">
                {advisoryDetail?.why_worth_researching?.matching_company && (
                  <Link
                    href={`/companies/${advisoryDetail.why_worth_researching.matching_company.id}`}
                    className="rounded-lg border border-cyan-700/60 bg-cyan-950/40 px-3.5 py-1.5 font-mono text-xs font-semibold text-cyan-300 hover:bg-cyan-900/50 transition"
                  >
                    Inspect {advisoryDetail.why_worth_researching.matching_company.name}
                  </Link>
                )}
                <button
                  onClick={() => setSelectedAdvisoryId(null)}
                  className="rounded-lg bg-slate-800 hover:bg-slate-700 px-4 py-1.5 font-mono text-xs font-semibold text-slate-200 transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
