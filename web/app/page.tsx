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

        {/* Feature Grid */}
        </div>
        <div className="relative hidden min-h-[390px] overflow-hidden rounded-[32px] border border-white/10 bg-white/[.025] lg:block">
          <div className="network-halo" />
          <div className="network-orbit orbit-one" />
          <div className="network-orbit orbit-two" />
          <div className="absolute left-[16%] top-[28%] rounded-full border border-cyan-200/40 bg-slate-950/70 px-3 py-2 font-mono text-[10px] uppercase text-cyan-200 shadow-[0_0_25px_var(--accent-wash)]">old surface</div>
          <div className="absolute right-[13%] top-[20%] rounded-full border border-cyan-200/40 bg-slate-950/70 px-3 py-2 font-mono text-[10px] uppercase text-cyan-200 shadow-[0_0_25px_var(--accent-wash)]">new endpoint</div>
          <div className="absolute bottom-[22%] left-[38%] rounded-full border border-cyan-200/40 bg-cyan-500/15 px-3 py-2 font-mono text-[10px] uppercase text-cyan-100 shadow-[0_0_25px_var(--accent-wash)]">research signal</div>
          <div className="absolute inset-x-8 bottom-6 flex justify-between border-t border-white/10 pt-3 font-mono text-[9px] uppercase tracking-widest text-slate-500"><span>discover</span><span>correlate</span><span>understand</span></div>
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
