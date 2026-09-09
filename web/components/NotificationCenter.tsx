"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Alert } from "@/lib/types";
import { usePreferences } from "@/lib/preferences";

// 50+ Real Event Types & Semantic Tone Configurations
export type NotificationEventType =
  | "NEW_ASSET"
  | "ASSET_REMOVED"
  | "SCOPE_CHANGED"
  | "PROGRAM_CHANGED"
  | "NEW_VULNERABILITY"
  | "NEW_ADVISORY"
  | "KEV_UPDATE"
  | "EPSS_CHANGE"
  | "TECHNOLOGY_CHANGE"
  | "DNS_CHANGE"
  | "CERTIFICATE_CHANGE"
  | "GITHUB_CHANGE"
  | "RELEASE_DETECTED"
  | "SECURITY_EVENT"
  | "RESEARCH_SIGNAL"
  | "HIGH_PRIORITY_SIGNAL"
  | "NEW_EVIDENCE"
  | "EVIDENCE_CONFLICT"
  | "VERIFICATION_COMPLETED"
  | "PROVIDER_WARNING"
  | "PROVIDER_DEGRADED"
  | "PROVIDER_RECOVERED"
  | "PIPELINE_COMPLETED"
  | "PIPELINE_FAILED"
  | "COMPANY_CHANGED"
  | "TIMELINE_EVENT_ADDED"
  | "TIMELINE_EVENT_UPDATED"
  | "HISTORICAL_EVENT_DISCOVERED"
  | "NEW_PROGRAM"
  | "PROGRAM_CLOSED"
  | "PROGRAM_REOPENED"
  | "NEW_TARGET"
  | "TARGET_REMOVED"
  | "ALERT_ESCALATED"
  | "ALERT_RESOLVED"
  | "AI_ANALYSIS_COMPLETED"
  | "AI_ANALYSIS_FAILED"
  | "SYNC_COMPLETED"
  | "SYNC_DELAYED"
  | "SOURCE_STALE"
  | "SOURCE_RECOVERED"
  | "ADMIN_EVENT"
  | "PROFILE_CHANGE"
  | "PRIORITY_CHANGE"
  | "SYSTEM_MAINTENANCE"
  | "LIVE_CONNECTION_ESTABLISHED"
  | "LIVE_CONNECTION_LOST"
  | "NEW_RESEARCHER_NOTE"
  | "COMPARISON_READY"
  | "EXPORT_READY"
  | "REPORT_READY";

interface EventMetadata {
  label: string;
  tone: "rose" | "amber" | "cyan" | "emerald" | "purple" | "slate";
  icon: string;
}

