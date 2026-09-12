"use client";

/**
 * VerifiedTelemetryHub — Production Verification Intelligence Hub
 *
 * Replaces TrackedAssetsOrbitalHub + the "SINCE 1H" left card.
 * Fetches all metrics from /api/v1/verification/telemetry with skipCache=true.
 *
 * RULES (non-negotiable):
 * - Every number is a live DB query result. No default 324. No default 1436. No 99.4%.
 * - If the API returns 0, we display 0.
 * - If the API is unavailable, all values show "—" with VERIFICATION UNAVAILABLE.
 * - Never use localStorage as a fallback for verification data.
 * - AI output cannot make a claim VERIFIED.
 * - "Truth is more important than visual completeness."
 */

import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
} from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { VerificationTelemetry } from "@/lib/types";
import VerificationOrbitalGraph from "./VerificationOrbitalGraph";
import VerificationEvidenceDrawer from "./VerificationEvidenceDrawer";
import { VerificationNode } from "./VerificationMetricNode";
import { VerificationState } from "./VerificationStatusBadge";

type TimeWindow = "10M" | "1H" | "24H" | "7D";

const WINDOW_HOURS: Record<TimeWindow, number> = {
  "10M": 0.167,  // ~10 minutes (will be rounded to 1h on API but filtered client-side)
  "1H": 1,
  "24H": 24,
  "7D": 168,
};

interface VerifiedTelemetryHubProps {
  /** Live diffs count from parent dashboard (from /api/v1/changes — real DB value) */
  recentDiffsCount?: number | null;
  /** Time filter controlled by parent or internal state */
  initialWindow?: TimeWindow;
  className?: string;
}

// Build orbital nodes from telemetry data
function buildNodes(
  telemetry: VerificationTelemetry | null,
  isMobile: boolean,
): VerificationNode[] {
  // Mobile: show 4 nodes (skip HISTORICAL slots at bottom)
  const allNodes: VerificationNode[] = [
    {
      id: 0,
      angle: 0,   // 12 o'clock
      title: "VERIFIED COVERAGE",
      subtitle: "Direct + Corroborated",
      value: telemetry
        ? (telemetry.verified_count ?? 0) + (telemetry.observed_count ?? 0)
        : null,
      state: "VERIFIED" as VerificationState,
      accentColor: "emerald",
      href: "/targets",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      ),
    },
    {
      id: 1,
      angle: 60,  // 2 o'clock
      title: "RECENT DIFFS",
      subtitle: "Detected Changes",
      value: telemetry ? (telemetry.recent_diffs_count ?? null) : null,
      state: "OBSERVED" as VerificationState,
      accentColor: "cyan",
      href: "/changes",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
    },
    {
      id: 2,
      angle: 120, // 4 o'clock
      title: "DIRECT OBS",
      subtitle: "Raw Snapshots",
      value: telemetry ? (telemetry.direct_observations_count ?? null) : null,
      state: "OBSERVED" as VerificationState,
      accentColor: "blue",
      href: "/changes",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
        </svg>
      ),
    },
    {
      id: 3,
      angle: 180, // 6 o'clock
      title: "CORROBORATED",
      subtitle: "Multi-Source",
      value: telemetry ? (telemetry.corroborated_count ?? null) : null,
      state: "CORROBORATED" as VerificationState,
      accentColor: "amber",
      href: "/companies",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      ),
    },
    {
      id: 4,
      angle: 240, // 8 o'clock
      title: "UNVERIFIED",
      subtitle: "Failed Checks",
      value: telemetry ? (telemetry.unverified_count ?? null) : null,
      state: "UNVERIFIED" as VerificationState,
      accentColor: "slate",
      href: "/changes",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    {
      id: 5,
      angle: 300, // 10 o'clock
      title: "CONFLICTING",
      subtitle: "Rate Limited",
      value: telemetry ? (telemetry.conflicting_count ?? null) : null,
      state: "CONFLICTING" as VerificationState,
      accentColor: "rose",
      href: "/changes",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
    },
  ];

  // On mobile, show only 4 nodes (0, 1, 3, 4 at equal spacing)
  if (isMobile) {
    const mobileAngles = [0, 90, 180, 270];
    return allNodes.slice(0, 4).map((n, i) => ({ ...n, angle: mobileAngles[i] }));
  }

  return allNodes;
}

