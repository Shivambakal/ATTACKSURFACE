"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import ThemeToggle from "@/components/ThemeToggle";
import CommandPalette from "@/components/CommandPalette";

export default function PublicNav() {
  const pathname = usePathname();
  const { user } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // Global Keyboard shortcuts: Ctrl+K / Cmd+K for Command Palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const navLinks = [
    { label: "Overview", href: "/" },
    { label: "Intelligence", href: "/intelligence" },
    { label: "Attack Surface", href: "/attack-surface" },
    { label: "Programs", href: "/programs" },
    { label: "Pricing", href: "/pricing" },
    { label: "About", href: "/about" },
  ];

  const isAuthPage =
    pathname === "/login" ||
    pathname === "/signup" ||
    pathname === "/forgot-password" ||
    pathname === "/reset-password";

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <>
      <header className="sticky top-3 sm:top-4 z-40 w-full px-3 sm:px-6 flex justify-center pointer-events-none select-none">
        {/* ── FLOATING PILL NAVBAR (MATCHING REFERENCE DESIGN) ─────────────── */}
        <div className="pointer-events-auto w-full max-w-5xl rounded-full border border-black/10 dark:border-white/[0.12] bg-white/80 dark:bg-[#0c0d14]/85 backdrop-blur-2xl shadow-[0_16px_40px_rgba(0,0,0,0.06)] dark:shadow-[0_16px_40px_rgba(0,0,0,0.65)] px-3 sm:px-4 py-1.5 flex items-center justify-between gap-2 sm:gap-4 transition-all duration-300">
          {/* Left: Animated PNG Logo & Brand */}
          <Link
            href="/"
            className="group flex items-center gap-2.5 rounded-full pr-2 focus:outline-none focus-visible:ring-1 focus-visible:ring-cyan-400"
          >
            {/* Animated 3D PNG Logo Emblem */}
            <div className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 dark:bg-white/[0.06] border border-black/10 dark:border-white/[0.1] overflow-hidden group-hover:border-cyan-400/50 transition-colors">
              <div className="absolute -inset-1 rounded-full bg-gradient-to-tr from-cyan-500/30 via-emerald-500/20 to-teal-400/20 blur-sm opacity-40 group-hover:opacity-100 transition-opacity duration-500" />
              <img
                src="/logo-icon-3d.png"
                alt="AttackSurface Logo"
                className="relative z-10 h-5 w-5 object-contain transition-transform duration-500 ease-out group-hover:scale-110 group-hover:rotate-6 drop-shadow-[0_2px_8px_rgba(0,240,255,0.4)]"
              />
            </div>

            <span className="text-sm font-semibold tracking-tight text-slate-900 dark:text-white font-display group-hover:text-cyan-500 dark:group-hover:text-cyan-300 transition-colors">
              AttackSurface
            </span>
          </Link>

          {/* Center: Sleek Navigation Links (Matching Image Pill Design) */}
          {!isAuthPage && (
            <nav className="hidden md:flex items-center gap-1 font-sans">
              {navLinks.map((link) => {
                const active = isActive(link.href);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`text-xs sm:text-sm font-medium transition-all duration-200 ${
                      active
                        ? "rounded-full bg-black/5 dark:bg-white/10 text-slate-900 dark:text-white px-3.5 py-1 border border-black/10 dark:border-white/[0.08] shadow-sm"
                        : "text-slate-600 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-white px-3 py-1"
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </nav>
          )}

          {/* Right Actions: Searchbar, Theme Toggle, Transparent Sign In & Profile / Start Free */}
          <div className="flex items-center gap-2 sm:gap-2.5">
            {/* Best Search Bar / Command Palette Trigger */}
            <button
              onClick={() => setCommandPaletteOpen(true)}
              className="flex items-center gap-2 rounded-full border border-black/10 dark:border-white/[0.1] bg-black/[0.03] dark:bg-white/[0.04] hover:bg-black/[0.06] dark:hover:bg-white/[0.08] px-2.5 sm:px-3 py-1 text-xs text-slate-600 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-white transition shadow-sm"
              title="Global Search & Command Palette (⌘K)"
              aria-label="Open Search Command Palette"
            >
              <svg
                className="h-3.5 w-3.5 text-cyan-500 dark:text-cyan-400 shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <span className="hidden xl:inline text-slate-500 dark:text-neutral-400 font-sans text-xs">
                Search...
              </span>
              <kbd className="hidden sm:inline-block rounded bg-black/[0.05] dark:bg-white/[0.08] px-1.5 py-0.2 text-[10px] font-mono text-cyan-600 dark:text-cyan-300 border border-black/10 dark:border-white/[0.1]">
                ⌘K
              </kbd>
            </button>

            {/* Single Icon Dark & Light Theme Toggle */}
            <ThemeToggle className="!h-8 !w-8 !rounded-full !border-black/10 dark:!border-white/[0.1] !bg-black/[0.03] dark:!bg-white/[0.04] hover:!bg-black/[0.06] dark:hover:!bg-white/[0.08]" />

            {/* Sign In & Transparent Apple-like Action Button */}
            {!user ? (
              <div className="flex items-center gap-1 sm:gap-2">
                <Link
                  href="/login"
                  className="hidden sm:inline-block text-xs sm:text-sm font-medium text-slate-700 dark:text-neutral-300 hover:text-slate-950 dark:hover:text-white transition-colors px-2.5 py-1"
                >
                  Sign in
                </Link>

                {/* Apple-style Transparent Frosted Pill (NOT filled) */}
                <Link
                  href="/signup"
                  className="rounded-full border border-slate-900/20 dark:border-white/20 bg-black/[0.04] dark:bg-white/[0.08] hover:bg-black/[0.08] dark:hover:bg-white/[0.16] text-slate-900 dark:text-white px-3.5 sm:px-4 py-1.5 text-xs sm:text-sm font-medium backdrop-blur-md transition-all shadow-[0_0_12px_rgba(0,0,0,0.02)] dark:shadow-[0_0_12px_rgba(255,255,255,0.04)] hover:shadow-[0_0_20px_rgba(0,240,255,0.2)] hover:border-cyan-500/40 dark:hover:border-cyan-400/40 flex items-center gap-1.5 whitespace-nowrap"
                >
                  <span>Start free</span>
                  <span className="text-xs">&rarr;</span>
                </Link>
              </div>
            ) : (
              /* Profile Button (Apple-style Transparent Frosted Pill, NOT filled) */
              <Link
                href="/dashboard"
                className="rounded-full border border-slate-900/15 dark:border-white/15 bg-black/[0.03] dark:bg-white/[0.06] hover:bg-black/[0.06] dark:hover:bg-white/[0.14] text-slate-800 dark:text-neutral-200 hover:text-slate-950 dark:hover:text-white px-3 py-1 text-xs font-medium backdrop-blur-md transition-all flex items-center gap-2"
                title="Open Operator Workspace"
              >
                <div className="h-5 w-5 rounded-full bg-gradient-to-tr from-cyan-500/40 to-emerald-500/40 border border-cyan-400/30 flex items-center justify-center text-[10px] font-bold text-cyan-600 dark:text-cyan-300 shrink-0">
                  {user.email?.charAt(0).toUpperCase() || "O"}
                </div>
                <span className="hidden sm:inline font-mono text-[11px] max-w-[90px] truncate">
                  {user.email.split("@")[0]}
                </span>
                <span className="text-slate-500 dark:text-neutral-400 text-xs">&rarr;</span>
              </Link>
            )}

            {/* Mobile Menu Toggle Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="flex h-8 w-8 items-center justify-center rounded-full border border-black/10 dark:border-white/[0.1] bg-black/[0.03] dark:bg-white/[0.04] text-slate-700 dark:text-neutral-300 md:hidden hover:text-slate-950 dark:hover:text-white"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? "✕" : "☰"}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Drawer (Clean Apple-Style Frosted Backdrop) */}
      {mobileMenuOpen && !isAuthPage && (
        <div className="fixed inset-x-3 top-16 z-30 rounded-3xl border border-white/[0.12] bg-[#0c0d14]/95 p-5 backdrop-blur-2xl shadow-2xl md:hidden">
          <div className="flex flex-col gap-2">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
                  isActive(link.href)
                    ? "bg-white/10 text-white font-semibold"
                    : "text-neutral-300 hover:bg-white/[0.05] hover:text-white"
                }`}
              >
                {link.label}
              </Link>
            ))}

            <div className="mt-3 pt-3 border-t border-white/[0.08] flex flex-col gap-2">
              {!user ? (
                <>
                  <Link
                    href="/login"
                    onClick={() => setMobileMenuOpen(false)}
                    className="w-full text-center rounded-xl border border-white/10 bg-white/[0.03] py-2 text-sm font-medium text-neutral-200"
                  >
                    Sign in
                  </Link>
                  <Link
                    href="/signup"
                    onClick={() => setMobileMenuOpen(false)}
                    className="w-full text-center rounded-xl border border-white/20 bg-white/[0.08] py-2 text-sm font-medium text-white"
                  >
                    Start free &rarr;
                  </Link>
                </>
              ) : (
                <Link
                  href="/dashboard"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full text-center rounded-xl border border-white/20 bg-white/[0.08] py-2 text-sm font-medium text-white"
                >
                  Go to Dashboard &rarr;
                </Link>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Embedded Global Command Palette (Triggered by Search Pill or ⌘K) */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
      />
    </>
  );
}
