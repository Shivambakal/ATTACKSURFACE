"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { SecurityProgram } from "@/lib/types";
import AnimatedList, { AnimatedItem } from "@/components/AnimatedList";

interface ProgramStats {
  total_programs: number;
  bounty_programs: number;
  vdp_programs: number;
  platform_breakdown: Record<string, number>;
  total_scope_rules: number;
  total_snapshots: number;
  total_change_events: number;
  canonical_companies_with_programs: number;
}

export default function ProgramsPage() {
  const [programs, setPrograms] = useState<SecurityProgram[]>([]);
  const [stats, setStats] = useState<ProgramStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPlatform, setSelectedPlatform] = useState<string>("ALL");
  const [bountyFilter, setBountyFilter] = useState<"ALL" | "BOUNTY" | "VDP">("ALL");
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [viewMode, setViewMode] = useState<"stream" | "grid">("stream");
  const pageSize = 30;

  const [selectedProgram, setSelectedProgram] = useState<SecurityProgram | null>(null);
  const [programDetailLoading, setProgramDetailLoading] = useState(false);
  const [programDetailData, setProgramDetailData] = useState<any | null>(null);
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await apiFetch("/api/v1/programs/sync", { method: "POST" });
      setTimeout(async () => {
        await fetchStats();
        await fetchPrograms();
        setSyncing(false);
      }, 3000);
    } catch (err) {
      console.error("Failed to sync programs:", err);
      setSyncing(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await apiFetch<ProgramStats>("/api/v1/programs/stats");
      setStats(data);
    } catch (err) {
      console.error("Failed to load program stats:", err);
    }
  };

  const fetchPrograms = async () => {
    setLoading(true);
    try {
      let url = `/api/v1/programs?limit=${pageSize}&offset=${(currentPage - 1) * pageSize}`;
      if (searchQuery.trim()) {
        url += `&q=${encodeURIComponent(searchQuery.trim())}`;
      }
      if (selectedPlatform !== "ALL") {
        url += `&platform=${encodeURIComponent(selectedPlatform)}`;
      }
      if (bountyFilter === "BOUNTY") {
        url += `&bounty_only=true`;
      } else if (bountyFilter === "VDP") {
        url += `&bounty_only=false`;
      }

      const res = await apiFetch<{ total: number; items: SecurityProgram[] }>(url);
      setPrograms(res.items || []);
      setTotalCount(res.total || 0);
    } catch (err) {
      console.error("Failed to load programs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchPrograms();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery, selectedPlatform, bountyFilter, currentPage]);

  const loadProgramDetail = async (prog: SecurityProgram) => {
    setSelectedProgram(prog);
    setProgramDetailLoading(true);
    try {
      const detail = await apiFetch<any>(`/api/v1/programs/${prog.id}`);
      setProgramDetailData(detail);
    } catch (err) {
      console.error("Failed to fetch program detail:", err);
    } finally {
      setProgramDetailLoading(false);
    }
  };

  const platforms = [
    "ALL",
    "HackerOne",
    "Bugcrowd",
    "Intigriti",
    "YesWeHack",
    "Federacy",
    "ProjectDiscovery",
  ];

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-display">
              PUBLIC SECURITY PROGRAMS DIRECTORY
            </h1>
            <span className="rounded-full bg-emerald-950/80 px-3 py-1 font-mono text-xs font-bold text-emerald-400 border border-emerald-800/60 shadow-sm">
              {stats ? stats.total_programs.toLocaleString() : totalCount.toLocaleString()} VERIFIED PROGRAMS
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400 font-sans">
            Authoritative public bug bounty &amp; vulnerability disclosure programs ingested continuously from HackerOne, Bugcrowd, Intigriti, YesWeHack, Federacy, and ProjectDiscovery.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 rounded-xl border border-emerald-800/60 bg-emerald-950/40 px-3.5 py-2.5 text-xs font-bold text-emerald-400 hover:bg-emerald-900/50 hover:border-emerald-700 transition-colors font-display disabled:opacity-50"
          >
            <svg
              className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            {syncing ? "SYNCING REGISTRY..." : "SYNC REGISTRY"}
          </button>
          <Link
            href="/companies"
            className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2.5 text-xs font-bold text-slate-300 hover:bg-slate-800 transition-colors font-display"
          >
            &larr; COMPANY DIRECTORY ({stats ? stats.canonical_companies_with_programs.toLocaleString() : "..."})
          </Link>
        </div>
      </div>

      {/* Stats Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3 font-sans">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 backdrop-blur-md">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-display">
            Total Programs
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-white font-display">
              {stats ? stats.total_programs.toLocaleString() : totalCount.toLocaleString()}
            </span>
            <span className="text-[10px] text-emerald-400 font-mono">Public</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Live verified registries</p>
        </div>

        <div className="rounded-2xl border border-emerald-800/40 bg-emerald-950/20 p-4 backdrop-blur-md">
          <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-300 font-display">
            Bounty Programs
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-emerald-400 font-display">
              {stats ? stats.bounty_programs.toLocaleString() : "..."}
            </span>
            <span className="text-[10px] text-emerald-300 font-mono">Rewarded</span>
          </div>
          <p className="mt-1 text-[11px] text-emerald-300/70">Offers cash rewards</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 backdrop-blur-md">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-display">
            VDP / Disclosure
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-cyan-400 font-display">
              {stats ? stats.vdp_programs.toLocaleString() : "..."}
            </span>
            <span className="text-[10px] text-slate-400 font-mono">Safe Harbor</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Responsible disclosure</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 backdrop-blur-md">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-display">
            Scope Rules Ingested
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-white font-display">
              {stats ? stats.total_scope_rules.toLocaleString() : "..."}
            </span>
            <span className="text-[10px] text-cyan-400 font-mono">Rules</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Verified target boundaries</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 backdrop-blur-md col-span-2 sm:col-span-1">
          <div className="text-[11px] font-bold uppercase tracking-wider text-amber-400 font-display">
            Canonical Organizations
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-amber-300 font-display">
              {stats ? stats.canonical_companies_with_programs.toLocaleString() : "..."}
            </span>
            <span className="text-[10px] text-amber-400 font-mono">Orgs</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Deduplicated entities</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 font-sans">
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center">
          <div className="relative flex-1">
            <svg className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search program name, handle, company name, or domain (e.g. google.com)..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full rounded-xl border border-slate-800 bg-slate-950 pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-sans"
            />
          </div>

            {/* Bounty Filter Toggle */}
            <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-950 p-1 flex-shrink-0">
              <button
                onClick={() => { setBountyFilter("ALL"); setCurrentPage(1); }}
                className={`rounded-lg px-3 py-1.5 text-xs font-bold transition ${
                  bountyFilter === "ALL" ? "bg-cyan-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                All Types
              </button>
              <button
                onClick={() => { setBountyFilter("BOUNTY"); setCurrentPage(1); }}
                className={`rounded-lg px-3 py-1.5 text-xs font-bold transition ${
                  bountyFilter === "BOUNTY" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Bounties Only
              </button>
              <button
                onClick={() => { setBountyFilter("VDP"); setCurrentPage(1); }}
                className={`rounded-lg px-3 py-1.5 text-xs font-bold transition ${
                  bountyFilter === "VDP" ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                VDP Only
              </button>
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-950 p-1 flex-shrink-0">
              <button
                type="button"
                onClick={() => setViewMode("stream")}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  viewMode === "stream"
                    ? "bg-cyan-500 text-slate-950 font-bold shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
                title="Animated Stream List with Gradients & Keyboard Navigation"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
                Stream List
              </button>
              <button
                type="button"
                onClick={() => setViewMode("grid")}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  viewMode === "grid"
                    ? "bg-cyan-500 text-slate-950 font-bold shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
                title="Animated Grid"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
                Grid
              </button>
            </div>
          </div>

          {/* Platform Chips */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 border-t border-slate-800/80 pt-3">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500 mr-1 flex-shrink-0">Platform:</span>
            {platforms.map((plat) => {
              const count = stats?.platform_breakdown?.[plat];
              return (
                <button
                  key={plat}
                  onClick={() => {
                    setSelectedPlatform(plat);
                    setCurrentPage(1);
                  }}
                  className={`rounded-xl px-3 py-1.5 font-display text-xs font-semibold whitespace-nowrap transition-all ${
                    selectedPlatform === plat
                      ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20 font-bold"
                      : "bg-slate-950 text-slate-400 border border-slate-800 hover:text-white hover:bg-slate-800/60"
                  }`}
                >
                  {plat} {count !== undefined && <span className="opacity-70 font-mono">({count.toLocaleString()})</span>}
                </button>
              );
            })}
          </div>
        </div>

        {/* Programs List */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-44 rounded-2xl border border-slate-800/80 bg-slate-900/40 animate-pulse" />
            ))}
          </div>
        ) : programs.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-800 p-12 text-center font-sans">
            <p className="text-slate-400 font-mono text-sm">NO PUBLIC PROGRAMS MATCH YOUR QUERY</p>
            <p className="mt-1 text-xs text-slate-500">Try adjusting your search query or platform filters.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {viewMode === "stream" ? (
              <div className="rounded-2xl border border-slate-800/80 bg-slate-900/30 p-2 sm:p-3 backdrop-blur-md">
                <div className="flex items-center justify-between px-3 py-2 text-xs font-mono text-slate-400 border-b border-slate-800/60 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="font-bold text-slate-200">INTERACTIVE STREAM</span>
                    <span>&bull; {programs.length} Programs</span>
                  </div>
                  <div className="hidden sm:flex items-center gap-2 text-[11px] text-slate-400">
                    <span>Use <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200 font-bold">↑</kbd> <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200 font-bold">↓</kbd> or <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200 font-bold">Enter</kbd> to inspect</span>
                  </div>
                </div>

                <AnimatedList
                  items={programs}
                  maxHeight="700px"
                  onItemSelect={(prog) => loadProgramDetail(prog)}
                  renderItem={(prog, index, isSelected) => (
                    <div
                      className={`p-4 sm:p-5 rounded-2xl border transition-all duration-200 backdrop-blur-md flex flex-col md:flex-row md:items-center md:justify-between gap-4 ${
                        isSelected
                          ? "bg-cyan-950/40 border-cyan-500/70 shadow-lg shadow-cyan-500/15 ring-1 ring-cyan-500/50"
                          : "bg-slate-900/80 border-slate-800/80 hover:border-cyan-500/40 hover:bg-slate-900"
                      }`}
                    >
                      {/* Program Info */}
                      <div className="flex items-start sm:items-center gap-3.5 min-w-0">
                        <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-xl bg-gradient-to-br from-emerald-950/60 to-slate-900 border border-emerald-800/40 flex items-center justify-center font-display font-extrabold text-emerald-300 text-xs sm:text-sm flex-shrink-0 shadow-inner">
                          {prog.platform.slice(0, 3).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-base font-bold text-white group-hover:text-cyan-400 transition font-display truncate">
                              {prog.program_name || prog.company_name}
                            </span>
                            <span className="rounded-md bg-slate-800/80 border border-slate-700/60 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-200">
                              {prog.platform}
                            </span>
                            {prog.offers_bounties ? (
                              <span className="rounded bg-emerald-950/80 border border-emerald-800/60 px-2 py-0.5 font-mono text-[10px] font-semibold text-emerald-400">
                                BOUNTY
                              </span>
                            ) : (
                              <span className="rounded bg-slate-800/80 px-2 py-0.5 font-mono text-[10px] text-slate-400">
                                VDP
                              </span>
                            )}
                          </div>
                          <div className="mt-1 flex items-center gap-2.5 text-xs text-slate-400 font-mono">
                            {prog.company_domain && <span className="text-cyan-300">{prog.company_domain}</span>}
                            <span>&bull; Scope: {prog.scope_rules_count ? `${prog.scope_rules_count} rules` : prog.scope_summary || "Public Targets"}</span>
                          </div>
                        </div>
                      </div>

                      {/* Reward & Actions */}
                      <div className="flex items-center justify-between md:justify-end gap-3 sm:gap-5 pt-2 md:pt-0 border-t md:border-t-0 border-slate-800/60">
                        {prog.max_bounty ? (
                          <div className="px-3 py-1.5 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-right">
                            <div className="text-[9px] uppercase tracking-wider text-emerald-400/80 font-mono font-bold">Max Reward</div>
                            <div className="font-mono text-xs sm:text-sm font-black text-emerald-300">
                              {prog.currency} {prog.max_bounty.toLocaleString()}
                            </div>
                          </div>
                        ) : (
                          <div className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800/60 text-right">
                            <div className="text-[9px] uppercase tracking-wider text-slate-500 font-mono">Reward</div>
                            <div className="font-mono text-xs text-slate-400">Safe Harbor</div>
                          </div>
                        )}

                        <div className="flex items-center gap-2 flex-shrink-0">
                          {prog.program_url && (
                            <a
                              href={prog.program_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="rounded-xl border border-cyan-800/60 bg-cyan-950/40 px-3 py-2 text-xs font-mono font-medium text-cyan-300 hover:bg-cyan-900/60 transition flex items-center gap-1"
                              title="Open Policy"
                            >
                              <span>POLICY</span>
                              <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                            </a>
                          )}
                          <button
                            onClick={() => loadProgramDetail(prog)}
                            className="rounded-xl bg-slate-800 hover:bg-cyan-600 hover:text-slate-950 px-3.5 py-2 text-xs font-display font-bold text-slate-200 transition shadow-sm"
                          >
                            INSPECT SCOPE &rarr;
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                />
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {programs.map((prog, idx) => (
                  <AnimatedItem key={prog.id} index={idx} delay={(idx % 6) * 0.04} style={{ marginBottom: 0 }}>
                    <div className="h-full flex flex-col justify-between rounded-2xl border border-slate-800/90 bg-slate-900/60 p-5 hover:border-cyan-500/50 transition-all shadow-md group card-3d-interactive">
                      <div>
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <div className="text-base font-bold text-white group-hover:text-cyan-400 transition-colors font-display truncate">
                              {prog.program_name || prog.company_name}
                            </div>
                            <div className="mt-0.5 flex items-center gap-2 flex-wrap">
                              {prog.company_id && (
                                <Link
                                  href={`/companies/${prog.company_id}`}
                                  className="font-mono text-xs text-cyan-300 hover:underline truncate"
                                >
                                  {prog.company_name || prog.company_domain}
                                </Link>
                              )}
                              {prog.company_domain && (
                                <span className="font-mono text-[10px] text-slate-500 truncate">
                                  ({prog.company_domain})
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex flex-col items-end gap-1 flex-shrink-0">
                            <span className="rounded-md bg-slate-800/80 border border-slate-700/60 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-200">
                              {prog.platform}
                            </span>
                            {prog.offers_bounties ? (
                              <span className="rounded bg-emerald-950/80 border border-emerald-800/60 px-2 py-0.5 font-mono text-[10px] font-semibold text-emerald-400">
                                BOUNTY
                              </span>
                            ) : (
                              <span className="rounded bg-slate-800/80 px-2 py-0.5 font-mono text-[10px] text-slate-400">
                                VDP
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Bounty / Scope Summary */}
                        <div className="mt-3.5 space-y-1.5 text-xs font-mono text-slate-300">
                          <div className="flex items-center justify-between text-[11px] text-slate-400">
                            <span>Scope:</span>
                            <span className="text-slate-200 font-bold">
                              {prog.scope_rules_count ? `${prog.scope_rules_count} items` : prog.scope_summary || "Public Targets"}
                            </span>
                          </div>

                          {prog.max_bounty ? (
                            <div className="flex items-center justify-between text-[11px]">
                              <span className="text-slate-400">Max Reward:</span>
                              <span className="text-emerald-400 font-bold">
                                {prog.currency} {prog.max_bounty.toLocaleString()}
                              </span>
                            </div>
                          ) : null}

                          <div className="flex items-center justify-between text-[11px] text-slate-400">
                            <span>Status:</span>
                            <span className="text-cyan-400 uppercase">{prog.submission_state || "OPEN"}</span>
                          </div>
                        </div>
                      </div>

                      {/* Card Actions */}
                      <div className="mt-4 flex items-center justify-between gap-2 border-t border-slate-800/80 pt-3">
                        <button
                          onClick={() => loadProgramDetail(prog)}
                          className="flex-1 rounded-xl bg-slate-800/80 py-2 text-center text-xs font-display font-bold text-slate-200 hover:bg-slate-700 transition-colors"
                        >
                          INSPECT SCOPE
                        </button>

                        {prog.program_url && (
                          <a
                            href={prog.program_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-center gap-1 rounded-xl border border-cyan-800/60 bg-cyan-950/40 px-3 py-2 text-xs font-mono font-medium text-cyan-300 hover:bg-cyan-900/60 transition-colors"
                            title="Open Official Policy"
                          >
                            <span>POLICY</span>
                            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </a>
                        )}

                        {prog.company_id && (
                          <Link
                            href={`/companies/${prog.company_id}`}
                            className="flex items-center justify-center rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs font-mono text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                            title="Company Command Center"
                          >
                            ORG &rarr;
                          </Link>
                        )}
                      </div>
                    </div>
                  </AnimatedItem>
                ))}
              </div>
            )}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-800 pt-5 text-xs font-mono text-slate-400">
              <div>
                Showing <strong className="text-white font-mono">{(currentPage - 1) * pageSize + 1}</strong> to{" "}
                <strong className="text-white font-mono">{Math.min(currentPage * pageSize, totalCount)}</strong> of{" "}
                <strong className="text-white font-mono">{totalCount.toLocaleString()}</strong> programs
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 font-bold text-slate-300 hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition"
                >
                  &larr; PREV
                </button>

                <span className="px-3 py-1.5 rounded-lg border border-cyan-800/80 bg-cyan-950/40 text-cyan-300 font-bold">
                  Page {currentPage} of {totalPages}
                </span>

                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 font-bold text-slate-300 hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition"
                >
                  NEXT &rarr;
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Program Detail Modal / Scope Inspector */}
      {selectedProgram && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
          <div className="relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden font-sans">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-800 p-5 bg-slate-950/40">
              <div>
                <div className="flex items-center gap-2.5">
                  <h2 className="text-lg font-bold text-white font-display">
                    {selectedProgram.program_name || selectedProgram.company_name}
                  </h2>
                  <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-300">
                    {selectedProgram.platform}
                  </span>
                  {selectedProgram.offers_bounties ? (
                    <span className="rounded bg-emerald-950 px-2 py-0.5 font-mono text-[10px] font-semibold text-emerald-400 border border-emerald-800/60">
                      BOUNTY
                    </span>
                  ) : (
                    <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-slate-400">
                      VDP
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-slate-400 font-mono">
                  Organization: {selectedProgram.company_name} ({selectedProgram.company_domain})
                </p>
              </div>

              <button
                onClick={() => {
                  setSelectedProgram(null);
                  setProgramDetailData(null);
                }}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {programDetailLoading ? (
                <div className="space-y-3 py-8 text-center text-xs font-mono text-slate-400">
                  <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent mb-2" />
                  <div>Loading program scope rules and snapshot history...</div>
                </div>
              ) : programDetailData ? (
                <>
                  {/* Overview Stats */}
                  <div className="grid grid-cols-3 gap-2.5 text-center font-mono text-xs">
                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                      <div className="text-[10px] uppercase text-slate-500">In-Scope Rules</div>
                      <div className="mt-1 text-base font-bold text-white">
                        {programDetailData.scope_rules?.length || 0}
                      </div>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                      <div className="text-[10px] uppercase text-slate-500">Snapshots Taken</div>
                      <div className="mt-1 text-base font-bold text-cyan-400">
                        {programDetailData.snapshots?.length || 0}
                      </div>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                      <div className="text-[10px] uppercase text-slate-500">Recorded Diffs</div>
                      <div className="mt-1 text-base font-bold text-amber-400">
                        {programDetailData.change_events?.length || 0}
                      </div>
                    </div>
                  </div>

                  {/* Scope Rules List */}
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-display mb-2">
                      Target Scope Rules ({programDetailData.scope_rules?.length || 0})
                    </h3>
                    <div className="max-h-60 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 divide-y divide-slate-800/60 font-mono text-xs">
                      {programDetailData.scope_rules && programDetailData.scope_rules.length > 0 ? (
                        programDetailData.scope_rules.map((rule: any) => (
                          <div key={rule.id} className="flex items-center justify-between p-2.5 hover:bg-slate-900/60">
                            <span className="text-slate-200 font-medium truncate pr-2">{rule.pattern}</span>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                                {rule.asset_type || "URL"}
                              </span>
                              <span className="rounded bg-emerald-950/80 px-1.5 py-0.5 text-[10px] font-bold text-emerald-400">
                                {rule.inclusion_type}
                              </span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="p-4 text-center text-slate-500 text-xs">No explicit scope rules recorded.</div>
                      )}
                    </div>
                  </div>

                  {/* Scope Change Events if any */}
                  {programDetailData.change_events && programDetailData.change_events.length > 0 && (
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-amber-400 font-display mb-2">
                        Scope Change Events
                      </h3>
                      <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 space-y-2 text-xs font-mono">
                        {programDetailData.change_events.map((ce: any) => (
                          <div key={ce.id} className="border-b border-slate-800/60 pb-2 last:border-b-0 last:pb-0">
                            <span className="text-cyan-400 font-bold">{ce.change_type}:</span> {ce.summary}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : null}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between border-t border-slate-800 p-4 bg-slate-950/40">
              {selectedProgram.company_id ? (
                <Link
                  href={`/companies/${selectedProgram.company_id}`}
                  className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-bold text-slate-200 hover:bg-slate-800 transition font-display"
                >
                  Open Company Command Center &rarr;
                </Link>
              ) : <div />}

              <button
                onClick={() => {
                  setSelectedProgram(null);
                  setProgramDetailData(null);
                }}
                className="rounded-xl bg-cyan-600 px-5 py-2 text-xs font-bold text-white hover:bg-cyan-500 transition font-display"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
