"use client";

import React from "react";
import Link from "next/link";

interface AttackSurfaceLogoProps {
  size?: "sm" | "md" | "lg" | "xl";
  showText?: boolean;
  href?: string;
  className?: string;
}

export default function AttackSurfaceLogo({
  size = "md",
  showText = true,
  href = "/",
  className = "",
}: AttackSurfaceLogoProps) {
  const sizeMap = {
    sm: { img: "h-7 w-7", title: "text-sm", sub: "text-[9px]", gap: "gap-2" },
    md: { img: "h-9 w-9", title: "text-base", sub: "text-[10px]", gap: "gap-2.5" },
    lg: { img: "h-11 w-11", title: "text-lg", sub: "text-[11px]", gap: "gap-3" },
    xl: { img: "h-14 w-14", title: "text-2xl", sub: "text-xs", gap: "gap-3.5" },
  }[size];

  const content = (
    <div className={`group relative inline-flex items-center ${sizeMap.gap} select-none transition-transform duration-300 hover:scale-[1.02] ${className}`}>
      {/* 3D Shield Emblem Container with Ambient Reactive Glow */}
      <div className="relative shrink-0 flex items-center justify-center">
        <div className="absolute -inset-1 rounded-2xl bg-gradient-to-tr from-cyan-500/30 via-emerald-500/20 to-teal-400/30 blur-md opacity-40 group-hover:opacity-90 transition-opacity duration-500 will-change-transform" />
        
        <img
          src="/logo-icon-3d.png"
          alt="AttackSurface 3D Shield"
          className={`${sizeMap.img} relative z-10 object-contain drop-shadow-[0_8px_16px_rgba(0,0,0,0.5)] transition-all duration-300 group-hover:brightness-110 group-hover:drop-shadow-[0_0_24px_rgba(0,240,255,0.6)]`}
        />
      </div>

      {showText && (
        <div className="flex flex-col justify-center leading-none">
          <span className={`${sizeMap.title} font-extrabold tracking-tight dark:text-white text-slate-900 font-display transition-colors group-hover:text-cyan-400 dark:group-hover:text-cyan-300`}>
            AttackSurface
          </span>
          <span className={`${sizeMap.sub} font-mono font-bold tracking-[0.25em] uppercase text-cyan-400 mt-0.5`}>
            Timeline
          </span>
        </div>
      )}
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="inline-block focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded-lg">
        {content}
      </Link>
    );
  }

  return content;
}
