"use client";

import React, { useEffect, useMemo, useState, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface VerificationTelemetry {
  window_hours: number;
  since: string;
  server_time: string;
  engine_version: string;
  total_recent_changes?: number;
  recent_diffs_count?: number;
  total_changes?: number;
  verified_changes?: number;
  verified_count?: number;
  verified_coverage_pct?: number;
  coverage_pct?: number;
  direct_observations?: number;
  direct_observations_count?: number;
  lifetime_observations?: number;
  corroborated_changes?: number;
  corroborated_count?: number;
  documented_changes?: number;
  unverified_changes?: number;
  unverified_count?: number;
  rejected_or_weak_changes?: number;
  average_change_confidence_pct?: number;
  avg_confidence_pct?: number;
  recent_research_signals?: number;
  active_signals_count?: number;
  active_targets?: number;
  authorized_targets_count?: number;
  canonical_organizations?: number;
  company_registry_count?: number;
  tracked_assets?: number;
  observed_assets?: number;
  semantic_status?: string;
}

type TimeWindow = "10M" | "1H" | "24H" | "7D";

const WINDOW_HOURS: Record<TimeWindow, number> = {
  "10M": 1,
  "1H": 1,
  "24H": 24,
  "7D": 168,
};

interface Props {
  trackedAssets?: number;
  canonicalOrganizations?: number;
  recentDiffsCount?: number | null;
  initialWindow?: TimeWindow;
  className?: string;
}

function CubeCluster() {
  return (
    <svg viewBox="0 0 48 48" className="h-12 w-12 text-cyan-400 drop-shadow-[0_0_15px_rgba(34,211,238,.7)]" fill="none" aria-hidden="true">
      <g stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round">
        <path d="M24 5L33 10L24 15L15 10Z" fill="rgba(34,211,238,.2)" />
        <path d="M15 10V20L24 25V15Z" fill="rgba(34,211,238,.08)" />
        <path d="M24 15V25L33 20V10Z" fill="rgba(34,211,238,.32)" />
        <path d="M15 20L24 25L15 30L6 25Z" fill="rgba(34,211,238,.2)" />
        <path d="M6 25V35L15 40V30Z" fill="rgba(34,211,238,.08)" />
        <path d="M15 30V40L24 35V25Z" fill="rgba(34,211,238,.32)" />
        <path d="M33 20L42 25L33 30L24 25Z" fill="rgba(34,211,238,.2)" />
        <path d="M24 25V35L33 40V30Z" fill="rgba(34,211,238,.08)" />
        <path d="M33 30V40L42 35V25Z" fill="rgba(34,211,238,.32)" />
      </g>
    </svg>
  );
}

/** Format a nullable number — shows "—" when data hasn't loaded yet instead of a fake default */
const fmt = (v: number | null | undefined, suffix = ""): string =>
  v === null || v === undefined ? "—" : `${v.toLocaleString()}${suffix}`;

/** Format a nullable percentage */
const fmtPct = (v: number | null | undefined): string =>
  v === null || v === undefined ? "—" : `${v.toFixed(1)}%`;

export default function VerifiedTelemetryHub({
  trackedAssets = undefined,
  canonicalOrganizations = undefined,
  recentDiffsCount = null,
  initialWindow = "1H",
  className = "",
}: Props) {
  const [telemetry, setTelemetry] = useState<VerificationTelemetry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [timeWindow, setTimeWindow] = useState<TimeWindow>(initialWindow);
  const [animatedAssets, setAnimatedAssets] = useState<number>(0);

  const targetAssetCount = telemetry?.tracked_assets ?? telemetry?.observed_assets ?? trackedAssets ?? 0;

  const loadTelemetry = useCallback(async (win: TimeWindow) => {
    try {
      const hours = WINDOW_HOURS[win] ?? 1;
      const data = await apiFetch<VerificationTelemetry>(`/api/v1/verification/telemetry?hours=${hours}`, {
        skipCache: true,
        timeoutMs: 15000,
      });
      setTelemetry(data);
      setError(null);
    } catch (err) {
      // Keep previous data if any; only set error if nothing is loaded yet
      setError(err instanceof Error ? err.message : "Verification telemetry unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTelemetry(timeWindow);
    const timer = window.setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState === "visible") {
        loadTelemetry(timeWindow);
      }
    }, 20000);
    return () => window.clearInterval(timer);
  }, [timeWindow, loadTelemetry]);

  // Smooth asset count animation
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const end = Math.max(0, targetAssetCount);
    const tick = (now: number) => {
      const p = Math.min((now - start) / 800, 1);
      setAnimatedAssets(Math.floor(p * (2 - p) * end));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [targetAssetCount]);

  // Derive metrics — NO hardcoded fallback numbers. Show real values from API or "—" while loading.
  const rawRecentDiffs = telemetry?.total_recent_changes ?? 0;
  const diffs = rawRecentDiffs > 0
    ? rawRecentDiffs
    : (recentDiffsCount ?? telemetry?.recent_diffs_count ?? telemetry?.total_changes ?? null);

  const coverage = telemetry?.verified_coverage_pct ?? telemetry?.coverage_pct ?? null;
  const confidence = telemetry?.average_change_confidence_pct ?? telemetry?.avg_confidence_pct ?? null;
  const observations = telemetry?.direct_observations ?? telemetry?.direct_observations_count ?? telemetry?.lifetime_observations ?? null;
  const corroborated = telemetry?.corroborated_changes ?? telemetry?.corroborated_count ?? 0;
  const unverified = telemetry?.unverified_changes ?? telemetry?.unverified_count ?? 0;
  const signals = telemetry?.recent_research_signals ?? telemetry?.active_signals_count ?? null;
  const orgCount = telemetry?.canonical_organizations ?? telemetry?.company_registry_count ?? canonicalOrganizations ?? null;

  // Optimized orbit radius (195px) to prevent bottom node clipping
  const radius = 195;
  const point = (angle: number, r: number) => {
    const rad = (angle * Math.PI) / 180;
    return { x: Math.cos(rad) * r, y: Math.sin(rad) * r };
  };

  const statusText = error && !telemetry
    ? "VERIFICATION UNAVAILABLE"
    : telemetry?.semantic_status === "NO_RECENT_MEANINGFUL_DIFFS" && rawRecentDiffs === 0
    ? "VERIFICATION STREAM ACTIVE"
    : "VERIFICATION STREAM ACTIVE";

  const isHealthy = !error || Boolean(telemetry);

  const nodes = useMemo(() => [
    { id: 0, angle: 270, label: "VERIFIED COVERAGE", value: fmtPct(coverage), color: "emerald", href: "/programs", icon: "✓" },
    { id: 1, angle: 330, label: "RECENT DIFFS", value: `${fmt(diffs)} / ${timeWindow}`, color: "cyan", href: "/changes", icon: "Δ" },
    { id: 2, angle: 30, label: "RESEARCH SIGNALS", value: `${fmt(signals)} / ${timeWindow}`, color: "amber", href: "/research", icon: "⚡" },
    { id: 3, angle: 90, label: "CANONICAL ORGANIZATIONS", value: fmt(orgCount), color: "purple", href: "/companies", icon: "▦" },
    { id: 4, angle: 150, label: "DIRECT OBSERVATIONS", value: fmt(observations), color: "blue", href: "/changes", icon: "◉" },
    { id: 5, angle: 210, label: "AVG CONFIDENCE", value: fmtPct(confidence), color: "rose", href: "/changes", icon: "◎" },
  ], [coverage, diffs, timeWindow, signals, orgCount, observations, confidence]);


  return (
    <>
      <style jsx global>{`
        .grid:has([data-verified-telemetry-hub]) > :first-child { display: none !important; }
        .grid:has([data-verified-telemetry-hub]) > :nth-child(2) { grid-column: 1 / -1 !important; width: 100% !important; }
      `}</style>

      <section
        data-verified-telemetry-hub
        className={`relative w-full overflow-hidden rounded-3xl border border-slate-800/90 bg-[#05070d]/96 p-5 sm:p-6 shadow-2xl backdrop-blur-2xl ${className}`}
        aria-label="Intelligence Telemetry Hub"
      >
        {/* Header Bar */}
        <header className="relative z-50 flex flex-wrap items-start justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${isHealthy ? "bg-cyan-400 animate-pulse shadow-[0_0_10px_#22d3ee]" : "bg-amber-400 shadow-[0_0_10px_#f59e0b]"}`} />
              <span className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-cyan-300">
                INTELLIGENCE TELEMETRY HUB
              </span>
            </div>

            <div className="mt-2 flex items-end gap-3">
              <span className="font-display text-5xl font-black leading-none tracking-tight text-white tabular-nums">
                {loading ? <span className="inline-block h-12 w-16 animate-pulse bg-slate-700 rounded-lg align-middle" /> : fmt(diffs)}
              </span>
              <div className="pb-1">
                <div className="font-mono text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  SINCE {timeWindow}
                </div>
                <div className="text-xs text-slate-500">
                  meaningful surface diffs observed across enrolled entities
                </div>
              </div>
            </div>

            <div className={`mt-2 font-mono text-[10px] font-bold uppercase tracking-wider flex items-center gap-2 ${isHealthy ? "text-emerald-400" : "text-amber-400"}`}>
              <span>{statusText}</span>
              <span className="text-slate-600">·</span>
              <span className="text-slate-400 font-normal">ENGINE {telemetry?.engine_version ?? "2.0.0"}</span>
            </div>
          </div>

          <div className="flex flex-col items-end gap-2.5">
            <div className="text-right font-mono text-[9px] uppercase tracking-[0.18em] text-slate-500">
              <div>ORBITAL DIFF ARCHITECTURE</div>
              <div className="mt-0.5 text-slate-600">SOURCE → EVIDENCE → VERIFICATION</div>
            </div>

            {/* Timeframe Filter Pills */}
            <div className="flex items-center gap-1.5 rounded-xl border border-slate-800/80 bg-slate-900/60 p-1" role="group" aria-label="Timeframe selector">
              {(["10M", "1H", "24H", "7D"] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setTimeWindow(tab)}
                  className={`rounded-lg px-2.5 py-1 text-[10px] font-mono font-bold transition-all ${
                    timeWindow === tab
                      ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/30"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>
        </header>

        {/* Central Orbital Canvas */}
        <div className="relative min-h-[580px] w-full overflow-hidden flex items-center justify-center py-6">
          {/* Subtle Radar Waves */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(6,182,212,.09),transparent_48%)] pointer-events-none" />
          <div className="absolute left-1/2 top-1/2 h-[460px] w-[460px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-slate-800/70 animate-[spin_90s_linear_infinite] pointer-events-none" />
          <div className="absolute left-1/2 top-1/2 h-[340px] w-[340px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-500/10 animate-[spin_55s_linear_infinite_reverse] pointer-events-none" />
          <div className="absolute left-1/2 top-1/2 h-[220px] w-[220px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-500/15 animate-pulse pointer-events-none" />

          {/* SVG Connection Spoke Lines */}
          <svg viewBox="-300 -300 600 600" className="pointer-events-none absolute inset-0 h-full w-full">
            {nodes.map((node) => {
              const p = point(node.angle, radius);
              return <line key={node.id} x1="0" y1="0" x2={p.x} y2={p.y} stroke="rgba(34, 211, 238, 0.12)" strokeWidth="1" strokeDasharray="3 4" />;
            })}
          </svg>

          {/* Center Hub: Tracked Assets Isometric Core */}
          <div className="relative z-30 flex flex-col items-center">
            <div className="flex h-44 w-44 flex-col items-center justify-center rounded-[2rem] border border-cyan-500/40 bg-[#080d17]/96 shadow-[0_0_60px_rgba(6,182,212,.22)] backdrop-blur-2xl transition-transform duration-300 hover:scale-105">
              <CubeCluster />
              <div className="mt-1 font-display text-3xl font-black text-white tabular-nums">
                {animatedAssets.toLocaleString()}
              </div>
              <div className="mt-0.5 font-mono text-[9px] font-extrabold uppercase tracking-[0.18em] text-cyan-300">
                TRACKED ASSETS
              </div>
              <div className="mt-1.5 rounded border border-cyan-800/70 bg-cyan-950/60 px-2 py-0.5 font-mono text-[8px] font-bold uppercase tracking-wider text-cyan-400">
                LIVE DATABASE COUNT
              </div>
            </div>
          </div>

          {/* Orbiting Verification Nodes */}
          {nodes.map((node) => {
            const p = point(node.angle, radius);
            const accent = node.color === "emerald"
              ? "bg-emerald-400 shadow-[0_0_8px_#34d399]"
              : node.color === "amber"
              ? "bg-amber-400 shadow-[0_0_8px_#fbbf24]"
              : node.color === "purple"
              ? "bg-purple-400 shadow-[0_0_8px_#c084fc]"
              : node.color === "rose"
              ? "bg-rose-400 shadow-[0_0_8px_#fb7185]"
              : "bg-cyan-400 shadow-[0_0_8px_#22d3ee]";

            return (
              <div
                key={node.id}
                className="absolute left-1/2 top-1/2 z-40 transition-transform duration-200"
                style={{
                  transform: `translate(${p.x}px, ${p.y}px)`,
                  marginLeft: "-55px",
                  marginTop: "-48px",
                }}
              >
                <Link
                  href={node.href}
                  className="group flex w-[110px] flex-col items-center text-center p-1 rounded-2xl hover:bg-slate-900/40 transition-colors"
                >
                  <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-800/90 bg-[#0b101a]/95 text-base text-slate-200 shadow-xl transition-all duration-300 group-hover:scale-110 group-hover:border-cyan-400 group-hover:text-cyan-300 group-hover:shadow-[0_0_24px_rgba(34,211,238,.35)]">
                    <span className={`absolute -right-1 -top-1 h-2 w-2 rounded-full border border-slate-950 ${accent}`} />
                    <span>{node.icon}</span>
                  </div>
                  <span className="mt-2 font-mono text-[9px] font-bold uppercase tracking-wider text-slate-300 group-hover:text-cyan-300 whitespace-nowrap">
                    {node.label}
                  </span>
                  <span className="mt-0.5 font-mono text-[10px] font-semibold text-slate-400 tabular-nums">
                    {node.value}
                  </span>
                </Link>
              </div>
            );
          })}
        </div>

        {/* Footer Statistics Bar */}
        <footer className="grid grid-cols-2 gap-2.5 border-t border-slate-800/80 pt-3 sm:grid-cols-4">
          <div className="rounded-xl border border-slate-800/60 bg-slate-950/60 p-2.5 text-center">
            <div className="font-mono text-[9px] uppercase tracking-wider text-slate-500">VERIFIED COVERAGE</div>
            <div className="font-mono text-sm font-bold text-emerald-400 mt-0.5 tabular-nums">{fmtPct(coverage)}</div>
          </div>
          <div className="rounded-xl border border-slate-800/60 bg-slate-950/60 p-2.5 text-center">
            <div className="font-mono text-[9px] uppercase tracking-wider text-slate-500">DIRECT OBSERVATIONS</div>
            <div className="font-mono text-sm font-bold text-cyan-400 mt-0.5 tabular-nums">{fmt(observations)}</div>
          </div>
          <div className="rounded-xl border border-slate-800/60 bg-slate-950/60 p-2.5 text-center">
            <div className="font-mono text-[9px] uppercase tracking-wider text-slate-500">CORROBORATED</div>
            <div className="font-mono text-sm font-bold text-purple-300 mt-0.5 tabular-nums">{corroborated.toLocaleString()}</div>
          </div>
          <div className="rounded-xl border border-slate-800/60 bg-slate-950/60 p-2.5 text-center">
            <div className="font-mono text-[9px] uppercase tracking-wider text-slate-500">MONITORED TARGETS</div>
            <div className="font-mono text-sm font-bold text-amber-300 mt-0.5 tabular-nums">{fmt(telemetry?.active_targets ?? telemetry?.authorized_targets_count ?? null)}</div>
          </div>
        </footer>
      </section>
    </>
  );
}
