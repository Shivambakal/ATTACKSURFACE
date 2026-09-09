"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { Company } from "@/lib/types";
import { usePreferences, PriorityZone } from "@/lib/preferences";
import { CardTilt3D, SeverityBadge } from "@/components/ui/InteractionPrimitives";

interface CompanyPriorityBoardProps {
  companies: Company[];
  onCompareCompanies?: (comp1: Company, comp2: Company) => void;
}

const ZONES: Array<{ id: PriorityZone; label: string; tone: string; dot: string; desc: string }> = [
  {
    id: "CRITICAL",
    label: "CRITICAL ASSET TARGETS",
    tone: "border-rose-500/40 bg-rose-500/[0.03]",
    dot: "bg-rose-500 shadow-[0_0_10px_#f43f5e]",
    desc: "Top priority targets with active zero-days, CISA KEV, or active bounty scope",
  },
  {
    id: "HIGH",
    label: "HIGH VALUE HUNTING",
    tone: "border-amber-500/40 bg-amber-500/[0.03]",
    dot: "bg-amber-400 shadow-[0_0_10px_#f59e0b]",
    desc: "Frequent release cycles, expanding API surfaces, and active signals",
  },
  {
    id: "WATCH",
    label: "CONTINUOUS BASELINE WATCH",
    tone: "border-cyan-500/40 bg-cyan-500/[0.03]",
    dot: "bg-cyan-400 shadow-[0_0_10px_#00f0ff]",
    desc: "Monitoring for scope changes, DNS deltas, and certificate renewals",
  },
  {
    id: "BACKGROUND",
    label: "PASSIVE INDEXING",
    tone: "border-slate-800/80 bg-slate-900/20",
    dot: "bg-slate-500",
    desc: "Archival observation and long-term attack surface tracking",
  },
];

