"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { useReducedMotion } from "@/lib/useReducedMotion";

/**
 * 1. CardTilt3D: 3D perspective card with pointer-following specular highlight
 */
export function CardTilt3D({
  children,
  className = "",
  maxTilt = 6,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  maxTilt?: number;
  onClick?: () => void;
}) {
  const cardRef = useRef<HTMLDivElement | null>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [glare, setGlare] = useState({ x: 50, y: 50, opacity: 0 });
  const reduced = useReducedMotion();

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (reduced || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;

    setTilt({
      x: (py - 0.5) * -maxTilt,
      y: (px - 0.5) * maxTilt,
    });
    setGlare({
      x: px * 100,
      y: py * 100,
      opacity: 0.15,
    });
  };

  const handlePointerLeave = () => {
    setTilt({ x: 0, y: 0 });
    setGlare((prev) => ({ ...prev, opacity: 0 }));
  };

  return (
    <div
      ref={cardRef}
      onClick={onClick}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      style={{
        transform: reduced
          ? undefined
          : `perspective(1000px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
        transition: "transform 0.22s cubic-bezier(0.2, 0.9, 0.3, 1)",
      }}
      className={`relative overflow-hidden ${className}`}
    >
      {/* Specular Glare */}
      {!reduced && (
        <div
          className="pointer-events-none absolute -inset-px rounded-inherit transition-opacity duration-300"
          style={{
            opacity: glare.opacity,
            background: `radial-gradient(400px circle at ${glare.x}% ${glare.y}%, rgba(0, 240, 255, 0.25), transparent 70%)`,
          }}
        />
      )}
      {children}
    </div>
  );
}

/**
 * 2. MagneticButton: Pulls subtly toward cursor and snaps back on leave
 */
export function MagneticButton({
  children,
  className = "",
  onClick,
  disabled = false,
  title,
}: {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
}) {
  const btnRef = useRef<HTMLButtonElement | null>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const reduced = useReducedMotion();

  const handlePointerMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (reduced || disabled || !btnRef.current) return;
    const rect = btnRef.current.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = (e.clientX - cx) * 0.25;
    const dy = (e.clientY - cy) * 0.25;
    setOffset({ x: dx, y: dy });
  };

  const handlePointerLeave = () => {
    setOffset({ x: 0, y: 0 });
  };

  return (
    <button
      ref={btnRef}
      onClick={onClick}
      disabled={disabled}
      title={title}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      style={{
        transform: reduced ? undefined : `translate3d(${offset.x}px, ${offset.y}px, 0)`,
        transition: "transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1)",
      }}
      className={`relative active:scale-95 transition-all ${className}`}
    >
      {children}
    </button>
  );
}

/**
 * 3. AnimatedNumber: Smooth spring/frame interpolation for digits (e.g. 7 -> 7.1 -> 7.4 -> 8)
 */
export function AnimatedNumber({
  value,
  duration = 650,
  formatter = (v) => Math.round(v).toLocaleString(),
}: {
  value: number;
  duration?: number;
  formatter?: (val: number) => string;
}) {
  const [displayValue, setDisplayValue] = useState<number>(value);
  const prevValueRef = useRef<number>(value);
  const reduced = useReducedMotion();

  useEffect(() => {
    if (reduced) {
      setDisplayValue(value);
      prevValueRef.current = value;
      return;
    }

    const startVal = prevValueRef.current;
    const endVal = value;
    if (startVal === endVal) return;

    const startTime = performance.now();

    const step = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / duration);
      // Snappy cubic ease-out
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = startVal + (endVal - startVal) * ease;
      setDisplayValue(current);

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        setDisplayValue(endVal);
        prevValueRef.current = endVal;
      }
    };

    const animId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(animId);
  }, [value, duration, reduced]);

  return <span>{formatter(displayValue)}</span>;
}

/**
 * 4. CursorSpotlight: Radial perimeter glow tracking pointer position
 */
export function CursorSpotlight({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  return (
    <div
      ref={containerRef}
      onPointerMove={handlePointerMove}
      onPointerLeave={() => setPos(null)}
      className={`group relative overflow-hidden ${className}`}
    >
      {pos && (
        <div
          className="pointer-events-none absolute -inset-px rounded-inherit transition-opacity duration-300 opacity-60"
          style={{
            background: `radial-gradient(200px circle at ${pos.x}px ${pos.y}px, rgba(0, 240, 255, 0.12), transparent 70%)`,
          }}
        />
      )}
      {children}
    </div>
  );
}

/**
 * 5. PulseDot: 2-second cyclical telemetry heartbeat indicator
 */
export function PulseDot({
  tone = "cyan",
  label,
}: {
  tone?: "cyan" | "rose" | "amber" | "emerald";
  label?: string;
}) {
  const colorMap = {
    cyan: "bg-cyan-400 shadow-[0_0_8px_#00f0ff]",
    rose: "bg-rose-500 shadow-[0_0_8px_#f43f5e]",
    amber: "bg-amber-400 shadow-[0_0_8px_#f59e0b]",
    emerald: "bg-emerald-400 shadow-[0_0_8px_#10b981]",
  };

  return (
    <div className="inline-flex items-center gap-1.5 font-mono text-[10px]">
      <span className="relative flex h-2 w-2">
        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${colorMap[tone]}`} />
        <span className={`relative inline-flex rounded-full h-2 w-2 ${colorMap[tone]}`} />
      </span>
      {label && <span className="uppercase tracking-wider text-slate-400">{label}</span>}
    </div>
  );
}

/**
 * 6. SkeletonShimmer: Holographic graphite placeholder for loading cards
 */
export function SkeletonShimmer({ className = "h-24 w-full" }: { className?: string }) {
  return (
    <div
      className={`relative overflow-hidden rounded-xl bg-slate-900/60 border border-slate-800/80 ${className}`}
    >
      <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/[0.04] to-transparent" />
    </div>
  );
}

/**
 * 7. SegmentedControl: Fluid sliding pill selector
 */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  className = "",
}: {
  options: Array<{ id: T; label: string; icon?: string }>;
  value: T;
  onChange: (val: T) => void;
  className?: string;
}) {
  return (
    <div
      className={`inline-flex items-center rounded-xl bg-slate-950/80 p-1 border border-slate-800/80 font-mono text-xs ${className}`}
    >
      {options.map((opt) => {
        const active = opt.id === value;
        return (
          <button
            key={opt.id}
            type="button"
            onClick={() => onChange(opt.id)}
            className={`relative rounded-lg px-3 py-1 font-semibold transition-all duration-200 ${
              active
                ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(0,240,255,0.12)]"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <span className="flex items-center gap-1.5">
              {opt.icon && <span>{opt.icon}</span>}
              <span>{opt.label}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

/**
 * 8. SeverityBadge: Verified color-coded severity tag with halo
 */
export function SeverityBadge({
  severity,
  size = "md",
}: {
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  size?: "sm" | "md";
}) {
  const norm = (severity || "INFO").toUpperCase();

  const styles: Record<string, string> = {
    CRITICAL: "border-rose-500/40 bg-rose-500/10 text-rose-300 shadow-[0_0_12px_rgba(244,63,94,0.3)]",
    HIGH: "border-amber-500/40 bg-amber-500/10 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.3)]",
    MEDIUM: "border-cyan-500/40 bg-cyan-500/10 text-cyan-300 shadow-[0_0_12px_rgba(0,240,255,0.2)]",
    LOW: "border-slate-700 bg-slate-800/40 text-slate-300",
  };

  const currentStyle = styles[norm] || styles.LOW;
  const padding = size === "sm" ? "px-1.5 py-0.2 text-[9px]" : "px-2 py-0.5 text-[10px]";

  return (
    <span className={`inline-flex items-center gap-1 rounded font-mono font-bold uppercase border ${currentStyle} ${padding}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      <span>{norm}</span>
    </span>
  );
}
