"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";

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

/**
 * Exact 3-Cubes Isometric Cluster matching the user's reference image.
 */
function IsometricThreeCubes({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      className={className}
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {/* Top Cube */}
      <path d="M24 6L32 10.5L24 15L16 10.5Z" fill="rgba(6,182,212,0.18)" stroke="#22d3ee" />
      <path d="M16 10.5V19.5L24 24V15Z" fill="rgba(6,182,212,0.08)" stroke="#22d3ee" />
      <path d="M24 15V24L32 19.5V10.5Z" fill="rgba(6,182,212,0.3)" stroke="#22d3ee" />

      {/* Bottom-Left Cube */}
      <path d="M16 20L24 24.5L16 29L8 24.5Z" fill="rgba(6,182,212,0.18)" stroke="#22d3ee" />
      <path d="M8 24.5V33.5L16 38V29Z" fill="rgba(6,182,212,0.08)" stroke="#22d3ee" />
      <path d="M16 29V38L24 33.5V24.5Z" fill="rgba(6,182,212,0.3)" stroke="#22d3ee" />

      {/* Bottom-Right Cube */}
      <path d="M32 20L40 24.5L32 29L24 24.5Z" fill="rgba(6,182,212,0.18)" stroke="#22d3ee" />
      <path d="M24 24.5V33.5L32 38V29Z" fill="rgba(6,182,212,0.08)" stroke="#22d3ee" />
      <path d="M32 29V38L40 33.5V24.5Z" fill="rgba(6,182,212,0.3)" stroke="#22d3ee" />
    </svg>
  );
}

