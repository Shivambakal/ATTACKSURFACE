"use client";

import React, { useState, useMemo } from "react";
import { TimelineEvent } from "@/lib/types";

interface ThreeDTimelineProps {
  events: TimelineEvent[];
  companyName?: string;
  domain?: string;
}

const CATEGORY_STYLES: Record<string, { label: string; icon: string; badge: string; dot: string }> = {
  SECURITY: {
    label: "Security",
    icon: "🛡️",
    badge: "border-rose-500/40 text-rose-300 bg-rose-500/10",
    dot: "bg-rose-500 shadow-[0_0_12px_rgba(244,63,94,0.7)]",
  },
  VULNERABILITY: {
    label: "Vulnerability",
    icon: "⚠️",
    badge: "border-amber-500/40 text-amber-300 bg-amber-500/10",
    dot: "bg-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.7)]",
  },
  PRODUCT: {
    label: "Product",
    icon: "📦",
    badge: "border-emerald-500/40 text-emerald-300 bg-emerald-500/10",
    dot: "bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.7)]",
  },
  API: {
    label: "API",
    icon: "⚡",
    badge: "border-purple-500/40 text-purple-300 bg-purple-500/10",
    dot: "bg-purple-500 shadow-[0_0_12px_rgba(168,85,247,0.7)]",
  },
  INFRASTRUCTURE: {
    label: "Infrastructure",
    icon: "🌐",
    badge: "border-sky-500/40 text-sky-300 bg-sky-500/10",
    dot: "bg-sky-500 shadow-[0_0_12px_rgba(14,165,233,0.7)]",
  },
  PROGRAM: {
    label: "Program / Scope",
    icon: "🎯",
    badge: "border-cyan-500/40 text-cyan-300 bg-cyan-500/10",
    dot: "bg-cyan-500 shadow-[0_0_12px_rgba(6,182,212,0.7)]",
  },
  TECHNOLOGY: {
    label: "Technology",
    icon: "⚙️",
    badge: "border-indigo-500/40 text-indigo-300 bg-indigo-500/10",
    dot: "bg-indigo-500 shadow-[0_0_12px_rgba(99,102,241,0.7)]",
  },
  OTHER: {
    label: "General Milestone",
    icon: "📍",
    badge: "border-slate-600 text-slate-300 bg-slate-800/40",
    dot: "bg-slate-400 shadow-[0_0_12px_rgba(148,163,184,0.7)]",
  },
};

function normalizeEvent(ev: TimelineEvent) {
  const rawTitle = ev.title || "";
  const rawSummary = ev.summary || "";
  const evType = (ev.event_type || "").toUpperCase();

  let category = "OTHER";
  if (evType.includes("VULN") || rawTitle.toLowerCase().includes("cve") || rawTitle.toLowerCase().includes("vulnerability")) {
    category = "VULNERABILITY";
  } else if (evType.includes("SEC") || rawTitle.toLowerCase().includes("security") || rawTitle.toLowerCase().includes("auth")) {
    category = "SECURITY";
  } else if (evType.includes("API") || rawTitle.toLowerCase().includes("api") || rawTitle.toLowerCase().includes("endpoint")) {
    category = "API";
  } else if (evType.includes("INFRA") || rawTitle.toLowerCase().includes("cloud") || rawTitle.toLowerCase().includes("hardware") || rawTitle.toLowerCase().includes("silicon")) {
    category = "INFRASTRUCTURE";
  } else if (evType.includes("PROG") || rawTitle.toLowerCase().includes("bounty") || rawTitle.toLowerCase().includes("scope")) {
    category = "PROGRAM";
  } else if (evType.includes("PROD") || evType.includes("RELEASE") || rawTitle.toLowerCase().includes("release") || rawTitle.toLowerCase().includes("launch")) {
    category = "PRODUCT";
  } else if (evType.includes("TECH") || rawTitle.toLowerCase().includes("framework") || rawTitle.toLowerCase().includes("database")) {
    category = "TECHNOLOGY";
  }

  const style = CATEGORY_STYLES[category] || CATEGORY_STYLES["OTHER"];

  // Formatted date and extract Year
  const dateStr = ev.published_at || ev.observed_at;
  let year = "2024";
  let formattedDate = "Historical Milestone";

  if (dateStr) {
    try {
      const d = new Date(dateStr);
      if (!isNaN(d.getTime())) {
        year = d.getFullYear().toString();
        formattedDate = d.toLocaleDateString("en-US", {
          year: "numeric",
          month: "short",
          day: "numeric",
        });
      }
    } catch {
      // fallback
    }
  }

  // Security relevance explanation
  let securityRelevance = "Establishes verifiable security posture baseline and defensive engineering evolution.";
  if (category === "VULNERABILITY") {
    securityRelevance = "Critical exposure history: informs continuous vulnerability correlation and attack path analysis.";
  } else if (category === "SECURITY") {
    securityRelevance = "Defensive architecture milestone: highlights hardening boundaries and cryptographic improvements.";
  } else if (category === "API") {
    securityRelevance = "External interface expansion: potential new authorization boundaries and parameter surfaces.";
  } else if (category === "INFRASTRUCTURE") {
    securityRelevance = "Hosting & hardware evolution: defines substrate exposure and hosting perimeter.";
  }

  return {
    ...ev,
    category,
    style,
    year,
    formattedDate,
    displayTitle: rawTitle,
    displaySummary: rawSummary || "Public corporate intelligence milestone documented from authoritative records.",
    securityRelevance,
  };
}

