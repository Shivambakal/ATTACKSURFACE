"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Note, Target } from "@/lib/types";

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTargetId, setSelectedTargetId] = useState<string>("ALL");

  // Modal / form state
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [targetId, setTargetId] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [notesRes, targetsRes] = await Promise.allSettled([
        apiFetch<Note[]>("/api/v1/research/notes"),
        apiFetch<Target[]>("/api/v1/targets"),
      ]);

      if (notesRes.status === "fulfilled") setNotes(Array.isArray(notesRes.value) ? notesRes.value : []);
      if (targetsRes.status === "fulfilled") setTargets(Array.isArray(targetsRes.value) ? targetsRes.value : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load notes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateNote = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);

    const tags = tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    try {
      const created = await apiFetch<Note>("/api/v1/research/notes", {
        method: "POST",
        body: JSON.stringify({
          title,
          body,
          tags,
          target_id: targetId ? Number(targetId) : null,
        }),
      });
      setNotes((prev) => [created, ...prev]);
      setShowModal(false);
      setTitle("");
      setBody("");
      setTagsInput("");
      setTargetId("");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to save note");
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteNote = async (id: number) => {
    if (!confirm("Delete this research note?")) return;
    try {
      await apiFetch(`/api/v1/research/notes/${id}`, { method: "DELETE" }).catch(() => {});
      setNotes((prev) => prev.filter((n) => n.id !== id));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete note");
    }
  };

  const filteredNotes = notes.filter((note) => {
    const matchesTarget =
      selectedTargetId === "ALL" || String(note.target_id) === selectedTargetId;
    const matchesSearch =
      note.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (note.body && note.body.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (note.tags && note.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase())));
    return matchesTarget && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Link href="/research" className="text-xs font-mono text-cyan-400 hover:underline">
              ← RESEARCH HUB
            </Link>
          </div>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-white">
            Research Notes &amp; Observations
          </h2>
          <p className="text-xs text-slate-400">
            Technical hypotheses, attack vectors, and observation logs.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 hover:bg-cyan-400"
        >
          + NEW NOTE
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-3">
        <input
          type="text"
          placeholder="Filter notes by keyword or tag..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full max-w-sm rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 font-mono text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-500"
        />

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-slate-400 text-[11px]">TARGET:</span>
          <select
            value={selectedTargetId}
            onChange={(e) => setSelectedTargetId(e.target.value)}
            className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-200 outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Targets</option>
            {targets.map((t) => (
              <option key={t.id} value={String(t.id)}>
                {t.domain}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Notes Grid */}
      {loading ? (
        <div className="py-20 text-center font-mono text-xs text-cyan-400">
          LOADING RESEARCH NOTES...
        </div>
      ) : filteredNotes.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 p-12 text-center text-xs text-slate-500 font-mono">
          NO RESEARCH NOTES FOUND. CREATE A NEW NOTE TO TRACK YOUR FINDINGS.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredNotes.map((note) => {
            const linkedTarget = targets.find((t) => t.id === note.target_id);
            return (
              <div
                key={note.id}
                className="flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-900/70 p-4 shadow-sm transition hover:border-slate-700 hover:bg-slate-900"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold text-sm text-slate-100">{note.title}</h3>
                    <button
                      onClick={() => handleDeleteNote(note.id)}
                      title="Delete note"
                      className="text-slate-500 hover:text-red-400 text-xs p-1"
                    >
                      ✕
                    </button>
                  </div>

                  {note.body && (
                    <p className="text-xs text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
                      {note.body}
                    </p>
                  )}

                  {note.tags && note.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {note.tags.map((t, idx) => (
                        <span
                          key={idx}
                          className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-cyan-400 border border-slate-700"
                        >
                          #{t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-slate-800/80 pt-2 font-mono text-[10px] text-slate-500">
                  <span>
                    {linkedTarget ? linkedTarget.domain : note.target_id ? `Target #${note.target_id}` : "Global"}
                  </span>
                  <span>{new Date(note.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Note Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-semibold text-white">Create Research Note</h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateNote} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300">Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Header leakage on /oauth/token"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300">Target (Optional)</label>
                <select
                  value={targetId}
                  onChange={(e) => setTargetId(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-500 font-mono"
                >
                  <option value="">-- Unlinked / General --</option>
                  {targets.map((t) => (
                    <option key={t.id} value={String(t.id)}>
                      {t.domain}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300">Body</label>
                <textarea
                  rows={5}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder="Describe your security analysis, payloads observed, or ideas..."
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300">Tags (comma separated)</label>
                <input
                  type="text"
                  placeholder="auth, idor, api, cve"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-500 font-mono"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={busy || !title.trim()}
                  className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
                >
                  {busy ? "SAVING..." : "SAVE NOTE"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
