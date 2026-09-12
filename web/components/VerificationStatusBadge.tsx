"use client";

import React from "react";

export type VerificationState =
  | "VERIFIED"
  | "OBSERVED"
  | "CORROBORATED"
  | "DOCUMENTED"
  | "DOCUMENTED_NOT_OBSERVED"
  | "HISTORICAL"
  | "DEVELOPMENT_EVIDENCE"
  | "CANDIDATE"
  | "UNVERIFIED"
  | "CONFLICTING"
  | "REJECTED";

interface VerificationStatusBadgeProps {
  state: VerificationState | string | null | undefined;
  size?: "xs" | "sm" | "md";
  showIcon?: boolean;
  className?: string;
}

const STATE_CONFIG: Record<
  VerificationState,
  { label: string; color: string; bg: string; border: string; icon: string; description: string }
> = {
  VERIFIED: {
    label: "VERIFIED",
    color: "text-emerald-300",
    bg: "bg-emerald-950/60",
    border: "border-emerald-500/40",
    icon: "✓",
    description: "Direct production observation + corroboration + content integrity + freshness",
  },
  OBSERVED: {
    label: "OBSERVED",
    color: "text-cyan-300",
    bg: "bg-cyan-950/60",
    border: "border-cyan-500/40",
    icon: "◉",
    description: "Direct production observation with verified content hash",
  },
  CORROBORATED: {
    label: "CORROBORATED",
    color: "text-amber-300",
    bg: "bg-amber-950/60",
    border: "border-amber-500/40",
    icon: "⊕",
    description: "Multiple independent official sources corroborate this claim",
  },
  DOCUMENTED: {
    label: "DOCUMENTED",
    color: "text-blue-300",
    bg: "bg-blue-950/60",
    border: "border-blue-500/40",
    icon: "▤",
    description: "Authoritative official source; not directly observed or corroborated",
  },
  DOCUMENTED_NOT_OBSERVED: {
    label: "DOC/NOT-OBS",
    color: "text-orange-300",
    bg: "bg-orange-950/60",
    border: "border-orange-500/40",
    icon: "⚠",
    description: "Documented but contradicted by direct observation (conflict detected)",
  },
  HISTORICAL: {
    label: "HISTORICAL",
    color: "text-violet-300",
    bg: "bg-violet-950/60",
    border: "border-violet-500/40",
    icon: "◷",
    description: "Evidence exists but is outside the freshness window",
  },
  DEVELOPMENT_EVIDENCE: {
    label: "DEV EVIDENCE",
    color: "text-indigo-300",
    bg: "bg-indigo-950/60",
    border: "border-indigo-500/40",
    icon: "⌬",
    description: "Repository/development activity only; no production observation",
  },
  CANDIDATE: {
    label: "CANDIDATE",
    color: "text-yellow-300",
    bg: "bg-yellow-950/60",
    border: "border-yellow-500/40",
    icon: "~",
    description: "AI-influenced; capped at CANDIDATE. AI cannot be the verification authority.",
  },
  UNVERIFIED: {
    label: "UNVERIFIED",
    color: "text-slate-400",
    bg: "bg-slate-900/60",
    border: "border-slate-600/40",
    icon: "?",
    description: "No verification checks passed",
  },
  CONFLICTING: {
    label: "CONFLICTING",
    color: "text-rose-300",
    bg: "bg-rose-950/60",
    border: "border-rose-500/40",
    icon: "✕",
    description: "Partial corroboration alongside detected evidence conflict",
  },
  REJECTED: {
    label: "REJECTED",
    color: "text-red-400",
    bg: "bg-red-950/60",
    border: "border-red-500/40",
    icon: "✗",
    description: "Source unreachable and content integrity cannot be verified",
  },
};

const SIZE_CLASSES = {
  xs: "text-[9px] px-1.5 py-0.5 rounded-md",
  sm: "text-[10px] px-2 py-0.5 rounded-lg",
  md: "text-xs px-2.5 py-1 rounded-lg",
};

export default function VerificationStatusBadge({
  state,
  size = "sm",
  showIcon = true,
  className = "",
}: VerificationStatusBadgeProps) {
  if (!state) {
    return (
      <span
        className={`inline-flex items-center gap-1 font-mono font-bold border
          text-slate-500 bg-slate-900/40 border-slate-700/30
          ${SIZE_CLASSES[size]} ${className}`}
        title="Verification state unknown"
        aria-label="Verification state: unknown"
      >
        —
      </span>
    );
  }

  const config = STATE_CONFIG[state as VerificationState];
  if (!config) {
    return (
      <span
        className={`inline-flex items-center gap-1 font-mono font-bold border
          text-slate-400 bg-slate-900/40 border-slate-600/30
          ${SIZE_CLASSES[size]} ${className}`}
        title={`Unknown verification state: ${state}`}
        aria-label={`Verification state: ${state}`}
      >
        {showIcon && <span aria-hidden="true">?</span>}
        {String(state).toUpperCase()}
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1 font-mono font-bold border
        ${config.color} ${config.bg} ${config.border}
        ${SIZE_CLASSES[size]} ${className}`}
      title={config.description}
      aria-label={`Verification state: ${config.label} — ${config.description}`}
    >
      {showIcon && <span aria-hidden="true">{config.icon}</span>}
      {config.label}
    </span>
  );
}

export { STATE_CONFIG };
