"use client";

import React, { useState } from "react";
import Link from "next/link";

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

  const toggleSection = (title: string) => {
    setOpenSections((prev) => ({
      ...prev,
      [title]: !prev[title],
    }));
  };

  const sections: FooterSection[] = [
    {
      title: "Product",
      links: [
        { label: "Intelligence Stream", href: "/intelligence" },
        { label: "Attack Surface Mapping", href: "/attack-surface" },
        { label: "Security Intelligence", href: "/security-intelligence" },
        { label: "Vulnerability Intelligence", href: "/vulnerability-intelligence" },
        { label: "Bug Bounty Programs", href: "/programs" },
        { label: "Evidence Engine", href: "/evidence" },
        { label: "Temporal Timeline", href: "/timeline" },
        { label: "Pricing & Tiers", href: "/pricing" },
      ],
    },
    {
      title: "Resources",
      links: [
        { label: "Documentation", href: "/docs" },
        { label: "REST API Reference", href: "/api" },
        { label: "Product Changelog", href: "/changelog", badge: "v2.4" },
        { label: "Platform Status", href: "/status" },
        { label: "FAQ", href: "/faq" },
        { label: "Research Roadmap", href: "/roadmap" },
      ],
    },
    {
      title: "Company",
      links: [
        { label: "About AttackSurface", href: "/about" },
        { label: "Careers", href: "/careers", badge: "0 Open" },
        { label: "Contact Intelligence Desk", href: "/contact" },
        { label: "Responsible Disclosure", href: "/responsible-disclosure" },
      ],
    },
    {
      title: "Security & Legal",
      links: [
        { label: "Security Architecture", href: "/security" },
        { label: "Disclosure Policy", href: "/responsible-disclosure" },
        { label: "Privacy Policy", href: "/privacy" },
        { label: "Terms of Service", href: "/terms" },
        { label: "Cookie Policy", href: "/cookies" },
      ],
    },
  ];

  return (
    <footer className="relative z-20 border-t border-white/[0.08] bg-[#030712] text-slate-400">

      {/* Main Multi-Column Content */}
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:gap-8">
          {/* Brand Column (Span 4) */}
          <div className="space-y-5 lg:col-span-4">
            <div className="flex items-center gap-3">
              <img
                src="/logo-icon-3d.png"
                alt="AttackSurface Logo"
                className="h-10 w-10 object-contain drop-shadow-[0_0_15px_rgba(0,240,255,0.4)]"
              />
              <div>
                <span className="text-base font-bold tracking-tight text-white font-sans font-display">
                  AttackSurface
                </span>
                <span className="block text-[10px] font-mono tracking-widest text-cyan-400 uppercase font-semibold">
                  Timeline
                </span>
              </div>
            </div>

            <p className="text-xs leading-relaxed text-slate-300 max-w-sm">
              Continuous security-change intelligence for researchers. We observe public internet surface deltas, verify cryptographic evidence trails, and deliver high-signal diffs without intrusive probing.
            </p>

            {/* Official Contact & Socials */}
            <div className="space-y-2.5 pt-2 border-t border-white/[0.06] max-w-sm">
              <div className="text-[11px] font-mono uppercase tracking-wider text-slate-300">
                Official Intelligence Channels
              </div>
              
              <div className="flex flex-col gap-2 text-xs">
                <a
                  href="mailto:attacksurface.alerts@gmail.com"
                  className="group flex items-center gap-2 text-slate-300 hover:text-cyan-400 transition-colors"
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-md bg-white/[0.04] border border-white/[0.08] text-slate-400 group-hover:text-cyan-400 group-hover:border-cyan-500/30">
                    ✉
                  </span>
                  <span className="font-mono text-[11px]">attacksurface.alerts@gmail.com</span>
                </a>

                <a
                  href="https://instagram.com/attacksurface_official"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-center gap-2 text-slate-300 hover:text-cyan-400 transition-colors"
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-md bg-white/[0.04] border border-white/[0.08] text-slate-400 group-hover:text-cyan-400 group-hover:border-cyan-500/30">
                    ◈
                  </span>
                  <span className="font-mono text-[11px]">@attacksurface_official</span>
                </a>
              </div>
            </div>

            {/* Security Guarantee Pill */}
            <div className="inline-flex items-center gap-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 text-[11px] font-mono text-emerald-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              <span>Zero-Weaponization Standard Enforced</span>
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
                    className="flex w-full items-center justify-between text-left font-mono text-xs font-semibold uppercase tracking-wider text-slate-200 md:pointer-events-none"
                  >
                    <span>{section.title}</span>
                    <span className="text-slate-300 md:hidden">
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
                      <li key={link.href}>
                        <Link
                          href={link.href}
                          className="group inline-flex items-center gap-1.5 text-slate-400 hover:text-cyan-400 hover:translate-x-0.5 transition-all duration-150"
                        >
                          <span>{link.label}</span>
                          {link.badge && (
                            <span className="rounded bg-cyan-500/15 border border-cyan-500/30 px-1.5 py-0.2 font-mono text-[9px] font-medium text-cyan-300">
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

        {/* Bottom Section */}
        <div className="mt-12 border-t border-white/[0.08] pt-8 lg:mt-16">
          <div className="flex flex-col items-center justify-between gap-4 md:flex-row text-xs text-slate-300">
            <div className="flex flex-col gap-1 text-center md:text-left">
              <p className="font-mono text-[11px] text-slate-300">
                &copy; 2026 AttackSurface. All rights reserved.
              </p>
              <p className="text-[11px] text-slate-400">
                Continuous security-change intelligence for authorized researchers. Non-intrusive public telemetry only.
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-6 font-mono text-[11px]">
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
      </div>
    </footer>
  );
}
