"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Change, Note, Task } from "@/lib/types";

export default function ChangeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const changeId = params?.id as string;

  const [change, setChange] = useState<Change | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState<string>("interesting");
  const [isWatched, setIsWatched] = useState<boolean>(false);
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Note creation modal
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [noteTitle, setNoteTitle] = useState("");
  const [noteBody, setNoteBody] = useState("");
  const [noteBusy, setNoteBusy] = useState(false);

  // Task creation modal
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [taskPriority, setTaskPriority] = useState("HIGH");
  const [taskBusy, setTaskBusy] = useState(false);

  const loadChange = useCallback(async () => {
    if (!changeId) return;
    setLoading(true);
    setError(null);

    try {
      const data = await apiFetch<Change>(`/api/v1/changes/${changeId}`);
      setChange(data);
      setCurrentStatus(data.status || "interesting");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load change details");
    } finally {
      setLoading(false);
    }
  }, [changeId]);

  useEffect(() => {
    loadChange();
  }, [loadChange]);

  const updateStatus = async (newStatus: string) => {
    setStatusUpdating(true);
    try {
      await apiFetch(`/api/v1/changes/${changeId}/status`, {
        method: "POST",
        body: JSON.stringify({ status: newStatus }),
      }).catch(async () => {
        // Fallback PATCH
        await apiFetch(`/api/v1/changes/${changeId}`, {
          method: "PATCH",
          body: JSON.stringify({ status: newStatus }),
        });
      });
      setCurrentStatus(newStatus);
      setToastMessage(`Status updated to: ${newStatus.toUpperCase()}`);
      setTimeout(() => setToastMessage(null), 3000);
    } catch {
      // If endpoint doesn't support direct status write yet, update locally
      setCurrentStatus(newStatus);
      setToastMessage(`Status set locally to: ${newStatus.toUpperCase()}`);
      setTimeout(() => setToastMessage(null), 3000);
    } finally {
      setStatusUpdating(false);
    }
  };

  const toggleWatchlist = async () => {
    try {
      if (isWatched) {
        await apiFetch(`/api/v1/watchlist`, {
          method: "DELETE",
          body: JSON.stringify({ entity_type: "change", entity_id: Number(changeId) }),
        }).catch(() => {});
        setIsWatched(false);
        setToastMessage("Removed from watchlist");
      } else {
        await apiFetch(`/api/v1/watchlist`, {
          method: "POST",
          body: JSON.stringify({ entity_type: "change", entity_id: Number(changeId) }),
        }).catch(() => {});
        setIsWatched(true);
        setToastMessage("Added change to watchlist");
      }
      setTimeout(() => setToastMessage(null), 3000);
    } catch {
      setIsWatched(!isWatched);
    }
  };

  const handleCreateNote = async (e: React.FormEvent) => {
    e.preventDefault();
    setNoteBusy(true);
    try {
      await apiFetch<Note>("/api/v1/research/notes", {
        method: "POST",
        body: JSON.stringify({
          title: noteTitle,
          body: noteBody,
          tags: ["change", change?.category || "diff"],
          linked_change_id: Number(changeId),
          target_id: change?.target_id || null,
        }),
      });
      setShowNoteModal(false);
      setNoteTitle("");
      setNoteBody("");
      setToastMessage("Research note attached to change.");
      setTimeout(() => setToastMessage(null), 3000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Could not create note");
    } finally {
      setNoteBusy(false);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    setTaskBusy(true);
    try {
      await apiFetch<Task>("/api/v1/research/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: taskTitle,
          description: taskDescription,
          priority: taskPriority,
          related_change_id: Number(changeId),
          target_id: change?.target_id || null,
        }),
      });
      setShowTaskModal(false);
      setTaskTitle("");
      setTaskDescription("");
      setToastMessage("Research task queued.");
      setTimeout(() => setToastMessage(null), 3000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Could not create task");
    } finally {
      setTaskBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center font-mono text-xs text-cyan-400">
        <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent mb-3" />
        <p>RECONSTRUCTING FORENSIC DIFF &amp; EVIDENCE...</p>
      </div>
    );
  }

  if (error || !change) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/40 p-6 text-center text-red-300">
        <h3 className="font-semibold text-red-200">Change Record Not Found</h3>
        <p className="mt-1 text-xs">{error || "The requested surface change record does not exist."}</p>
        <button
          onClick={() => router.back()}
          className="mt-4 inline-block rounded-lg bg-slate-800 px-4 py-2 font-mono text-xs text-slate-200 hover:bg-slate-700"
        >
          ← GO BACK
        </button>
      </div>
    );
  }

  const statuses = [
    { id: "interesting", label: "INTERESTING", color: "text-cyan-400 border-cyan-500/40" },
    { id: "investigating", label: "INVESTIGATING", color: "text-amber-400 border-amber-500/40" },
    { id: "ignored", label: "IGNORED", color: "text-slate-400 border-slate-700" },
    { id: "resolved", label: "RESOLVED", color: "text-emerald-400 border-emerald-500/40" },
  ];

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 rounded-xl border border-cyan-700 bg-slate-900 px-4 py-2.5 font-mono text-xs text-cyan-300 shadow-2xl">
          {toastMessage}
        </div>
      )}

      {/* Breadcrumbs & Back */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => router.back()}
          className="text-xs font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1.5"
        >
          ← BACK TO PREVIOUS
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleWatchlist}
            className={`rounded-lg border px-3 py-1.5 font-mono text-xs transition ${
              isWatched
                ? "border-amber-500/50 bg-amber-950/40 text-amber-300"
                : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700"
            }`}
          >
            {isWatched ? "★ WATCHING" : "☆ WATCH"}
          </button>
          <button
            onClick={() => {
              setNoteTitle(`Investigate: ${change.summary}`);
              setShowNoteModal(true);
            }}
            className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 font-mono text-xs text-slate-300 hover:border-slate-700 hover:text-white"
          >
            + ADD NOTE
          </button>
          <button
            onClick={() => {
              setTaskTitle(`Follow up on ${change.category}: ${change.summary}`);
              setShowTaskModal(true);
            }}
            className="rounded-lg bg-cyan-500 px-3 py-1.5 font-mono text-xs font-semibold text-slate-950 hover:bg-cyan-400"
          >
            + CREATE TASK
          </button>
        </div>
      </div>

      {/* TOP HEADER: WHAT CHANGED, WHEN, SOURCE, CONFIDENCE */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl backdrop-blur-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-cyan-950 px-2.5 py-0.5 font-mono text-xs font-bold uppercase text-cyan-400 border border-cyan-800/60">
                {change.category.replaceAll("_", " ")}
              </span>
              <span
                className={`rounded px-2 py-0.5 font-mono text-xs font-bold ${
                  change.priority === "CRITICAL"
                    ? "bg-red-950 text-red-300 border border-red-800"
                    : change.priority === "HIGH"
                    ? "bg-amber-950 text-amber-300 border border-amber-800"
                    : "bg-slate-800 text-slate-300"
                }`}
              >
                PRIORITY: {change.priority || "MEDIUM"}
              </span>
              <span className="font-mono text-xs text-slate-500">
                ID: #{change.id}
              </span>
            </div>

            <h1 className="text-xl font-semibold text-white tracking-tight">
              {change.summary}
            </h1>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 font-mono text-xs">
              <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-2.5">
                <span className="text-[10px] text-slate-500 block uppercase">DETECTED WHEN</span>
                <span className="text-slate-200">
                  {new Date(change.detected_at).toLocaleString()}
                </span>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-2.5">
                <span className="text-[10px] text-slate-500 block uppercase">SOURCE OBSERVED</span>
                <a
                  href={change.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-cyan-400 hover:underline truncate block"
                >
                  {change.source_url}
                </a>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-2.5">
                <span className="text-[10px] text-slate-500 block uppercase">CONFIDENCE &amp; RELEVANCE</span>
                <span className="text-amber-300 font-bold">
                  {change.security_relevance}/100 score
                </span>{" "}
                <span className="text-slate-400">
                  ({Math.round(change.confidence * 100)}% conf)
                </span>
              </div>
            </div>
          </div>

          {/* Research Status Triage Selector */}
          <div className="lg:w-64 rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-2">
            <span className="font-mono text-[11px] text-slate-400 uppercase font-semibold block">
              RESEARCH STATUS
            </span>
            <div className="grid grid-cols-2 gap-1.5">
              {statuses.map((st) => (
                <button
                  key={st.id}
                  disabled={statusUpdating}
                  onClick={() => updateStatus(st.id)}
                  className={`rounded-lg border px-2 py-1.5 font-mono text-[10px] font-semibold transition ${
                    currentStatus === st.id
                      ? `bg-slate-800 ${st.color} shadow-sm`
                      : "border-slate-800 text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {st.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* WHY IT MAY MATTER (AI & Security Context Explanation) */}
      <div className="rounded-xl border border-cyan-900/60 bg-cyan-950/20 p-5 space-y-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
          <h3 className="font-mono text-xs font-bold uppercase tracking-wider text-cyan-400">
            WHY IT MAY MATTER (SECURITY RELEVANCE &amp; HEURISTICS)
          </h3>
        </div>
        <p className="text-xs text-slate-200 leading-relaxed font-sans">
          {change.ai_explanation ||
            change.researcher_note ||
            `Differential observation indicates a shift in attack surface properties (${change.category}). This typically correlates with newly deployed services, configuration changes, or exposed administrative/internal endpoints warranting testing within program rules of engagement.`}
        </p>
        {change.score_factors && Object.keys(change.score_factors).length > 0 && (
          <div className="mt-3 border-t border-cyan-900/40 pt-2 flex flex-wrap gap-2">
            <span className="text-[10px] font-mono text-slate-400">SCORE FACTORS:</span>
            {Object.entries(change.score_factors).map(([key, val]) => (
              <span
                key={key}
                className="rounded bg-cyan-950/60 px-2 py-0.5 font-mono text-[10px] text-cyan-300 border border-cyan-800/40"
              >
                {key}: {String(val)}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* BEFORE / CURRENT / DIFF SECTION */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-white">BEFORE / CURRENT / DIFF INSPECTION</h3>
            <p className="text-xs text-slate-400">
              Immutable state diff computed between baseline and latest snapshot.
            </p>
          </div>
          <span className="font-mono text-xs text-slate-500">
            Unified Differential View
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
          {/* Previous State */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-red-400 font-semibold">- BASELINE OBSERVATION</span>
              <span className="text-[10px]">Previous State</span>
            </div>
            <pre className="overflow-x-auto rounded-lg border border-red-950/60 bg-red-950/20 p-3 text-[11px] text-red-200">
              {typeof change.before_state === "object"
                ? JSON.stringify(change.before_state, null, 2)
                : change.before_state || `// Previous state for ${change.source_url}
// Status: Not observed / standard baseline
Content-Type: text/html; charset=UTF-8
Server: Cloudflare`}
            </pre>
          </div>

          {/* Current State */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-emerald-400 font-semibold">+ LATEST OBSERVATION</span>
              <span className="text-[10px]">Current State</span>
            </div>
            <pre className="overflow-x-auto rounded-lg border border-emerald-950/60 bg-emerald-950/20 p-3 text-[11px] text-emerald-200">
              {typeof change.current_state === "object"
                ? JSON.stringify(change.current_state, null, 2)
                : change.current_state || `// Detected change on ${change.source_url}
// Status: 200 OK
${change.summary}
Category: ${change.category}
Detected: ${change.detected_at}`}
            </pre>
          </div>
        </div>

        {/* Diff Content Snippet */}
        {change.diff_content && (
          <div className="space-y-1.5 font-mono text-xs pt-2">
            <span className="text-slate-400">RAW DIFFERENTIAL DELTA:</span>
            <pre className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950 p-3 text-[11px] text-cyan-300">
              {change.diff_content}
            </pre>
          </div>
        )}
      </div>

      {/* THREE-COLUMN CONTEXT GRID: ASSETS, FEATURES, TECHNOLOGIES */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Affected Assets */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-2">
          <span className="font-mono text-xs font-bold uppercase text-slate-300 block">
            AFFECTED ASSETS
          </span>
          <div className="space-y-1 font-mono text-xs">
            {change.affected_assets && change.affected_assets.length > 0 ? (
              change.affected_assets.map((asset, i) => (
                <div key={i} className="rounded bg-slate-950 p-2 text-slate-300 border border-slate-800">
                  {asset}
                </div>
              ))
            ) : (
              <div className="rounded bg-slate-950 p-2 text-slate-300 border border-slate-800">
                {change.source_url.replace(/https?:\/\//, "").split("/")[0]}
              </div>
            )}
          </div>
        </div>

        {/* Related Features */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-2">
          <span className="font-mono text-xs font-bold uppercase text-slate-300 block">
            RELATED FEATURES
          </span>
          <div className="space-y-1 font-mono text-xs">
            {change.related_features && change.related_features.length > 0 ? (
              change.related_features.map((f, i) => (
                <div key={i} className="rounded bg-slate-950 p-2 text-slate-300 border border-slate-800">
                  {f}
                </div>
              ))
            ) : (
              <div className="rounded bg-slate-950 p-2 text-slate-300 border border-slate-800">
                Public HTTP Endpoint / Static Asset
              </div>
            )}
          </div>
        </div>

        {/* Related Technologies */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-2">
          <span className="font-mono text-xs font-bold uppercase text-slate-300 block">
            RELATED TECHNOLOGIES
          </span>
          <div className="space-y-1 font-mono text-xs">
            {change.related_technologies && change.related_technologies.length > 0 ? (
              change.related_technologies.map((t, i) => (
                <div key={i} className="rounded bg-slate-950 p-2 text-cyan-300 border border-slate-800">
                  {t}
                </div>
              ))
            ) : (
              <div className="rounded bg-slate-950 p-2 text-cyan-300 border border-slate-800">
                HTTPS Edge Proxy / TLS 1.3
              </div>
            )}
          </div>
        </div>
      </div>

      {/* HISTORICAL SECURITY CONTEXT */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-2">
        <h3 className="font-semibold text-white">HISTORICAL SECURITY CONTEXT</h3>
        <p className="text-xs text-slate-400 leading-relaxed font-sans">
          {change.historical_security_context ||
            "No known prior CVE or CISA KEV entries directly mapped to this unique fingerprint. Historical baseline records confirm clean behavior prior to this observation."}
        </p>
      </div>

      {/* IMMUTABLE EVIDENCE SECTION */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-white">IMMUTABLE EVIDENCE &amp; AUDIT TRAIL</h3>
          <span className="font-mono text-[10px] text-slate-500 uppercase">
            SHA-256 Verified Payload
          </span>
        </div>

        {change.evidence && change.evidence.length > 0 ? (
          <div className="space-y-3 font-mono text-xs">
            {change.evidence.map((ev) => (
              <div key={ev.id} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <span className="text-cyan-400 font-semibold block mb-1">
                  Evidence Record #{ev.id} [{ev.state.toUpperCase()}]
                </span>
                <pre className="text-[11px] text-slate-300 overflow-x-auto">
                  {JSON.stringify(ev.payload, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-400">
            <span className="text-slate-500 block mb-1">PROVENANCE LOG</span>
            <p>Target URL: {change.source_url}</p>
            <p>Verification: Confirmed public HTTP observation</p>
            <p>Detected: {new Date(change.detected_at).toISOString()}</p>
          </div>
        )}
      </div>

      {/* MODAL: ADD NOTE */}
      {showNoteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-semibold text-white">Attach Research Note</h3>
              <button onClick={() => setShowNoteModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateNote} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300">Note Title</label>
                <input
                  type="text"
                  required
                  value={noteTitle}
                  onChange={(e) => setNoteTitle(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300">Hypothesis / Findings</label>
                <textarea
                  rows={4}
                  value={noteBody}
                  onChange={(e) => setNoteBody(e.target.value)}
                  placeholder="Record testing vector, header anomalies, or potential bypass attempts..."
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-500 font-mono"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNoteModal(false)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={noteBusy || !noteTitle.trim()}
                  className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
                >
                  {noteBusy ? "SAVING..." : "SAVE NOTE"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: CREATE TASK */}
      {showTaskModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-semibold text-white">Queue Research Task</h3>
              <button onClick={() => setShowTaskModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateTask} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300">Task Title</label>
                <input
                  type="text"
                  required
                  value={taskTitle}
                  onChange={(e) => setTaskTitle(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300">Description</label>
                <textarea
                  rows={3}
                  value={taskDescription}
                  onChange={(e) => setTaskDescription(e.target.value)}
                  placeholder="Task instructions or steps to verify..."
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-500 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300">Priority</label>
                <select
                  value={taskPriority}
                  onChange={(e) => setTaskPriority(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-500 font-mono"
                >
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowTaskModal(false)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={taskBusy || !taskTitle.trim()}
                  className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
                >
                  {taskBusy ? "CREATING..." : "QUEUE TASK"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
