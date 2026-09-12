"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import PublicNav from "@/components/PublicNav";
import PublicFooter from "@/components/PublicFooter";
import WhiteAesthetic3DBackground from "@/components/WhiteAesthetic3DBackground";

export default function LandingPage() {
  const router = useRouter();
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      router.replace("/dashboard");
    }
  }, [user, router]);

  return (
    <div className="relative min-h-screen overflow-hidden selection:bg-cyan-500 selection:text-slate-950 flex flex-col justify-between transition-colors duration-500">
      <WhiteAesthetic3DBackground />

      {/* Top Public Navigation */}
      <PublicNav />

      {/* Hero Section */}
      <main className="relative z-10 mx-auto my-auto w-full max-w-7xl px-6 py-12 lg:px-10">
        <div className="animate-surface-in inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono tracking-wider text-cyan-400 mb-6">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          AUTHORIZED RESEARCH ONLY · PUBLIC DATA DIFFING
        </div>

        <div className="grid items-center gap-12 lg:grid-cols-[1fr_.8fr]">
        <div>
        <h2 className="mt-2 max-w-4xl text-left text-6xl font-extrabold uppercase leading-[.84] tracking-[-.07em] text-white sm:text-8xl lg:text-[9.5rem]">
          See what<br />
          <span className="text-cyan-300"> changed.</span>
        </h2>

        <p className="mt-8 max-w-xl text-left text-lg leading-relaxed text-slate-300 sm:text-xl">
          Continuous intelligence for the modern attack surface. Discover the delta, understand the context, and move from observation to research with confidence.
        </p>

        {/* CTA Buttons */}
        <div className="mt-8 flex flex-col items-start gap-3 sm:flex-row">
          <Link
            href="/signup"
            className="w-full rounded-full bg-cyan-500 px-8 py-3.5 font-mono text-xs font-bold uppercase tracking-wider text-slate-950 shadow-lg shadow-cyan-500/20 transition hover:bg-cyan-400 hover:shadow-cyan-400/30 sm:w-auto"
          >
            Start Monitoring Assets →
          </Link>
          <Link
            href="/login"
            className="w-full rounded-full border border-slate-800 bg-slate-900/60 px-8 py-3.5 font-mono text-xs font-semibold text-slate-300 transition hover:bg-slate-800 hover:text-white sm:w-auto"
          >
            Operator Sign In
          </Link>
        </div>
        </div>

        {/* Orbital visualization — public preview (decorative, not live data) */}
        <div className="relative hidden w-full lg:block">
          <div className="relative w-full overflow-hidden rounded-3xl border border-slate-800/70 bg-[#07090e]/90 p-6 shadow-2xl backdrop-blur-2xl">
            <div className="flex items-center gap-2 border-b border-slate-800/60 pb-3 mb-4">
              <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#22d3ee]" />
              <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-cyan-300">
                INTELLIGENCE TELEMETRY HUB
              </span>
            </div>
            {/* Static decorative rings — no fabricated numbers */}
            <div className="relative flex items-center justify-center" style={{ minHeight: 300 }}>
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-48 h-48 rounded-full border border-cyan-400/10 border-dashed animate-spin" style={{ animationDuration: "18s" }} />
                <div className="absolute w-32 h-32 rounded-full border border-cyan-400/15" />
              </div>
              <div className="relative z-10 w-16 h-16 rounded-full bg-gradient-to-br from-slate-900 to-[#030608] border border-cyan-500/30 shadow-[0_0_24px_rgba(34,211,238,0.18)] flex items-center justify-center">
                <svg viewBox="0 0 48 48" fill="none" className="w-8 h-8">
                  <path d="M24 8L30 11.5L24 15L18 11.5Z" fill="rgba(6,182,212,0.18)" stroke="#22d3ee" strokeWidth="1.5" />
                  <path d="M18 11.5V18.5L24 22V15Z" fill="rgba(6,182,212,0.08)" stroke="#22d3ee" strokeWidth="1.5" />
                  <path d="M24 15V22L30 18.5V11.5Z" fill="rgba(6,182,212,0.30)" stroke="#22d3ee" strokeWidth="1.5" />
                </svg>
              </div>
              {/* Decorative node labels — no fabricated DB numbers */}
              {[
                { label: "VERIFIED", angle: -90, color: "emerald" },
                { label: "OBSERVED", angle: -30, color: "cyan" },
                { label: "CORROBORATED", angle: 30, color: "amber" },
                { label: "DOCUMENTED", angle: 90, color: "blue" },
              ].map((n) => {
                const rad = (n.angle * Math.PI) / 180;
                const r = 110;
                const x = Math.cos(rad) * r;
                const y = Math.sin(rad) * r;
                return (
                  <div
                    key={n.label}
                    className="absolute w-14 h-14 rounded-2xl border border-slate-700/50 bg-slate-900/60 flex items-center justify-center"
                    style={{ left: `calc(50% + ${x}px - 28px)`, top: `calc(50% + ${y}px - 28px)` }}
                    aria-hidden="true"
                  >
                    <span className={`font-mono text-[8px] font-bold text-${n.color}-400 text-center leading-tight uppercase`}>
                      {n.label}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="mt-3 text-center font-mono text-[9px] text-slate-600 uppercase tracking-widest">
              Sign in to see live verified telemetry
            </div>
          </div>
        </div>
        </div>

        <div className="mt-20 grid grid-cols-1 gap-5 text-left md:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-sm">
            <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs uppercase font-semibold">
              <span className="h-2 w-2 rounded-full bg-cyan-400" />
              Timeline Differentials
            </div>
            <h3 className="mt-2 font-semibold text-sm text-slate-100">Before &amp; Current Diffing</h3>
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">
              Pinpoint newly added headers, changed DNS records, updated TLS certificates, and newly visible API routes.
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-sm">
            <div className="flex items-center gap-2 text-amber-400 font-mono text-xs uppercase font-semibold">
              <span className="h-2 w-2 rounded-full bg-amber-400" />
              Evidence-First Proof
            </div>
            <h3 className="mt-2 font-semibold text-sm text-slate-100">Cryptographic Observations</h3>
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">
              Every flagged diff is backed by raw HTTP headers, payload snapshots, and timestamped audit trails.
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-sm">
            <div className="flex items-center gap-2 text-emerald-400 font-mono text-xs uppercase font-semibold">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              Zero Weaponization
            </div>
            <h3 className="mt-2 font-semibold text-sm text-slate-100">Scope Enforced Collection</h3>
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">
              Strictly non-intrusive GET requests respecting robots.txt, rate limits, same-origin bounds, and program scope.
            </p>
          </div>
        </div>
      </main>

      {/* Public Footer */}
      <PublicFooter />
    </div>
  );
}
