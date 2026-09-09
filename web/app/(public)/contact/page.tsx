"use client";

import React, { useState } from "react";
import Link from "next/link";

export default function ContactPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    topic: "researcher_inquiry",
    message: "",
  });
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="max-w-3xl space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          COMMUNICATIONS DESK
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          Contact <span className="text-cyan-400">AttackSurface</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          Connect with our intelligence desk for research inquiries, platform integrations, responsible disclosure submissions, or enterprise licensing.
        </p>
      </div>

      <div className="mt-14 grid grid-cols-1 gap-10 lg:grid-cols-12">
        {/* Contact Info & Official Channels (Span 5) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 backdrop-blur-xl shadow-2xl space-y-5">
            <h2 className="text-lg font-bold text-white">Direct Intelligence Channels</h2>
            <p className="text-xs text-slate-300">
              For fastest response, reach us directly via our verified official channels:
            </p>

            <div className="space-y-4 font-mono text-xs">
              <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4 space-y-1">
                <span className="text-[10px] text-slate-300 uppercase block">Official Email</span>
                <a
                  href="mailto:attacksurface.alerts@gmail.com"
                  className="text-cyan-400 hover:text-cyan-300 transition-colors font-bold block break-all"
                >
                  attacksurface.alerts@gmail.com
                </a>
                <span className="text-[10px] text-slate-300 block mt-1">SLA: &le; 24 hours</span>
              </div>

              <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4 space-y-1">
                <span className="text-[10px] text-slate-300 uppercase block">Official Instagram</span>
                <a
                  href="https://instagram.com/attacksurface_official"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-cyan-400 hover:text-cyan-300 transition-colors font-bold block"
                >
                  @attacksurface_official &rarr;
                </a>
                <span className="text-[10px] text-slate-300 block mt-1">Platform updates &amp; alerts</span>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-white/[0.08] bg-[#02050b] p-5 font-mono text-xs text-slate-300 space-y-2">
            <span className="text-emerald-400 font-bold block">ENCRYPTION AVAILABLE</span>
            <p className="font-sans text-xs text-slate-300 leading-relaxed">
              If you require PGP-encrypted communication for sensitive vulnerability disclosures, request our public key via email.
            </p>
          </div>
        </div>

        {/* Interactive Contact Form (Span 7) */}
        <div className="lg:col-span-7 rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl">
          {submitted ? (
            <div className="py-12 text-center space-y-4">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xl font-bold">
                ✓
              </div>
              <h3 className="text-xl font-bold text-white">Transmission Queued</h3>
              <p className="text-xs text-slate-300 max-w-md mx-auto">
                Thank you for reaching out. Your transmission has been received by our security intelligence desk. We will respond to <span className="text-cyan-300 font-mono">{formData.email}</span> shortly.
              </p>
              <button
                onClick={() => setSubmitted(false)}
                className="mt-4 rounded-xl border border-white/[0.1] px-4 py-2 font-mono text-xs text-slate-300 hover:bg-white/[0.05]"
              >
                Send Another Transmission
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-slate-300 mb-1">
                  Your Name / Researcher Handle
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. HunterZero"
                  className="w-full rounded-xl border border-white/[0.1] bg-white/[0.03] px-4 py-2.5 font-mono text-xs text-white placeholder:text-slate-400 focus:border-cyan-400 focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-slate-300 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="name@organization.com"
                  className="w-full rounded-xl border border-white/[0.1] bg-white/[0.03] px-4 py-2.5 font-mono text-xs text-white placeholder:text-slate-400 focus:border-cyan-400 focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-slate-300 mb-1">
                  Topic of Inquiry
                </label>
                <select
                  value={formData.topic}
                  onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
                  className="w-full rounded-xl border border-white/[0.1] bg-slate-900 px-4 py-2.5 font-mono text-xs text-white focus:border-cyan-400 focus:outline-none"
                >
                  <option value="researcher_inquiry">Researcher Account &amp; Feature Inquiry</option>
                  <option value="enterprise_license">Enterprise Team License &amp; Exports</option>
                  <option value="vulnerability_report">Responsible Vulnerability Disclosure</option>
                  <option value="platform_partner">Bug Bounty Platform Scope Integration</option>
                </select>
              </div>

              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-slate-300 mb-1">
                  Message / Details
                </label>
                <textarea
                  required
                  rows={5}
                  value={formData.message}
                  onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                  placeholder="Describe your inquiry or question in detail..."
                  className="w-full rounded-xl border border-white/[0.1] bg-white/[0.03] p-4 font-mono text-xs text-white placeholder:text-slate-400 focus:border-cyan-400 focus:outline-none"
                />
              </div>

              <button
                type="submit"
                className="w-full rounded-xl bg-cyan-500 py-3 font-mono text-xs font-bold text-slate-950 hover:bg-cyan-400 transition-all shadow-lg shadow-cyan-500/20"
              >
                Transmit to Intelligence Desk &rarr;
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
