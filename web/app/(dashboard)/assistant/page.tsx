"use client";

import React, { useState } from "react";
import { apiFetch } from "@/lib/api";

export default function AssistantPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<string | null>(null);
  const [grounded, setGrounded] = useState<any>(null);

  const handleAsk = async (q: string) => {
    setQuery(q);
    setLoading(true);
    try {
      const data = await apiFetch<any>("/api/v1/assistant/chat", {
        method: "POST",
        body: JSON.stringify({ message: q }),
      });
      setResponse(data.response);
      setGrounded(data.grounded_data);
    } catch (err: any) {
      setResponse(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16 font-sans">
      {/* Header */}
      <div className="border-b border-slate-800 pb-6">
        <div className="flex items-center gap-2 font-mono text-xs text-cyan-400 uppercase tracking-widest mb-1">
          <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee] animate-pulse" />
          THREAT INTELLIGENCE WORKSPACE
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white">
          AI Cyber Threat Analyst
        </h1>
        <p className="text-slate-400 text-sm mt-1 max-w-3xl">
          Contextual threat analysis, historical exploit correlation, and enterprise vulnerability intelligence.
        </p>
      </div>

      {/* Suggested Quick Exploration Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          onClick={() => handleAsk("What was the biggest attack on Google in history and breakdown by years?")}
          className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-cyan-500/50 cursor-pointer group transition-all"
        >
          <div className="text-[11px] font-mono text-cyan-400 uppercase tracking-wider mb-1">
            TARGET: GOOGLE (GOOGLE.COM)
          </div>
          <div className="text-sm font-semibold text-white group-hover:text-cyan-200">
            Biggest attack in history & 20-year attack breakdown
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Examines Operation Aurora (2009–2010), Chrome zero-days, and BeyondCorp Zero Trust emergence.
          </p>
        </div>

        <div
          onClick={() => handleAsk("What are the most dangerous CISA KEV vulnerabilities in 2024?")}
          className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-rose-500/50 cursor-pointer group transition-all"
        >
          <div className="text-[11px] font-mono text-rose-400 uppercase tracking-wider mb-1">
            ACTIVE EXPLOITS: CISA KEV
          </div>
          <div className="text-sm font-semibold text-white group-hover:text-rose-200">
            Top actively exploited zero-days in the wild
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Analyzes edge appliance RCEs, Ivanti, Palo Alto, and browser sandbox escapes.
          </p>
        </div>

        <div
          onClick={() => handleAsk("Analyze Microsoft's top attack vectors over the last 15 years")}
          className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-purple-500/50 cursor-pointer group transition-all"
        >
          <div className="text-[11px] font-mono text-purple-400 uppercase tracking-wider mb-1">
            TARGET: MICROSOFT
          </div>
          <div className="text-sm font-semibold text-white group-hover:text-purple-200">
            15-year attack vector evolution & APT campaigns
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Explores SolarWinds SUNBURST, ProxyLogon Exchange 0-days, and Storm-0558 signing key breach.
          </p>
        </div>
      </div>

      {/* Query Bar */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk(query);
          }}
          className="flex gap-3"
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask any cyber threat or company intelligence question (e.g. biggest attack on google in history)..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-3 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold font-mono text-sm disabled:opacity-50 transition-colors shrink-0"
          >
            {loading ? "ANALYZING..." : "QUERY THREAT AI"}
          </button>
        </form>
      </div>

      {/* Intelligence Briefing Output */}
      {response && (
        <div className="p-6 rounded-xl bg-slate-900/90 border border-cyan-500/40 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <span className="h-2 w-2 rounded-full bg-cyan-400" />
              INTELLIGENCE BRIEFING REPORT
            </div>
            {grounded?.total_security_events && (
              <div className="flex gap-3 text-xs font-mono text-slate-400">
                <span>Database Events: <strong className="text-white">{grounded.total_security_events}</strong></span>
                <span>CISA KEV: <strong className="text-rose-400">{grounded.total_cisa_items}</strong></span>
              </div>
            )}
          </div>
          <div className="prose prose-invert max-w-none text-sm leading-relaxed whitespace-pre-wrap font-sans text-slate-200">
            {response}
          </div>
        </div>
      )}
    </div>
  );
}
