"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import ThemeToggle from "@/components/ThemeToggle";

export default function PublicNav() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: "Intelligence", href: "/intelligence" },
    { label: "Attack Surface", href: "/attack-surface" },
    { label: "Programs", href: "/programs" },
    { label: "Security Intel", href: "/security-intelligence" },
    { label: "Pricing", href: "/pricing" },
    { label: "Docs", href: "/docs" },
  ];

  const isActive = (href: string) => pathname === href;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-white/[0.08] bg-[#030712]/85 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-3 group">
          <img
            src="/logo-icon-3d.png"
            alt="AttackSurface Logo"
            className="h-9 w-9 object-contain drop-shadow-[0_0_12px_rgba(0,240,255,0.4)] group-hover:scale-105 transition-transform"
          />
          <div>
            <span className="text-sm font-bold tracking-tight text-white font-sans group-hover:text-cyan-300 transition-colors font-display">
              AttackSurface
            </span>
            <span className="block text-[9px] font-mono tracking-widest text-cyan-400 uppercase font-semibold">
              Timeline
            </span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map((link) => {
            const active = isActive(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-lg px-3 py-1.5 text-xs font-mono transition-all ${
                  active
                    ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-300 hover:text-white hover:bg-white/[0.04]"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right Actions */}
        <div className="hidden sm:flex items-center gap-3">
          <ThemeToggle />

          <Link
            href="/status"
            className="flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.02] px-2.5 py-1 text-[11px] font-mono text-slate-400 hover:border-white/[0.15] hover:text-slate-300 transition-colors"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>OPERATIONAL</span>
          </Link>

          <Link
            href="/login"
            className="rounded-lg border border-slate-800 bg-slate-900/60 px-3.5 py-1.5 font-mono text-xs text-slate-300 transition hover:border-slate-700 hover:text-white"
          >
            SIGN IN
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-cyan-500 px-3.5 py-1.5 font-mono text-xs font-semibold text-slate-950 shadow-sm shadow-cyan-500/20 transition hover:bg-cyan-400"
          >
            START MONITORING &rarr;
          </Link>
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/[0.08] text-slate-300 md:hidden hover:text-white hover:border-white/[0.2]"
          aria-label="Toggle Navigation Menu"
        >
          {mobileMenuOpen ? "✕" : "☰"}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="border-b border-white/[0.08] bg-[#030712] px-4 py-4 md:hidden">
          <div className="flex flex-col gap-2">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`rounded-lg px-3 py-2 text-xs font-mono ${
                  isActive(link.href)
                    ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-300 hover:bg-white/[0.04] hover:text-white"
                }`}
              >
                {link.label}
              </Link>
            ))}

            <div className="mt-3 pt-3 border-t border-white/[0.08] flex flex-col gap-2">
              <Link
                href="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="w-full text-center rounded-lg border border-slate-800 bg-slate-900/60 py-2 font-mono text-xs text-slate-300"
              >
                SIGN IN
              </Link>
              <Link
                href="/signup"
                onClick={() => setMobileMenuOpen(false)}
                className="w-full text-center rounded-lg bg-cyan-500 py-2 font-mono text-xs font-semibold text-slate-950"
              >
                START MONITORING
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
