"use client";

import React, { useCallback } from "react";
import VerificationStatusBadge, { VerificationState } from "./VerificationStatusBadge";

export interface VerificationNode {
  id: number;
  angle: number;        // Degrees from top (0 = 12 o'clock)
  title: string;
  subtitle: string;
  value: number | null; // null = data unavailable → shows "—"
  valueLabel?: string;  // Optional suffix (e.g., "LIVE")
  state: VerificationState;
  href: string;
  accentColor: string;  // Tailwind color name: "emerald", "cyan", etc.
  icon: React.ReactNode;
}

interface VerificationMetricNodeProps {
  node: VerificationNode;
  isActive: boolean;
  orbitRadius: number;
  onClick: (id: number) => void;
  isMobile?: boolean;
}

const ACCENT_COLORS: Record<string, { glow: string; ring: string; text: string; bg: string }> = {
  emerald: {
    glow: "shadow-[0_0_18px_rgba(52,211,153,0.25)]",
    ring: "border-emerald-500/50",
    text: "text-emerald-300",
    bg: "bg-emerald-950/30",
  },
  cyan: {
    glow: "shadow-[0_0_18px_rgba(34,211,238,0.25)]",
    ring: "border-cyan-500/50",
    text: "text-cyan-300",
    bg: "bg-cyan-950/30",
  },
  amber: {
    glow: "shadow-[0_0_18px_rgba(251,191,36,0.25)]",
    ring: "border-amber-500/50",
    text: "text-amber-300",
    bg: "bg-amber-950/30",
  },
  rose: {
    glow: "shadow-[0_0_18px_rgba(251,113,133,0.25)]",
    ring: "border-rose-500/50",
    text: "text-rose-300",
    bg: "bg-rose-950/30",
  },
  slate: {
    glow: "shadow-[0_0_10px_rgba(100,116,139,0.15)]",
    ring: "border-slate-600/50",
    text: "text-slate-400",
    bg: "bg-slate-900/30",
  },
  blue: {
    glow: "shadow-[0_0_18px_rgba(96,165,250,0.25)]",
    ring: "border-blue-500/50",
    text: "text-blue-300",
    bg: "bg-blue-950/30",
  },
};

function getCoordinates(angleDeg: number, radius: number): { x: number; y: number } {
  // 0° = top (12 o'clock) → shift by -90 deg
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: Math.cos(rad) * radius,
    y: Math.sin(rad) * radius,
  };
}

export { getCoordinates };

export default function VerificationMetricNode({
  node,
  isActive,
  orbitRadius,
  onClick,
  isMobile = false,
}: VerificationMetricNodeProps) {
  const { x, y } = getCoordinates(node.angle, orbitRadius);
  const accent = ACCENT_COLORS[node.accentColor] ?? ACCENT_COLORS.slate;

  const handleClick = useCallback(() => onClick(node.id), [node.id, onClick]);
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onClick(node.id);
      }
    },
    [node.id, onClick]
  );

  const displayValue =
    node.value === null || node.value === undefined
      ? "—"
      : node.value.toLocaleString();

  const nodeSize = isMobile ? 64 : 80;
  const halfSize = nodeSize / 2;

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${node.title}: ${displayValue}${node.valueLabel ? " " + node.valueLabel : ""}. Verification state: ${node.state}. Click to view evidence.`}
      aria-pressed={isActive}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className="absolute focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/80 rounded-2xl cursor-pointer"
      style={{
        width: nodeSize,
        height: nodeSize,
        left: `calc(50% + ${x}px - ${halfSize}px)`,
        top: `calc(50% + ${y}px - ${halfSize}px)`,
        transition: "transform 180ms ease, box-shadow 180ms ease",
        transform: isActive ? "scale(1.12)" : "scale(1)",
        zIndex: isActive ? 20 : 10,
      }}
    >
      {/* Node Card */}
      <div
        className={`
          w-full h-full rounded-2xl border backdrop-blur-sm
          flex flex-col items-center justify-center gap-0.5
          transition-all duration-200
          ${accent.bg} ${accent.ring}
          ${isActive ? accent.glow : ""}
          hover:${accent.glow}
        `}
      >
        {/* Icon */}
        <div className={`${accent.text} mb-0.5`} aria-hidden="true">
          {node.icon}
        </div>

        {/* Value */}
        <div
          className={`font-mono font-black text-white leading-none ${
            isMobile ? "text-sm" : "text-base"
          }`}
        >
          {displayValue === "—" ? (
            <span className="text-slate-500">—</span>
          ) : (
            displayValue
          )}
          {node.valueLabel && displayValue !== "—" && (
            <span className={`${accent.text} text-[8px] ml-0.5 font-bold`}>
              {node.valueLabel}
            </span>
          )}
        </div>

        {/* Title */}
        <div
          className={`font-mono font-bold text-center leading-tight px-1 ${
            isMobile ? "text-[7px]" : "text-[8px]"
          } ${accent.text} uppercase tracking-wide`}
        >
          {node.title}
        </div>
      </div>

      {/* Active indicator ring */}
      {isActive && (
        <div
          className={`absolute inset-0 rounded-2xl border-2 ${accent.ring} pointer-events-none animate-pulse`}
          aria-hidden="true"
        />
      )}
    </div>
  );
}
