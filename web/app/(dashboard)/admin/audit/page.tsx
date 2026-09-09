"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface AuditEntry {
  id: string;
  type: string;
  action: string;
  actor: string;
  target: string;
  status: string;
  timestamp: string | null;
  detail?: string;
}

export default function AdminAuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");

  const loadAudit = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiFetch<AuditEntry[]>("/api/v1/admin/audit?limit=100");
      setEntries(Array.isArray(res) ? res : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load audit records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAudit();
  }, []);

  const filteredEntries = entries.filter((e) => {
    const matchesType = typeFilter === "ALL" || e.type === typeFilter;
    const q = searchTerm.toLowerCase().trim();
    const matchesSearch =
      !q ||
      e.action.toLowerCase().includes(q) ||
      e.actor.toLowerCase().includes(q) ||
      e.target.toLowerCase().includes(q) ||
      (e.detail && e.detail.toLowerCase().includes(q));
    return matchesType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Link
              href="/admin"
              className="text-xs font-mono text-slate-400 hover:text-slate-200 transition"
            >
              ADMIN
            </Link>
            <span className="text-xs text-slate-600">/</span>
            <span className="text-xs font-mono text-cyan-400">AUDIT</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
            System &amp; Pipeline Audit Trail
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Immutable chronological ledger of automated collection runs, intelligence syntheses, and security changes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadAudit}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-xs font-mono text-slate-200 transition disabled:opacity-50 flex items-center gap-2"
          >
            <svg
              className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Refresh Audit
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300 font-mono">
          [Audit Load Error]: {error}
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          {["ALL", "PIPELINE_COLLECTION", "SECURITY_TIMELINE_EVENT"].map((tab) => (
            <button
              key={tab}
              onClick={() => setTypeFilter(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition ${
                typeFilter === tab
                  ? "bg-slate-800 text-white border border-slate-700 font-bold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab === "ALL" ? "All Entries" : tab.replace(/_/g, " ")}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <input
            type="text"
            placeholder="Search audit ledger..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              className="absolute right-2.5 top-2 text-xs text-slate-400 hover:text-white"
            >
              &times;
            </button>
          )}
        </div>
      </div>

      {/* Audit Ledger List */}
      <div className="space-y-2.5">
        {filteredEntries.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-8 text-center text-xs text-slate-500 font-mono">
            No audit ledger entries found matching query.
          </div>
        ) : (
          filteredEntries.map((e) => (
            <div
              key={e.id}
              className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-3.5 hover:border-slate-700 transition space-y-2 backdrop-blur-sm"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                      e.type === "PIPELINE_COLLECTION"
                        ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
                        : "bg-purple-500/10 text-purple-400 border-purple-500/20"
                    }`}
                  >
                    {e.type.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs font-semibold text-white font-mono">
                    {e.action}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-slate-500">
                  {e.timestamp ? new Date(e.timestamp).toLocaleString() : "--"}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-mono text-slate-400">
                <div>
                  <span className="text-slate-500">Actor:</span>{" "}
                  <span className="text-slate-300">{e.actor}</span>
                </div>
                <div>
                  <span className="text-slate-500">Target:</span>{" "}
                  <span className="text-slate-300">{e.target}</span>
                </div>
                <div>
                  <span className="text-slate-500">Status:</span>{" "}
                  <span className="text-cyan-400">{e.status}</span>
                </div>
              </div>

              {e.detail && (
                <p className="text-xs font-mono text-slate-400/90 bg-slate-950/60 rounded px-2.5 py-1.5 border border-slate-800/60 break-words">
                  {e.detail}
                </p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