export const NOTIFICATION_STATE_MAP: Record<NotificationEventType, EventMetadata> = {
  NEW_ASSET: { label: "New Asset Discovered", tone: "cyan", icon: "🌐" },
  ASSET_REMOVED: { label: "Asset Decommissioned", tone: "slate", icon: "🗑️" },
  SCOPE_CHANGED: { label: "Scope Boundary Modified", tone: "amber", icon: "🎯" },
  PROGRAM_CHANGED: { label: "Bounty Program Updated", tone: "cyan", icon: "📋" },
  NEW_VULNERABILITY: { label: "New Vulnerability Disclosed", tone: "rose", icon: "⚠️" },
  NEW_ADVISORY: { label: "Security Advisory Published", tone: "amber", icon: "📜" },
  KEV_UPDATE: { label: "CISA KEV Addition", tone: "rose", icon: "🛡️" },
  EPSS_CHANGE: { label: "EPSS Exploit Probability Spike", tone: "rose", icon: "📈" },
  TECHNOLOGY_CHANGE: { label: "Technology Stack Shift", tone: "purple", icon: "⚙️" },
  DNS_CHANGE: { label: "DNS Record Alteration", tone: "cyan", icon: "📡" },
  CERTIFICATE_CHANGE: { label: "TLS Certificate Transition", tone: "cyan", icon: "🔒" },
  GITHUB_CHANGE: { label: "Public Repository Delta", tone: "purple", icon: "🐙" },
  RELEASE_DETECTED: { label: "Software Release Detected", tone: "emerald", icon: "🚀" },
  SECURITY_EVENT: { label: "Security Event Observed", tone: "rose", icon: "🚨" },
  RESEARCH_SIGNAL: { label: "Research Signal Generated", tone: "cyan", icon: "💡" },
  HIGH_PRIORITY_SIGNAL: { label: "High Priority Signal", tone: "rose", icon: "🔥" },
  NEW_EVIDENCE: { label: "Forensic Evidence Linked", tone: "emerald", icon: "🔎" },
  EVIDENCE_CONFLICT: { label: "Evidence Conflict Flagged", tone: "amber", icon: "⚖️" },
  VERIFICATION_COMPLETED: { label: "Data Truth Verified", tone: "emerald", icon: "✅" },
  PROVIDER_WARNING: { label: "Provider Latency Warning", tone: "amber", icon: "⚠️" },
  PROVIDER_DEGRADED: { label: "Provider Status Degraded", tone: "rose", icon: "📉" },
  PROVIDER_RECOVERED: { label: "Provider Fully Operational", tone: "emerald", icon: "🔋" },
  PIPELINE_COMPLETED: { label: "9-Stage Ingestion Finished", tone: "emerald", icon: "🏁" },
  PIPELINE_FAILED: { label: "Pipeline Stage Failed", tone: "rose", icon: "❌" },
  COMPANY_CHANGED: { label: "Company Profile Shift", tone: "cyan", icon: "🏢" },
  TIMELINE_EVENT_ADDED: { label: "Milestone Added to Timeline", tone: "cyan", icon: "⏱️" },
  TIMELINE_EVENT_UPDATED: { label: "Timeline Record Refined", tone: "cyan", icon: "✏️" },
  HISTORICAL_EVENT_DISCOVERED: { label: "Historical Event Correlated", tone: "purple", icon: "🏛️" },
  NEW_PROGRAM: { label: "Public Bounty Program Enrolled", tone: "emerald", icon: "⭐" },
  PROGRAM_CLOSED: { label: "Program Discontinued", tone: "slate", icon: "🛑" },
  PROGRAM_REOPENED: { label: "Program Resumed", tone: "emerald", icon: "🔄" },
  NEW_TARGET: { label: "Authorized Target Enrolled", tone: "cyan", icon: "🎯" },
  TARGET_REMOVED: { label: "Target Scope Discontinued", tone: "slate", icon: "⛔" },
  ALERT_ESCALATED: { label: "Alert Escalated to Critical", tone: "rose", icon: "🔺" },
  ALERT_RESOLVED: { label: "Alert Remediation Confirmed", tone: "emerald", icon: "✓" },
  AI_ANALYSIS_COMPLETED: { label: "Advisory Analysis Completed", tone: "cyan", icon: "🛡️" },
  AI_ANALYSIS_FAILED: { label: "Analysis Pipeline Retrying", tone: "amber", icon: "⌛" },
  SYNC_COMPLETED: { label: "Source Telemetry Synchronized", tone: "emerald", icon: "🔄" },
  SYNC_DELAYED: { label: "Telemetry Polling Delayed", tone: "amber", icon: "⏳" },
  SOURCE_STALE: { label: "Feed Inactivity Detected", tone: "amber", icon: "⚠️" },
  SOURCE_RECOVERED: { label: "Feed Live Stream Restored", tone: "emerald", icon: "🌊" },
  ADMIN_EVENT: { label: "Administrative Audit Event", tone: "amber", icon: "⚡" },
  PROFILE_CHANGE: { label: "Operator Settings Saved", tone: "cyan", icon: "👤" },
  PRIORITY_CHANGE: { label: "Target Priority Reclassified", tone: "cyan", icon: "📌" },
  SYSTEM_MAINTENANCE: { label: "Platform Maintenance Window", tone: "slate", icon: "🛠️" },
  LIVE_CONNECTION_ESTABLISHED: { label: "Live Telemetry Connected", tone: "emerald", icon: "🟢" },
  LIVE_CONNECTION_LOST: { label: "Live Telemetry Reconnecting", tone: "rose", icon: "🔴" },
  NEW_RESEARCHER_NOTE: { label: "Field Note Logged", tone: "cyan", icon: "📝" },
  COMPARISON_READY: { label: "Attack Surface Diff Ready", tone: "purple", icon: "📊" },
  EXPORT_READY: { label: "Intelligence Export Available", tone: "emerald", icon: "💾" },
  REPORT_READY: { label: "Comprehensive Briefing Prepared", tone: "emerald", icon: "📄" },
};

