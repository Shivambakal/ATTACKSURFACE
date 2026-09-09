"use client";

import React from "react";
import Link from "next/link";

export default function CareersPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          ENGINEERING &amp; RESEARCH TEAM
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          Careers at <span className="text-cyan-400">AttackSurface</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          We are engineering the future of continuous security-change intelligence. Our mission is to provide ethical researchers with mathematical precision and cryptographic truth over perimeter deltas.
        </p>
      </div>

      {/* No Open Positions Banner (Explicit requirement) */}
      <div className="mt-12 rounded-3xl border border-white/[0.1] bg-slate-950/90 p-6 sm:p-8 backdrop-blur-xl shadow-2xl text-center space-y-4">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-white/[0.05] border border-white/[0.1] text-cyan-400 font-mono text-lg font-bold">
          0
        </div>
        <h2 className="text-xl font-bold text-white">No Open Positions Currently</h2>
        <p className="text-xs sm:text-sm text-slate-300 max-w-lg mx-auto leading-relaxed">
          We are currently a tight-knit, highly autonomous engineering team focused on scaling our core differential pipeline and crawler infrastructure. While we do not have active listings today, we always welcome conversations with exceptional systems and security engineers.
        </p>

        <div className="pt-2">
          <a
            href="mailto:attacksurface.alerts@gmail.com?subject=Talent%20Network%20Inquiry"
            className="inline-flex items-center gap-2 rounded-xl bg-white/[0.05] border border-white/[0.1] px-5 py-2.5 font-mono text-xs text-slate-200 hover:text-white hover:bg-white/[0.1] transition"
          >
            <span>Join Talent Network: attacksurface.alerts@gmail.com</span>
            <span>&rarr;</span>
          </a>
        </div>
      </div>

      {/* Engineering Culture */}
      <div className="mt-16 space-y-6">
        <h2 className="text-2xl font-bold text-white">How We Build</h2>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 space-y-3">
            <span className="font-mono text-xs text-cyan-400 uppercase font-bold">01 · Evidence Over Opinion</span>
            <h3 className="font-bold text-white text-base">Mathematical Ground Truth</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              We never guess or extrapolate speculative figures. Every decision is grounded in real wire-level observations and reproducible cryptographic proof.
            </p>
          </div>

          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 space-y-3">
            <span className="font-mono text-xs text-emerald-400 uppercase font-bold">02 · Zero Weaponization</span>
            <h3 className="font-bold text-white text-base">Ethical Defense Standard</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              We build tools that defend and assist researchers safely. We do not build weaponized exploits or intrusive scanners that disrupt infrastructure.
            </p>
          </div>

          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 space-y-3">
            <span className="font-mono text-xs text-purple-400 uppercase font-bold">03 · High-Throughput Systems</span>
            <h3 className="font-bold text-white text-base">Low-Latency Ingestion</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Handling millions of Certificate Transparency events and DNS SOA updates requires relentless performance profiling, asynchronous pipelines, and lock-free concurrency.
            </p>
          </div>

          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 space-y-3">
            <span className="font-mono text-xs text-amber-400 uppercase font-bold">04 · Researcher-First Empathy</span>
            <h3 className="font-bold text-white text-base">Designed for the Cockpit</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              We design tools that eliminate fatigue, highlight critical deltas instantly, and respect the researcher&apos;s time and focus.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
