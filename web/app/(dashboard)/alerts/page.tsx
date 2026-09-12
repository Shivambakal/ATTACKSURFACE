"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Alert } from "@/lib/types";
import { openThreatAnalyst } from "@/components/CyberAssistantChat";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const handleCopyAlert = (alert: Alert) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(JSON.stringify(alert, null, 2));
      setCopiedId(alert.id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  // Filters
  const [filterPriority, setFilterPriority] = useState("ALL");
  const [filterRead, setFilterRead] = useState<"ALL" | "UNREAD" | "READ">("ALL");

  const loadAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<Alert[]>("/api/v1/alerts");
      setAlerts(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  const markAsRead = async (id: number) => {
    try {
      await apiFetch(`/api/v1/alerts/${id}/read`, { method: "PATCH" }).catch(async () => {
        await apiFetch(`/api/v1/alerts/${id}/read`, { method: "POST" });
      });
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, read: true } : a)));
    } catch {
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, read: true } : a)));
    }
  };

  const markAllAsRead = async () => {
    try {
      await apiFetch("/api/v1/alerts/read-all", { method: "POST" }).catch(async () => {
        await apiFetch("/api/v1/alerts/mark-all-read", { method: "POST" });
      });
      setAlerts((prev) => prev.map((a) => ({ ...a, read: true })));
    } catch {
      setAlerts((prev) => prev.map((a) => ({ ...a, read: true })));
    }
  };

  const filteredAlerts = alerts.filter((alert) => {
    const matchesPriority =
      filterPriority === "ALL" || alert.priority?.toUpperCase() === filterPriority;
    const matchesRead =
      filterRead === "ALL" ||
      (filterRead === "UNREAD" && !alert.read) ||
      (filterRead === "READ" && alert.read);
    return matchesPriority && matchesRead;
  });

  const unreadCount = alerts.filter((a) => !a.read).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs uppercase tracking-wider text-cyan-400">
              DISPATCH
            </span>
          </div>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-white">
            Security Intelligence Alerts
          </h2>
          <p className="text-xs text-slate-400">
            Real-time differential notifications, high-risk surface shifts, and KEV exposures.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 font-mono text-xs text-slate-300 hover:border-cyan-500 hover:text-cyan-300"
            >
              ✓ MARK ALL AS READ ({unreadCount})
            </button>
          )}
          <button
            onClick={loadAlerts}
            className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 font-mono text-xs text-slate-300 hover:bg-slate-800"
          >
            ↻ REFRESH
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-slate-400">STATE:</span>
          {(["ALL", "UNREAD", "READ"] as const).map((r) => (
            <button
              key={r}
              onClick={() => setFilterRead(r)}
              className={`rounded px-2.5 py-1 font-mono text-[10px] font-semibold transition ${
                filterRead === r
                  ? "bg-cyan-500 text-slate-950"
                  : "bg-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              {r}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-slate-400">PRIORITY:</span>
          {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((pr) => (
            <button
              key={pr}
              onClick={() => setFilterPriority(pr)}
              className={`rounded px-2 py-0.5 font-mono text-[10px] transition ${
                filterPriority === pr
                  ? "bg-slate-700 text-cyan-300 font-bold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {pr}
            </button>
          ))}
        </div>
      </div>

      {/* Alerts Stream */}
      {loading ? (
        <div className="py-20 text-center font-mono text-xs text-cyan-400">
          POLLING DISPATCH QUEUE...
        </div>
      ) : filteredAlerts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 p-16 text-center text-xs text-slate-500 font-mono">
          NO ALERTS FOUND MATCHING CRITERIA.
        </div>
      ) : (
        <div className="space-y-3">
          {filteredAlerts.map((alert) => {
            const isCritical = alert.priority === "CRITICAL";
            const isHigh = alert.priority === "HIGH";

            return (
              <div
                key={alert.id}
                className={`rounded-2xl border p-5 transition-all card-25d backdrop-blur-xl ${
                  alert.read
                    ? "border-white/[0.06] bg-[#070b14]/50 text-slate-400"
                    : isCritical
                    ? "border-l-4 border-l-rose-500 border-white/[0.08] bg-[#070b14]/85 text-slate-100 shadow-[0_0_20px_rgba(244,63,94,0.15)]"
                    : isHigh
                    ? "border-l-4 border-l-amber-500 border-white/[0.08] bg-[#070b14]/85 text-slate-100 shadow-[0_0_20px_rgba(245,158,11,0.15)]"
                    : "border-l-4 border-l-cyan-400 border-white/[0.08] bg-[#070b14]/85 text-slate-100 shadow-[0_0_20px_rgba(6,182,212,0.15)]"
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-cyan-950/80 px-2 py-0.5 font-mono text-[10px] uppercase text-cyan-300 border border-cyan-800/60 font-bold">
                        {alert.alert_type}
                      </span>
                      <span
                        className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                          isCritical
                            ? "bg-rose-950/80 text-rose-300 border border-rose-800/60"
                            : isHigh
                            ? "bg-amber-950/80 text-amber-300 border border-amber-800/60"
                            : "bg-white/[0.05] text-slate-300 border border-white/[0.08]"
                        }`}
                      >
                        {alert.priority}
                      </span>
                      {!alert.read && (
                        <span className="rounded-full bg-cyan-400 px-2 py-0.5 font-mono text-[9px] font-bold text-slate-950 animate-pulse">
                          UNREAD DISPATCH
                        </span>
                      )}
                    </div>

                    <h3 className="text-sm font-bold text-white tracking-tight">{alert.title}</h3>
                    {alert.summary && (
                      <p className="text-xs text-slate-300 font-sans leading-relaxed">
                        {alert.summary}
                      </p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    {/* Ask Threat AI */}
                    <button
                      type="button"
                      onClick={() =>
                        openThreatAnalyst(
                          `Perform threat assessment on security dispatch alert: "${alert.title}". Type: ${alert.alert_type}. Priority: ${alert.priority}. Summary: ${alert.summary || "No details provided"}. What is the recommended remediation and verification path?`,
                          `Alert: ${alert.title.slice(0, 30)}`
                        )
                      }
                      className="rounded-lg bg-purple-500/15 hover:bg-purple-500/25 border border-purple-500/30 px-2.5 py-1 font-mono text-xs font-semibold text-purple-300 transition flex items-center gap-1.5 active:scale-95 shadow-sm"
                      title="Investigate this alert with AI Threat Analyst"
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-purple-400 shadow-[0_0_6px_#c084fc]" />
                      <span>ASK THREAT AI</span>
                    </button>

                    {/* Copy Payload */}
                    <button
                      type="button"
                      onClick={() => handleCopyAlert(alert)}
                      className="rounded-lg border border-white/[0.08] bg-white/[0.05] hover:bg-white/[0.1] px-2.5 py-1 font-mono text-xs text-slate-300 transition"
                      title="Copy alert JSON payload"
                    >
                      {copiedId === alert.id ? "✓ COPIED" : "COPY RAW"}
                    </button>

                    {/* Surface Diffs */}
                    <Link
                      href="/changes"
                      className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 px-2.5 py-1 font-mono text-xs text-cyan-300 transition"
                    >
                      DIFFS &rarr;
                    </Link>

                    {/* Mark Read */}
                    {!alert.read && (
                      <button
                        onClick={() => markAsRead(alert.id)}
                        className="rounded-lg bg-cyan-500 px-2.5 py-1 font-mono text-xs font-bold text-slate-950 hover:bg-cyan-400 transition shadow-sm"
                      >
                        MARK READ
                      </button>
                    )}
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between border-t border-white/[0.08] pt-2 font-mono text-[10px] text-slate-400">
                  <span>Alert ID: #{alert.id}</span>
                  <span>Received: {new Date(alert.created_at).toLocaleString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
