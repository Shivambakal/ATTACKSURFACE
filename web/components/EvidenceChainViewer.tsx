"use client";

import React, { useState } from "react";

export type EvidenceStatus = "VERIFIED" | "SUPPORTED" | "CANDIDATE" | "UNVERIFIED" | "CONTEXT_ONLY";

export interface EvidenceItem {
  id: string | number;
  claim: string;
  evidence: string;
  source: string;
  sourceType?: string;
  observationMethod?: string;
  timestamp: string;
  entity: string;
  confidenceScore: number; // 0 - 100
  status: EvidenceStatus;
  aiAnalysis?: {
    reasoningSummary: string;
    modelName: string;
    whyItMatters: string;
    suggestedInvestigation: string;
  };
}

interface EvidenceChainViewerProps {
  items: EvidenceItem[];
  title?: string;
}

const STATUS_CONFIG: Record<EvidenceStatus, { label: string; tone: string; dot: string; desc: string }> = {
  VERIFIED: {
    label: "VERIFIED",
    tone: "border-emerald-500/40 text-emerald-300 bg-emerald-950/20",
    dot: "bg-emerald-400 shadow-[0_0_8px_#10b981]",
    desc: "Cryptographically or authoritatively corroborated by official security source",
  },
  SUPPORTED: {
    label: "SUPPORTED",
    tone: "border-cyan-500/40 text-cyan-300 bg-cyan-950/20",
    dot: "bg-cyan-400 shadow-[0_0_8px_#00f0ff]",
    desc: "Corroborated by independent telemetry feeds or multi-source consensus",
  },
  CANDIDATE: {
    label: "CANDIDATE",
    tone: "border-amber-500/40 text-amber-300 bg-amber-950/20",
    dot: "bg-amber-400 shadow-[0_0_8px_#f59e0b]",
    desc: "Preliminary signal awaiting second-factor telemetry verification",
  },
  UNVERIFIED: {
    label: "UNVERIFIED",
    tone: "border-slate-700 text-slate-400 bg-slate-900/30",
    dot: "bg-slate-500",
    desc: "Unconfirmed observation; do not treat as ground truth",
  },
  CONTEXT_ONLY: {
    label: "CONTEXT ONLY",
    tone: "border-purple-500/40 text-purple-300 bg-purple-950/20",
    dot: "bg-purple-400",
    desc: "Contextual background without direct vulnerability attribution",
  },
};