export default function CompanyPriorityBoard({ companies, onCompareCompanies }: CompanyPriorityBoardProps) {
  const { preferences, setCompanyPriority, togglePinCompany } = usePreferences();
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [activeDropZone, setActiveDropZone] = useState<PriorityZone | null>(null);
  const [dropNotice, setDropNotice] = useState<string | null>(null);
  const [compareSelection, setCompareSelection] = useState<Company[]>([]);

  // Map companies to zones using preferences.companyPriorities
  const categorized = useMemo(() => {
    const map: Record<PriorityZone, Company[]> = {
      CRITICAL: [],
      HIGH: [],
      WATCH: [],
      BACKGROUND: [],
    };

    // If company is in preferences, place it in user's priority zone.
    // Defaults: if bug bounty program present or > 0 assets, place in HIGH/WATCH, otherwise BACKGROUND
    for (const c of companies) {
      const assigned = preferences.companyPriorities[String(c.id)];
      if (assigned && map[assigned]) {
        map[assigned].push(c);
      } else if (c.signals_count && c.signals_count > 0) {
        map.HIGH.push(c);
      } else if (c.bug_bounty_url || (c.assets_count && c.assets_count > 10)) {
        map.WATCH.push(c);
      } else {
        map.BACKGROUND.push(c);
      }
    }

    return map;
  }, [companies, preferences.companyPriorities]);

  const handleDragStart = (e: React.DragEvent, id: number | string) => {
    const idStr = String(id);
    setDraggedId(idStr);
    e.dataTransfer.setData("text/plain", idStr);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent, zone: PriorityZone) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (activeDropZone !== zone) {
      setActiveDropZone(zone);
    }
  };

  const handleDragLeave = (zone: PriorityZone) => {
    if (activeDropZone === zone) {
      setActiveDropZone(null);
    }
  };

  const handleDrop = async (e: React.DragEvent, zone: PriorityZone) => {
    e.preventDefault();
    const idStr = e.dataTransfer.getData("text/plain") || draggedId;
    setActiveDropZone(null);
    setDraggedId(null);

    if (idStr) {
      await setCompanyPriority(idStr, zone);
      const matched = companies.find((c) => String(c.id) === idStr);
      setDropNotice(`${matched?.name || "Target"} reclassified to ${zone}`);
      setTimeout(() => setDropNotice(null), 2500);
    }
  };

  const handleCompareClick = (c: Company) => {
    const exists = compareSelection.some((item) => item.id === c.id);
    let next: Company[];
    if (exists) {
      next = compareSelection.filter((item) => item.id !== c.id);
    } else {
      next = [...compareSelection, c].slice(0, 2);
    }
    setCompareSelection(next);
    if (next.length === 2 && onCompareCompanies) {
      onCompareCompanies(next[0], next[1]);
    }
  };

  return (
    <div className="space-y-4">
      {/* Board Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-white tracking-tight font-display flex items-center gap-2">
              <span>MY INTELLIGENCE PRIORITIES</span>
              <span className="rounded bg-cyan-950/80 px-2 py-0.5 font-mono text-[10px] font-bold text-cyan-300 border border-cyan-800/60">
                DRAG &amp; DROP
              </span>
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Physical priority matrix. Reorder, pin, or drag entities to establish operational surveillance frequency.
          </p>
        </div>

        {dropNotice && (
          <div className="animate-surface-in flex items-center gap-1.5 rounded-lg border border-cyan-500/40 bg-cyan-950/60 px-3 py-1 text-xs font-mono text-cyan-300">
            <span>✓</span>
            <span>{dropNotice}</span>
          </div>
        )}
      </div>

      {/* 4 Priority Zones */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {ZONES.map((zone) => {
          const zoneCompanies = categorized[zone.id];
          const isTargeted = activeDropZone === zone.id;

          return (
            <div
              key={zone.id}
              onDragOver={(e) => handleDragOver(e, zone.id)}
              onDragLeave={() => handleDragLeave(zone.id)}
              onDrop={(e) => handleDrop(e, zone.id)}
              className={`flex flex-col rounded-2xl border transition-all duration-200 min-h-[380px] p-3.5 ${zone.tone} ${
                isTargeted
                  ? "ring-2 ring-cyan-400 border-cyan-400 bg-cyan-950/30 scale-[1.01]"
                  : "hover:border-slate-700"
              }`}
            >
              {/* Zone Header */}
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${zone.dot}`} />
                  <h3 className="font-mono text-xs font-bold tracking-wider text-slate-200">
                    {zone.label}
                  </h3>
                </div>
                <span className="rounded-md bg-slate-900 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-400 border border-slate-800">
                  {zoneCompanies.length}
                </span>
              </div>

              <p className="mt-1.5 text-[10px] text-slate-400 leading-snug">
                {zone.desc}
              </p>

              {/* Cards Rail */}
              <div className="mt-3 flex-1 space-y-2 overflow-y-auto max-h-[460px] pr-1 scrollbar-thin">
                {zoneCompanies.length === 0 ? (
                  <div className="flex h-32 items-center justify-center rounded-xl border border-dashed border-slate-800/80 p-4 text-center text-[11px] font-mono text-slate-400">
                    DRAG TARGET HERE
                  </div>
                ) : (
                  zoneCompanies.map((c) => {
                    const isPinned = preferences.pinnedCompanies.includes(String(c.id));
                    const isComparing = compareSelection.some((item) => item.id === c.id);

                    return (
                      <div
                        key={c.id}
                        draggable
                        onDragStart={(e) => handleDragStart(e, c.id)}
                        className={`group relative rounded-xl border border-slate-800/90 bg-slate-950/80 p-3 transition-all duration-200 cursor-grab active:cursor-grabbing hover:border-cyan-500/50 hover:shadow-[0_8px_20px_rgba(0,0,0,0.6)] ${
                          isPinned ? "ring-1 ring-cyan-400/40" : ""
                        } ${isComparing ? "ring-2 ring-purple-400" : ""}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="overflow-hidden">
                            <Link
                              href={`/companies/${c.id}`}
                              className="text-xs font-bold text-white hover:text-cyan-300 transition truncate block font-display"
                            >
                              {c.name}
                            </Link>
                            <span className="font-mono text-[11px] text-slate-400 block truncate">
                              {c.canonical_domain}
                            </span>
                          </div>

                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              type="button"
                              onClick={() => togglePinCompany(c.id)}
                              title={isPinned ? "Unpin entity" : "Pin entity to top"}
                              className={`p-1 rounded text-xs transition ${
                                isPinned ? "text-cyan-400" : "text-slate-400 hover:text-white"
                              }`}
                            >
                              📌
                            </button>
                            <button
                              type="button"
                              onClick={() => handleCompareClick(c)}
                              title="Compare target"
                              className={`p-1 rounded text-xs transition ${
                                isComparing ? "text-purple-400 font-bold" : "text-slate-400 hover:text-white"
                              }`}
                            >
                              ⚖️
                            </button>
                          </div>
                        </div>

                        {/* Metrics Bar */}
                        <div className="mt-2.5 flex items-center justify-between border-t border-slate-800/80 pt-2 text-[10px] font-mono">
                          <span className="text-slate-400">
                            {c.assets_count ?? 0} assets
                          </span>
                          {c.signals_count && c.signals_count > 0 ? (
                            <span className="text-amber-400 font-bold">
                              {c.signals_count} signals
                            </span>
                          ) : (
                            <span className="text-emerald-400">
                              {c.bug_bounty_url ? "BOUNTY" : "OBSERVED"}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
