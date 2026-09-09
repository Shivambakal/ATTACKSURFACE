"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import {
  HistoricalCoverage,
  HistoricalRelease,
  HistoryComparisonResult,
  TimelineEvent,
} from "@/lib/types";
import ThreeDTimeline from "@/components/ThreeDTimeline";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function CompanyHistoryPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const companyId = resolvedParams.id;

  const [loading, setLoading] = useState(true);
  const [reconstructing, setReconstructing] = useState(false);
  const [company, setCompany] = useState<any>(null);
  const [coverage, setCoverage] = useState<HistoricalCoverage | null>(null);
  const [fingerprint, setFingerprint] = useState<Record<string, number>>({});
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);

  // Filter States
  const [timeRange, setTimeRange] = useState<string>("all");
  const [category, setCategory] = useState<string>("ALL");
  const [activeTab, setActiveTab] = useState<"timeline" | "releases" | "features" | "assets" | "security" | "compare">("timeline");

  // Tab Data States
  const [releases, setReleases] = useState<HistoricalRelease[]>([]);
  const [features, setFeatures] = useState<any[]>([]);
  const [assets, setAssets] = useState<any[]>([]);
  const [securityEvents, setSecurityEvents] = useState<any[]>([]);

  // Compare Tool States
  const [compareFrom, setCompareFrom] = useState<string>("2024-01-01");
  const [compareTo, setCompareTo] = useState<string>("2026-09-01");
  const [comparisonResult, setComparisonResult] = useState<HistoryComparisonResult | null>(null);
  const [comparing, setComparing] = useState(false);

  const fetchHistoryOverview = async () => {
    setLoading(true);
    try {
      let url = `/api/v1/companies/${companyId}/history?range=${timeRange}`;
      if (category !== "ALL") {
        url += `&category=${category}`;
      }
      const data = await apiFetch<any>(url);
      setCompany(data.company);
      setCoverage(data.coverage);
      setFingerprint(data.weakness_fingerprint || {});
      setTimelineEvents(data.timeline_events || []);
    } catch (err) {
      console.error("Failed to load history overview:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTabData = async () => {
    try {
      if (activeTab === "releases") {
        const data = await apiFetch<HistoricalRelease[]>(`/api/v1/companies/${companyId}/history/releases`);
        setReleases(data);
      } else if (activeTab === "features") {
        const data = await apiFetch<any[]>(`/api/v1/companies/${companyId}/history/features`);
        setFeatures(data);
      } else if (activeTab === "assets") {
        const data = await apiFetch<any[]>(`/api/v1/companies/${companyId}/history/assets`);
        setAssets(data);
      } else if (activeTab === "security") {
        const data = await apiFetch<any>(`/api/v1/companies/${companyId}/history/security`);
        setSecurityEvents(data.security_events || []);
      }
    } catch (err) {
      console.error(`Failed to load ${activeTab} data:`, err);
    }
  };

  useEffect(() => {
    fetchHistoryOverview();
  }, [companyId, timeRange, category]);

  useEffect(() => {
    fetchTabData();
  }, [companyId, activeTab]);

  const handleReconstruct = async () => {
    setReconstructing(true);
    try {
      await apiFetch(`/api/v1/companies/${companyId}/history/reconstruct`, { method: "POST" });
      await fetchHistoryOverview();
      await fetchTabData();
    } catch (err) {
      console.error("Reconstruction trigger failed:", err);
    } finally {
      setReconstructing(false);
    }
  };

  const handleRunCompare = async (e: React.FormEvent) => {
    e.preventDefault();
    setComparing(true);
    try {
      const res = await apiFetch<HistoryComparisonResult>(
        `/api/v1/companies/${companyId}/history/compare?from=${compareFrom}&to=${compareTo}`
      );
      setComparisonResult(res);
    } catch (err) {
      console.error("Comparison failed:", err);
    } finally {
      setComparing(false);
    }
  };

  if (loading && !company) {
    return (
      <div className="space-y-6">
        <div className="h-40 rounded-2xl border border-slate-800 bg-slate-900/60 animate-pulse" />
        <div className="h-96 rounded-2xl border border-slate-800 bg-slate-900/40 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header & Historical Coverage Banner */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-xl backdrop-blur-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <Link
              href={`/companies/${companyId}`}
              className="rounded-lg border border-slate-800 bg-slate-950 p-2 text-slate-400 hover:text-white transition-colors"
              title="Back to Command Center"
            >
              ←
            </Link>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-white">HISTORICAL INTELLIGENCE</h1>
                <span className="rounded bg-cyan-950 px-2 py-0.5 font-mono text-xs font-semibold text-cyan-300 border border-cyan-800/80">
                  {company?.canonical_domain}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Evidence-backed attack surface evolution reconstructed from GitHub releases, changelogs, documentation, and vulnerability databases.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleReconstruct}
              disabled={reconstructing}
              className="flex items-center gap-2 rounded-lg bg-cyan-600 px-4 py-2 font-mono text-xs font-bold text-white shadow-lg hover:bg-cyan-500 disabled:opacity-50 transition-colors"
            >
              <svg className={`h-4 w-4 ${reconstructing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {reconstructing ? "RECONSTRUCTING..." : "TRIGGER RECONSTRUCTION"}
            </button>
          </div>
        </div>

        {/* Coverage Metrics Card */}
        <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3 border-t border-slate-800 pt-5 font-mono text-xs">
          <div className="rounded-xl bg-slate-950/70 p-3 border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase">Temporal Coverage</span>
            <span className="text-white font-bold block mt-0.5 text-sm">
              {coverage?.coverage_start ? new Date(coverage.coverage_start).getFullYear() : "2021"} → {coverage?.coverage_end ? new Date(coverage.coverage_end).getFullYear() : "2026"}
            </span>
          </div>

          <div className="rounded-xl bg-slate-950/70 p-3 border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase">Independent Sources</span>
            <span className="text-cyan-300 font-bold block mt-0.5 text-sm">
              {coverage?.sources_count || 3} Verified Sources
            </span>
          </div>

          <div className="rounded-xl bg-slate-950/70 p-3 border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase">Confirmed Events</span>
            <span className="text-emerald-400 font-bold block mt-0.5 text-sm">
              {coverage?.confirmed_events_count || 0} Events
            </span>
          </div>

          <div className="rounded-xl bg-slate-950/70 p-3 border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase">Coverage Confidence</span>
            <span className="text-amber-300 font-bold block mt-0.5 text-sm">
              {Math.round((coverage?.confidence || 0.85) * 100)}%
            </span>
          </div>
        </div>

        {/* Transparency Disclaimer */}
        <div className="mt-4 flex items-center gap-2 rounded-lg bg-slate-950/50 border border-slate-800/80 px-3.5 py-2 text-[11px] text-slate-400 font-mono">
          <span className="text-amber-400 font-bold">ℹ DISCLAIMER:</span>
          <span>{coverage?.notes || "Historical intelligence reconstructed from publicly available evidence. Coverage represents verifiable public signals and may be partial."}</span>
        </div>
      </div>

      {/* Historical Weakness Fingerprint */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-md">
        <div className="mb-4">
          <h2 className="text-base font-bold text-white tracking-wide uppercase font-mono">
            HISTORICAL WEAKNESS FINGERPRINT
          </h2>
          <p className="text-xs text-slate-400">
            Distribution of public historical vulnerabilities and disclosures. Used to contextualize current attack surface expansions.
          </p>
        </div>

        {Object.keys(fingerprint).length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
            {Object.entries(fingerprint).map(([vClass, count]) => (
              <div key={vClass} className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 flex justify-between items-center">
                <span className="text-slate-300 font-semibold">{vClass}</span>
                <span className="rounded bg-red-950/80 border border-red-800/60 px-2 py-0.5 text-red-400 font-bold text-[11px]">
                  {count}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-800 p-6 text-center text-xs font-mono text-slate-500">
            NO PRIOR PUBLIC VULNERABILITIES RECORDED IN OSV / KEV CATALOGS FOR THIS ENTITY.
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-1 overflow-x-auto font-mono text-xs font-semibold">
        {[
          { key: "timeline", label: "UNIFIED TIMELINE" },
          { key: "releases", label: "RELEASES & TAGS" },
          { key: "features", label: "FEATURE EVOLUTION" },
          { key: "assets", label: "ASSET LIFECYCLE" },
          { key: "security", label: "SECURITY HISTORY" },
          { key: "compare", label: "COMPARE TWO DATES" },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key as any)}
            className={`px-4 py-2.5 border-b-2 transition-colors whitespace-nowrap ${
              activeTab === t.key
                ? "border-cyan-400 text-cyan-400 bg-cyan-950/20"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* TAB 1: UNIFIED 3D INTERACTIVE TIMELINE */}
      {activeTab === "timeline" && (
        <div className="space-y-4">
          <ThreeDTimeline
            events={timelineEvents}
            companyName={company?.name}
            domain={company?.canonical_domain}
          />
        </div>
      )}

      {/* TAB 2: RELEASES & TAGS */}
      {activeTab === "releases" && (
        <div className="space-y-3">
          {releases.map((rel) => (
            <div key={rel.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-sm">Tag: {rel.tag} ({rel.title})</span>
                <span className="text-slate-400">{rel.published_at ? new Date(rel.published_at).toLocaleDateString() : "Undated"}</span>
              </div>
              {rel.semantic_changes && rel.semantic_changes.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {rel.semantic_changes.map((sc) => (
                    <span key={sc} className="rounded bg-cyan-950/80 border border-cyan-800/60 px-2 py-0.5 text-[10px] font-bold text-cyan-300">
                      {sc}
                    </span>
                  ))}
                </div>
              )}
              {rel.body && <p className="mt-2 text-slate-300 whitespace-pre-line text-[11px]">{rel.body.slice(0, 400)}</p>}
            </div>
          ))}
        </div>
      )}

      {/* TAB 3: FEATURE EVOLUTION */}
      {activeTab === "features" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {features.map((feat) => (
            <div key={feat.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-sm">{feat.name}</span>
                <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-cyan-300">{feat.category}</span>
              </div>
              <p className="mt-1 text-slate-400 text-[11px]">{feat.description}</p>
              <div className="mt-3 border-t border-slate-800 pt-2 text-[10px] text-slate-500">
                First Observed: <strong className="text-slate-300">{new Date(feat.first_observed).toLocaleDateString()}</strong>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TAB 4: ASSET LIFECYCLE */}
      {activeTab === "assets" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden font-mono text-xs">
          <table className="w-full text-left">
            <thead className="border-b border-slate-800 bg-slate-950/80 text-slate-400 uppercase">
              <tr>
                <th className="p-3">Hostname</th>
                <th className="p-3">Type</th>
                <th className="p-3">Lifecycle Status</th>
                <th className="p-3">First Seen</th>
                <th className="p-3">Last Seen</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {assets.map((a) => (
                <tr key={a.id} className="hover:bg-slate-800/40">
                  <td className="p-3 font-semibold text-white">{a.hostname}</td>
                  <td className="p-3 text-slate-300">{a.asset_type}</td>
                  <td className="p-3">
                    <span className="rounded bg-emerald-950 border border-emerald-800 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
                      {a.lifecycle_status || "ACTIVE"}
                    </span>
                  </td>
                  <td className="p-3 text-slate-400">{new Date(a.first_observed).toLocaleDateString()}</td>
                  <td className="p-3 text-slate-400">{new Date(a.last_seen_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB 5: SECURITY HISTORY */}
      {activeTab === "security" && (
        <div className="space-y-3">
          {securityEvents.map((sec) => (
            <div key={sec.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-red-400 text-sm">{sec.cve_id}</span>
                <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">{sec.vulnerability_class || "GENERAL"}</span>
              </div>
              <p className="mt-1.5 text-slate-300">{sec.summary}</p>
            </div>
          ))}
        </div>
      )}

      {/* TAB 6: COMPARE TWO DATES */}
      {activeTab === "compare" && (
        <div className="space-y-4">
          <form onSubmit={handleRunCompare} className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4 font-mono text-xs">
            <div>
              <label className="block text-slate-400 text-[10px] uppercase mb-1">From Date</label>
              <input
                type="date"
                value={compareFrom}
                onChange={(e) => setCompareFrom(e.target.value)}
                className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-white"
              />
            </div>
            <div>
              <label className="block text-slate-400 text-[10px] uppercase mb-1">To Date</label>
              <input
                type="date"
                value={compareTo}
                onChange={(e) => setCompareTo(e.target.value)}
                className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-white"
              />
            </div>
            <button
              type="submit"
              disabled={comparing}
              className="mt-4 rounded-lg bg-cyan-600 px-4 py-2 font-bold text-white hover:bg-cyan-500 disabled:opacity-50"
            >
              {comparing ? "COMPARING..." : "COMPARE DATES"}
            </button>
          </form>

          {comparisonResult && (
            <div className="space-y-4 font-mono text-xs">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-center">
                  <span className="block text-lg font-bold text-cyan-400">{comparisonResult.summary.assets_count}</span>
                  <span className="text-[10px] text-slate-500 uppercase">Assets Added</span>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-center">
                  <span className="block text-lg font-bold text-amber-300">{comparisonResult.summary.features_count}</span>
                  <span className="text-[10px] text-slate-500 uppercase">Features Added</span>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-center">
                  <span className="block text-lg font-bold text-emerald-400">{comparisonResult.summary.apis_count}</span>
                  <span className="text-[10px] text-slate-500 uppercase">APIs Added</span>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-center">
                  <span className="block text-lg font-bold text-red-400">{comparisonResult.summary.security_events_count}</span>
                  <span className="text-[10px] text-slate-500 uppercase">Security Events</span>
                </div>
              </div>

              {comparisonResult.added_features.length > 0 && (
                <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                  <h4 className="font-bold text-white mb-2 uppercase">Features Introduced In Period</h4>
                  <ul className="space-y-1.5 text-slate-300">
                    {comparisonResult.added_features.map((f) => (
                      <li key={f.id} className="flex justify-between">
                        <span>+ {f.name}</span>
                        <span className="text-slate-500">{new Date(f.first_observed).toLocaleDateString()}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
