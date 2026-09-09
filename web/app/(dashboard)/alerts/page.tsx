"use client";

import React, { useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { Alert } from "@/lib/types";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
                className={`rounded-xl border p-4 transition ${
                  alert.read
                    ? "border-slate-800/80 bg-slate-900/40 text-slate-400"
                    : isCritical
                    ? "border-l-4 border-l-red-500 border-slate-800 bg-red-950/20 text-slate-100"
                    : isHigh
                    ? "border-l-4 border-l-amber-500 border-slate-800 bg-amber-950/20 text-slate-100"
                    : "border-l-4 border-l-cyan-400 border-slate-800 bg-slate-900/80 text-slate-100"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-cyan-950 px-2 py-0.5 font-mono text-[10px] uppercase text-cyan-300 border border-cyan-800">
                        {alert.alert_type}
                      </span>
                      <span
                        className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                          isCritical
                            ? "bg-red-950 text-red-300 border border-red-800"
                            : isHigh
                            ? "bg-amber-950 text-amber-300 border border-amber-800"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {alert.priority}
                      </span>
                      {!alert.read && (
                        <span className="rounded-full bg-cyan-400 px-1.5 py-0.2 font-mono text-[9px] font-bold text-slate-950">
                          NEW
                        </span>
                      )}
                    </div>

                    <h3 className="text-xs font-semibold text-slate-100">{alert.title}</h3>
                    {alert.summary && (
                      <p className="text-xs text-slate-300 font-sans leading-relaxed">
                        {alert.summary}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {!alert.read && (
                      <button
                        onClick={() => markAsRead(alert.id)}
                        className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 font-mono text-[10px] text-cyan-300 hover:bg-slate-700"
                      >
                        MARK READ
                      </button>
                    )}
                  </div>
                </div>

                <div className="mt-2.5 flex items-center justify-between border-t border-slate-800/60 pt-2 font-mono text-[10px] text-slate-500">
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