export default function EvidenceChainViewer({
  items,
  title = "Forensic Evidence & Provenance Chain",
}: EvidenceChainViewerProps) {
  const [expandedId, setExpandedId] = useState<string | number | null>(items[0]?.id ?? null);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-5 shadow-xl backdrop-blur-md space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 shadow-[0_0_10px_#00f0ff]" />
          <h2 className="text-base font-bold text-white font-display tracking-tight">
            {title}
          </h2>
        </div>
        <span className="font-mono text-xs text-slate-400">
          {items.length} Forensic Claims
        </span>
      </div>

      <div className="space-y-3">
        {items.map((item) => {
          const isExpanded = expandedId === item.id;
          const statusCfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.UNVERIFIED;

          return (
            <div
              key={item.id}
              className={`rounded-xl border transition-all duration-200 overflow-hidden ${
                isExpanded
                  ? "border-cyan-500/40 bg-slate-900/60 shadow-[0_0_20px_rgba(0,240,255,0.05)]"
                  : "border-slate-800/80 bg-slate-900/30 hover:border-slate-700"
              }`}
            >
              {/* Claim Header Bar */}
              <div
                onClick={() => setExpandedId(isExpanded ? null : item.id)}
                className="flex items-center justify-between p-3.5 cursor-pointer"
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  <span className={`h-2 w-2 rounded-full shrink-0 ${statusCfg.dot}`} />
                  <div className="overflow-hidden">
                    <span className="font-mono text-[10px] text-slate-500 block uppercase">
                      CLAIM: {item.entity}
                    </span>
                    <h3 className="text-xs font-bold text-white truncate">
                      {item.claim}
                    </h3>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span
                    className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold uppercase border ${statusCfg.tone}`}
                    title={statusCfg.desc}
                  >
                    {statusCfg.label}
                  </span>
                  <span className="font-mono text-xs font-bold text-cyan-400">
                    {item.confidenceScore}% CONF
                  </span>
                  <span className="font-mono text-xs text-slate-500">
                    {isExpanded ? "▲" : "▼"}
                  </span>
                </div>
              </div>

              {/* Expanded Hierarchical Forensic Chain */}
              {isExpanded && (
                <div className="border-t border-slate-800/80 p-4 space-y-4 bg-slate-950/60 animate-surface-in">
                  {/* Step 1 to 7 Vertical Flow */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    {/* Left: Telemetry Details */}
                    <div className="space-y-3 font-mono">
                      <div className="rounded-lg bg-slate-900/80 p-3 border border-slate-800">
                        <span className="text-[10px] uppercase text-slate-500 block">
                          1. Raw Evidence Payload
                        </span>
                        <p className="mt-1 text-slate-200 font-sans text-xs">
                          {item.evidence}
                        </p>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800">
                          <span className="text-[10px] uppercase text-slate-500 block">
                            2. Source Authority
                          </span>
                          <span className="mt-0.5 block text-cyan-300 font-bold truncate">
                            {item.source}
                          </span>
                        </div>

                        <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800">
                          <span className="text-[10px] uppercase text-slate-500 block">
                            3. Observation Method
                          </span>
                          <span className="mt-0.5 block text-slate-300 truncate">
                            {item.observationMethod || "Direct HTTP / DNS probe"}
                          </span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800">
                          <span className="text-[10px] uppercase text-slate-500 block">
                            4. Timestamp Observed
                          </span>
                          <span className="mt-0.5 block text-slate-300">
                            {new Date(item.timestamp).toLocaleString()}
                          </span>
                        </div>

                        <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800">
                          <span className="text-[10px] uppercase text-slate-500 block">
                            5. Confidence Rating
                          </span>
                          <div className="mt-1 flex items-center gap-2">
                            <div className="h-1.5 flex-1 rounded-full bg-slate-800 overflow-hidden">
                              <div
                                className="h-full bg-cyan-400 rounded-full"
                                style={{ width: `${item.confidenceScore}%` }}
                              />
                            </div>
                            <span className="text-cyan-300 font-bold">
                              {item.confidenceScore}%
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Right: Distinct AI Analysis Layer (if available) */}
                    {item.aiAnalysis ? (
                      <div className="rounded-xl border border-purple-500/40 bg-purple-950/20 p-4 space-y-3">
                        <div className="flex items-center justify-between border-b border-purple-500/30 pb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-base">🧠</span>
                            <span className="font-mono text-xs font-bold text-purple-300 tracking-wider">
                              AI ANALYSIS (HEURISTIC)
                            </span>
                          </div>
                          <span className="rounded bg-purple-900/60 px-1.5 py-0.2 font-mono text-[9px] text-purple-300 border border-purple-700/50">
                            {item.aiAnalysis.modelName}
                          </span>
                        </div>

                        <div>
                          <span className="text-[10px] font-mono uppercase text-purple-400 block">
                            Reasoning Summary
                          </span>
                          <p className="mt-1 text-slate-200 text-xs leading-relaxed">
                            {item.aiAnalysis.reasoningSummary}
                          </p>
                        </div>

                        <div>
                          <span className="text-[10px] font-mono uppercase text-purple-400 block">
                            Why It Matters
                          </span>
                          <p className="mt-1 text-slate-300 text-xs leading-relaxed">
                            {item.aiAnalysis.whyItMatters}
                          </p>
                        </div>

                        <div>
                          <span className="text-[10px] font-mono uppercase text-purple-400 block">
                            What to Investigate Next
                          </span>
                          <p className="mt-1 text-cyan-300 text-xs font-mono">
                            {item.aiAnalysis.suggestedInvestigation}
                          </p>
                        </div>

                        <div className="pt-2 border-t border-purple-500/20 text-[10px] font-mono text-purple-400/80">
                          Note: AI hypotheses require verified confirmation through dynamic security telemetry.
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center rounded-xl border border-dashed border-slate-800 p-6 text-center text-xs font-mono text-slate-500">
                        Raw verified observation without automated model synthesis
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
