import React from "react";
import Link from "next/link";
import WhiteAesthetic3DBackground from "@/components/WhiteAesthetic3DBackground";
import ThemeToggle from "@/components/ThemeToggle";

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

      <div className="relative z-10 w-full max-w-md animate-surface-in">
        {/* Branding header */}
        <div className="mb-6 text-center">
          <Link href="/" className="inline-flex flex-col items-center group">
            <img
              src="/logo-icon-3d.png"
              alt="AttackSurface Logo"
              className="h-16 w-16 object-contain drop-shadow-[0_0_25px_rgba(0,240,255,0.45)] transition-transform duration-300 group-hover:scale-105 mb-3"
            />
            <div className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-mono tracking-wider"
              style={{
                borderColor: "var(--line-strong)",
                background: "var(--accent-wash)",
                color: "var(--accent-strong)",
              }}
            >
              <span className="h-1.5 w-1.5 rounded-full animate-pulse" style={{ background: "var(--accent)" }} />
              AUTHORIZED RESEARCH ONLY
            </div>
            <h1
              className="mt-3 text-2xl font-bold tracking-tight transition-colors font-display"
              style={{ color: "var(--ink)" }}
            >
              AttackSurface <span style={{ color: "var(--accent)" }}>Timeline</span>
            </h1>
            <p
              className="mt-1 text-xs font-mono tracking-wide"
              style={{ color: "var(--muted)" }}
            >
              BUG BOUNTY RESEARCH INTELLIGENCE
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