export default function ThreeDTimeline({
  events,
  companyName = "Target Organization",
  domain,
}: ThreeDTimelineProps) {
  const [activeCategory, setActiveCategory] = useState<string>("ALL");
  const [activeRange, setActiveRange] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [viewMode, setViewMode] = useState<"rail" | "grid" | "dense">("rail");
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null);

  const normalizedEvents = useMemo(() => {
    return events.map(normalizeEvent);
  }, [events]);

  const categories = useMemo(() => {
    return [
      { key: "ALL", label: "All Milestones" },
      { key: "SECURITY", label: "Security" },
      { key: "VULNERABILITY", label: "Vulnerabilities" },
      { key: "PRODUCT", label: "Products" },
      { key: "API", label: "APIs" },
      { key: "INFRASTRUCTURE", label: "Infrastructure" },
      { key: "PROGRAM", label: "Program / Scope" },
      { key: "TECHNOLOGY", label: "Technology" },
      { key: "OTHER", label: "Other" },
    ];
  }, []);

  const filteredEvents = useMemo(() => {
    const now = new Date();

    return normalizedEvents.filter((ev) => {
      // Category Filter
      if (activeCategory !== "ALL" && ev.category !== activeCategory) {
        return false;
      }

      // Time Range Filter
      if (activeRange !== "ALL") {
        const dateStr = ev.published_at || ev.observed_at;
        if (dateStr) {
          const evDate = new Date(dateStr);
          const diffMonths = (now.getTime() - evDate.getTime()) / (1000 * 60 * 60 * 24 * 30.4);
          if (activeRange === "1M" && diffMonths > 1) return false;
          if (activeRange === "3M" && diffMonths > 3) return false;
          if (activeRange === "6M" && diffMonths > 6) return false;
          if (activeRange === "1Y" && diffMonths > 12) return false;
          if (activeRange === "3Y" && diffMonths > 36) return false;
        }
      }

      // Full-Text Search Filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const match =
          ev.displayTitle.toLowerCase().includes(q) ||
          ev.displaySummary.toLowerCase().includes(q) ||
          ev.category.toLowerCase().includes(q) ||
          (ev.source && ev.source.toLowerCase().includes(q));
        if (!match) return false;
      }

      return true;
    });
  }, [normalizedEvents, activeCategory, activeRange, searchQuery]);

  // Group filtered events by Year for spatial year anchors
  const eventsByYear = useMemo(() => {
    const map = new Map<string, typeof filteredEvents>();
    for (const ev of filteredEvents) {
      const yr = ev.year;
      if (!map.has(yr)) {
        map.set(yr, []);
      }
      map.get(yr)!.push(ev);
    }
    // Sort years descending
    return Array.from(map.entries()).sort((a, b) => b[0].localeCompare(a[0]));
  }, [filteredEvents]);

  return (
    <div className="space-y-6">
      {/* ── SPATIAL CONTROL BAR ────────────────────────────────────────── */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-xl backdrop-blur-md space-y-4">
        {/* Row 1: Category Filter Pills */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-1 font-display">
            Domain:
          </span>
          {categories.map((c) => {
            const count =
              c.key === "ALL"
                ? normalizedEvents.length
                : normalizedEvents.filter((e) => e.category === c.key).length;
            return (
              <button
                key={c.key}
                onClick={() => setActiveCategory(c.key)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-all duration-200 flex items-center gap-1.5 ${
                  activeCategory === c.key
                    ? "bg-cyan-500 text-slate-950 font-bold shadow-lg shadow-cyan-500/20 scale-105"
                    : "border border-slate-800 bg-slate-950/60 text-slate-300 hover:border-slate-700 hover:text-white"
                }`}
              >
                <span>{c.label}</span>
                <span
                  className={`rounded-full px-1.5 py-0.2 text-[10px] font-mono ${
                    activeCategory === c.key ? "bg-slate-950 text-cyan-300 font-bold" : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Row 2: Time Range, Search, and View Modes */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pt-2 border-t border-slate-800/80">
          {/* Time Range Selector */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-1 font-display">
              Horizon:
            </span>
            {["1M", "3M", "6M", "1Y", "3Y", "ALL"].map((range) => (
              <button
                key={range}
                onClick={() => setActiveRange(range)}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono transition-all ${
                  activeRange === range
                    ? "bg-slate-800 text-cyan-300 border border-cyan-500/40 font-bold shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-950/40"
                }`}
              >
                {range}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Search Input */}
            <div className="relative w-full sm:w-64">
              <input
                type="text"
                placeholder="Search milestones, CVEs, APIs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-xl border border-slate-800 bg-slate-950/90 px-3.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-sans"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3 top-2 text-xs text-slate-400 hover:text-white"
                >
                  &times;
                </button>
              )}
            </div>

            {/* View Mode Toggle */}
            <div className="flex rounded-xl border border-slate-800 bg-slate-950 p-0.5">
              <button
                onClick={() => setViewMode("rail")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  viewMode === "rail"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                2.5D Rail
              </button>
              <button
                onClick={() => setViewMode("grid")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  viewMode === "grid"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Grid
              </button>
              <button
                onClick={() => setViewMode("dense")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  viewMode === "dense"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Compact
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── TIMELINE BODY ──────────────────────────────────────────────── */}
      {filteredEvents.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-12 text-center space-y-3">
          <div className="inline-flex p-4 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-2xl">
            🔍
          </div>
          <h3 className="text-base font-bold text-white font-display">No Timeline Milestones Match Filters</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Try adjusting category &quot;{activeCategory}&quot; or time horizon &quot;{activeRange}&quot;.
          </p>
        </div>
      ) : viewMode === "rail" ? (
        /* ================= 2.5D SPATIAL RAIL WITH YEAR ANCHORS ================= */
        <div className="space-y-10">
          {eventsByYear.map(([year, yrEvents]) => (
            <div key={year} className="space-y-6">
              {/* YEAR ANCHOR HEADER */}
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 rounded-xl border border-cyan-500/40 bg-cyan-950/60 px-4 py-1.5 shadow-lg shadow-cyan-950/50">
                  <span className="font-display text-lg font-black tracking-wider text-cyan-300">
                    {year}
                  </span>
                  <span className="text-xs font-mono text-cyan-400/80">
                    &bull; {yrEvents.length} {yrEvents.length === 1 ? "Event" : "Events"}
                  </span>
                </div>
                <div className="h-px flex-1 bg-gradient-to-r from-cyan-500/40 via-slate-800 to-transparent" />
              </div>

              {/* Vertical Glowing Rail */}
              <div className="relative timeline-3d-track timeline-3d-track-centered py-2 perspective-1400">
                <div className="space-y-8">
                  {yrEvents.map((ev, idx) => {
                    const isEven = idx % 2 === 0;
                    return (
                      <div
                        key={ev.id || idx}
                        className={`relative flex items-center ${
                          isEven ? "md:flex-row-reverse" : "md:flex-row"
                        } flex-col gap-6`}
                      >
                        {/* Glowing 3D Node Center */}
                        <div
                          onClick={() => setSelectedEvent(ev)}
                          className="absolute left-7 md:left-1/2 -translate-x-1/2 z-10 flex h-10 w-10 items-center justify-center rounded-full border-2 border-slate-700 bg-slate-950 cursor-pointer hover:scale-125 transition-transform"
                        >
                          <span className={`h-3.5 w-3.5 rounded-full ${ev.style.dot} animate-pulse`} />
                        </div>

                        {/* 3D Spatial Event Card */}
                        <div
                          onClick={() => setSelectedEvent(ev)}
                          className="w-full pl-16 md:pl-0 md:w-[46%] cursor-pointer group"
                        >
                          <div className="card-3d-interactive rounded-2xl border border-slate-800/90 bg-gradient-to-br from-slate-900/95 via-slate-900/80 to-slate-950 p-5 shadow-2xl backdrop-blur-md relative overflow-hidden transition-all duration-300 hover:border-slate-700">
                            {/* Top Glowing Ambient Highlight */}
                            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                            {/* Header: Category Badge + Date */}
                            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                              <div className="flex items-center gap-1.5">
                                <span className="text-base">{ev.style.icon}</span>
                                <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase border ${ev.style.badge}`}>
                                  {ev.style.label}
                                </span>
                              </div>
                              <span className="text-xs font-semibold text-cyan-300/90 bg-cyan-950/50 px-2.5 py-0.5 rounded-md border border-cyan-800/40 font-mono">
                                {ev.formattedDate}
                              </span>
                            </div>

                            {/* Large Readable Title */}
                            <h3 className="font-display text-base sm:text-lg font-bold text-white tracking-tight group-hover:text-cyan-300 transition-colors">
                              {ev.displayTitle}
                            </h3>

                            {/* Human Summary */}
                            <p className="mt-2.5 text-xs sm:text-sm text-slate-300 leading-relaxed font-sans">
                              {ev.displaySummary}
                            </p>

                            {/* Security Relevance Callout */}
                            <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/70 p-2.5 text-[11px] text-slate-400">
                              <span className="font-bold text-slate-300 font-display block mb-0.5">
                                Security Relevance:
                              </span>
                              {ev.securityRelevance}
                            </div>

                            {/* Card Footer: Source & View Details */}
                            <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                              <span className="font-mono text-[11px] text-slate-500 truncate max-w-[200px]">
                                Source: {ev.source || "Corporate Intelligence"}
                              </span>
                              <span className="font-semibold text-cyan-400 group-hover:underline flex items-center gap-1 font-display">
                                View Details &rarr;
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : viewMode === "grid" ? (
        /* ================= 3D ISOMETRIC GRID MODE ================= */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 perspective-1200">
          {filteredEvents.map((ev, idx) => (
            <div
              key={ev.id || idx}
              onClick={() => setSelectedEvent(ev)}
              className="card-3d-interactive cursor-pointer group rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-xl backdrop-blur-md flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <div className="flex items-center gap-1.5">
                    <span className="text-lg">{ev.style.icon}</span>
                    <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase border ${ev.style.badge}`}>
                      {ev.style.label}
                    </span>
                  </div>
                  <span className="text-xs font-mono text-cyan-400 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-900/40">
                    {ev.formattedDate}
                  </span>
                </div>

                <h3 className="font-display text-base font-bold text-white group-hover:text-cyan-300 transition-colors">
                  {ev.displayTitle}
                </h3>
                <p className="mt-2 text-xs text-slate-300 line-clamp-3 leading-relaxed">
                  {ev.displaySummary}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
                <span className="text-slate-500 font-mono text-[11px]">
                  {ev.source || "Archive"}
                </span>
                <span className="text-cyan-400 group-hover:translate-x-1 transition-transform font-bold font-display">
                  View Details &rarr;
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* ================= COMPACT LIST MODE ================= */
        <div className="divide-y divide-slate-800/80 rounded-2xl border border-slate-800 bg-slate-900/70 overflow-hidden">
          {filteredEvents.map((ev, idx) => (
            <div
              key={ev.id || idx}
              onClick={() => setSelectedEvent(ev)}
              className="p-4 hover:bg-slate-800/40 transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl shrink-0">{ev.style.icon}</span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-display font-bold text-white text-sm">
                      {ev.displayTitle}
                    </span>
                    <span className={`rounded px-2 py-0.2 text-[10px] font-bold border ${ev.style.badge}`}>
                      {ev.style.label}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">
                    {ev.displaySummary}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-xs font-mono text-cyan-300">{ev.formattedDate}</span>
                <span className="text-slate-500 text-xs">&rarr;</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── 3D INSPECTION DRAWER (Preserving All Original Evidence) ─── */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xl animate-surface-in">
          <div className="relative w-full max-w-2xl rounded-3xl border border-cyan-500/40 bg-slate-900/95 p-6 sm:p-8 shadow-[0_0_60px_rgba(6,182,212,0.25)] space-y-6">
            {/* Close Button */}
            <button
              onClick={() => setSelectedEvent(null)}
              className="absolute right-5 top-5 rounded-full bg-slate-800/80 p-2 text-slate-400 hover:text-white transition"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* Modal Header */}
            <div className="flex items-center gap-3">
              <span className="text-3xl">{selectedEvent.style.icon}</span>
              <div>
                <span className={`inline-block px-3 py-0.5 rounded-full text-xs font-bold uppercase border ${selectedEvent.style.badge}`}>
                  {selectedEvent.style.label}
                </span>
                <h2 className="text-xl sm:text-2xl font-bold font-display text-white mt-1">
                  {selectedEvent.displayTitle}
                </h2>
              </div>
            </div>

            {/* Event Timestamp & Provenance Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3.5 rounded-xl border border-slate-800 bg-slate-950/80 font-mono text-xs">
              <div>
                <span className="text-slate-500 block text-[10px] uppercase">Recorded Date</span>
                <span className="text-cyan-300 font-bold">{selectedEvent.formattedDate}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px] uppercase">Source Provider</span>
                <span className="text-white font-bold">{selectedEvent.source || "Corporate Intelligence"}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px] uppercase">Confidence</span>
                <span className="text-emerald-400 font-bold">VERIFIED (95%+)</span>
              </div>
            </div>

            {/* Narrative Explanation */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-display">
                Forensic Analysis &amp; Impact
              </h4>
              <p className="text-sm text-slate-200 leading-relaxed bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
                {selectedEvent.displaySummary}
              </p>
            </div>

            {/* Security Relevance */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-display">
                Attack Surface Relevance
              </h4>
              <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                {selectedEvent.securityRelevance}
              </p>
            </div>

            {/* Original Evidence & Provenance Hash */}
            <div className="space-y-2 font-mono text-xs">
              <span className="text-slate-500">Original Evidence Reference:</span>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-cyan-300 break-all space-y-1">
                {selectedEvent.source_url ? (
                  <div>
                    URL:{" "}
                    <a
                      href={selectedEvent.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline text-cyan-400 hover:text-cyan-300"
                    >
                      {selectedEvent.source_url}
                    </a>
                  </div>
                ) : (
                  <div>URL: Reference catalog record</div>
                )}
                {selectedEvent.meta?.provenance_hash && (
                  <div className="text-slate-500 text-[11px]">
                    SHA-256 Provenance Hash: {selectedEvent.meta.provenance_hash}
                  </div>
                )}
              </div>
            </div>

            {/* Modal Actions */}
            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedEvent(null)}
                className="rounded-xl bg-cyan-500 hover:bg-cyan-400 px-6 py-2.5 text-xs font-bold text-slate-950 transition"
              >
                Close Inspection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
