"use client";

import React, { useState } from "react";
import Link from "next/link";

interface FaqItem {
  question: string;
  category: "Platform" | "Safety" | "Scopes" | "Pricing";
  answer: string;
}

const FAQS: FaqItem[] = [
  {
    category: "Platform",
    question: "What is AttackSurface and how does it differ from a vulnerability scanner?",
    answer:
      "Traditional vulnerability scanners actively bombard servers with thousands of fuzzing strings and injection attacks, frequently causing server errors and WAF bans. AttackSurface is a continuous security-change intelligence engine. We monitor non-intrusive public perimeter signals (Certificate Transparency logs, DNS changes, HTTP headers) and compute temporal differentials (T0 vs T1) to catch vulnerabilities the moment an infrastructure change occurs.",
  },
  {
    category: "Safety",
    question: "Does AttackSurface launch exploit payloads or perform weaponized scans?",
    answer:
      "No. We enforce a strict Zero-Weaponization standard. We never send malicious payloads (SQLi, XSS, SSRF, buffer overflows), attempt privilege escalation, or access internal data. All telemetry is obtained via standard, benign DNS queries and read-only HTTP GET/HEAD requests respecting rate limits and robots.txt policies.",
  },
  {
    category: "Scopes",
    question: "Where do the bug bounty programs and scope rules come from?",
    answer:
      "AttackSurface synchronizes public bug bounty scopes from leading platforms including HackerOne, Bugcrowd, Intigriti, and direct enterprise Vulnerability Disclosure Programs (VDPs). Our directory indexes over 2,000 programs and 14,000+ individual wildcard scope rules, automatically categorizing assets as In-Scope or Out-of-Scope.",
  },
  {
    category: "Platform",
    question: "How fast are perimeter changes detected?",
    answer:
      "Certificate Transparency logs are ingested within seconds of certificate pre-issuance. Authoritative DNS changes and header modifications are tracked through continuous ingestion cycles, surfacing high-priority security diffs typically in under 60 seconds.",
  },
  {
    category: "Platform",
    question: "How do I prove a vulnerability in my bug bounty report?",
    answer:
      "AttackSurface provides an Evidence Engine that archives raw wire-level HTTP headers, TLS negotiation states, and DNS SOA records timestamped according to RFC 3339, accompanied by SHA-256 cryptographic checksums. You can export these bundles directly as attachments for your bug bounty submissions.",
  },
  {
    category: "Pricing",
    question: "What is the difference between Community Hunter, Pro Hunter, and Enterprise?",
    answer:
      "Community Hunter is completely free forever with core program directory search and community alerts. Pro Hunter (₹3,999/mo) unlocks unlimited target watchlists, real-time instant alerts, temporal time travel, and evidence bundle exports. Enterprise Team (₹15,999/mo) provides multi-seat collaboration, custom webhook dispatchers, and dedicated API rate allowances.",
  },
  {
    category: "Safety",
    question: "How can I report a security vulnerability in AttackSurface itself?",
    answer:
      "We take platform security seriously. Please report vulnerabilities directly to our security desk at attacksurface.alerts@gmail.com. We offer full Safe Harbor protections for good-faith ethical research.",
  },
];

export default function FaqPage() {
  const [activeCategory, setActiveCategory] = useState<string>("ALL");
  const [openIndexes, setOpenIndexes] = useState<Record<number, boolean>>({ 0: true, 1: true });

  const toggleIndex = (idx: number) => {
    setOpenIndexes((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  const filteredFaqs = activeCategory === "ALL"
    ? FAQS
    : FAQS.filter((f) => f.category === activeCategory);

  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          KNOWLEDGE BASE
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          Frequently Asked <span className="text-cyan-400">Questions</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          Everything you need to know about AttackSurface architecture, zero-weaponization standards, bug bounty scopes, and evidence exports.
        </p>

        {/* Category Filter Pills */}
        <div className="pt-4 flex flex-wrap gap-2 font-mono text-xs">
          {["ALL", "Platform", "Safety", "Scopes", "Pricing"].map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`rounded-xl px-3.5 py-1.5 transition-all ${
                activeCategory === cat
                  ? "bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/20"
                  : "bg-white/[0.04] text-slate-300 hover:bg-white/[0.08] hover:text-white border border-white/[0.06]"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* FAQs List */}
      <div className="mt-12 space-y-4">
        {filteredFaqs.map((faq, idx) => {
          const isOpen = openIndexes[idx];
          return (
            <div
              key={idx}
              className="rounded-2xl border border-white/[0.08] bg-slate-950/80 backdrop-blur-xl overflow-hidden transition-all"
            >
              <button
                onClick={() => toggleIndex(idx)}
                className="w-full text-left p-5 sm:p-6 flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3">
                  <span className="rounded bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 font-mono text-[10px] text-cyan-400 font-bold">
                    {faq.category.toUpperCase()}
                  </span>
                  <span className="font-bold text-sm sm:text-base text-white">{faq.question}</span>
                </div>
                <span className="text-slate-400 font-mono text-base shrink-0">
                  {isOpen ? "−" : "+"}
                </span>
              </button>

              {isOpen && (
                <div className="px-5 pb-6 sm:px-6 text-xs sm:text-sm text-slate-300 leading-relaxed border-t border-white/[0.06] pt-4">
                  {faq.answer}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Still have questions? */}
      <div className="mt-16 rounded-3xl border border-white/[0.08] bg-white/[0.02] p-8 text-center space-y-3">
        <h3 className="text-xl font-bold text-white">Still have questions?</h3>
        <p className="text-xs text-slate-300 max-w-md mx-auto">
          Our security intelligence team is standing by to assist you with any questions or specific target tracking inquiries.
        </p>
        <div className="pt-2">
          <Link
            href="/contact"
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-6 py-2.5 font-mono text-xs font-bold text-slate-950 hover:bg-cyan-400 transition"
          >
            <span>Contact Intelligence Desk</span>
            <span>&rarr;</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
