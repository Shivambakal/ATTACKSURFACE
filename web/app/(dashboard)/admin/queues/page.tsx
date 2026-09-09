"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface QueueInfo {
  name: string;
  length: number;
  failed_count: number;
  is_empty: boolean;
}

interface QueueTelemetry {
  total_queued: number;
  queues: QueueInfo[];
  redis_connected: boolean;
}

interface ActivityItem {
  id: number;
  type: string;
  source_id: number;
  source_name: string;
  company_name: string;
  status: string;
  http_status: number;
  items_found: number;
  items_changed: number;
  duration_ms: number;
  response_bytes: number;
  timestamp: string;
}

export default function AdminQueuesPage() {
  const [queues, setQueues] = useState<QueueTelemetry | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [q, act] = await Promise.all([
        apiFetch<QueueTelemetry>("/api/v1/admin/queues").catch(() => null),
        apiFetch<ActivityItem[]>("/api/v1/admin/activity?limit=25").catch(() => []),
      ]);
      setQueues(q);
      setActivity(act || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
        <Link href="/admin" className="text-amber-400 hover:underline">Admin Console</Link>
        <span>/</span>
        <span className="text-white">Queues &amp; Workers</span>
      </div>

      {/* Header */}
      <div className="bg-slate-900/90 border border-amber-500/20 rounded-xl p-6 shadow-xl backdrop-blur">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
              </svg>
            </span>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">RQ Queue Depths &amp; Live Activity</h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Real-time job queues, worker status, and live collection run logs.
              </p>
            </div>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="px-3.5 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition"
          >
            {loading ? "Refreshing..." : "↻ Refresh"}
          </button>
        </div>
      </div>

      {/* Queue Depths Cards */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-white">Priority Queue Telemetry</h3>
          <span className="text-xs text-amber-300 font-mono bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
            Total In Queue: {queues?.total_queued ?? 0}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {queues?.queues.map((q) => (
            <div key={q.name} className="bg-slate-950 border border-slate-800/80 rounded-lg p-3">
              <div className="text-[11px] font-mono text-slate-400 truncate">{q.name}</div>
              <div className="text-2xl font-mono font-bold text-white mt-1">{q.length}</div>
              <div className="text-[10px] text-slate-400 mt-1 flex items-center justify-between">
                <span>Failed: {q.failed_count}</span>
                <span className={`w-2 h-2 rounded-full ${q.is_empty ? "bg-slate-600" : "bg-cyan-400 animate-pulse"}`} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Live Collection Runs Stream */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <div className="p-5 border-b border-slate-800">
          <h3 className="text-base font-semibold text-white">Recent Collection Runs</h3>
          <p className="text-xs text-slate-400 mt-0.5">Chronological record of recent source fetches, payload sizes, and durations.</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Time</th>
                <th className="py-3 px-4">Source</th>
                <th className="py-3 px-4">Company</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">HTTP</th>
                <th className="py-3 px-4">Items (Found / Changed)</th>
                <th className="py-3 px-4">Duration</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {activity.map((a) => (
                <tr key={a.id} className="hover:bg-slate-850/50">
                  <td className="py-3 px-4 font-mono text-slate-400">{new Date(a.timestamp).toLocaleTimeString()}</td>
                  <td className="py-3 px-4 font-semibold text-slate-200">{a.source_name}</td>
                  <td className="py-3 px-4 text-slate-400">{a.company_name}</td>
                  <td className="py-3 px-4 font-mono font-bold">
                    <span className={`px-2 py-0.5 rounded text-[10px] ${
                      a.status === "SUCCESS_CHANGED" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" :
                      a.status === "SUCCESS_UNCHANGED" ? "bg-slate-800 text-slate-400" : "bg-rose-500/10 text-rose-400"
                    }`}>
                      {a.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-300">{a.http_status || "--"}</td>
                  <td className="py-3 px-4 font-mono text-slate-300">{a.items_found} / {a.items_changed}</td>
                  <td className="py-3 px-4 font-mono text-slate-400">{a.duration_ms} ms</td>
                </tr>
              ))}
              {activity.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No recent runs recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
