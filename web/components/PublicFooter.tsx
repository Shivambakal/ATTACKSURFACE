"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import AttackSurfaceLogo from "@/components/AttackSurfaceLogo";

interface FooterLink {
  label: string;
  href: string;
  badge?: string;
  external?: boolean;
}

interface FooterSection {
  title: string;
  links: FooterLink[];
}

export default function PublicFooter() {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});
  const [emailInput, setEmailInput] = useState("");
  const [subscribed, setSubscribed] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);
  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(
        now.toISOString().replace("T", " ").substring(0, 19) + " UTC"
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const toggleSection = (title: string) => {
    setOpenSections((prev) => ({
      ...prev,
      [title]: !prev[title],
    }));
  };

  const handleSubscribe = (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailInput.trim()) return;
    setSubscribed(true);
    setTimeout(() => {
      setEmailInput("");
    }, 2000);
  };

  const handleCopyEmail = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText("attacksurface.alerts@gmail.com");
      setCopiedEmail(true);
      setTimeout(() => setCopiedEmail(false), 2000);
    }
  };

  const sections: FooterSection[] = [
    {
      title: "Product",
      links: [
        { label: "Intelligence Stream", href: "/intelligence" },
        { label: "Attack Surface Mapping", href: "/attack-surface" },
        { label: "Security Intelligence", href: "/security-intelligence" },
        { label: "Vulnerability Intelligence", href: "/vulnerability-intelligence" },
        { label: "Bug Bounty Programs", href: "/programs", badge: "2,010" },
        { label: "Evidence Engine", href: "/evidence" },
        { label: "Temporal Timeline", href: "/timeline" },
        { label: "Pricing & Tiers", href: "/pricing" },
      ],
    },
    {
      title: "Intelligence & Scope",
      links: [
        { label: "CISA KEV Catalog", href: "/security-knowledge", badge: "KEV" },
        { label: "Bug Bounty Directory", href: "/programs" },
        { label: "Entity Watchlist", href: "/watchlist" },
        { label: "Temporal Diff Engine", href: "/changes" },
        { label: "Scope Verification", href: "/targets" },
      ],
    },
    {
      title: "Resources",
      links: [
        { label: "Documentation", href: "/docs" },
        { label: "REST API Reference", href: "/api" },
        { label: "Platform Changelog", href: "/changelog", badge: "v2.4" },
        { label: "Platform Status", href: "/status", badge: "99.99%" },
        { label: "Research Roadmap", href: "/roadmap" },
        { label: "Frequently Asked", href: "/faq" },
      ],
    },
    {
      title: "Company",
      links: [
        { label: "About AttackSurface", href: "/about" },
        { label: "How We Operate", href: "/about#how-we-operate" },
        { label: "Careers", href: "/careers", badge: "0 Open" },
        { label: "Contact Intelligence Desk", href: "/contact" },
        { label: "Responsible Disclosure", href: "/responsible-disclosure" },
      ],
    },
  ];

  return (
    <footer className="relative z-20 border-t border-white/[0.08] bg-black text-neutral-400 overflow-hidden">
      {/* Ethereal Atmospheric Crest Light Beam */}
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent pointer-events-none" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[160px] bg-[radial-gradient(ellipse_50%_100%_at_50%_0%,rgba(6,182,212,0.12),rgba(0,0,0,0))] pointer-events-none" />

      {/* Top Live Telemetry Bar */}
      <div className="border-b border-white/[0.06] bg-neutral-950/70 py-2.5 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] font-mono">
          <div className="flex items-center gap-2.5 text-neutral-300">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
            <span className="text-emerald-400 font-bold uppercase tracking-wider">
              OPERATIONAL
            </span>
            <span className="text-neutral-600">·</span>
            <span className="text-neutral-400">14,740 Scope Assets Synchronized</span>
            <span className="hidden md:inline text-neutral-600">·</span>
            <span className="hidden md:inline text-cyan-400">0 Synthetic Figures</span>
          </div>

          <div className="flex items-center gap-3 text-neutral-500">
            <span className="hidden sm:inline">INGEST SPEED 14ms</span>
            <span className="hidden sm:inline text-neutral-700">·</span>
            <span className="text-neutral-400">{currentTime || "UTC LIVE"}</span>
          </div>
        </div>
      </div>

      {/* Main Multi-Column Content */}
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16 relative">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-12 lg:gap-10">
          {/* Brand & Subscribe Column (Span 4) */}
          <div className="space-y-6 lg:col-span-4">
            <AttackSurfaceLogo size="md" />

            <p className="text-xs sm:text-sm text-neutral-400 leading-relaxed max-w-sm">
              Continuous perimeter intelligence engine built for ethical security researchers. Replacing blind noise with verified temporal diffs.
            </p>

            {/* Newsletter / Critical Diff Alert Input */}
            <div className="space-y-2 pt-1 max-w-sm">
              <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-300">
                Critical Perimeter Diffs Feed
              </span>
              <form onSubmit={handleSubscribe} className="flex items-center gap-2">
                <input
                  type="email"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  placeholder="operator@security.org"
                  className="w-full rounded-xl border border-white/[0.1] bg-white/[0.03] px-3.5 py-2 text-xs font-mono text-white placeholder-neutral-500 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 transition"
                  disabled={subscribed}
                />
                <button
                  type="submit"
                  disabled={subscribed}
                  className={`rounded-xl px-4 py-2 text-xs font-mono font-bold transition-all whitespace-nowrap shadow-md ${
                    subscribed
                      ? "bg-emerald-500 text-slate-950 shadow-emerald-500/20"
                      : "bg-cyan-500 text-slate-950 hover:bg-cyan-400 shadow-cyan-500/20"
                  }`}
                >
                  {subscribed ? "Subscribed ✓" : "Join →"}
                </button>
              </form>
            </div>

            {/* Official Contact & Socials */}
            <div className="space-y-2 pt-2 max-w-sm">
              <div className="text-[11px] font-mono uppercase tracking-wider text-neutral-400">
                Verified Communication Channels
              </div>
              
              <div className="flex flex-col gap-2 text-xs">
                <button
                  onClick={handleCopyEmail}
                  className="group flex items-center gap-2.5 text-left text-neutral-300 hover:text-cyan-400 transition-colors"
                  title="Click to copy email address"
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-white/[0.04] border border-white/[0.08] text-neutral-400 group-hover:text-cyan-400 group-hover:border-cyan-500/30">
                    ✉
                  </span>
                  <span className="font-mono text-[11px]">
                    attacksurface.alerts@gmail.com
                  </span>
                  {copiedEmail && (
                    <span className="text-[10px] font-mono text-emerald-400">
                      Copied!
                    </span>
                  )}
                </button>

                <a
                  href="https://instagram.com/attacksurface_official"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-center gap-2.5 text-neutral-300 hover:text-cyan-400 transition-colors"
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-white/[0.04] border border-white/[0.08] text-neutral-400 group-hover:text-cyan-400 group-hover:border-cyan-500/30">
                    ◈
                  </span>
                  <span className="font-mono text-[11px]">@attacksurface_official</span>
                </a>
              </div>
            </div>
          </div>

          {/* Navigation Columns (Span 8) */}
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 md:grid-cols-4 lg:col-span-8">
            {sections.map((section) => {
              const isOpen = openSections[section.title];
              return (
                <div key={section.title} className="space-y-4">
                  {/* Desktop Title / Mobile Accordion Header */}
                  <button
                    onClick={() => toggleSection(section.title)}
                    className="flex w-full items-center justify-between text-left font-mono text-xs font-semibold uppercase tracking-wider text-neutral-200 md:pointer-events-none"
                  >
                    <span>{section.title}</span>
                    <span className="text-neutral-500 md:hidden">
                      {isOpen ? "−" : "+"}
                    </span>
                  </button>

                  {/* Links List */}
                  <ul
                    className={`space-y-2.5 text-xs transition-all duration-200 ${
                      isOpen ? "block" : "hidden md:block"
                    }`}
                  >
                    {section.links.map((link) => (
                      <li key={link.label}>
                        <Link
                          href={link.href}
                          className="group inline-flex items-center gap-1.5 text-neutral-400 hover:text-white hover:translate-x-0.5 transition-all duration-150"
                        >
                          <span>{link.label}</span>
                          {link.badge && (
                            <span className="rounded bg-cyan-500/10 border border-cyan-500/30 px-1.5 py-0.2 font-mono text-[9px] font-medium text-cyan-300">
                              {link.badge}
                            </span>
                          )}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </div>

        {/* Massive Jaw-Dropping Typography Watermark Banner */}
        <div className="mt-14 pt-8 border-t border-white/[0.05] relative overflow-hidden select-none pointer-events-none text-center">
          <div className="text-[3.25rem] sm:text-[6.5rem] md:text-[8.5rem] lg:text-[11.5rem] font-black tracking-tighter leading-none text-transparent bg-clip-text bg-gradient-to-b from-white/[0.09] via-white/[0.03] to-transparent">
            ATTACKSURFACE
          </div>
        </div>

        {/* Sub-Footer Legal & Security Bar */}
        <div className="border-t border-white/[0.06] pt-6 flex flex-col items-center justify-between gap-4 md:flex-row text-xs text-neutral-400">
          <div className="flex flex-col sm:flex-row items-center gap-3 text-center sm:text-left">
            <p className="font-mono text-[11px] text-neutral-500">
              &copy; 2026 AttackSurface Timeline Inc. Truth over noise.
            </p>
            <span className="hidden sm:inline text-neutral-700">·</span>
            <span className="inline-flex items-center gap-1 font-mono text-[10px] text-neutral-500 bg-white/[0.03] border border-white/[0.06] px-2 py-0.5 rounded">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
              RFC 9116 COMPLIANT
            </span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-5 font-mono text-[11px]">
            <Link href="/privacy" className="hover:text-cyan-400 transition-colors">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-cyan-400 transition-colors">
              Terms
            </Link>
            <Link href="/security" className="hover:text-cyan-400 transition-colors">
              Security
            </Link>
            <Link href="/responsible-disclosure" className="hover:text-cyan-400 transition-colors">
              Disclosure
            </Link>
            <Link href="/cookies" className="hover:text-cyan-400 transition-colors">
              Cookies
            </Link>
            <Link href="/contact" className="hover:text-cyan-400 transition-colors">
              Contact
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
