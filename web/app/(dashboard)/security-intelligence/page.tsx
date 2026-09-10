"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { SecurityIntelligenceEvent, SecurityIntelligenceStats } from "@/lib/types";
import ModernFilterDropdown from "@/components/ModernFilterDropdown";

export default function SecurityIntelligencePage() {
  const [events, setEvents] = useState<SecurityIntelligenceEvent[]>([]);
  const [stats, setStats] = useState<SecurityIntelligenceStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [collecting, setCollecting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("ALL");
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [onlyExploited, setOnlyExploited] = useState<boolean>(false);

  const fetchIntelligenceData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [eventsRes, statsRes] = await Promise.all([
        apiFetch<{ items: SecurityIntelligenceEvent[]; total: number }>("/api/v1/security-intelligence/?limit=50"),
        apiFetch<SecurityIntelligenceStats>("/api/v1/security-intelligence/stats"),
      ]);

      setEvents(eventsRes.items || []);
      setStats(statsRes);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load security intelligence.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntelligenceData();
  }, []);

  const handleCollectNow = async () => {
    try {
      setCollecting(true);
      setActionSuccess(null);
      setError(null);

      const res = await apiFetch<{ status: string; collected_count: number; events: SecurityIntelligenceEvent[] }>(
        "/api/v1/security-intelligence/collect-now",
        {
          method: "POST",
          body: JSON.stringify({ limit: 15 }),
        }
      );

      setActionSuccess(`Collected ${res.collected_count} new verified threat intelligence items.`);
      await fetchIntelligenceData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Collection failed.";
      setError(msg);
    } finally {
      setCollecting(false);
    }
  };

  const filteredEvents = useMemo(() => {
    return events.filter((item) => {
      if (selectedSeverity !== "ALL" && item.severity.toUpperCase() !== selectedSeverity) {
        return false;
      }
      if (selectedType !== "ALL" && item.event_type.toUpperCase() !== selectedType) {
        return false;
      }
      if (onlyExploited && !item.actively_exploited) {
        return false;
      }
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const inTitle = item.title.toLowerCase().includes(query);
        const inSummary = item.summary.toLowerCase().includes(query);
        const inCve = item.cve_ids?.some((c) => c.toLowerCase().includes(query));
        const inProduct = item.affected_products?.some((p) => p.toLowerCase().includes(query));
        const inCompany = item.affected_companies?.some((c) => c.toLowerCase().includes(query));
        if (!inTitle && !inSummary && !inCve && !inProduct && !inCompany) {
          return false;
        }
      }
      return true;
    });
  }, [events, selectedSeverity, selectedType, onlyExploited, searchTerm]);

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">Security News & Vulnerability Intelligence</h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Real-time vulnerability intelligence and authoritative security advisories.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleCollectNow}
            disabled={collecting}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all shadow-md ${
              collecting
                ? "bg-slate-800 text-slate-400 cursor-not-allowed border border-slate-700"
                : "bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-950/50 hover:shadow-cyan-900/50 border border-cyan-400/30"
            }`}
          >
            {collecting ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-slate-300" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Collecting Advisories...
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Collect Now
              </>
            )}
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-lg bg-red-950/50 border border-red-800/80 text-red-200 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 ml-4 font-bold">×</button>
        </div>
      )}

      {actionSuccess && (
        <div className="p-4 rounded-lg bg-emerald-950/50 border border-emerald-800/80 text-emerald-200 text-sm flex items-center justify-between">
          <span>{actionSuccess}</span>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-400 hover:text-emerald-300 ml-4 font-bold">×</button>
        </div>
      )}

      {/* Stats Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-xs uppercase font-medium tracking-wider text-slate-400">Total Intel Events</div>
          <div className="text-2xl font-bold text-slate-100 mt-1">{stats ? stats.total_events : "—"}</div>
          <div className="text-xs text-slate-500 mt-1">Grounding verified entries</div>
        </div>

        <div className="bg-slate-900/80 border border-red-900/30 rounded-xl p-4 shadow-sm">
          <div className="text-xs uppercase font-medium tracking-wider text-red-400">Actively Exploited (In-The-Wild)</div>
          <div className="text-2xl font-bold text-red-400 mt-1">{stats ? stats.actively_exploited_count : "—"}</div>
          <div className="text-xs text-red-400/70 mt-1">Confirmed exploitation evidence</div>
        </div>

        <div className="bg-slate-900/80 border border-amber-900/30 rounded-xl p-4 shadow-sm">
          <div className="text-xs uppercase font-medium tracking-wider text-amber-400">Critical / High Severity</div>
          <div className="text-2xl font-bold text-amber-300 mt-1">
            {stats ? (stats.by_severity["CRITICAL"] || 0) + (stats.by_severity["HIGH"] || 0) : "—"}
          </div>
          <div className="text-xs text-amber-400/70 mt-1">Priority researcher focus</div>
        </div>

        <div className="bg-slate-900/80 border border-cyan-900/30 rounded-xl p-4 shadow-sm">
          <div className="text-xs uppercase font-medium tracking-wider text-cyan-400">Cadence & Engine</div>
          <div className="text-2xl font-bold text-cyan-300 mt-1">10 Min</div>
          <div className="text-xs text-cyan-400/70 mt-1">Automated continuous polling</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
        <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
          <div className="relative flex-1 w-full">
            <svg className="w-4 h-4 absolute left-3.5 top-3 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search intelligence by title, CVE-ID, vendor, or product..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-red-800/80 transition-colors text-slate-300 select-none">
              <input
                type="checkbox"
                checked={onlyExploited}
                onChange={(e) => setOnlyExploited(e.target.checked)}
                className="rounded border-slate-700 text-red-500 focus:ring-0 bg-slate-900 cursor-pointer"
              />
              <span className={onlyExploited ? "text-red-400 font-bold" : ""}>Actively Exploited Only</span>
            </label>
          </div>
        </div>

        {/* Modern Filter Dropdowns */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2.5 border-t border-slate-800/60 text-xs">
          <div className="flex flex-wrap items-center gap-2.5">
            <ModernFilterDropdown
              label="Severity"
              value={selectedSeverity}
              onChange={setSelectedSeverity}
              options={[
                { value: "ALL", label: "All Severities" },
                { value: "CRITICAL", label: "Critical Severity", color: "rose" },
                { value: "HIGH", label: "High Severity", color: "amber" },
                { value: "MEDIUM", label: "Medium Severity", color: "cyan" },
                { value: "LOW", label: "Low Severity", color: "emerald" },
              ]}
            />

            <ModernFilterDropdown
              label="Intel Type"
              value={selectedType}
              onChange={setSelectedType}
              options={[
                { value: "ALL", label: "All Intelligence Types" },
                { value: "CVE", label: "CVE Records", color: "rose" },
                { value: "SECURITY_ADVISORY", label: "Security Advisories", color: "cyan" },
                { value: "EXPLOIT", label: "Exploits & PoCs", color: "amber" },
                { value: "BUG_BOUNTY", label: "Bug Bounty Scope", color: "emerald" },
                { value: "SECURITY_NEWS", label: "Threat News", color: "purple" },
              ]}
            />
          </div>

          <div className="text-[11px] font-mono text-slate-400">
            <span>Showing <strong className="text-white font-semibold">{filteredEvents.length}</strong> intelligence feeds</span>
          </div>
        </div>
      </div>

      {/* Intelligence Feed */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
          <svg className="animate-spin h-6 w-6 text-cyan-500 mx-auto mb-3" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Loading continuous security intelligence...
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="p-12 text-center text-slate-400 bg-slate-900/40 rounded-xl border border-slate-800 space-y-3">
          <div className="text-lg font-semibold text-slate-300">No Intelligence Events Found</div>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            {events.length === 0
              ? "No security intelligence items found. Click 'Collect Now' above to synchronize the latest threat advisories and vulnerability feeds."
              : "No events match the current filter criteria. Try adjusting your search query or severity filter."}
          </p>
          {events.length === 0 && (
            <button
              onClick={handleCollectNow}
              disabled={collecting}
              className="mt-3 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg uppercase tracking-wider"
            >
              Fetch Advisories
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredEvents.map((item) => {
            const isCrit = item.severity === "CRITICAL";
            const isHigh = item.severity === "HIGH";

            return (
              <div
                key={item.id}
                className={`bg-slate-900/90 rounded-xl border transition-all p-5 shadow-sm hover:shadow-md ${
                  item.actively_exploited
                    ? "border-red-800/80 bg-gradient-to-r from-red-950/20 to-slate-900/90"
                    : isCrit
                    ? "border-red-900/40"
                    : isHigh
                    ? "border-amber-900/40"
                    : "border-slate-800"
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                  <div className="space-y-2 flex-1">
                    {/* Badge Row */}
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        Threat Advisory
                      </span>

                      <span
                        className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${
                          isCrit
                            ? "bg-red-950/90 text-red-300 border-red-800"
                            : isHigh
                            ? "bg-orange-950/90 text-orange-300 border-orange-800"
                            : "bg-slate-800 text-slate-300 border-slate-700"
                        }`}
                      >
                        {item.severity}
                      </span>

                      {item.actively_exploited && (
                        <span className="inline-flex items-center text-[10px] uppercase font-black tracking-wider px-2 py-0.5 rounded bg-red-900 text-white border border-red-600 shadow-sm animate-pulse">
                          ⚠️ Actively Exploited
                        </span>
                      )}

                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        {item.event_type}
                      </span>

                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 text-amber-300 border border-amber-900/40">
                        Priority {item.priority_score}/100
                      </span>
                    </div>

                    {/* Title */}
                    <h3 className="text-base font-semibold text-slate-100 hover:text-cyan-400 transition-colors">
                      <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5">
                        {item.title}
                        <svg className="w-3.5 h-3.5 text-slate-500 inline flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </a>
                    </h3>

                    {/* Summary */}
                    <p className="text-sm text-slate-300 leading-relaxed">{item.summary}</p>

                    {/* Active exploitation evidence */}
                    {item.known_exploitation_evidence && (
                      <div className="p-2.5 rounded-lg bg-red-950/40 border border-red-900/60 text-xs text-red-200">
                        <span className="font-bold text-red-300">Exploitation Evidence: </span>
                        {item.known_exploitation_evidence}
                      </div>
                    )}

                    {/* Tags & Entities */}
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      {item.cve_ids?.map((cve) => (
                        <span key={cve} className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-950 text-cyan-300 border border-cyan-800/40">
                          {cve}
                        </span>
                      ))}

                      {item.affected_products?.map((prod) => (
                        <span key={prod} className="text-xs px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800">
                          Product: {prod}
                        </span>
                      ))}

                      {item.affected_companies?.map((comp) => (
                        <span key={comp} className="text-xs px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                          Vendor: {comp}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Right side metadata */}
                  <div className="text-xs text-slate-500 space-y-1 md:text-right flex-shrink-0">
                    <div>
                      Source: <span className="text-slate-300 font-medium">{item.source_name}</span>
                    </div>
                    <div>
                      Published: {item.published_at ? new Date(item.published_at).toLocaleDateString() : "Unknown"}
                    </div>
                    {item.confidence && (
                      <div>Confidence: <span className="text-cyan-400">{(item.confidence * 100).toFixed(0)}%</span></div>
                    )}
                  </div>
                </div>

                {/* Grounding Provenance Footer */}
                {item.grounding_metadata && (
                  <div className="mt-3 pt-3 border-t border-slate-800/60 text-[11px] text-slate-500 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400 font-semibold">Web Citations:</span>
                      <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline truncate max-w-xs">
                        {item.source_url}
                      </a>
                    </div>
                    <div className="font-mono text-[10px] text-slate-600">
                      Fingerprint: {item.fingerprint.slice(0, 12)}...
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
