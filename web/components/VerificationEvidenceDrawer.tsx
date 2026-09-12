"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { apiFetch } from "@/lib/api";
import VerificationStatusBadge, { VerificationState } from "./VerificationStatusBadge";

interface ClaimDetail {
  claim_id: number;
  claim_type: string;
  title?: string;
  summary?: string;
  state: VerificationState;
  confidence: number;
  evidence_chain?: Array<{ step: string; value: string }>;
  evidence_records?: Array<{ state: string; payload: Record<string, unknown> }>;
  score_factors: Record<string, unknown>;
  ai_influenced: boolean;
  computed_at: string;
  error?: string;
}

interface VerificationEvidenceDrawerProps {
  claimId: number | null;
  claimType?: "signal" | "change";
  isOpen: boolean;
  onClose: () => void;
  nodeTitle?: string;
  nodeValue?: string;
}

export default function VerificationEvidenceDrawer({
  claimId,
  claimType = "signal",
  isOpen,
  onClose,
  nodeTitle,
  nodeValue,
}: VerificationEvidenceDrawerProps) {
  const [detail, setDetail] = useState<ClaimDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  // Focus trap: focus close button when drawer opens
  useEffect(() => {
    if (isOpen && closeRef.current) {
      closeRef.current.focus();
    }
  }, [isOpen]);

  // Escape key closes drawer
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  // Fetch claim detail when drawer opens with a real claim ID
  useEffect(() => {
    if (!isOpen || claimId === null) {
      setDetail(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setDetail(null);

    apiFetch<ClaimDetail>(
      `/api/v1/verification/claims/${claimId}?claim_type=${claimType}`,
      { skipCache: true }
    )
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || "Failed to load evidence");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, claimId, claimType]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-[2px]"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Evidence drawer for ${nodeTitle ?? "verification node"}`}
        className="
          fixed right-0 top-0 bottom-0 z-50
          w-full max-w-sm sm:max-w-md
          flex flex-col
          bg-[#060a10]/98 border-l border-slate-800/80
          shadow-2xl backdrop-blur-2xl
          overflow-hidden
        "
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3 p-5 border-b border-slate-800/80">
          <div>
            <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-cyan-400/70 mb-1">
              VERIFICATION EVIDENCE
            </div>
            <div className="font-mono text-sm font-bold text-white leading-snug">
              {nodeTitle ?? "Node Evidence"}
            </div>
            {nodeValue && (
              <div className="font-mono text-2xl font-black text-white mt-0.5">
                {nodeValue}
              </div>
            )}
          </div>
          <button
            ref={closeRef}
            onClick={onClose}
            aria-label="Close evidence drawer"
            className="
              flex-shrink-0 w-8 h-8 rounded-xl
              flex items-center justify-center
              border border-slate-700 text-slate-400
              hover:text-white hover:border-slate-500
              transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/80
            "
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Loading */}
          {loading && (
            <div className="space-y-3" aria-live="polite" aria-label="Loading evidence">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 rounded-xl bg-slate-900/60 animate-pulse" />
              ))}
            </div>
          )}

          {/* Error */}
          {!loading && error && (
            <div
              role="alert"
              className="rounded-2xl border border-rose-800/60 bg-rose-950/40 p-4 text-center"
            >
              <div className="font-mono text-xs font-bold text-rose-400 uppercase tracking-wider mb-1">
                EVIDENCE UNAVAILABLE
              </div>
              <div className="font-mono text-[10px] text-rose-500/70">{error}</div>
              <div className="font-mono text-[9px] text-slate-600 mt-2">
                This does not fabricate any verification state. The claim remains at its current state.
              </div>
            </div>
          )}

          {/* No claim ID (node showing aggregate count) */}
          {!loading && !error && claimId === null && (
            <div className="rounded-2xl border border-slate-800/60 bg-slate-900/30 p-5 text-center">
              <div className="font-mono text-xs text-slate-400 mb-2">AGGREGATE METRIC</div>
              <p className="font-mono text-[11px] text-slate-500 leading-relaxed">
                This node displays an aggregated count from the database.
                Click an individual record in the feed to view its specific evidence chain.
              </p>
            </div>
          )}

          {/* Claim detail loaded */}
          {!loading && !error && detail && (
            <>
              {/* State badge */}
              <div className="flex items-center gap-3">
                <VerificationStatusBadge state={detail.state} size="md" />
                {detail.ai_influenced && (
                  <span className="font-mono text-[9px] text-yellow-400/70 uppercase tracking-widest border border-yellow-800/50 bg-yellow-950/30 px-2 py-0.5 rounded-lg">
                    AI INFLUENCED
                  </span>
                )}
              </div>

              {/* Confidence */}
              {detail.confidence != null && (
                <div>
                  <div className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-1.5">
                    CONFIDENCE
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-500 to-emerald-500 rounded-full transition-all duration-700"
                        style={{ width: `${Math.min(100, detail.confidence)}%` }}
                      />
                    </div>
                    <span className="font-mono text-xs font-bold text-white tabular-nums">
                      {typeof detail.confidence === "number" && detail.confidence <= 1
                        ? `${Math.round(detail.confidence * 100)}%`
                        : `${Math.round(detail.confidence)}%`}
                    </span>
                  </div>
                </div>
              )}

              {/* Evidence chain */}
              {detail.evidence_chain && detail.evidence_chain.length > 0 && (
                <div>
                  <div className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-2">
                    EVIDENCE CHAIN
                  </div>
                  <div className="space-y-1.5">
                    {detail.evidence_chain.map((step, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-3 rounded-xl border border-slate-800/60 bg-slate-900/40 px-3.5 py-2.5"
                      >
                        <span className="flex-shrink-0 w-5 h-5 rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center font-mono text-[8px] font-bold text-cyan-400">
                          {idx + 1}
                        </span>
                        <div className="min-w-0">
                          <div className="font-mono text-[9px] font-bold text-cyan-400/70 uppercase tracking-wider">
                            {step.step}
                          </div>
                          <div className="font-mono text-[10px] text-slate-300 mt-0.5 break-words">
                            {step.value}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Evidence records (for change type) */}
              {detail.evidence_records && detail.evidence_records.length > 0 && (
                <div>
                  <div className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-2">
                    CHANGE EVIDENCE RECORDS
                  </div>
                  <div className="space-y-2">
                    {detail.evidence_records.map((rec, idx) => (
                      <div
                        key={idx}
                        className="rounded-xl border border-slate-800/60 bg-slate-900/40 px-3.5 py-2.5"
                      >
                        <VerificationStatusBadge state={rec.state as VerificationState} size="xs" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Score factors (sanitized) */}
              {detail.score_factors && Object.keys(detail.score_factors).length > 0 && (
                <div>
                  <div className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-2">
                    SCORE FACTORS
                    {detail.ai_influenced && (
                      <span className="ml-2 text-yellow-400/60">⚠ AI keys detected</span>
                    )}
                  </div>
                  <div className="rounded-xl border border-slate-800/60 bg-slate-900/30 p-3 overflow-x-auto">
                    <pre className="font-mono text-[9px] text-slate-400 whitespace-pre-wrap">
                      {JSON.stringify(detail.score_factors, null, 2).slice(0, 600)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Computed at */}
              <div className="font-mono text-[9px] text-slate-600 border-t border-slate-800/60 pt-3">
                Computed: {new Date(detail.computed_at).toLocaleString()} · Source: database
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