export default function VerifiedTelemetryHub({
  recentDiffsCount,
  initialWindow = "1H",
  className = "",
}: VerifiedTelemetryHubProps) {
  const [telemetry, setTelemetry] = useState<VerificationTelemetry | null>(null);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);
  const [timeWindow, setTimeWindow] = useState<TimeWindow>(initialWindow);
  const [activeNode, setActiveNode] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Responsive detection
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const fetchTelemetry = useCallback(async (hours: number) => {
    try {
      setUnavailable(false);
      // Always skipCache for verification data
      const data = await apiFetch<VerificationTelemetry>(
        `/api/v1/verification/telemetry?hours=${hours}`,
        { skipCache: true }
      );
      setTelemetry(data);
    } catch {
      // On failure: show unavailable state, keep previous data if any
      setUnavailable(true);
      // Do NOT set telemetry to a fake value
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch when window changes
  useEffect(() => {
    setLoading(true);
    const hours = Math.max(1, Math.round(WINDOW_HOURS[timeWindow]));
    fetchTelemetry(hours);

    // Refresh every 30 seconds (page visibility aware)
    if (refreshTimer.current) clearInterval(refreshTimer.current);
    refreshTimer.current = setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState === "visible") {
        fetchTelemetry(hours);
      }
    }, 30_000);

    return () => {
      if (refreshTimer.current) clearInterval(refreshTimer.current);
    };
  }, [timeWindow, fetchTelemetry]);

  const nodes = useMemo(() => buildNodes(telemetry, isMobile), [telemetry, isMobile]);

  const activeNodeData = activeNode !== null ? nodes.find((n) => n.id === activeNode) : null;

  // Summary metrics for the header bar
  const diffCount = recentDiffsCount ?? telemetry?.recent_diffs_count ?? null;
  const avgConf =
    telemetry?.avg_confidence_pct != null
      ? `${telemetry.avg_confidence_pct.toFixed(1)}%`
      : null;
  const coverage =
    telemetry?.coverage_pct != null
      ? `${telemetry.coverage_pct.toFixed(1)}%`
      : null;
  const companyCount = telemetry?.company_registry_count ?? null;

  return (
    <div
      className={`relative w-full overflow-hidden rounded-3xl border border-slate-800/90 bg-[#07090e]/95 shadow-2xl backdrop-blur-2xl ${className}`}
      aria-label="Intelligence Telemetry Hub"
    >
      {/* ── Header bar ──────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 px-5 pt-4 pb-3">
        <div className="min-w-0">
          {/* Badge */}
          <div className="flex items-center gap-2 mb-1">
            <span
              className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#22d3ee]"
              aria-hidden="true"
            />
            <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-cyan-300">
              INTELLIGENCE TELEMETRY HUB
            </span>
          </div>

          {/* Primary metric: live diff count, shown directly under heading */}
          <div className="flex items-baseline gap-2 mt-0.5">
            {loading && diffCount === null ? (
              <div className="h-8 w-16 rounded-lg bg-slate-800/60 animate-pulse" aria-label="Loading count" />
            ) : (
              <span
                className="font-mono text-3xl font-black text-white tabular-nums"
                aria-label={`${diffCount ?? "—"} changes in window`}
              >
                {diffCount === null ? "—" : diffCount.toLocaleString()}
              </span>
            )}
            <span className="font-mono text-xs text-slate-400 uppercase tracking-wider">
              DIFFS • {timeWindow}
            </span>
            {unavailable && (
              <span
                className="font-mono text-[9px] text-rose-400/80 uppercase tracking-wider border border-rose-800/50 bg-rose-950/30 px-1.5 py-0.5 rounded-lg"
                role="alert"
                aria-live="polite"
              >
                VERIFICATION UNAVAILABLE
              </span>
            )}
          </div>
        </div>

        {/* Right: secondary metrics + time filter */}
        <div className="flex flex-col items-end gap-2">
          {/* Secondary metric chips */}
          <div className="flex items-center gap-3 font-mono text-[10px] text-slate-500">
            {companyCount !== null && (
              <span>
                <strong className="text-slate-300">{companyCount.toLocaleString()}</strong> registry
              </span>
            )}
            {avgConf && (
              <span>
                <strong className="text-slate-300">{avgConf}</strong> avg conf
              </span>
            )}
            {coverage && (
              <span>
                <strong className="text-slate-300">{coverage}</strong> coverage
              </span>
            )}
          </div>

          {/* Temporal filter pills */}
          <div className="flex items-center gap-1" role="group" aria-label="Time window selector">
            {(["10M", "1H", "24H", "7D"] as TimeWindow[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setTimeWindow(tab)}
                aria-pressed={timeWindow === tab}
                className={`rounded-xl px-3 py-1 text-[10px] font-mono font-bold transition-all
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/80
                  ${
                    timeWindow === tab
                      ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20 scale-105"
                      : "bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700"
                  }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Orbital Graph ──────────────────────────────────────────── */}
      <div className="px-4 py-2">
        {loading && !telemetry ? (
          // Skeleton state
          <div
            className="flex items-center justify-center"
            style={{ minHeight: isMobile ? 360 : 520 }}
            aria-label="Loading orbital graph"
            aria-busy="true"
          >
            <div className="space-y-3 w-48 text-center">
              <div className="w-20 h-20 rounded-full bg-slate-800/60 animate-pulse mx-auto" />
              <div className="h-2 rounded bg-slate-800/60 animate-pulse" />
              <div className="h-2 rounded bg-slate-800/60 animate-pulse w-3/4 mx-auto" />
            </div>
          </div>
        ) : (
          <VerificationOrbitalGraph
            nodes={nodes}
            activeNode={activeNode}
            onNodeClick={(id) => {
              setActiveNode((prev) => (prev === id ? null : id));
              setDrawerOpen(true);
            }}
            isMobile={isMobile}
            unavailable={unavailable && !telemetry}
          />
        )}
      </div>

      {/* ── Footer: quick stats bar ─────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-slate-800/60 px-5 py-2.5">
        <FooterStat
          label="AUTHORIZED TARGETS"
          value={telemetry?.authorized_targets_count ?? null}
          href="/targets"
        />
        <FooterStat
          label="ACTIVE SIGNALS"
          value={telemetry?.active_signals_count ?? null}
          href="/research"
        />
        <FooterStat
          label="VERIFIED"
          value={telemetry?.verified_count ?? null}
          color="emerald"
        />
        <FooterStat
          label="UNVERIFIED"
          value={telemetry?.unverified_count ?? null}
          color="slate"
        />

        <span className="ml-auto font-mono text-[9px] text-slate-600 uppercase tracking-widest">
          ORBITAL DIFF ARCHITECTURE
        </span>
      </div>

      {/* ── Evidence Drawer ─────────────────────────────────────────── */}
      <VerificationEvidenceDrawer
        claimId={null}  // Nodes show aggregate counts; no single claim ID
        isOpen={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setActiveNode(null);
        }}
        nodeTitle={activeNodeData?.title}
        nodeValue={
          activeNodeData?.value != null
            ? activeNodeData.value.toLocaleString()
            : "—"
        }
      />
    </div>
  );
}

// Footer stat chip
function FooterStat({
  label,
  value,
  href,
  color = "cyan",
}: {
  label: string;
  value: number | null;
  href?: string;
  color?: string;
}) {
  const colorMap: Record<string, string> = {
    cyan: "text-cyan-300",
    emerald: "text-emerald-300",
    amber: "text-amber-300",
    slate: "text-slate-400",
    rose: "text-rose-300",
  };
  const textColor = colorMap[color] ?? colorMap.cyan;

  const inner = (
    <span className="flex items-center gap-1.5 font-mono text-[9px] text-slate-500 hover:text-slate-300 transition-colors">
      <strong className={`text-[10px] font-black tabular-nums ${textColor}`}>
        {value === null ? "—" : value.toLocaleString()}
      </strong>
      <span className="uppercase tracking-widest">{label}</span>
    </span>
  );

  return href ? <Link href={href}>{inner}</Link> : inner;
}