export default function TrackedAssetsOrbitalHub({
  trackedAssets = 324,
  verifiedScope = "VERIFIED SCOPE",
  activeSignals = 0,
  actionableLeads = "ACTIONABLE LEADS",
  companiesWatched = 1436,
  canonicalOrgs = "CANONICAL ORGANIZATIONS",
  avgConfidence = "99.4%",
  consensusStatus = "CONSENSUS",
  className = "",
}: TrackedAssetsOrbitalHubProps) {
  const [activeNode, setActiveNode] = useState<number | null>(null);
  const [animatedAssets, setAnimatedAssets] = useState(0);

  // Smooth number ticker on mount
  useEffect(() => {
    let start = 0;
    const end = trackedAssets;
    const duration = 1200;
    const startTime = performance.now();

    const step = (now: number) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const easeOutQuad = (t: number) => t * (2 - t);
      setAnimatedAssets(Math.floor(easeOutQuad(progress) * end));
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };

    requestAnimationFrame(step);
  }, [trackedAssets]);

  // Orbital Satellite Nodes configuration arranged around 360 degrees
  const nodes = [
    {
      id: 0,
      angle: 270, // Top (12 o'clock)
      title: "VERIFIED SCOPE",
      subtitle: "100% Policy Match",
      value: (trackedAssets ?? 324).toLocaleString(),
      accent: "emerald",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      ),
      href: "/programs",
    },
    {
      id: 1,
      angle: 330, // Top-Right (2 o'clock)
      title: "ACTIVE SIGNALS",
      subtitle: "Temporal Stream",
      value: activeSignals > 0 ? `${activeSignals} LIVE` : "LIVE DIFFS",
      accent: "cyan",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
      href: "/changes",
    },
    {
      id: 2,
      angle: 30, // Bottom-Right (4 o'clock)
      title: "ACTIONABLE LEADS",
      subtitle: "Target Correlations",
      value: actionableLeads,
      accent: "amber",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
        </svg>
      ),
      href: "/research",
    },
    {
      id: 3,
      angle: 90, // Bottom (6 o'clock)
      title: "COMPANIES WATCHED",
      subtitle: "Monitored Programs",
      value: companiesWatched.toLocaleString(),
      accent: "purple",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      ),
      href: "/companies",
    },
    {
      id: 4,
      angle: 150, // Bottom-Left (8 o'clock)
      title: "CANONICAL ORGANIZATIONS",
      subtitle: "Verified Enrolled",
      value: `${companiesWatched.toLocaleString()} ENTITIES`,
      accent: "blue",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
        </svg>
      ),
      href: "/companies",
    },
    {
      id: 5,
      angle: 210, // Top-Left (10 o'clock)
      title: "AVG CONFIDENCE",
      subtitle: "CONSENSUS",
      value: avgConfidence,
      accent: "rose",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
        </svg>
      ),
      href: "/admin/data-truth",
    },
  ];

  // Helper to calculate X, Y on circle
  const getCoordinates = (angleDeg: number, radius: number) => {
    const rad = (angleDeg * Math.PI) / 180;
    return {
      x: Math.cos(rad) * radius,
      y: Math.sin(rad) * radius,
    };
  };

  const orbitRadius = 185; // Distance from center to satellite nodes

  return (
    <div className={`relative w-full overflow-hidden rounded-3xl border border-slate-800/90 bg-[#07090e]/95 p-6 shadow-2xl backdrop-blur-2xl ${className}`}>
      {/* ── Subtitle / Header Badge ── */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#22d3ee]" />
          <span className="font-mono text-xs font-bold uppercase tracking-wider text-cyan-300">
            INTELLIGENCE TELEMETRY HUB
          </span>
        </div>
        <span className="font-mono text-[10px] text-slate-500 uppercase tracking-widest">
          ORBITAL DIFF ARCHITECTURE
        </span>
      </div>

      {/* ── Central Orbital Canvas ── */}
      <div className="relative mx-auto flex items-center justify-center min-h-[500px] w-full max-w-[580px] py-4">
        {/* Background Radar Waves (expanding pulses) */}
        <div className="absolute h-72 w-72 rounded-full border border-cyan-500/15 animate-ping opacity-30 pointer-events-none" />
        <div className="absolute h-[380px] w-[380px] rounded-full border border-cyan-500/10 animate-pulse pointer-events-none" />

        {/* Outer Orbital Ring with animated subtle dashed rotation */}
        <div
          className="absolute h-[370px] w-[370px] rounded-full border border-dashed border-slate-800/90 pointer-events-none animate-[spin_80s_linear_infinite]"
          style={{ willChange: "transform" }}
        />

        {/* Inner Orbital Ring */}
        <div
          className="absolute h-[250px] w-[250px] rounded-full border border-slate-800/60 pointer-events-none animate-[spin_50s_linear_infinite_reverse]"
          style={{ willChange: "transform" }}
        />

        {/* Floating Data Packets (Orbital Particles) */}
        <div className="absolute h-[370px] w-[370px] rounded-full pointer-events-none animate-[spin_24s_linear_infinite]">
          <span className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_10px_#22d3ee]" />
        </div>
        <div className="absolute h-[370px] w-[370px] rounded-full pointer-events-none animate-[spin_36s_linear_infinite_reverse]">
          <span className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
        </div>
        <div className="absolute h-[250px] w-[250px] rounded-full pointer-events-none animate-[spin_18s_linear_infinite]">
          <span className="absolute top-1/2 right-0 translate-x-1/2 -translate-y-1/2 h-1.5 w-1.5 rounded-full bg-amber-400 shadow-[0_0_8px_#fbbf24]" />
        </div>

        {/* SVG Connecting Spoke Lines from Center Hub to each Node */}
        <svg
          viewBox="-240 -240 480 480"
          className="absolute inset-0 w-full h-full pointer-events-none"
        >
          {nodes.map((node) => {
            const { x, y } = getCoordinates(node.angle, orbitRadius);
            const isHovered = activeNode === node.id;
            return (
              <g key={node.id}>
                {/* Static Spoke Line */}
                <line
                  x1={0}
                  y1={0}
                  x2={x}
                  y2={y}
                  stroke={isHovered ? "#22d3ee" : "#1e293b"}
                  strokeWidth={isHovered ? 2 : 1}
                  strokeDasharray={isHovered ? "none" : "3,3"}
                  className="transition-all duration-300"
                />
                {/* Dynamic pulse particle traveling along active spoke */}
                {isHovered && (
                  <circle
                    cx={x * 0.5}
                    cy={y * 0.5}
                    r={3}
                    fill="#38bdf8"
                    className="animate-pulse shadow-[0_0_8px_#38bdf8]"
                  />
                )}
              </g>
            );
          })}
        </svg>

        {/* ── Center Hub Card: TRACKED ASSETS ── */}
        <div className="relative z-20 flex flex-col items-center justify-center">
          <div className="group relative flex h-36 w-36 flex-col items-center justify-center rounded-3xl border border-cyan-500/40 bg-gradient-to-b from-[#0c101c] to-[#05070d] p-3 shadow-[0_0_45px_rgba(6,182,212,0.22)] backdrop-blur-2xl transition-all duration-300 hover:scale-105 hover:border-cyan-300 hover:shadow-[0_0_55px_rgba(6,182,212,0.4)]">
            {/* Corner Decorative Dots */}
            <span className="absolute top-2 left-2 h-1 w-1 rounded-full bg-cyan-400/60" />
            <span className="absolute top-2 right-2 h-1 w-1 rounded-full bg-cyan-400/60" />
            <span className="absolute bottom-2 left-2 h-1 w-1 rounded-full bg-cyan-400/60" />
            <span className="absolute bottom-2 right-2 h-1 w-1 rounded-full bg-cyan-400/60" />

            {/* Geometric Isometric 3-Cubes Icon */}
            <div className="relative mb-1 transition-transform duration-300 group-hover:-translate-y-0.5">
              <IsometricThreeCubes className="w-10 h-10 text-cyan-400 drop-shadow-[0_0_12px_rgba(6,182,212,0.7)]" />
            </div>

            {/* Animated Big Metric */}
            <div className="font-display text-2xl font-black tracking-tight text-white group-hover:text-cyan-200 transition-colors">
              {animatedAssets.toLocaleString()}
            </div>

            {/* Subtitle / Center Label */}
            <div className="mt-0.5 font-mono text-[9px] font-extrabold uppercase tracking-widest text-cyan-300">
              TRACKED ASSETS
            </div>

            {/* Scope badge */}
            <div className="mt-1 rounded bg-cyan-950/80 px-1.5 py-0.5 border border-cyan-800/60 font-mono text-[8px] font-bold text-cyan-400 tracking-wider">
              {verifiedScope}
            </div>
          </div>
        </div>

        {/* ── Orbiting Satellite Nodes (6 Surrounding Cards) ── */}
        {nodes.map((node) => {
          const { x, y } = getCoordinates(node.angle, orbitRadius);
          const isHovered = activeNode === node.id;

          return (
            <div
              key={node.id}
              className="absolute z-30 transition-transform duration-300"
              style={{
                transform: `translate(${x}px, ${y}px)`,
                left: "50%",
                top: "50%",
                marginLeft: "-32px",
                marginTop: "-32px",
              }}
              onMouseEnter={() => setActiveNode(node.id)}
              onMouseLeave={() => setActiveNode(null)}
            >
              <Link
                href={node.href}
                className="group flex flex-col items-center cursor-pointer"
              >
                {/* Node Squircle Card matching user's image */}
                <div
                  className={`relative flex h-14 w-14 items-center justify-center rounded-2xl border transition-all duration-300 shadow-xl ${
                    isHovered
                      ? "scale-115 border-cyan-400 bg-slate-900 text-cyan-300 shadow-[0_0_25px_rgba(6,182,212,0.4)]"
                      : "border-slate-800/90 bg-[#0d101a]/95 text-slate-300 hover:border-slate-700 hover:text-white"
                  }`}
                >
                  {/* Active node dot */}
                  <span
                    className={`absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full border-2 border-slate-950 ${
                      node.accent === "emerald"
                        ? "bg-emerald-400 shadow-[0_0_6px_#34d399]"
                        : node.accent === "amber"
                        ? "bg-amber-400 shadow-[0_0_6px_#fbbf24]"
                        : node.accent === "purple"
                        ? "bg-purple-400 shadow-[0_0_6px_#c084fc]"
                        : node.accent === "rose"
                        ? "bg-rose-400 shadow-[0_0_6px_#f43f5e]"
                        : "bg-cyan-400 shadow-[0_0_6px_#22d3ee]"
                    }`}
                  />
                  {node.icon}
                </div>

                {/* Node Label & Subtitle underneath */}
                <div className="mt-1.5 flex flex-col items-center text-center max-w-[110px]">
                  <span
                    className={`font-mono text-[9px] font-bold uppercase tracking-wider transition-colors ${
                      isHovered ? "text-cyan-300" : "text-slate-300"
                    }`}
                  >
                    {node.title}
                  </span>
                  <span className="font-mono text-[8px] text-slate-500 uppercase tracking-tight">
                    {node.value}
                  </span>
                </div>
              </Link>
            </div>
          );
        })}
      </div>

      {/* ── Bottom Telemetry Legend Bar ── */}
      <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 border-t border-slate-800/80 pt-3 text-center">
        <div className="rounded-xl bg-slate-950/60 p-2 border border-slate-800/50">
          <div className="text-[10px] font-mono text-slate-500 uppercase">VERIFIED SCOPE</div>
          <div className="font-mono text-xs font-bold text-emerald-400">100% VERIFIED</div>
        </div>
        <div className="rounded-xl bg-slate-950/60 p-2 border border-slate-800/50">
          <div className="text-[10px] font-mono text-slate-500 uppercase">ACTIVE SIGNALS</div>
          <div className="font-mono text-xs font-bold text-cyan-400">STREAMING</div>
        </div>
        <div className="rounded-xl bg-slate-950/60 p-2 border border-slate-800/50">
          <div className="text-[10px] font-mono text-slate-500 uppercase">COMPANIES</div>
          <div className="font-mono text-xs font-bold text-purple-300">{companiesWatched} WATCHED</div>
        </div>
        <div className="rounded-xl bg-slate-950/60 p-2 border border-slate-800/50">
          <div className="text-[10px] font-mono text-slate-500 uppercase">AVG CONFIDENCE</div>
          <div className="font-mono text-xs font-bold text-amber-300">{avgConfidence} CONSENSUS</div>
        </div>
      </div>
    </div>
  );
}
