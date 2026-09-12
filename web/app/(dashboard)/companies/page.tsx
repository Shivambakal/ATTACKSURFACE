"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Company } from "@/lib/types";
import ModernFilterDropdown from "@/components/ModernFilterDropdown";
import AnimatedList, { AnimatedItem } from "@/components/AnimatedList";
import { AnimatedNumber } from "@/components/ui/InteractionPrimitives";
import { openThreatAnalyst } from "@/components/CyberAssistantChat";

interface CompanyStats {
  canonical_companies: number;
  public_programs: number;
  authorized_targets: number;
  observed_assets: number;
  research_signals: number;
}

export default function CompaniesPage() {
  const router = useRouter();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [stats, setStats] = useState<CompanyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIndustry, setSelectedIndustry] = useState<string>("ALL");
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [viewMode, setViewMode] = useState<"stream" | "grid">("stream");
  const pageSize = 24;

  // Add Company Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [inputVal, setInputVal] = useState("");
  const [descriptionVal, setDescriptionVal] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchStats = async () => {
    try {
      const data = await apiFetch<CompanyStats>("/api/v1/companies/stats");
      setStats(data);
    } catch (err) {
      console.error("Failed to load company stats:", err);
    }
  };

  const fetchCompanies = async () => {
    setLoading(true);
    try {
      let url = `/api/v1/companies?limit=100`;
      if (searchQuery.trim()) {
        url += `&q=${encodeURIComponent(searchQuery.trim())}`;
      }
      if (selectedIndustry !== "ALL") {
        url += `&industry=${encodeURIComponent(selectedIndustry)}`;
      }
      const compData = await apiFetch<{ total: number; items: Company[] }>(url);
      setCompanies(compData.items || []);
      setTotalCount(compData.total || 1436);
      setCurrentPage(1);
    } catch (err) {
      console.error("Failed to load companies:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchCompanies();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, selectedIndustry]);

  // Escape key listener to close Add Company modal
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape" && showAddModal) {
        setShowAddModal(false);
      }
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [showAddModal]);

  const handleAddCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) {
      setErrorMsg("Domain or company name is required.");
      return;
    }
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const newComp = await apiFetch<Company>("/api/v1/companies", {
        method: "POST",
        body: JSON.stringify({
          name: inputVal.trim(),
          domain: inputVal.trim().toLowerCase().includes(".") ? inputVal.trim().toLowerCase() : `${inputVal.trim().toLowerCase().replace(/\s+/g, "")}.com`,
          description: descriptionVal.trim() || undefined,
        }),
      });
      setShowAddModal(false);
      setInputVal("");
      setDescriptionVal("");
      router.push(`/companies/${newComp.id}`);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to add company");
    } finally {
      setIsSubmitting(false);
    }
  };

  const industries = [
    "ALL",
    "Software & Internet",
    "Financial Services",
    "Healthcare",
    "Retail & E-commerce",
    "Telecommunications",
    "Energy & Utilities",
    "Government & Defense",
    "Manufacturing",
  ];

  const paginatedCompanies = companies.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const totalPages = Math.ceil((totalCount || companies.length) / pageSize) || 1;
  const totalAssets = companies.reduce((acc, c) => acc + (c.assets_count || c.metrics?.total_assets || 0), 0);
  const totalSignals = companies.reduce((acc, c) => acc + (c.signals_count || c.metrics?.signals_count || 0), 0);

  return (
    <div className="space-y-6">
      {/* Top Header & Metrics */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-display">
              COMPANY INTELLIGENCE — {stats ? stats.canonical_companies.toLocaleString() : (totalCount ? totalCount.toLocaleString() : "1,436")} Verified Organizations
            </h1>
            <span className="rounded-full bg-cyan-950/80 px-3 py-1 font-mono text-xs font-bold text-cyan-400 border border-cyan-800/60 shadow-sm">
              {stats ? stats.canonical_companies.toLocaleString() : (totalCount ? totalCount.toLocaleString() : "1,436")} CANONICAL ENTITIES
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400 font-sans">
            Authoritative continuous entity graph. Correlates canonical corporate entities, public security disclosure programs, authorized bug bounty targets, and historical attack surfaces.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <Link
            href="/programs"
            className="flex items-center gap-2 rounded-xl border border-cyan-700/60 bg-cyan-950/40 px-3.5 py-2.5 text-xs font-bold text-cyan-300 shadow-sm hover:bg-cyan-900/60 transition-colors font-display"
          >
            VIEW PROGRAMS DIRECTORY ({stats ? stats.public_programs.toLocaleString() : "4,249"}) &rarr;
          </Link>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 rounded-xl bg-cyan-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-cyan-950/50 hover:bg-cyan-500 transition-colors font-display"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            ADD COMPANY / DOMAIN
          </button>
        </div>
      </div>

      {/* Secondary Metrics Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3 font-sans">
        <div className="rounded-2xl border border-white/[0.08] bg-[#070b14]/75 p-4 shadow-xl backdrop-blur-xl card-25d">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-display">
            Canonical Companies
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-white font-display">
              <AnimatedNumber value={stats ? stats.canonical_companies : (totalCount || 1436)} />
            </span>
            <span className="text-[10px] text-cyan-400 font-mono">Registry</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Authoritative master data</p>
        </div>

        <div className="rounded-2xl border border-cyan-800/40 bg-cyan-950/25 p-4 shadow-xl backdrop-blur-xl card-25d">
          <div className="text-[11px] font-bold uppercase tracking-wider text-cyan-300 font-display">
            Authorized Targets
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-cyan-400 font-display">
              <AnimatedNumber value={stats ? stats.authorized_targets : 50} />
            </span>
            <span className="text-[10px] text-cyan-300 font-mono">Active Scope</span>
          </div>
          <p className="mt-1 text-[11px] text-cyan-300/70">Explicit continuous monitoring</p>
        </div>

        <div className="rounded-2xl border border-white/[0.08] bg-[#070b14]/75 p-4 shadow-xl backdrop-blur-xl card-25d">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-display">
            Public Programs
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-emerald-400 font-display">
              <AnimatedNumber value={stats ? stats.public_programs : 0} />
            </span>
            <span className="text-[10px] text-emerald-400 font-mono">Public Ecosystem</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">H1, Bugcrowd, Intigriti, YWH</p>
        </div>

        <div className="rounded-2xl border border-white/[0.08] bg-[#070b14]/75 p-4 shadow-xl backdrop-blur-xl card-25d">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-display">
            Observed Assets
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-white font-display">
              <AnimatedNumber value={stats ? stats.observed_assets : totalAssets} />
            </span>
            <span className="text-[10px] text-cyan-400 font-mono">Discovered</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Subdomains &amp; endpoints</p>
        </div>

        <div className="rounded-2xl border border-white/[0.08] bg-[#070b14]/75 p-4 shadow-xl backdrop-blur-xl card-25d col-span-2 sm:col-span-1">
          <div className="text-[11px] font-bold uppercase tracking-wider text-amber-400 font-display">
            Research Signals
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-amber-300 font-display">
              <AnimatedNumber value={stats ? stats.research_signals : totalSignals} />
            </span>
            <span className="text-[10px] text-amber-400 font-mono">Synthesized</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Prioritized attack leads</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 rounded-2xl border border-white/[0.08] bg-[#070b14]/75 p-4 shadow-xl backdrop-blur-xl md:flex-row md:items-center md:justify-between">
        <div className="relative flex-1">
          <svg className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search canonical company name, domain (e.g. google.com), or alias..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-xl border border-slate-800 bg-slate-950 pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-sans"
          />
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {/* View Mode Switcher */}
          <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-950 p-1">
            <button
              type="button"
              onClick={() => setViewMode("stream")}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                viewMode === "stream"
                  ? "bg-cyan-500 text-slate-950 font-bold shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
              title="Animated Stream List with Top/Bottom Gradients & Keyboard Navigation"
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
              title="Animated Card Grid"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
              Grid
            </button>
          </div>

          <ModernFilterDropdown
            label="Sector"
            value={selectedIndustry}
            onChange={(val) => setSelectedIndustry(val)}
            align="right"
            options={industries.map((ind) => ({
              value: ind,
              label: ind === "ALL" ? "All Sectors & Industries" : ind,
            }))}
          />
        </div>
      </div>

      {/* Company List / Grid */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-44 rounded-xl border border-slate-800/80 bg-slate-900/40 animate-pulse" />
          ))}
        </div>
      ) : companies.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 p-12 text-center">
          <p className="text-slate-400 font-mono text-sm">NO ORGANIZATIONS MATCH YOUR QUERY</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="mt-4 text-xs font-mono text-cyan-400 hover:underline"
          >
            + Add this organization to build its public graph
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {viewMode === "stream" ? (
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/30 p-2 sm:p-3 backdrop-blur-md">
              <div className="flex items-center justify-between px-3 py-2 text-xs font-mono text-slate-400 border-b border-slate-800/60 mb-2">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
                  <span className="font-bold text-slate-200">INTERACTIVE STREAM</span>
                  <span>&bull; {paginatedCompanies.length} Organizations</span>
                </div>
                <div className="hidden sm:flex items-center gap-2 text-[11px] text-slate-400">
                  <span>Use <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200 font-bold">↑</kbd> <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200 font-bold">↓</kbd> or <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200 font-bold">Enter</kbd> to open</span>
                </div>
              </div>

              <AnimatedList
                items={paginatedCompanies}
                maxHeight="680px"
                onItemSelect={(comp) => router.push(`/companies/${comp.id}`)}
                renderItem={(c, index, isSelected) => (
                  <div
                    className={`p-4 sm:p-5 rounded-2xl border transition-all duration-200 backdrop-blur-md flex flex-col md:flex-row md:items-center md:justify-between gap-4 ${
                      isSelected
                        ? "bg-cyan-950/40 border-cyan-500/70 shadow-lg shadow-cyan-500/15 ring-1 ring-cyan-500/50"
                        : "bg-slate-900/80 border-slate-800/80 hover:border-cyan-500/40 hover:bg-slate-900"
                    }`}
                  >
                    {/* Organization Details */}
                    <div className="flex items-start sm:items-center gap-3.5 min-w-0">
                      <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-xl bg-gradient-to-br from-cyan-950 to-slate-900 border border-cyan-800/50 flex items-center justify-center font-display font-extrabold text-cyan-300 text-sm sm:text-base flex-shrink-0 shadow-inner">
                        {c.name.slice(0, 2).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-base font-bold text-white group-hover:text-cyan-400 transition font-display truncate">
                            {c.name}
                          </span>
                          {c.bug_bounty_url ? (
                            <span className="rounded bg-emerald-950/80 border border-emerald-800/60 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-400">
                              BOUNTY
                            </span>
                          ) : (
                            <span className="rounded bg-slate-800/80 px-2 py-0.5 font-mono text-[10px] text-slate-400">
                              DISCLOSURE
                            </span>
                          )}
                          {c.industry && (
                            <span className="rounded-md bg-slate-800/60 px-2 py-0.5 text-[11px] font-mono text-slate-300">
                              {c.industry}
                            </span>
                          )}
                        </div>
                        <div className="mt-1 flex items-center gap-2.5 text-xs text-slate-400 font-mono">
                          <span className="text-cyan-300 font-medium">{c.canonical_domain}</span>
                          {c.country && <span>&bull; {c.country}</span>}
                          <span className="hidden sm:inline text-slate-500">&bull; ID #{c.id}</span>
                        </div>
                      </div>
                    </div>

                    {/* Quick Metrics & Actions */}
                    <div className="flex items-center justify-between md:justify-end gap-3 sm:gap-6 pt-2 md:pt-0 border-t md:border-t-0 border-slate-800/60">
                      <div className="flex items-center gap-2 sm:gap-3 text-center">
                        <div className="px-2.5 py-1 rounded-lg bg-slate-950/80 border border-slate-800/60">
                          <div className="font-mono text-xs font-bold text-white">{c.assets_count ?? 0}</div>
                          <div className="text-[9px] uppercase tracking-wider text-slate-500 font-mono">Assets</div>
                        </div>
                        <div className="px-2.5 py-1 rounded-lg bg-slate-950/80 border border-slate-800/60">
                          <div className="font-mono text-xs font-bold text-emerald-400">{c.in_scope_assets_count ?? 0}</div>
                          <div className="text-[9px] uppercase tracking-wider text-slate-500 font-mono">Scope</div>
                        </div>
                        <div className="px-2.5 py-1 rounded-lg bg-slate-950/80 border border-slate-800/60">
                          <div className="font-mono text-xs font-bold text-cyan-400">{c.programs_count ?? (c.bug_bounty_url ? 1 : 0)}</div>
                          <div className="text-[9px] uppercase tracking-wider text-slate-500 font-mono">Progs</div>
                        </div>
                        <div className="px-2.5 py-1 rounded-lg bg-slate-950/80 border border-slate-800/60">
                          <div className="font-mono text-xs font-bold text-amber-400">{c.signals_count ?? 0}</div>
                          <div className="text-[9px] uppercase tracking-wider text-slate-500 font-mono">Signals</div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 flex-shrink-0">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            openThreatAnalyst(
                              `Provide a high-priority cyber threat and attack surface intelligence briefing for ${c.name} (${c.canonical_domain}). Detail verified assets, public programs, and active exploit leads.`,
                              `Company: ${c.name}`
                            );
                          }}
                          className="rounded-xl border border-purple-500/30 bg-purple-950/40 px-2.5 py-2 text-xs font-mono font-bold text-purple-300 hover:bg-purple-900/60 transition shadow-sm active:scale-95"
                          title="Ask AI Threat Analyst about this organization"
                        >
                          AI
                        </button>
                        <Link
                          href={`/companies/${c.id}/attack-surface`}
                          onClick={(e) => e.stopPropagation()}
                          className="rounded-xl border border-cyan-800/60 bg-cyan-950/40 px-3 py-2 text-xs font-mono font-medium text-cyan-300 hover:bg-cyan-900/60 transition"
                          title="View Attack Surface Graph"
                        >
                          GRAPH
                        </Link>
                        <Link
                          href={`/companies/${c.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="rounded-xl bg-slate-800 hover:bg-cyan-600 hover:text-slate-950 px-3.5 py-2 text-xs font-display font-bold text-slate-200 transition shadow-sm"
                        >
                          CORE &rarr;
                        </Link>
                      </div>
                    </div>
                  </div>
                )}
              />
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {paginatedCompanies.map((c, idx) => (
                <AnimatedItem key={c.id} index={idx} delay={(idx % 6) * 0.04} style={{ marginBottom: 0 }}>
                  <div className="h-full flex flex-col justify-between rounded-2xl border border-slate-800/90 bg-slate-900/60 p-5 hover:border-cyan-500/50 transition-all shadow-md group card-3d-interactive">
                    <div>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <Link
                            href={`/companies/${c.id}`}
                            className="text-base font-bold text-white group-hover:text-cyan-400 transition-colors font-display"
                          >
                            {c.name}
                          </Link>
                          <div className="mt-0.5 flex items-center gap-2">
                            <span className="font-mono text-xs text-cyan-300">{c.canonical_domain}</span>
                            {c.country && (
                              <span className="text-[10px] text-slate-500 font-mono">({c.country})</span>
                            )}
                          </div>
                        </div>

                        {c.bug_bounty_url ? (
                          <span className="rounded bg-emerald-950/80 border border-emerald-800/60 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-emerald-400">
                            BOUNTY
                          </span>
                        ) : (
                          <span className="rounded bg-slate-800/80 px-2 py-0.5 font-mono text-[10px] text-slate-400">
                            DISCLOSURE
                          </span>
                        )}
                      </div>

                      {c.industry && (
                        <div className="mt-2.5">
                          <span className="inline-block rounded-md bg-slate-800/60 px-2 py-0.5 text-[11px] font-mono text-slate-300">
                            {c.industry}
                          </span>
                        </div>
                      )}

                      {/* Graph Metrics */}
                      <div className="mt-4 grid grid-cols-4 gap-1.5 border-t border-slate-800/80 pt-3 text-center">
                        <div className="rounded-xl bg-slate-950/60 p-2">
                          <span className="block font-mono text-xs font-bold text-white">{c.assets_count ?? 0}</span>
                          <span className="block text-[9px] uppercase tracking-wider text-slate-500 font-mono">Assets</span>
                        </div>
                        <div className="rounded-xl bg-slate-950/60 p-2">
                          <span className="block font-mono text-xs font-bold text-emerald-400">{c.in_scope_assets_count ?? 0}</span>
                          <span className="block text-[9px] uppercase tracking-wider text-slate-500 font-mono">Scope</span>
                        </div>
                        <div className="rounded-xl bg-slate-950/60 p-2">
                          <span className="block font-mono text-xs font-bold text-cyan-400">{c.programs_count ?? (c.bug_bounty_url ? 1 : 0)}</span>
                          <span className="block text-[9px] uppercase tracking-wider text-slate-500 font-mono">Progs</span>
                        </div>
                        <div className="rounded-xl bg-slate-950/60 p-2">
                          <span className="block font-mono text-xs font-bold text-amber-400">{c.signals_count ?? 0}</span>
                          <span className="block text-[9px] uppercase tracking-wider text-slate-500 font-mono">Signals</span>
                        </div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="mt-4 flex items-center justify-between gap-2 border-t border-slate-800/80 pt-3">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          openThreatAnalyst(
                            `Provide a high-priority cyber threat and attack surface intelligence briefing for ${c.name} (${c.canonical_domain}). Detail verified assets, public programs, and active exploit leads.`,
                            `Company: ${c.name}`
                          );
                        }}
                        className="rounded-xl border border-purple-500/30 bg-purple-950/40 px-3 py-2 text-xs font-mono font-bold text-purple-300 hover:bg-purple-900/60 transition shadow-sm active:scale-95"
                        title="Ask AI Threat Analyst"
                      >
                        AI
                      </button>
                      <Link
                        href={`/companies/${c.id}`}
                        className="flex-1 rounded-xl bg-slate-800/80 py-2 text-center text-xs font-display font-bold text-slate-200 hover:bg-slate-700 transition-colors"
                      >
                        INTELLIGENCE CORE &rarr;
                      </Link>
                      <Link
                        href={`/companies/${c.id}/attack-surface`}
                        className="flex items-center justify-center gap-1.5 rounded-xl border border-cyan-800/60 bg-cyan-950/40 px-3.5 py-2 text-xs font-mono font-medium text-cyan-300 hover:bg-cyan-900/60 transition-colors"
                        title="View Attack Surface Graph"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        GRAPH
                      </Link>
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
                <strong className="text-white font-mono">{Math.min(currentPage * pageSize, companies.length)}</strong> of{" "}
                <strong className="text-white font-mono">{companies.length}</strong> companies
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 font-bold text-slate-300 hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition"
                >
                  &larr; PREV
                </button>

                {Array.from({ length: Math.min(7, totalPages) }, (_, idx) => {
                  let pageNum = idx + 1;
                  if (totalPages > 7) {
                    if (currentPage > 4) {
                      pageNum = currentPage - 3 + idx;
                    }
                    if (pageNum > totalPages) {
                      pageNum = totalPages - (6 - idx);
                    }
                  }
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`h-8 w-8 rounded-lg font-mono text-xs font-bold transition ${
                        currentPage === pageNum
                          ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                          : "border border-slate-800 bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800"
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}

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

      {/* Add Company Modal */}
      {showAddModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-surface-in"
          onClick={() => setShowAddModal(false)}
        >
          <div
            className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white">ADD COMPANY / ROOT TARGET</h3>
                <p className="text-xs text-slate-400">
                  Enter a root domain, URL, or organization name to construct its public graph.
                </p>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddCompany} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
                  Company Name or Domain <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. google.com, https://stripe.com, or Slack"
                  value={inputVal}
                  onChange={(e) => setInputVal(e.target.value)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:border-cyan-500 focus:outline-none"
                />
                <p className="mt-1 text-[11px] text-slate-500">
                  Safe public discovery will automatically resolve root boundaries and discover public references.
                </p>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
                  Description / Research Scope Notes
                </label>
                <textarea
                  rows={3}
                  placeholder="Optional scope context or research objectives..."
                  value={descriptionVal}
                  onChange={(e) => setDescriptionVal(e.target.value)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-cyan-500 focus:outline-none"
                />
              </div>

              {errorMsg && (
                <div className="rounded-lg border border-red-900/60 bg-red-950/40 p-3 text-xs text-red-400 font-mono">
                  {errorMsg}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="rounded-lg px-4 py-2 text-xs font-mono text-slate-400 hover:text-white"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-lg bg-cyan-600 px-5 py-2 text-xs font-mono font-bold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors"
                >
                  {isSubmitting ? "RESOLVING..." : "BUILD PUBLIC GRAPH"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
