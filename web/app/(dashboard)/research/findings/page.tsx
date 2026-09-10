"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Finding, Target } from "@/lib/types";

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedSeverity, setSelectedSeverity] = useState("ALL");
  const [selectedStatus, setSelectedStatus] = useState("ALL");

  // Create Finding Modal
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState("MEDIUM");
  const [targetId, setTargetId] = useState("");
  const [busy, setBusy] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [findingsRes, targetsRes] = await Promise.allSettled([
        apiFetch<Finding[]>("/api/v1/research/findings"),
        apiFetch<Target[]>("/api/v1/targets"),
      ]);

      if (findingsRes.status === "fulfilled") setFindings(Array.isArray(findingsRes.value) ? findingsRes.value : []);
      if (targetsRes.status === "fulfilled") setTargets(Array.isArray(targetsRes.value) ? targetsRes.value : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load findings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateFinding = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);

    try {
      const created = await apiFetch<Finding>("/api/v1/research/findings", {
        method: "POST",
        body: JSON.stringify({
          title,
          description,
          severity,
          target_id: targetId ? Number(targetId) : null,
        }),
      });
      setFindings((prev) => [created, ...prev]);
      setShowModal(false);
      setTitle("");
      setDescription("");
      setSeverity("MEDIUM");
      setTargetId("");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to create finding");
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteFinding = async (id: number) => {
    if (!confirm("Delete this security finding report?")) return;
    try {
      await apiFetch(`/api/v1/research/findings/${id}`, { method: "DELETE" }).catch(() => {});
      setFindings((prev) => prev.filter((f) => f.id !== id));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete finding");
    }
  };

  const filteredFindings = findings.filter((f) => {
    const matchesSev =
      selectedSeverity === "ALL" || f.severity?.toUpperCase() === selectedSeverity;
    const matchesStatus =
      selectedStatus === "ALL" || f.status?.toUpperCase() === selectedStatus;
    return matchesSev && matchesStatus;
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
            Vulnerability Findings
          </h2>
          <p className="text-xs text-slate-400">
            Documented security findings and scope validation reports.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="rounded-lg bg-red-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 hover:bg-red-400"
        >
          + FILE FINDING
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-slate-400">SEVERITY:</span>
          {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"].map((sev) => (
            <button
              key={sev}
              onClick={() => setSelectedSeverity(sev)}
              className={`rounded px-2.5 py-1 font-mono text-[10px] font-semibold transition ${
                selectedSeverity === sev
                  ? "bg-red-500 text-slate-950"
                  : "bg-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              {sev}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-slate-400">STATUS:</span>
          {["ALL", "DRAFT", "VERIFIED", "REPORTED", "RESOLVED"].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`rounded px-2 py-0.5 font-mono text-[10px] transition ${
                selectedStatus === st
                  ? "bg-slate-700 text-cyan-300 font-bold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Findings Cards List */}
      {loading ? (
        <div className="py-20 text-center font-mono text-xs text-cyan-400">
          LOADING VULNERABILITY FINDINGS...
        </div>
      ) : filteredFindings.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 p-12 text-center text-xs text-slate-500 font-mono">
          NO FINDINGS FILED YET. CLICK &apos;+ FILE FINDING&apos; TO RECORD A VULNERABILITY.
        </div>
      ) : (
        <div className="space-y-3">
          {filteredFindings.map((finding) => {
            const targetObj = targets.find((t) => t.id === finding.target_id);
            const sev = (finding.severity || "INFO").toUpperCase();
            const sevColor =
              sev === "CRITICAL"
                ? "bg-red-950 text-red-300 border-red-800"
                : sev === "HIGH"
                ? "bg-amber-950 text-amber-300 border-amber-800"
                : sev === "MEDIUM"
                ? "bg-yellow-950 text-yellow-300 border-yellow-800"
                : "bg-cyan-950 text-cyan-300 border-cyan-800";

            return (
              <div
                key={finding.id}
                className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 transition hover:border-slate-700"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold uppercase border ${sevColor}`}
                      >
                        {sev}
                      </span>
                      <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] uppercase text-slate-300">
                        STATUS: {finding.status || "draft"}
                      </span>
                      {targetObj && (
                        <span className="font-mono text-xs text-cyan-400">
                          {targetObj.domain}
                        </span>
                      )}
                    </div>

                    <h3 className="text-sm font-semibold text-slate-100">{finding.title}</h3>
                    {finding.description && (
                      <p className="text-xs text-slate-300 font-sans leading-relaxed whitespace-pre-wrap">
                        {finding.description}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleDeleteFinding(finding.id)}
                      title="Delete finding"
                      className="rounded border border-slate-800 p-1 text-slate-500 hover:text-red-400 hover:border-red-800 text-xs"
                    >
                      ✕
                    </button>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between border-t border-slate-800/70 pt-2 font-mono text-[10px] text-slate-500">
                  <span>Finding ID: #{finding.id}</span>
                  <span>Recorded: {new Date(finding.created_at).toLocaleString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Finding Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-semibold text-white">File Security Finding</h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateFinding} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300">Vulnerability Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Unauthenticated IDOR in /api/v1/customer/export"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-red-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300">Severity</label>
                  <select
                    value={severity}
                    onChange={(e) => setSeverity(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 outline-none focus:border-red-500"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                    <option value="INFO">INFO</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300">Target Asset</label>
                  <select
                    value={targetId}
                    onChange={(e) => setTargetId(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 outline-none focus:border-red-500"
                  >
                    <option value="">-- General / Out of Band --</option>
                    {targets.map((t) => (
                      <option key={t.id} value={String(t.id)}>
                        {t.domain}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300">
                  Description &amp; Reproduction Steps
                </label>
                <textarea
                  rows={5}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Summarize root cause, affected parameters, proof-of-concept steps, and recommended remediation..."
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-red-500 font-mono"
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
                  className="rounded-lg bg-red-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 hover:bg-red-400 disabled:opacity-50"
                >
                  {busy ? "FILING..." : "FILE FINDING"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
