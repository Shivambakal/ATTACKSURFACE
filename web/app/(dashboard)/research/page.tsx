"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Note, Task, Finding } from "@/lib/types";

export default function ResearchHubPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [nRes, tRes, fRes] = await Promise.allSettled([
        apiFetch<Note[]>("/api/v1/research/notes"),
        apiFetch<Task[]>("/api/v1/research/tasks"),
        apiFetch<Finding[]>("/api/v1/research/findings"),
      ]);

      if (nRes.status === "fulfilled") setNotes(Array.isArray(nRes.value) ? nRes.value : []);
      if (tRes.status === "fulfilled") setTasks(Array.isArray(tRes.value) ? tRes.value : []);
      if (fRes.status === "fulfilled") setFindings(Array.isArray(fRes.value) ? fRes.value : []);
    } catch {
      // ignore load errors
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openTasks = tasks.filter((t) => t.status !== "done");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs uppercase tracking-wider text-cyan-400">
              WORKSPACE
            </span>
          </div>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-white">
            Research Intelligence Hub
          </h2>
          <p className="text-xs text-slate-400">
            Organize hypotheses, task queues, and verified vulnerability findings.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/research/notes"
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 font-mono text-xs text-slate-200 hover:border-cyan-500 hover:text-cyan-300"
          >
            NOTES ({notes.length})
          </Link>
          <Link
            href="/research/tasks"
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 font-mono text-xs text-slate-200 hover:border-cyan-500 hover:text-cyan-300"
          >
            TASKS ({openTasks.length})
          </Link>
          <Link
            href="/research/findings"
            className="rounded-lg bg-cyan-500 px-3.5 py-1.5 font-mono text-xs font-semibold text-slate-950 hover:bg-cyan-400"
          >
            FINDINGS ({findings.length})
          </Link>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Notes Summary */}
        <Link
          href="/research/notes"
          className="group rounded-xl border border-slate-800 bg-slate-900/60 p-5 transition hover:border-cyan-500/40 hover:bg-slate-900"
        >
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs text-cyan-400 uppercase">FIELD NOTES</span>
            <span className="text-slate-500 font-mono text-xs">VIEW →</span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-white">{notes.length}</p>
          <p className="mt-1 text-xs text-slate-400">Recorded hypotheses and observation logs</p>
        </Link>

        {/* Tasks Summary */}
        <Link
          href="/research/tasks"
          className="group rounded-xl border border-slate-800 bg-slate-900/60 p-5 transition hover:border-amber-500/40 hover:bg-slate-900"
        >
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs text-amber-400 uppercase">ACTIVE TASKS</span>
            <span className="text-slate-500 font-mono text-xs">VIEW →</span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-amber-300">{openTasks.length}</p>
          <p className="mt-1 text-xs text-slate-400">Exploration checklist &amp; test items</p>
        </Link>

        {/* Findings Summary */}
        <Link
          href="/research/findings"
          className="group rounded-xl border border-slate-800 bg-slate-900/60 p-5 transition hover:border-red-500/40 hover:bg-slate-900"
        >
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs text-red-400 uppercase">FINDINGS</span>
            <span className="text-slate-500 font-mono text-xs">VIEW →</span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-red-300">{findings.length}</p>
          <p className="mt-1 text-xs text-slate-400">Validated reports &amp; vulnerabilities</p>
        </Link>
      </div>

      {/* Three Column Recent Feeds */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Notes */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-white text-sm">Recent Notes</h3>
            <Link href="/research/notes" className="text-xs font-mono text-cyan-400 hover:underline">
              Manage
            </Link>
          </div>
          {notes.length === 0 ? (
            <p className="text-xs text-slate-500 py-6 text-center font-mono">NO NOTES SAVED</p>
          ) : (
            <div className="space-y-2">
              {notes.slice(0, 4).map((n) => (
                <div key={n.id} className="rounded-lg border border-slate-800 bg-slate-950/60 p-2.5">
                  <h4 className="text-xs font-medium text-slate-200 truncate">{n.title}</h4>
                  <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">{n.body}</p>
                  <span className="text-[10px] font-mono text-slate-500 block mt-1.5">
                    {new Date(n.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pending Tasks */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-white text-sm">Pending Tasks</h3>
            <Link href="/research/tasks" className="text-xs font-mono text-amber-400 hover:underline">
              Manage
            </Link>
          </div>
          {openTasks.length === 0 ? (
            <p className="text-xs text-slate-500 py-6 text-center font-mono">ALL TASKS COMPLETED</p>
          ) : (
            <div className="space-y-2">
              {openTasks.slice(0, 4).map((t) => (
                <div key={t.id} className="rounded-lg border border-slate-800 bg-slate-950/60 p-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-200 truncate">{t.title}</span>
                    <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[9px] text-amber-300">
                      {t.priority}
                    </span>
                  </div>
                  {t.description && (
                    <p className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">{t.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Vulnerability Findings */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-white text-sm">Reported Findings</h3>
            <Link href="/research/findings" className="text-xs font-mono text-red-400 hover:underline">
              Manage
            </Link>
          </div>
          {findings.length === 0 ? (
            <p className="text-xs text-slate-500 py-6 text-center font-mono">NO FINDINGS FILED</p>
          ) : (
            <div className="space-y-2">
              {findings.slice(0, 4).map((f) => (
                <div key={f.id} className="rounded-lg border border-slate-800 bg-slate-950/60 p-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-200 truncate">{f.title}</span>
                    <span className="rounded bg-red-950 px-1.5 py-0.5 font-mono text-[9px] text-red-300 border border-red-800">
                      {f.severity || "INFO"}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 block mt-1">
                    Status: {f.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
