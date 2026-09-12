"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ResearchSignal } from "@/lib/types";
import { apiFetch } from "@/lib/api";
import { openThreatAnalyst } from "@/components/CyberAssistantChat";

interface ResearchSignalCardProps {
  signal: ResearchSignal;
  onStatusChange?: (updated: ResearchSignal) => void;
}

export default function ResearchSignalCard({ signal, onStatusChange }: ResearchSignalCardProps) {
  const [currentStatus, setCurrentStatus] = useState(signal.status);
  const [busy, setBusy] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState<string | null>(null);

  const handleStatus = async (newStatus: string) => {
    setBusy(true);
    try {
      const updated = await apiFetch<ResearchSignal>(`/api/v1/signals/${signal.id}/status`, {
        method: "POST",
        body: JSON.stringify({ status: newStatus }),
      });
      setCurrentStatus(newStatus);
      if (onStatusChange) onStatusChange(updated);
    } catch {
      // Fallback update
      setCurrentStatus(newStatus);
    } finally {
      setBusy(false);
    }
  };

  const handleFeedback = async (feedbackType: string) => {
    setBusy(true);
    try {
      await apiFetch(`/api/v1/signals/${signal.id}/feedback`, {
        method: "POST",
        body: JSON.stringify({ feedback: feedbackType }),
      });
      setFeedbackSuccess(feedbackType);
      if (feedbackType === "FALSE_POSITIVE" || feedbackType === "NOT_RELEVANT") {
        setCurrentStatus("ignored");
      }
      setTimeout(() => setFeedbackSuccess(null), 3000);
    } catch {
      // Ignore error
    } finally {
      setBusy(false);
    }
  };

  // Priority color
  const priorityColor =
    signal.priority === "CRITICAL"
      ? "text-rose-400 bg-rose-950/40 border-rose-800/60"
      : signal.priority === "HIGH"
      ? "text-amber-400 bg-amber-950/40 border-amber-800/60"
      : "text-cyan-400 bg-cyan-950/40 border-cyan-800/60";

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#070b14]/75 p-5 shadow-xl backdrop-blur-xl transition hover:border-white/[0.15] card-25d">
      {/* Header bar: Type, Priority, Confidence & Context Scores */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.08] pb-3">
        <div className="flex items-center gap-2">
          <span className={`rounded-md border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${priorityColor}`}>
            {signal.priority}
          </span>
          <span className="rounded-md border border-cyan-900/60 bg-cyan-950/30 px-2 py-0.5 font-mono text-[10px] text-cyan-300">
            {signal.signal_type.replace(/_/g, " ")}
          </span>
          <span className="rounded-md border border-white/[0.08] bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] text-slate-300 font-semibold">
            {signal.confidence_score >= 85 ? "VERIFIED QUALIFIED" : signal.confidence_score >= 60 ? "CORRELATED" : "CANDIDATE"}
          </span>
          {signal.source_count > 1 && (
            <span className="rounded-md border border-slate-800 bg-slate-800/60 px-2 py-0.5 font-mono text-[10px] text-slate-300">
              {signal.source_count} sources
            </span>
          )}
        </div>

        <div className="flex items-center gap-3 font-mono text-[11px]">
          <span className="text-slate-400">
            Relevance: <span className="font-bold text-amber-300">{signal.relevance_score}/100</span>
          </span>
          <span className="text-slate-400">
            Confidence: <span className="font-bold text-cyan-400">{signal.confidence_score}%</span>
          </span>
          {signal.security_context_score > 0 && (
            <span className="text-slate-400 hidden sm:inline">
              Context: <span className="font-bold text-purple-300">{signal.security_context_score}/100</span>
            </span>
          )}
        </div>
      </div>

      {/* Main Title & Summary */}
      <div className="mt-3.5">
        <h4 className="text-base font-semibold text-slate-100 leading-snug">
          {signal.title}
        </h4>
        <p className="mt-1.5 text-xs text-slate-300 leading-relaxed font-sans">
          {signal.summary}
        </p>
      </div>

      {/* Why It Matters Callout */}
      <div className="mt-3.5 rounded-lg border border-cyan-500/20 bg-cyan-950/20 p-3">
        <div className="flex items-center gap-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
          WHY THIS MATTERS
        </div>
        <p className="mt-1 text-xs text-slate-200 leading-relaxed">
          {signal.why_it_matters}
        </p>
      </div>

      {/* Recommended Research Area */}
      {signal.recommended_research_area && (
        <div className="mt-2.5 rounded-lg border border-amber-500/20 bg-amber-950/20 p-3">
          <div className="flex items-center gap-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-amber-400">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            RESEARCH GUIDANCE
          </div>
          <p className="mt-1 text-xs text-slate-300 leading-relaxed">
            {signal.recommended_research_area}
          </p>
        </div>
      )}

      {/* Historical Security Context Callout */}
      {signal.security_context_score > 0 && (
        <div className="mt-2.5 rounded-lg border border-purple-500/30 bg-purple-950/20 p-3 font-mono">
          <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-purple-400">
            <span className="h-1.5 w-1.5 rounded-full bg-purple-400" />
            HISTORICAL SECURITY CONTEXT
          </div>
          <p className="mt-1 text-xs text-slate-300 leading-relaxed font-sans">
            Prior public vulnerability disclosures or historical evolution in this capability area observed. Correlate with historical weakness fingerprint.
          </p>
        </div>
      )}

      {/* Affected Assets & Historical Context */}
      <div className="mt-3.5 flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono border-t border-slate-800/80 pt-3 text-slate-400">
        <div className="flex items-center gap-2 overflow-hidden">
          <span className="text-slate-500">AFFECTED:</span>
          {signal.affected_assets && signal.affected_assets.length > 0 ? (
            signal.affected_assets.slice(0, 2).map((asset, i) => (
              <span key={i} className="rounded bg-slate-800/80 px-1.5 py-0.5 text-cyan-300 truncate max-w-[200px]">
                {asset}
              </span>
            ))
          ) : (
            <span>Target infrastructure</span>
          )}
        </div>

        {/* Action & Feedback Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {feedbackSuccess && (
            <span className="text-[10px] text-emerald-400 font-semibold mr-1">
              Feedback saved!
            </span>
          )}

          {/* Ask Threat AI */}
          <button
            type="button"
            onClick={() =>
              openThreatAnalyst(
                `Perform in-depth hypothesis testing on prioritized research signal #${signal.id}: "${signal.title}". Relevance: ${signal.relevance_score}/100, Confidence: ${signal.confidence_score}%. Summary: ${signal.summary}. Recommended research: ${signal.recommended_research_area || "General reconnaissance"}. Outline step-by-step verification methods and safe proof-of-concept guidelines.`,
                `Signal #${signal.id}`
              )
            }
            className="rounded-lg bg-purple-500/15 hover:bg-purple-500/25 border border-purple-500/30 px-2.5 py-1 text-[11px] font-mono font-semibold text-purple-300 transition flex items-center gap-1 active:scale-95 shadow-sm"
            title="Ask AI Threat Analyst to evaluate this signal"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-purple-400 shadow-[0_0_6px_#c084fc]" />
            <span>ASK THREAT AI</span>
          </button>

          <button
            onClick={() => handleStatus("investigating")}
            disabled={busy || currentStatus === "investigating"}
            className={`rounded px-2.5 py-1 text-[11px] font-semibold transition ${
              currentStatus === "investigating"
                ? "bg-purple-900/60 text-purple-200 border border-purple-700"
                : "bg-cyan-500 text-slate-950 hover:bg-cyan-400 font-bold"
            }`}
          >
            {currentStatus === "investigating" ? "INVESTIGATING" : "INVESTIGATE"}
          </button>

          <button
            onClick={() => handleStatus("saved")}
            disabled={busy || currentStatus === "saved"}
            className="rounded border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-[11px] text-slate-300 hover:text-white"
          >
            {currentStatus === "saved" ? "SAVED" : "SAVE"}
          </button>

          <button
            onClick={() => handleStatus("ignored")}
            disabled={busy || currentStatus === "ignored"}
            className="rounded border border-slate-800 bg-slate-900 px-2 py-1 text-[11px] text-slate-500 hover:text-slate-300"
          >
            IGNORE
          </button>

          {/* Rapid Feedback */}
          <button
            onClick={() => handleFeedback("INTERESTING")}
            title="Mark as high-interest for ranking"
            className="rounded border border-slate-800 bg-slate-900 px-1.5 py-1 text-[11px] text-slate-400 hover:text-amber-400"
          >
            ★
          </button>
        </div>
      </div>
    </div>
  );
}
