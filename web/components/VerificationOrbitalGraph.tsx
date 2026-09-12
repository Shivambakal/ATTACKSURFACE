"use client";

import React, { useEffect, useRef } from "react";
import VerificationMetricNode, {
  VerificationNode,
  getCoordinates,
} from "./VerificationMetricNode";

interface VerificationOrbitalGraphProps {
  nodes: VerificationNode[];
  activeNode: number | null;
  onNodeClick: (id: number) => void;
  isMobile?: boolean;
  unavailable?: boolean;
}

export default function VerificationOrbitalGraph({
  nodes,
  activeNode,
  onNodeClick,
  isMobile = false,
  unavailable = false,
}: VerificationOrbitalGraphProps) {
  const canvasRef = useRef<HTMLDivElement>(null);

  // Orbit ring radius: smaller on mobile
  const orbitRadius = isMobile ? 110 : 170;
  // Canvas height: desktop 500px, mobile 360px
  const canvasHeight = isMobile ? 360 : 520;

  return (
    <div
      className="relative w-full"
      style={{ height: canvasHeight }}
      aria-label="Verification intelligence orbital graph"
      role="region"
    >
      {/* ── SVG: Orbit rings and connection lines ── */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none"
        aria-hidden="true"
        style={{ overflow: "visible" }}
      >
        {/* Center coordinates in SVG */}
        <defs>
          <radialGradient id="orbitGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.06" />
            <stop offset="100%" stopColor="#22d3ee" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Radar background glow */}
        <ellipse
          cx="50%"
          cy="50%"
          rx={orbitRadius + 60}
          ry={orbitRadius + 60}
          fill="url(#orbitGlow)"
        />

        {/* Primary orbit ring */}
        <circle
          cx="50%"
          cy="50%"
          r={orbitRadius}
          fill="none"
          stroke="rgba(34,211,238,0.08)"
          strokeWidth="1"
          strokeDasharray="4 8"
        />

        {/* Inner pulse ring */}
        <circle
          cx="50%"
          cy="50%"
          r={orbitRadius * 0.55}
          fill="none"
          stroke="rgba(34,211,238,0.05)"
          strokeWidth="1"
          strokeDasharray="2 10"
        />

        {/* Spoke lines to each node — rendered in SVG space */}
        {nodes.map((node) => {
          const pos = getCoordinates(node.angle, orbitRadius);
          return (
            <line
              key={`spoke-${node.id}`}
              x1="50%"
              y1="50%"
              x2={`calc(50% + ${pos.x}px)`}
              y2={`calc(50% + ${pos.y}px)`}
              stroke={
                activeNode === node.id
                  ? "rgba(34,211,238,0.20)"
                  : "rgba(34,211,238,0.05)"
              }
              strokeWidth={activeNode === node.id ? 1.5 : 1}
              strokeDasharray="3 6"
            />
          );
        })}
      </svg>

      {/* ── Center Hub ── */}
      <div
        className="absolute"
        style={{
          left: "50%",
          top: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 15,
        }}
        aria-hidden="true"
      >
        {/* Outer animated ring */}
        <div
          className="absolute inset-0 rounded-full border border-cyan-400/20 animate-ping"
          style={{ width: 72, height: 72, left: -36, top: -36 }}
        />

        {/* Center sphere */}
        <div
          className={`
            w-16 h-16 rounded-full border backdrop-blur-xl
            flex items-center justify-center
            bg-gradient-to-br from-slate-900/90 to-[#030608]/95
            border-cyan-500/30
            shadow-[0_0_24px_rgba(34,211,238,0.18)]
            ${unavailable ? "opacity-40" : ""}
          `}
          style={{ marginLeft: -32, marginTop: -32 }}
        >
          {/* Isometric cubes icon */}
          <svg viewBox="0 0 48 48" fill="none" className="w-8 h-8">
            <path d="M24 8L30 11.5L24 15L18 11.5Z" fill="rgba(6,182,212,0.18)" stroke="#22d3ee" strokeWidth="1.5" />
            <path d="M18 11.5V18.5L24 22V15Z" fill="rgba(6,182,212,0.08)" stroke="#22d3ee" strokeWidth="1.5" />
            <path d="M24 15V22L30 18.5V11.5Z" fill="rgba(6,182,212,0.30)" stroke="#22d3ee" strokeWidth="1.5" />
            <path d="M18 22L24 25.5L18 29L12 25.5Z" fill="rgba(6,182,212,0.18)" stroke="#22d3ee" strokeWidth="1.5" />
            <path d="M12 25.5V32.5L18 36V29Z" fill="rgba(6,182,212,0.08)" stroke="#22d3ee" strokeWidth="1.5" />
            <path d="M18 29V36L24 32.5V25.5Z" fill="rgba(6,182,212,0.30)" stroke="#22d3ee" strokeWidth="1.5" />
            <path d="M30 22L36 25.5L30 29L24 25.5Z" fill="rgba(6,182,212,0.18)" stroke="#22d3ee" strokeWidth="1.5" />
            <path d="M24 25.5V32.5L30 36V29Z" fill="rgba(6,182,212,0.08)" stroke="#22d3ee" strokeWidth="1.5" />
            <path d="M30 29V36L36 32.5V25.5Z" fill="rgba(6,182,212,0.30)" stroke="#22d3ee" strokeWidth="1.5" />
          </svg>
        </div>
      </div>

      {/* ── Orbital Metric Nodes ── */}
      {nodes.map((node) => (
        <VerificationMetricNode
          key={node.id}
          node={node}
          isActive={activeNode === node.id}
          orbitRadius={orbitRadius}
          onClick={onNodeClick}
          isMobile={isMobile}
        />
      ))}

      {/* ── Unavailable overlay ── */}
      {unavailable && (
        <div
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          aria-live="polite"
          aria-label="Verification unavailable"
        >
          <div className="rounded-2xl border border-rose-800/60 bg-rose-950/40 px-5 py-3 backdrop-blur-sm text-center">
            <div className="font-mono text-xs font-bold text-rose-400 uppercase tracking-widest">
              VERIFICATION UNAVAILABLE
            </div>
            <div className="font-mono text-[10px] text-rose-500/70 mt-1">
              Database unreachable — values cannot be verified
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