/**
 * Web Audio Synthesizer Pulse (Opt-in)
 */
function playAcousticChime() {
  if (typeof window === "undefined") return;
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const now = ctx.currentTime;

    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = "sine";
    osc1.frequency.setValueAtTime(880, now);
    osc1.frequency.exponentialRampToValueAtTime(1320, now + 0.12);

    gain1.gain.setValueAtTime(0.08, now);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.2);

    osc1.connect(gain1);
    gain1.connect(ctx.destination);

    osc1.start(now);
    osc1.stop(now + 0.2);
  } catch {
    // AudioContext blocked by browser autoplay policy
  }
}

interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function NotificationCenter({ isOpen, onClose }: NotificationCenterProps) {
  const router = useRouter();
  const { preferences } = usePreferences();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [activeTab, setActiveTab] = useState<"ALL" | "CRITICAL" | "UNREAD">("ALL");
  const [loading, setLoading] = useState(false);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<Alert[]>("/api/v1/alerts");
      if (Array.isArray(data)) {
        setAlerts(data);
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchAlerts();
    }
  }, [isOpen, fetchAlerts]);

  const markAsRead = async (alertId: number) => {
    try {
      await apiFetch(`/api/v1/alerts/${alertId}/read`, { method: "PATCH" }).catch(async () => {
        await apiFetch(`/api/v1/alerts/${alertId}/read`, { method: "POST" });
      });
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, read: true } : a)));
    } catch {
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, read: true } : a)));
    }
  };

  const markAllRead = async () => {
    try {
      await apiFetch("/api/v1/alerts/read-all", { method: "POST" }).catch(async () => {
        await apiFetch("/api/v1/alerts/mark-all-read", { method: "POST" });
      });
      setAlerts((prev) => prev.map((a) => ({ ...a, read: true })));
    } catch {
      setAlerts((prev) => prev.map((a) => ({ ...a, read: true })));
    }
  };

  // Classify alert into one of the 50+ event types
  const classifyAlert = (alert: Alert): EventMetadata => {
    const title = (alert.title || "").toLowerCase();
    const type = (alert.alert_type || "").toUpperCase();

    if (type.includes("KEV") || title.includes("cisa") || title.includes("kev")) {
      return NOTIFICATION_STATE_MAP.KEV_UPDATE;
    }
    if (type.includes("VULN") || title.includes("vulnerability") || title.includes("cve")) {
      return NOTIFICATION_STATE_MAP.NEW_VULNERABILITY;
    }
    if (type.includes("SCOPE") || title.includes("scope")) {
      return NOTIFICATION_STATE_MAP.SCOPE_CHANGED;
    }
    if (type.includes("ASSET") || title.includes("subdomain") || title.includes("domain")) {
      return NOTIFICATION_STATE_MAP.NEW_ASSET;
    }
    if (type.includes("TECH") || title.includes("technology") || title.includes("server")) {
      return NOTIFICATION_STATE_MAP.TECHNOLOGY_CHANGE;
    }
    if (type.includes("SIGNAL") || title.includes("signal")) {
      return alert.priority === "CRITICAL"
        ? NOTIFICATION_STATE_MAP.HIGH_PRIORITY_SIGNAL
        : NOTIFICATION_STATE_MAP.RESEARCH_SIGNAL;
    }
    if (alert.priority === "CRITICAL") {
      return NOTIFICATION_STATE_MAP.ALERT_ESCALATED;
    }
    return NOTIFICATION_STATE_MAP.SECURITY_EVENT;
  };

  const filteredAlerts = useMemo(() => {
    return alerts.filter((a) => {
      if (activeTab === "CRITICAL") return a.priority === "CRITICAL" || a.priority === "HIGH";
      if (activeTab === "UNREAD") return !a.read;
      return true;
    });
  }, [alerts, activeTab]);

  const unreadCount = alerts.filter((a) => !a.read).length;

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-slate-950/60 backdrop-blur-sm animate-surface-in"
      onClick={onClose}
    >
      <div
        className="flex h-full w-full max-w-md flex-col border-l border-slate-800 bg-slate-950/95 shadow-2xl backdrop-blur-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800/80 px-5 py-4 bg-slate-900/40">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-3 w-3">
              {unreadCount > 0 && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
              )}
              <span className={`relative inline-flex rounded-full h-3 w-3 ${unreadCount > 0 ? "bg-rose-500" : "bg-emerald-500"}`} />
            </span>
            <h2 className="text-base font-bold text-white font-display tracking-tight">
              Intelligence Dispatch
            </h2>
            {unreadCount > 0 && (
              <span className="rounded-full bg-rose-500/20 px-2 py-0.5 font-mono text-[10px] font-bold text-rose-300 border border-rose-500/30">
                {unreadCount} NEW
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300 hover:underline"
              >
                Mark all read
              </button>
            )}
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition"
              title="Close dispatch (ESC)"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 border-b border-slate-800/80 px-5 py-2.5 bg-slate-950/50">
          {(["ALL", "CRITICAL", "UNREAD"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`rounded-lg px-3 py-1 font-mono text-xs font-semibold transition ${
                activeTab === tab
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Notifications Feed */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5 scrollbar-thin">
          {loading ? (
            <div className="py-20 text-center font-mono text-xs text-slate-500">
              POLLING INTELLIGENCE DISPATCH...
            </div>
          ) : filteredAlerts.length === 0 ? (
            <div className="py-24 text-center">
              <span className="text-3xl">🛡️</span>
              <p className="mt-2 text-xs font-mono text-slate-400 uppercase">
                Zero Pending Intelligence Alerts
              </p>
              <p className="text-[11px] text-slate-600 mt-1">
                Surface observations and signals will populate here automatically.
              </p>
            </div>
          ) : (
            filteredAlerts.map((item) => {
              const meta = classifyAlert(item);
              return (
                <div
                  key={item.id}
                  className={`group relative rounded-xl border p-3.5 transition-all duration-200 ${
                    !item.read
                      ? "border-cyan-500/30 bg-cyan-950/20 shadow-[0_0_15px_rgba(0,240,255,0.05)]"
                      : "border-slate-800/70 bg-slate-900/40 opacity-80"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-base">{meta.icon}</span>
                      <span
                        className={`rounded px-1.5 py-0.2 font-mono text-[9px] font-bold uppercase border ${
                          meta.tone === "rose"
                            ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                            : meta.tone === "amber"
                            ? "bg-amber-500/15 text-amber-300 border-amber-500/30"
                            : meta.tone === "purple"
                            ? "bg-purple-500/15 text-purple-300 border-purple-500/30"
                            : meta.tone === "emerald"
                            ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                            : "bg-cyan-500/15 text-cyan-300 border-cyan-500/30"
                        }`}
                      >
                        {meta.label}
                      </span>
                    </div>

                    {!item.read && (
                      <button
                        onClick={() => markAsRead(item.id)}
                        className="text-[10px] font-mono text-slate-400 hover:text-cyan-300"
                        title="Acknowledge"
                      >
                        ✓
                      </button>
                    )}
                  </div>

                  <h3 className="mt-2 text-xs font-semibold text-white group-hover:text-cyan-200 transition">
                    {item.title}
                  </h3>

                  {(item.summary || (item as any).message) && (
                    <p className="mt-1 text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                      {item.summary || (item as any).message}
                    </p>
                  )}

                  <div className="mt-3 flex items-center justify-between border-t border-slate-800/60 pt-2 text-[10px] font-mono text-slate-500">
                    <span>{new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    <button
                      onClick={() => {
                        onClose();
                        router.push("/alerts");
                      }}
                      className="text-cyan-400 hover:underline font-semibold"
                    >
                      Investigate &rarr;
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-800/80 p-3 bg-slate-950 text-center">
          <button
            onClick={() => {
              onClose();
              router.push("/alerts");
            }}
            className="w-full rounded-xl bg-slate-900 border border-slate-800 py-2 font-mono text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition"
          >
            VIEW FULL DISPATCH ARCHIVE
          </button>
        </div>
      </div>
    </div>
  );
}
