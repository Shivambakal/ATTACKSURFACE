"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Company } from "@/lib/types";
import ModernFilterDropdown from "@/components/ModernFilterDropdown";

interface CompanyStats {
  canonical_companies: number;
  public_programs: number;
  authorized_targets: number;
  observed_assets: number;
  research_signals: number;
}

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [stats, setStats] = useState<CompanyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIndustry, setSelectedIndustry] = useState<string>("ALL");
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
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
      let url = `/api/v1/companies?limit=1000`;
      if (searchQuery.trim()) {
        url += `&q=${encodeURIComponent(searchQuery.trim())}`;
      }
      if (selectedIndustry !== "ALL") {
        url += `&industry=${encodeURIComponent(selectedIndustry)}`;
      }
      const compData = await apiFetch<{ total: number; items: Company[] }>(url);
      setCompanies(compData.items || []);
      setTotalCount(compData.total || 0);
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

  const handleAddCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await apiFetch<Company>("/api/v1/companies", {
        method: "POST",
        body: JSON.stringify({
          name_or_domain: inputVal.trim(),
          description: descriptionVal.trim() || undefined,
        }),
      });
      setShowAddModal(false);
      setInputVal("");
      setDescriptionVal("");
      fetchCompanies();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to resolve company.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const industries = [
    "ALL",
    "Technology",
    "Software & Cloud",
    "Developer Tools",
    "Fintech & Payments",
    "Cybersecurity & Bug Bounty",
    "Gaming & Entertainment",
  ];

  // Aggregate metrics
  const totalAssets = companies.reduce((acc, c) => acc + (c.assets_count || 1), 0);
  const totalInScope = companies.reduce((acc, c) => acc + (c.in_scope_assets_count || 1), 0);
  const totalSignals = companies.reduce((acc, c) => acc + (c.signals_count || 0), 0);

  // Pagination slice
  const totalPages = Math.max(1, Math.ceil(companies.length / pageSize));
  const paginatedCompanies = companies.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="space-y-6">
      {/* Top Header & Metrics */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-display">
              COMPANY INTELLIGENCE — {stats ? stats.canonical_companies.toLocaleString() : totalCount.toLocaleString()} Verified Organizations
            </h1>
            <span className="rounded-full bg-cyan-950/80 px-3 py-1 font-mono text-xs font-bold text-cyan-400 border border-cyan-800/60 shadow-sm">
              {stats ? stats.canonical_companies.toLocaleString() : totalCount.toLocaleString()} CANONICAL ENTITIES
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
            VIEW PROGRAMS DIRECTORY ({stats ? stats.public_programs.toLocaleString() : "..."}) &rarr;
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
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 backdrop-blur-md">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-display">
            Canonical Companies
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-white font-display">
              {stats ? stats.canonical_companies.toLocaleString() : totalCount.toLocaleString()}
            </span>
            <span className="text-[10px] text-cyan-400 font-mono">Registry</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Authoritative master data</p>
        </div>

        <div className="rounded-2xl border border-cyan-800/40 bg-cyan-950/20 p-4 backdrop-blur-md">
          <div className="text-[11px] font-bold uppercase tracking-wider text-cyan-300 font-display">
            Authorized Targets
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-cyan-400 font-display">
              {stats ? stats.authorized_targets.toLocaleString() : "50"}
            </span>
            <span className="text-[10px] text-cyan-300 font-mono">Active Scope</span>
          </div>
          <p className="mt-1 text-[11px] text-cyan-300/70">Explicit continuous monitoring</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 backdrop-blur-md">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-display">
            Public Programs
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-emerald-400 font-display">
              {stats ? stats.public_programs.toLocaleString() : "..."}
            </span>
            <span className="text-[10px] text-emerald-400 font-mono">Public Ecosystem</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">H1, Bugcrowd, Intigriti, YWH</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 backdrop-blur-md">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-display">
            Observed Assets
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-white font-display">
              {stats ? stats.observed_assets.toLocaleString() : totalAssets.toLocaleString()}
            </span>
            <span className="text-[10px] text-cyan-400 font-mono">Discovered</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Subdomains &amp; endpoints</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 backdrop-blur-md col-span-2 sm:col-span-1">
          <div className="text-[11px] font-bold uppercase tracking-wider text-amber-400 font-display">
            Research Signals
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-amber-300 font-display">
              {stats ? stats.research_signals.toLocaleString() : totalSignals.toLocaleString()}
            </span>
            <span className="text-[10px] text-amber-400 font-mono">Synthesized</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Prioritized attack leads</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 md:flex-row md:items-center md:justify-between">
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

      {/* Company Grid */}
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
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {paginatedCompanies.map((c) => (
              <div
                key={c.id}
                className="flex flex-col justify-between rounded-2xl border border-slate-800/90 bg-slate-900/60 p-5 hover:border-cyan-500/50 transition-all shadow-md group card-3d-interactive"
              >
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
                  <Link
                    href={`/companies/${c.id}`}
                    className="flex-1 rounded-xl bg-slate-800/80 py-2 text-center text-xs font-display font-bold text-slate-200 hover:bg-slate-700 transition-colors"
                  >
                    COMMAND CENTER
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
            ))}
          </div>

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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
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
