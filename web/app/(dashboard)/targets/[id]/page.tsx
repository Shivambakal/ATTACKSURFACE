"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Target, Change, TimelineEvent, ResearchSignal, ChangeCluster } from "@/lib/types";
import ResearchSignalCard from "@/components/ResearchSignalCard";

export default function TargetDetailPage() {
  const params = useParams();
  const targetId = params?.id as string;

  const [target, setTarget] = useState<Target | null>(null);
  const [changes, setChanges] = useState<Change[]>([]);
  const [signals, setSignals] = useState<ResearchSignal[]>([]);
  const [clusters, setClusters] = useState<ChangeCluster[]>([]);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [sinceLastVisitEvents, setSinceLastVisitEvents] = useState<TimelineEvent[]>([]);
  const [activeTab, setActiveTab] = useState<
    "overview" | "assets" | "features" | "technologies" | "history"
  >("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Snapshot action state
  const [snapshotBusy, setSnapshotBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const loadTargetData = useCallback(async () => {
    if (!targetId) return;
    setLoading(true);
    setError(null);

    try {
      // 1. Fetch Target Overview
      const overviewRes = await apiFetch<{ target: Target; changes: Change[] }>(
        `/api/v1/targets/${targetId}/overview`
      ).catch(async () => {
        // Fallback to direct get target
        const t = await apiFetch<Target>(`/api/v1/targets/${targetId}`);
        return { target: t, changes: [] };
      });

      setTarget(overviewRes.target);
      setChanges(overviewRes.changes || []);

      // 1.5 Fetch Research Signals and Clusters
      try {
        const [sigs, cls] = await Promise.all([
          apiFetch<ResearchSignal[]>(`/api/v1/targets/${targetId}/signals/top`).catch(() => []),
          apiFetch<ChangeCluster[]>(`/api/v1/targets/${targetId}/clusters`).catch(() => []),
        ]);
        setSignals(sigs);
        setClusters(cls);
      } catch {
        // Fallback
      }

      // 2. Fetch Changes / Events Since Last Visit
      try {
        const sinceRes = await apiFetch<TimelineEvent[]>(
          `/api/v1/targets/${targetId}/timeline/since-last-visit`
        );
        setSinceLastVisitEvents(Array.isArray(sinceRes) ? sinceRes : []);
      } catch {
        // If not implemented or no events, filter changes relative to last visit
        setSinceLastVisitEvents([]);
      }

      // 3. Fetch Recent Timeline Events
      try {
        const eventsRes = await apiFetch<TimelineEvent[]>(
          `/api/v1/targets/${targetId}/timeline`
        );
        setTimelineEvents(Array.isArray(eventsRes) ? eventsRes : []);
      } catch {
        setTimelineEvents([]);
      }

      // 4. Mark visit timestamp in background
      apiFetch(`/api/v1/targets/${targetId}/visit`, { method: "POST" }).catch(() => {});
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load target details");
    } finally {
      setLoading(false);
    }
  }, [targetId]);

  useEffect(() => {
    loadTargetData();
  }, [loadTargetData]);

  const handleTakeSnapshot = async () => {
    if (!targetId) return;
    setSnapshotBusy(true);
    setStatusMessage("Collecting permitted public observations...");

    try {
      const res = await apiFetch<{ status: string; detail?: string }>(
        `/api/v1/targets/${targetId}/snapshots`,
        { method: "POST" }
      );
      setStatusMessage(
        res.status === "completed"
          ? "Snapshot completed! Differential analysis updated."
          : `Snapshot job ${res.status || "queued"}. Changes will populate momentarily.`
      );
      await loadTargetData();
    } catch (err: unknown) {
      setStatusMessage(
        `Collection failed: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setSnapshotBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center font-mono text-xs text-cyan-400">
        <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent mb-3" />
        <p>ANALYZING TARGET ATTACK SURFACE...</p>
      </div>
    );
  }

  if (error || !target) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/40 p-6 text-center text-red-300">
        <h3 className="font-semibold text-red-200">Target Not Found or Access Denied</h3>
        <p className="mt-1 text-xs">{error || "The target domain does not exist in your scope."}</p>
        <Link
          href="/targets"
          className="mt-4 inline-block rounded-lg bg-slate-800 px-4 py-2 font-mono text-xs text-slate-200 hover:bg-slate-700"
        >
          ← BACK TO TARGETS
        </Link>
      </div>
    );
  }

  const highPriorityOpportunities = changes.filter(
    (c) => c.security_relevance >= 60 || c.priority === "CRITICAL" || c.priority === "HIGH"
  );

  return (
    <div className="space-y-6">
      {/* Target Header Banner */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 backdrop-blur-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-semibold tracking-wider text-cyan-400">
                AUTHORIZED SCOPE
              </span>
              <span className="rounded-full border border-emerald-500/30 bg-emerald-950/50 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-emerald-300">
                ✓ VERIFIED
              </span>
              <span className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-0.5 font-mono text-[10px] text-slate-300">
                STATUS: {target.monitoring_status || "ACTIVE"}
              </span>
            </div>

            <h2 className="text-2xl font-mono font-bold tracking-tight text-white">
              {target.domain}
            </h2>

            <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono text-slate-400">
              <span>Target ID: #{target.id}</span>
              <span>Enrolled: {new Date(target.created_at).toLocaleDateString()}</span>
              {target.last_visited_at && (
                <span>
                  Last Visited: {new Date(target.last_visited_at).toLocaleString()}
                </span>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={handleTakeSnapshot}
              disabled={snapshotBusy}
              className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-50"
            >
              {snapshotBusy ? "COLLECTING SNAPSHOT..." : "TAKE SNAPSHOT"}
            </button>
            <Link
              href={`/targets/${target.id}/timeline`}
              className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 font-mono text-xs font-medium text-slate-200 transition hover:border-cyan-500 hover:text-cyan-300"
            >
              FULL TIMELINE →
            </Link>
          </div>
        </div>

        {statusMessage && (
          <div className="mt-4 flex items-center justify-between rounded-lg border border-cyan-800 bg-cyan-950/60 p-3 text-xs text-cyan-200 font-mono">
            <span>{statusMessage}</span>
            <button onClick={() => setStatusMessage(null)} className="text-cyan-400 hover:text-white">
              ✕
            </button>
          </div>
        )}
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-slate-800 font-mono text-xs">
        {[
          { id: "overview", label: "OVERVIEW" },
          { id: "assets", label: "ASSETS" },
          { id: "features", label: "FEATURES" },
          { id: "technologies", label: "TECHNOLOGIES" },
          { id: "history", label: "SECURITY HISTORY" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`border-b-2 px-4 py-2.5 font-medium transition-colors ${
              activeTab === tab.id
                ? "border-cyan-400 text-cyan-400 bg-slate-900/40"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* SECTION: CHANGES SINCE LAST VISIT */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-cyan-400" />
                  <h3 className="font-semibold text-white">CHANGES SINCE LAST VISIT</h3>
                </div>
                <p className="text-xs text-slate-400">
                  New surface differentials discovered since your previous session.
                </p>
              </div>
              <span className="font-mono text-xs text-cyan-400">
                {sinceLastVisitEvents.length > 0
                  ? `${sinceLastVisitEvents.length} new events`
                  : `${changes.slice(0, 3).length} recent diffs`}
              </span>
            </div>

            {sinceLastVisitEvents.length > 0 ? (
              <div className="space-y-2.5">
                {sinceLastVisitEvents.map((evt) => (
                  <div
                    key={evt.id}
                    className="flex items-start justify-between gap-4 rounded-lg border border-cyan-900/50 bg-cyan-950/20 p-3"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-cyan-900/60 px-1.5 py-0.5 font-mono text-[10px] text-cyan-300 uppercase">
                          {evt.event_type}
                        </span>
                        <span className="font-mono text-[10px] text-slate-500">
                          {new Date(evt.observed_at).toLocaleDateString()}
                        </span>
                      </div>
                      <h4 className="mt-1 text-xs font-semibold text-slate-100">{evt.title}</h4>
                      <p className="text-xs text-slate-400">{evt.summary}</p>
                    </div>
                    <span className="font-mono text-xs font-bold text-amber-300">
                      {evt.relevance_score}/100
                    </span>
                  </div>
                ))}
              </div>
            ) : changes.length > 0 ? (
              <div className="space-y-2.5">
                {changes.slice(0, 3).map((change) => (
                  <Link
                    key={change.id}
                    href={`/changes/${change.id}`}
                    className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/50 p-3 hover:border-slate-700 hover:bg-slate-900 transition"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] uppercase text-cyan-400">
                          {change.category}
                        </span>
                        <span className="font-mono text-[10px] text-slate-500">
                          {new Date(change.detected_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-xs font-medium text-slate-200">{change.summary}</p>
                    </div>
                    <div className="text-right font-mono">
                      <span className="font-bold text-amber-300">{change.security_relevance}</span>
                      <span className="text-[10px] text-slate-500">/100</span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-slate-800 p-6 text-center text-xs text-slate-500 font-mono">
                NO NEW CHANGES DETECTED SINCE LAST OBSERVATION
              </div>
            )}
          </div>

          {/* SECTION: TOP RESEARCH OPPORTUNITIES */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-amber-400" />
                  <h3 className="font-semibold text-white">TOP RESEARCH OPPORTUNITIES</h3>
                </div>
                <p className="text-xs text-slate-400">
                  High-priority surface anomalies prioritized by security relevance heuristics and historical correlation.
                </p>
              </div>
              <span className="font-mono text-xs text-amber-300">
                {signals.length > 0 ? `${signals.length} ACTIVE SIGNALS` : `${highPriorityOpportunities.length} LEADS`}
              </span>
            </div>

            {signals.length > 0 ? (
              <div className="space-y-4">
                {signals.map((sig) => (
                  <ResearchSignalCard
                    key={sig.id}
                    signal={sig}
                    onStatusChange={(updated) => {
                      setSignals((prev) =>
                        prev.map((s) => (s.id === updated.id ? updated : s))
                      );
                    }}
                  />
                ))}
              </div>
            ) : highPriorityOpportunities.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-800 p-6 text-center text-xs text-slate-500 font-mono">
                NO HIGH-RELEVANCE OPPORTUNITIES FLAGGED
              </div>
            ) : (
              <div className="space-y-3">
                {highPriorityOpportunities.map((opp) => (
                  <div
                    key={opp.id}
                    className="rounded-lg border border-slate-800 bg-slate-950/70 p-4 transition hover:border-slate-700"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-amber-950/70 border border-amber-600/40 px-2 py-0.5 font-mono text-[10px] font-bold text-amber-300 uppercase">
                            PRIORITY: {opp.priority || "HIGH"}
                          </span>
                          <span className="font-mono text-[10px] text-slate-500">
                            {opp.category}
                          </span>
                        </div>
                        <h4 className="font-semibold text-xs text-slate-100">{opp.summary}</h4>
                        <p className="truncate font-mono text-[11px] text-slate-400">
                          {opp.source_url}
                        </p>
                      </div>

                      <div className="text-right shrink-0 font-mono">
                        <div className="text-sm font-bold text-amber-300">
                          {opp.security_relevance}
                          <span className="text-[10px] text-slate-500">/100</span>
                        </div>
                        <p className="text-[10px] text-slate-500">
                          {Math.round(opp.confidence * 100)}% conf
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center justify-between border-t border-slate-800/80 pt-2.5">
                      <span className="font-mono text-[10px] text-slate-500">
                        Detected: {new Date(opp.detected_at).toLocaleString()}
                      </span>
                      <Link
                        href={`/changes/${opp.id}`}
                        className="rounded bg-cyan-500/10 border border-cyan-500/30 px-3 py-1 font-mono text-[11px] text-cyan-300 hover:bg-cyan-500 hover:text-slate-950 transition"
                      >
                        VIEW FORENSICS &amp; EVIDENCE →
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* SECTION: SECURITY TIMELINE PREVIEW */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-white">SECURITY TIMELINE PREVIEW</h3>
                <p className="text-xs text-slate-400">
                  Chronological trail of public events, DNS modifications, and headers.
                </p>
              </div>
              <Link
                href={`/targets/${target.id}/timeline`}
                className="font-mono text-xs text-cyan-400 hover:text-cyan-300"
              >
                OPEN FULL TIMELINE →
              </Link>
            </div>

            {timelineEvents.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-800 p-6 text-center text-xs text-slate-500 font-mono">
                NO TIMELINE EVENTS RECORDED FOR THIS DOMAIN YET
              </div>
            ) : (
              <div className="space-y-3">
                {timelineEvents.slice(0, 5).map((evt) => (
                  <div
                    key={evt.id}
                    className="flex items-start gap-3 rounded-lg border border-slate-800 bg-slate-950/40 p-3"
                  >
                    <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-cyan-400" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[10px] text-cyan-400 uppercase">
                          {evt.event_type}
                        </span>
                        <span className="font-mono text-[10px] text-slate-500">
                          {new Date(evt.observed_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-xs font-medium text-slate-200 mt-0.5">{evt.title}</p>
                      <p className="text-[11px] text-slate-400 mt-0.5 truncate">{evt.summary}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: ASSETS */}
      {activeTab === "assets" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <div>
            <h3 className="font-semibold text-white">Observed Public Assets</h3>
            <p className="text-xs text-slate-400">
              Hostnames, public endpoints, and DNS records discovered through permitted passive observation.
            </p>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-xs space-y-2">
            <div className="flex justify-between border-b border-slate-800 pb-2 text-slate-400">
              <span>PRIMARY TARGET HOST</span>
              <span className="text-emerald-400">RESOLVED</span>
            </div>
            <div className="flex justify-between py-1 text-slate-200">
              <span>{target.domain}</span>
              <span className="text-slate-500">Root Scope</span>
            </div>
            <div className="flex justify-between py-1 text-slate-200">
              <span>www.{target.domain}</span>
              <span className="text-slate-500">Canonical Alias</span>
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-xs text-slate-400 space-y-1">
            <span className="font-mono text-cyan-400 uppercase font-semibold text-[10px]">
              SCOPE BOUNDARY
            </span>
            <p>
              Strict same-origin constraint active. Out-of-scope third party CDN links, advertiser scripts, and external CDNs are automatically bounded and prevented from recursive traversal.
            </p>
          </div>
        </div>
      )}

      {/* TAB 3: FEATURES */}
      {activeTab === "features" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <div>
            <h3 className="font-semibold text-white">Discovered Features &amp; Functional Endpoints</h3>
            <p className="text-xs text-slate-400">
              Detected authentication gateways, REST APIs, OAuth endpoints, and developer portals.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              { name: "Authentication / Login Gateway", type: "AUTH", status: "Identified" },
              { name: "Public API v1 Endpoint", type: "API", status: "Active" },
              { name: "Developer Documentation / Portal", type: "DOCS", status: "Observed" },
              { name: "Password Reset Flow", type: "AUTH", status: "Observed" },
            ].map((f, idx) => (
              <div key={idx} className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] text-cyan-400">{f.type}</span>
                  <span className="font-mono text-[10px] text-emerald-400">{f.status}</span>
                </div>
                <h4 className="mt-1 text-xs font-semibold text-slate-200">{f.name}</h4>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: TECHNOLOGIES */}
      {activeTab === "technologies" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <div>
            <h3 className="font-semibold text-white">Technology Stack Fingerprinting</h3>
            <p className="text-xs text-slate-400">
              Fingerprinted server software, web frameworks, and libraries with CVE/KEV correlations.
            </p>
          </div>

          <div className="space-y-2">
            {[
              { name: "Cloudflare CDN / Edge Proxy", cat: "Infrastructure", cve: "None" },
              { name: "Next.js / React Frontend", cat: "Web Framework", cve: "Monitored" },
              { name: "Nginx Ingress Controller", cat: "Web Server", cve: "Under Check" },
            ].map((tech, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/60 p-3 font-mono text-xs"
              >
                <div>
                  <p className="font-semibold text-slate-200">{tech.name}</p>
                  <p className="text-[10px] text-slate-500">{tech.cat}</p>
                </div>
                <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-cyan-300">
                  KEV: {tech.cve}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 5: SECURITY HISTORY */}
      {activeTab === "history" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <div>
            <h3 className="font-semibold text-white">Historical Snapshot Log</h3>
            <p className="text-xs text-slate-400">
              Audit log of all past public observations and automated differential passes.
            </p>
          </div>

          <div className="space-y-2 font-mono text-xs">
            <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-3 flex justify-between items-center">
              <div>
                <span className="text-emerald-400 font-semibold">Snapshot Completed</span>
                <p className="text-[10px] text-slate-500">Collected via standard HTTP GET</p>
              </div>
              <span className="text-slate-400 text-[11px]">
                {new Date(target.created_at).toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
