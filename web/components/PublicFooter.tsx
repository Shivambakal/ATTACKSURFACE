"use client";

import React, { useState } from "react";
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
      title: "Intelligence & Scope",
      links: [
        { label: "CISA KEV Catalog", href: "/security-knowledge" },
        { label: "Bug Bounty Directory", href: "/programs" },
        { label: "Entity Watchlist", href: "/watchlist" },
        { label: "Vulnerability Feed", href: "/security-intelligence" },
        { label: "REST Documentation", href: "/docs" },
      ],
    },
  ];

  return (
    <footer className="relative z-20 border-t border-slate-800/90 bg-[#02040a] text-slate-400 shadow-[0_-20px_40px_rgba(0,0,0,0.7)]">

      {/* Main Multi-Column Content */}
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:gap-8">
          {/* Brand Column (Span 4) */}
          <div className="space-y-6 lg:col-span-4">
            <AttackSurfaceLogo size="md" />

            {/* Official Contact & Socials */}
            <div className="space-y-2.5 max-w-sm">
              <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
                Official Channels
              </div>
              
              <div className="flex flex-col gap-2 text-xs">
                <a
                  href="mailto:attacksurface.alerts@gmail.com"
                  className="group flex items-center gap-2.5 text-slate-300 hover:text-cyan-400 transition-colors"
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
                  className="group flex items-center gap-2.5 text-slate-300 hover:text-cyan-400 transition-colors"
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-md bg-white/[0.04] border border-white/[0.08] text-slate-400 group-hover:text-cyan-400 group-hover:border-cyan-500/30">
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
              <p className="font-mono text-[11px] text-slate-400">
                &copy; 2026 AttackSurface Timeline. All rights reserved.
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
