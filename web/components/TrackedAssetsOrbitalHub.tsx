"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface VerificationTelemetry {
  window_hours: number;
  since: string;
  server_time: string;
  engine_version: string;
  total_recent_changes: number;
  verified_changes: number;
  verified_coverage_pct: number;
  direct_observations: number;
  corroborated_changes: number;
  documented_changes: number;
  unverified_changes: number;
  rejected_or_weak_changes: number;
  average_change_confidence_pct: number;
  recent_research_signals: number;
  active_targets: number;
  semantic_status: string;
}

interface TrackedAssetsOrbitalHubProps {
  trackedAssets?: number;
  verifiedScope?: string;
  activeSignals?: number;
  actionableLeads?: string;
  companiesWatched?: number;
  canonicalOrgs?: string;
  avgConfidence?: string;
  consensusStatus?: string;
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

export default function TrackedAssetsOrbitalHub({ trackedAssets = 0, companiesWatched = 0, className = "" }: TrackedAssetsOrbitalHubProps) {
  const [telemetry, setTelemetry] = useState<VerificationTelemetry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [animatedAssets, setAnimatedAssets] = useState(0);

  const loadTelemetry = async () => {
    try {
      const data = await apiFetch<VerificationTelemetry>("/api/v1/verification/telemetry?hours=1", { skipCache: true });
      setTelemetry(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification telemetry unavailable");
    }
  };

  useEffect(() => {
    loadTelemetry();
    const timer = window.setInterval(loadTelemetry, 30000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const end = Math.max(0, trackedAssets);
    const tick = (now: number) => {
      const p = Math.min((now - start) / 900, 1);
      setAnimatedAssets(Math.floor((p * (2 - p)) * end));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [trackedAssets]);

  const diffs = telemetry?.total_recent_changes ?? 0;
  const coverage = telemetry?.verified_coverage_pct ?? 0;
  const confidence = telemetry?.average_change_confidence_pct ?? 0;
  const observations = telemetry?.direct_observations ?? 0;
  const corroborated = telemetry?.corroborated_changes ?? 0;
  const unverified = telemetry?.unverified_changes ?? 0;
  const signals = telemetry?.recent_research_signals ?? 0;

  const nodes = useMemo(() => [
    { id: 0, angle: 270, label: "VERIFIED COVERAGE", value: `${coverage.toFixed(1)}%`, color: "emerald", href: "/programs", icon: "✓" },
    { id: 1, angle: 330, label: "RECENT DIFFS", value: `${diffs} / 1H`, color: "cyan", href: "/changes", icon: "Δ" },
    { id: 2, angle: 30, label: "RESEARCH SIGNALS", value: `${signals} / 1H`, color: "amber", href: "/research", icon: "⚡" },
    { id: 3, angle: 90, label: "CANONICAL ORGANIZATIONS", value: companiesWatched.toLocaleString(), color: "purple", href: "/companies", icon: "▦" },
    { id: 4, angle: 150, label: "DIRECT OBSERVATIONS", value: observations.toLocaleString(), color: "blue", href: "/changes", icon: "◉" },
    { id: 5, angle: 210, label: "AVG CONFIDENCE", value: `${confidence.toFixed(1)}%`, color: "rose", href: "/changes", icon: "◎" },
  ], [companiesWatched, confidence, coverage, diffs, observations, signals]);

  const point = (angle: number, radius: number) => {
    const r = (angle * Math.PI) / 180;
    return { x: Math.cos(r) * radius, y: Math.sin(r) * radius };
  };
  const radius = 240;
  const status = error ? "VERIFICATION UNAVAILABLE" : diffs === 0 ? "NO RECENT MEANINGFUL DIFFS" : "VERIFICATION STREAM ACTIVE";

  return (
    <>
      <style jsx global>{`
        .grid:has([data-verified-telemetry-hub]) > :first-child { display: none !important; }
        .grid:has([data-verified-telemetry-hub]) > :nth-child(2) { grid-column: 1 / -1 !important; width: 100% !important; }
      `}</style>
      <section data-verified-telemetry-hub className={`relative w-full overflow-hidden rounded-3xl border border-slate-800/90 bg-[#05070d]/96 p-5 shadow-2xl backdrop-blur-2xl ${className}`}>
        <header className="relative z-50 flex flex-wrap items-start justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${error ? "bg-amber-400" : "bg-cyan-400 animate-pulse"} shadow-[0_0_10px_#22d3ee]`} />
              <span className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-cyan-300">INTELLIGENCE TELEMETRY HUB</span>
            </div>
            <div className="mt-2 flex items-end gap-3">
              <span className="font-display text-5xl font-black leading-none tracking-tight text-white">{diffs}</span>
              <div className="pb-1">
                <div className="font-mono text-[10px] font-bold uppercase tracking-widest text-slate-400">SINCE 1H</div>
                <div className="text-xs text-slate-500">meaningful surface diffs observed across enrolled entities</div>
              </div>
            </div>
            <div className={`mt-2 font-mono text-[9px] font-bold uppercase tracking-wider ${error ? "text-amber-300" : "text-emerald-400"}`}>
              {status} · ENGINE {telemetry?.engine_version ?? "2.0.0"}
            </div>
          </div>
          <div className="text-right font-mono text-[9px] uppercase tracking-[0.18em] text-slate-500">
            <div>ORBITAL DIFF ARCHITECTURE</div>
            <div className="mt-1 text-slate-600">SOURCE → EVIDENCE → VERIFICATION</div>
          </div>
        </header>

        <div className="relative min-h-[620px] w-full overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(6,182,212,.08),transparent_45%)]" />
          <div className="absolute left-1/2 top-1/2 h-[540px] w-[540px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-slate-800/80 animate-[spin_90s_linear_infinite]" />
          <div className="absolute left-1/2 top-1/2 h-[370px] w-[370px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-500/10 animate-[spin_55s_linear_infinite_reverse]" />
          <div className="absolute left-1/2 top-1/2 h-[250px] w-[250px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-500/10 animate-pulse" />

          <svg viewBox="-300 -300 600 600" className="pointer-events-none absolute inset-0 h-full w-full">
            {nodes.map((node) => {
              const p = point(node.angle, radius);
              return <line key={node.id} x1="0" y1="0" x2={p.x} y2={p.y} stroke="#182230" strokeWidth="1" strokeDasharray="4 5" />;
            })}
          </svg>

          <div className="absolute left-1/2 top-1/2 z-30 -translate-x-1/2 -translate-y-1/2">
            <div className="flex h-48 w-48 flex-col items-center justify-center rounded-[2.2rem] border border-cyan-500/45 bg-[#080d17]/96 shadow-[0_0_80px_rgba(6,182,212,.25)] backdrop-blur-2xl transition-transform duration-300 hover:scale-105">
              <CubeCluster />
              <div className="mt-1 font-display text-3xl font-black text-white">{animatedAssets.toLocaleString()}</div>
              <div className="mt-1 font-mono text-[9px] font-extrabold uppercase tracking-[0.18em] text-cyan-300">TRACKED ASSETS</div>
              <div className="mt-2 rounded border border-cyan-800/70 bg-cyan-950/60 px-2 py-1 font-mono text-[8px] font-bold uppercase tracking-wider text-cyan-400">LIVE DATABASE COUNT</div>
            </div>
          </div>

          {nodes.map((node) => {
            const p = point(node.angle, radius);
            const accent = node.color === "emerald" ? "bg-emerald-400" : node.color === "amber" ? "bg-amber-400" : node.color === "purple" ? "bg-purple-400" : node.color === "rose" ? "bg-rose-400" : "bg-cyan-400";
            return (
              <div key={node.id} className="absolute left-1/2 top-1/2 z-40" style={{ transform: `translate(${p.x}px, ${p.y}px)`, marginLeft: "-50px", marginTop: "-50px" }}>
                <Link href={node.href} className="group flex w-[100px] flex-col items-center text-center">
                  <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-800 bg-[#0b101a]/95 text-lg text-slate-200 shadow-xl transition-all duration-300 group-hover:scale-110 group-hover:border-cyan-400 group-hover:text-cyan-300 group-hover:shadow-[0_0_28px_rgba(34,211,238,.35)]">
                    <span className={`absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border-2 border-slate-950 ${accent}`} />
                    {node.icon}
                  </div>
                  <span className="mt-2 font-mono text-[9px] font-bold uppercase tracking-wider text-slate-300 group-hover:text-cyan-300">{node.label}</span>
                  <span className="mt-0.5 font-mono text-[9px] text-slate-500">{node.value}</span>
                </Link>
              </div>
            );
          })}
        </div>

        <footer className="grid grid-cols-2 gap-2 border-t border-slate-800/80 pt-3 sm:grid-cols-4">
          <div className="rounded-xl border border-slate-800/60 bg-slate-950/60 p-2 text-center"><div className="font-mono text-[9px] uppercase text-slate-500">VERIFIED COVERAGE</div><div className="font-mono text-xs font-bold text-emerald-400">{coverage.toFixed(1)}%</div></div>
          <div className="rounded-xl border border-slate-800/60 bg-slate-950/60 p-2 text-center"><div className="font-mono text-[9px] uppercase text-slate-500">DIRECT OBSERVATIONS</div><div className="font-mono text-xs font-bold text-cyan-400">{observations}</div></div>
          <div className="rounded-xl border border-slate-800/60 bg-slate-950/60 p-2 text-center"><div className="font-mono text-[9px] uppercase text-slate-500">CORROBORATED</div><div className="font-mono text-xs font-bold text-purple-300">{corroborated}</div></div>
          <div className="rounded-xl border border-slate-800/60 bg-slate-950/60 p-2 text-center"><div className="font-mono text-[9px] uppercase text-slate-500">UNVERIFIED</div><div className="font-mono text-xs font-bold text-amber-300">{unverified}</div></div>
        </footer>
      </section>
    </>
  );
}
