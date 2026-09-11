import React from "react";
import Link from "next/link";
import WhiteAesthetic3DBackground from "@/components/WhiteAesthetic3DBackground";
import ThemeToggle from "@/components/ThemeToggle";

import AttackSurfaceLogo from "@/components/AttackSurfaceLogo";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center px-4 py-12 selection:bg-cyan-500 selection:text-slate-950 overflow-hidden transition-colors duration-500">
      <WhiteAesthetic3DBackground />

      {/* Top Floating Theme Switcher */}
      <div className="absolute top-6 right-6 z-20">
        <ThemeToggle />
      </div>

      <div className="relative z-10 w-full max-w-2xl animate-surface-in transition-all duration-300">
        {/* Branding header */}
        <div className="mb-6 text-center">
          <Link href="/" className="inline-flex flex-col items-center group">
            <AttackSurfaceLogo size="xl" showText={false} href="/" className="mb-3" />
            <h1
              className="mt-2 text-2xl font-black tracking-tight transition-colors font-display"
              style={{ color: "var(--ink)" }}
            >
              AttackSurface <span style={{ color: "var(--accent)" }}>Timeline</span>
            </h1>
            <p
              className="mt-1 text-xs font-mono tracking-wider uppercase text-cyan-400 font-semibold"
            >
              Continuous Intelligence Platform
            </p>
          </Link>
        </div>

        {/* Content Card — solid surface so background never bleeds through form text */}
        <div className="auth-panel rounded-[30px] border border-white/15 p-8 shadow-2xl">
          {children}
        </div>

        {/* Footer legal disclaimer */}
        <p
          className="mt-6 text-center text-xs font-mono"
          style={{ color: "var(--muted)" }}
        >
          Only authorized public data collection. Passive diffing &amp; audit logging active.
        </p>
      </div>
    </div>
  );
}
