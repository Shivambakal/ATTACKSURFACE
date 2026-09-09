"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import {
  Company,
  CompanyAsset,
  Product,
  CompanyApi,
  CompanyFeature,
  ResearchSignal,
  SecurityProgram,
  TimelineEvent,
} from "@/lib/types";
import TemporalTimeMachine from "@/components/TemporalTimeMachine";
import { CardTilt3D, SeverityBadge } from "@/components/ui/InteractionPrimitives";

interface CompanyIntelligenceEnvironmentProps {
  company: Company;
  products: Product[];
  assets: CompanyAsset[];
  apis: CompanyApi[];
  features: CompanyFeature[];
  signals: ResearchSignal[];
  timelineEvents: TimelineEvent[];
  programs: SecurityProgram[];
  bugs?: any[];
}

type EntityLayer = "ALL" | "PRODUCTS" | "DOMAINS" | "APIS" | "VULNS" | "SIGNALS";

interface FocalTarget {
  type: "COMPANY" | "PRODUCT" | "DOMAIN" | "API" | "VULN" | "SIGNAL";
  id: string;
  name: string;
  meta?: any;
}

export default function CompanyIntelligenceEnvironment({
  company,
  products = [],
  assets = [],
  apis = [],
  features = [],
  signals = [],
  timelineEvents = [],
  programs = [],
  bugs = [],
}: CompanyIntelligenceEnvironmentProps) {
  const [activeLayer, setActiveLayer] = useState<EntityLayer>("ALL");
  const [focalTarget, setFocalTarget] = useState<FocalTarget>({
    type: "COMPANY",
    id: String(company.id),
    name: company.name,
    meta: company,
  });
  const [selectedYear, setSelectedYear] = useState<string>("NOW");
  const [searchFilter, setSearchFilter] = useState<string>("");
  const [historicalPulse, setHistoricalPulse] = useState<string | null>(null);

  // Trigger historical pulse animation across environment
  const handleEventPulse = (ev: TimelineEvent) => {
    setHistoricalPulse(ev.title || "Historical Observation");
    setTimeout(() => setHistoricalPulse(null), 1800);
  };

  // Filter assets by temporal position
  const visibleAssets = useMemo(() => {
    if (selectedYear === "ALL" || selectedYear === "NOW") return assets;
    const yearNum = parseInt(selectedYear, 10);
    return assets.filter((a) => {
      const dateStr = a.discovered_at || a.last_seen_at || (a as any).created_at;
      if (!dateStr) return true;
      try {
        const aYr = new Date(dateStr).getFullYear();
        return aYr <= yearNum;
      } catch {
        return true;
      }
    });
  }, [assets, selectedYear]);

  // Contextual relevance computation:
  // When a focal target is selected (e.g. an API), determine which other entities are directly related
  const isEntityRelevant = (type: string, id: string | number, name: string) => {
    if (focalTarget.type === "COMPANY") return true; // everything in scope

    const focalName = (focalTarget.name || "").toLowerCase();
    const targetName = (name || "").toLowerCase();

    if (focalTarget.type === "API") {
      // Related if matching asset domain or path
      if (type === "DOMAIN" && (focalName.includes(targetName) || targetName.includes(focalName))) return true;
      if (type === "PRODUCT") return true;
      return type === "API" && String(id) === focalTarget.id;
    }

    if (focalTarget.type === "PRODUCT") {
      if (type === "API" || type === "FEATURE") return true;
      if (type === "DOMAIN" && (targetName.includes(focalName) || focalName.includes(targetName))) return true;
      return type === "PRODUCT" && String(id) === focalTarget.id;
    }

    if (focalTarget.type === "DOMAIN") {
      if (type === "API") return true;
      return type === "DOMAIN" && String(id) === focalTarget.id;
    }

    return true;
  };

  return (
    <div className="relative space-y-6">
      {/* ── TOP AMBIENT CONTROL HUD ───────────────────────────── */}
      <div className="rounded-2xl border border-slate-800 bg-slate-950/85 p-5 shadow-2xl backdrop-blur-xl space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-cyan-500/10 border border-cyan-400/50 text-cyan-300 font-mono font-bold text-lg shadow-[0_0_25px_rgba(0,240,255,0.25)]">
              {company.name.slice(0, 2).toUpperCase()}
              <span className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-cyan-400 animate-ping" />
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-extrabold text-white tracking-tight font-display">
                  {company.name}
                </h1>
                <span className="rounded bg-cyan-950/80 px-2 py-0.5 font-mono text-xs font-semibold text-cyan-400 border border-cyan-800/60">
                  {company.canonical_domain}
                </span>
                {company.bug_bounty_url && (
                  <span className="rounded bg-emerald-950/80 px-2 py-0.5 font-mono text-xs font-bold text-emerald-400 border border-emerald-800/60">
                    PUBLIC BOUNTY
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Contextual Spatial Navigation • Active Focal Center:{" "}
                <strong className="text-cyan-300 font-mono">
                  [{focalTarget.type}] {focalTarget.name}
                </strong>
              </p>
            </div>
          </div>

          {/* Focal Reset & Isolation Controls */}
          <div className="flex flex-wrap items-center gap-2">
            {focalTarget.type !== "COMPANY" && (
              <button
                type="button"
                onClick={() =>
                  setFocalTarget({
                    type: "COMPANY",
                    id: String(company.id),
                    name: company.name,
                    meta: company,
                  })
                }
                className="rounded-xl border border-cyan-400/50 bg-cyan-950/80 px-3.5 py-1.5 font-mono text-xs font-bold text-cyan-300 hover:bg-cyan-900/80 transition flex items-center gap-1.5 shadow-[0_0_15px_rgba(0,240,255,0.15)]"
              >
                <span>↺ RESET FOCAL CENTER</span>
              </button>
            )}

            <div className="flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800 font-mono text-xs">
              {(["ALL", "PRODUCTS", "DOMAINS", "APIS", "VULNS", "SIGNALS"] as const).map(
                (layer) => (
                  <button
                    key={layer}
                    onClick={() => setActiveLayer(layer)}
                    className={`px-2.5 py-1 rounded-lg transition ${
                      activeLayer === layer
                        ? "bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/20"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {layer}
                  </button>
                )
              )}
            </div>
          </div>
        </div>

        {/* Historical Pulse Shockwave Alert */}
        {historicalPulse && (
          <div className="animate-surface-in flex items-center gap-2 rounded-xl border border-purple-500/50 bg-purple-950/40 p-2.5 text-xs font-mono text-purple-200">
            <span className="animate-ping h-2 w-2 rounded-full bg-purple-400" />
            <span>HISTORICAL TELEMETRY PULSE: {historicalPulse}</span>
          </div>
        )}
      </div>

      {/* ── CONTEXTUAL SPATIAL INFORMATION MATRIX ───────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* COL 1: Products & Public Program Scope */}
        {(activeLayer === "ALL" || activeLayer === "PRODUCTS") && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-800/90 bg-slate-950/70 p-4 backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#10b981]" />
                  <h3 className="font-mono text-xs font-bold uppercase text-slate-200 tracking-wider">
                    Products &amp; Platforms ({products.length})
                  </h3>
                </div>
              </div>

              <div className="mt-3 space-y-2 max-h-72 overflow-y-auto pr-1 scrollbar-thin">
                {products.length === 0 ? (
                  <div className="p-4 text-center font-mono text-xs text-slate-500">
                    No discrete products indexed
                  </div>
                ) : (
                  products.map((prod) => {
                    const isFocus = focalTarget.type === "PRODUCT" && focalTarget.id === String(prod.id);
                    const isRelevant = isEntityRelevant("PRODUCT", prod.id, prod.name);

                    return (
                      <div
                        key={prod.id}
                        onClick={() =>
                          setFocalTarget({
                            type: "PRODUCT",
                            id: String(prod.id),
                            name: prod.name,
                            meta: prod,
                          })
                        }
                        className={`p-3 rounded-xl border cursor-pointer transition-all duration-200 ${
                          isFocus
                            ? "border-emerald-400 bg-emerald-950/40 shadow-[0_0_20px_rgba(16,185,129,0.2)] scale-[1.02]"
                            : isRelevant
                            ? "border-slate-800 bg-slate-900/50 hover:border-emerald-500/40"
                            : "border-slate-900 bg-slate-950/40 opacity-35"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-white font-display">
                            {prod.name}
                          </span>
                          <span className="rounded bg-emerald-950/60 px-1.5 py-0.2 font-mono text-[9px] font-bold text-emerald-400 border border-emerald-800/40">
                            PRODUCT
                          </span>
                        </div>
                        {prod.description && (
                          <p className="mt-1 text-[11px] text-slate-400 line-clamp-2">
                            {prod.description}
                          </p>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Scope & Bug Bounty Policy */}
            <div className="rounded-2xl border border-slate-800/90 bg-slate-950/70 p-4 backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#00f0ff]" />
                  <h3 className="font-mono text-xs font-bold uppercase text-slate-200 tracking-wider">
                    Program Scope ({programs.length})
                  </h3>
                </div>
              </div>

              <div className="mt-3 space-y-2 max-h-56 overflow-y-auto scrollbar-thin">
                {programs.length === 0 ? (
                  <div className="p-4 text-center font-mono text-xs text-slate-500">
                    Self-hosted vulnerability disclosure policy
                  </div>
                ) : (
                  programs.map((prog) => (
                    <div
                      key={prog.id}
                      className="p-3 rounded-xl border border-slate-800 bg-slate-900/40 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white">
                          {prog.program_name || prog.program_handle || prog.company_name || "Security Program"}
                        </span>
                        <span className="font-mono text-[10px] text-cyan-400">
                          {prog.platform}
                        </span>
                      </div>
                      {prog.policy_url && (
                        <a
                          href={prog.policy_url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1.5 inline-block text-[11px] font-mono text-cyan-400 hover:underline"
                        >
                          View Official Scope &rarr;
                        </a>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* COL 2: Attack Surface Assets & APIs */}
        {(activeLayer === "ALL" || activeLayer === "DOMAINS" || activeLayer === "APIS") && (
          <div className="space-y-4">
            {/* Domain & Subdomain Layer */}
            <div className="rounded-2xl border border-slate-800/90 bg-slate-950/70 p-4 backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-sky-400 shadow-[0_0_8px_#38bdf8]" />
                  <h3 className="font-mono text-xs font-bold uppercase text-slate-200 tracking-wider">
                    Surface Assets ({visibleAssets.length})
                  </h3>
                </div>
              </div>

              <div className="mt-3 space-y-2 max-h-72 overflow-y-auto pr-1 scrollbar-thin">
                {visibleAssets.length === 0 ? (
                  <div className="p-4 text-center font-mono text-xs text-slate-500">
                    No assets recorded for current temporal coordinates
                  </div>
                ) : (
                  visibleAssets.slice(0, 30).map((ast) => {
                    const isFocus = focalTarget.type === "DOMAIN" && focalTarget.id === String(ast.id);
                    const domainName = ast.hostname || ast.name || `asset-${ast.id}`;
                    const isRelevant = isEntityRelevant("DOMAIN", ast.id, domainName);

                    return (
                      <div
                        key={ast.id}
                        onClick={() =>
                          setFocalTarget({
                            type: "DOMAIN",
                            id: String(ast.id),
                            name: domainName,
                            meta: ast,
                          })
                        }
                        className={`p-2.5 rounded-xl border cursor-pointer transition-all duration-200 ${
                          isFocus
                            ? "border-sky-400 bg-sky-950/40 shadow-[0_0_20px_rgba(56,189,248,0.2)] scale-[1.02]"
                            : isRelevant
                            ? "border-slate-800 bg-slate-900/50 hover:border-sky-500/40"
                            : "border-slate-900 bg-slate-950/40 opacity-35"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs text-white truncate max-w-[200px]">
                            {domainName}
                          </span>
                          <span
                            className={`rounded px-1.5 py-0.2 font-mono text-[9px] font-bold ${
                              ast.scope_status === "IN_SCOPE"
                                ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/40"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {ast.asset_type || "SUBDOMAIN"}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* API Endpoints Surface */}
            <div className="rounded-2xl border border-slate-800/90 bg-slate-950/70 p-4 backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-purple-400 shadow-[0_0_8px_#c084fc]" />
                  <h3 className="font-mono text-xs font-bold uppercase text-slate-200 tracking-wider">
                    API Endpoints ({apis.length})
                  </h3>
                </div>
              </div>

              <div className="mt-3 space-y-2 max-h-56 overflow-y-auto scrollbar-thin">
                {apis.length === 0 ? (
                  <div className="p-4 text-center font-mono text-xs text-slate-500">
                    No external APIs recorded in graph
                  </div>
                ) : (
                  apis.map((api) => {
                    const isFocus = focalTarget.type === "API" && focalTarget.id === String(api.id);
                    const apiLabel = `${api.method ? api.method.toUpperCase() + " " : ""}${api.path || (api as any).endpoint_pattern || (api as any).name || "/api"}`;
                    const isRelevant = isEntityRelevant("API", api.id, apiLabel);

                    return (
                      <div
                        key={api.id}
                        onClick={() =>
                          setFocalTarget({
                            type: "API",
                            id: String(api.id),
                            name: apiLabel,
                            meta: api,
                          })
                        }
                        className={`p-2.5 rounded-xl border cursor-pointer transition-all duration-200 ${
                          isFocus
                            ? "border-purple-400 bg-purple-950/40 shadow-[0_0_20px_rgba(192,132,252,0.2)] scale-[1.02]"
                            : isRelevant
                            ? "border-slate-800 bg-slate-900/50 hover:border-purple-500/40"
                            : "border-slate-900 bg-slate-950/40 opacity-35"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs text-purple-300 truncate max-w-[200px]">
                            {apiLabel}
                          </span>
                          <span className="rounded bg-purple-950/60 px-1.5 py-0.2 font-mono text-[9px] font-bold text-purple-300 border border-purple-800/40">
                            {api.auth_requirement || api.method || "API"}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        )}

        {/* COL 3: Vulnerabilities & Research Signals */}
        {(activeLayer === "ALL" || activeLayer === "VULNS" || activeLayer === "SIGNALS") && (
          <div className="space-y-4">
            {/* Prioritized Signals */}
            <div className="rounded-2xl border border-slate-800/90 bg-slate-950/70 p-4 backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-amber-400 shadow-[0_0_8px_#f59e0b]" />
                  <h3 className="font-mono text-xs font-bold uppercase text-slate-200 tracking-wider">
                    Research Signals ({signals.length})
                  </h3>
                </div>
              </div>

              <div className="mt-3 space-y-2 max-h-72 overflow-y-auto pr-1 scrollbar-thin">
                {signals.length === 0 ? (
                  <div className="p-4 text-center font-mono text-xs text-slate-500">
                    No active research signals generated
                  </div>
                ) : (
                  signals.map((sig) => (
                    <div
                      key={sig.id}
                      className="p-3 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-amber-500/40 transition"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white font-display">
                          {sig.title}
                        </span>
                        <SeverityBadge severity={sig.priority || "MEDIUM"} size="sm" />
                      </div>
                      <p className="mt-1 text-[11px] text-slate-400 line-clamp-2">
                        {sig.summary}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Confirmed CVEs */}
            <div className="rounded-2xl border border-slate-800/90 bg-slate-950/70 p-4 backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-rose-500 shadow-[0_0_8px_#f43f5e]" />
                  <h3 className="font-mono text-xs font-bold uppercase text-slate-200 tracking-wider">
                    Verified Vulnerabilities ({bugs.length})
                  </h3>
                </div>
              </div>

              <div className="mt-3 space-y-2 max-h-56 overflow-y-auto scrollbar-thin">
                {bugs.length === 0 ? (
                  <div className="p-4 text-center font-mono text-xs text-slate-500">
                    No confirmed CVE records published
                  </div>
                ) : (
                  bugs.slice(0, 10).map((b: any) => (
                    <div
                      key={b.id || b.cve_id}
                      className="p-2.5 rounded-xl border border-rose-500/30 bg-rose-950/20 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-rose-300">{b.cve_id}</span>
                        <SeverityBadge severity={b.severity || "HIGH"} size="sm" />
                      </div>
                      <p className="mt-1 text-[11px] text-slate-300 line-clamp-2">
                        {b.title}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── TIME MACHINE INTEGRATION ──────────────────────────── */}
      <TemporalTimeMachine
        events={timelineEvents}
        selectedYear={selectedYear}
        onSelectYear={setSelectedYear}
        onEventPulse={handleEventPulse}
      />
    </div>
  );
}
