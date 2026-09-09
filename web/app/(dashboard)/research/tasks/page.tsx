"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Task, Target } from "@/lib/types";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");

  // Create Task Modal
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("MEDIUM");
  const [dueDate, setDueDate] = useState("");
  const [targetId, setTargetId] = useState("");
  const [busy, setBusy] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tasksRes, targetsRes] = await Promise.allSettled([
        apiFetch<Task[]>("/api/v1/research/tasks"),
        apiFetch<Target[]>("/api/v1/targets"),
      ]);

      if (tasksRes.status === "fulfilled") setTasks(Array.isArray(tasksRes.value) ? tasksRes.value : []);
      if (targetsRes.status === "fulfilled") setTargets(Array.isArray(targetsRes.value) ? targetsRes.value : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load tasks");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);

    try {
      const created = await apiFetch<Task>("/api/v1/research/tasks", {
        method: "POST",
        body: JSON.stringify({
          title,
          description,
          priority,
          due_date: dueDate || null,
          target_id: targetId ? Number(targetId) : null,
        }),
      });
      setTasks((prev) => [created, ...prev]);
      setShowModal(false);
      setTitle("");
      setDescription("");
      setPriority("MEDIUM");
      setDueDate("");
      setTargetId("");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setBusy(false);
    }
  };

  const handleStatusChange = async (taskId: number, newStatus: string) => {
    try {
      await apiFetch(`/api/v1/research/tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      }).catch(() => {});

      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t))
      );
    } catch {
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t))
      );
    }
  };

  const handleDeleteTask = async (id: number) => {
    if (!confirm("Delete this research task?")) return;
    try {
      await apiFetch(`/api/v1/research/tasks/${id}`, { method: "DELETE" }).catch(() => {});
      setTasks((prev) => prev.filter((t) => t.id !== id));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete task");
    }
  };

  const filteredTasks = tasks.filter((task) => {
    const matchesStatus =
      statusFilter === "ALL" || task.status.toLowerCase() === statusFilter.toLowerCase();
    const matchesPriority =
      priorityFilter === "ALL" || task.priority.toUpperCase() === priorityFilter;
    return matchesStatus && matchesPriority;
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
            Research Investigation Tasks
          </h2>
          <p className="text-xs text-slate-400">
            Track verification steps, test payloads, and security audits across targets.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 hover:bg-cyan-400"
        >
          + CREATE TASK
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-slate-400">STATUS:</span>
          {["ALL", "OPEN", "IN_PROGRESS", "DONE"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`rounded px-2.5 py-1 font-mono text-[10px] font-semibold transition ${
                statusFilter === st
                  ? "bg-cyan-500 text-slate-950"
                  : "bg-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              {st.replaceAll("_", " ")}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-slate-400">PRIORITY:</span>
          {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((pr) => (
            <button
              key={pr}
              onClick={() => setPriorityFilter(pr)}
              className={`rounded px-2 py-0.5 font-mono text-[10px] transition ${
                priorityFilter === pr
                  ? "bg-slate-700 text-cyan-300 font-bold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {pr}
            </button>
          ))}
        </div>
      </div>

      {/* Task List */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow">
        {loading ? (
          <div className="py-20 text-center font-mono text-xs text-cyan-400">
            LOADING TASK QUEUE...
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="py-16 text-center font-mono text-xs text-slate-500">
            NO RESEARCH TASKS MATCHING CRITERIA
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {filteredTasks.map((task) => {
              const targetObj = targets.find((t) => t.id === task.target_id);
              return (
                <div
                  key={task.id}
                  className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between transition hover:bg-slate-800/30"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded px-1.5 py-0.5 font-mono text-[9px] font-bold ${
                          task.priority === "CRITICAL"
                            ? "bg-red-950 text-red-300 border border-red-800"
                            : task.priority === "HIGH"
                            ? "bg-amber-950 text-amber-300 border border-amber-800"
                            : "bg-slate-800 text-slate-300"
                        }`}
                      >
                        {task.priority}
                      </span>
                      <h3
                        className={`text-xs font-semibold ${
                          task.status === "done" ? "line-through text-slate-500" : "text-slate-100"
                        }`}
                      >
                        {task.title}
                      </h3>
                    </div>

                    {task.description && (
                      <p className="text-xs text-slate-400">{task.description}</p>
                    )}

                    <div className="flex flex-wrap items-center gap-3 text-[10px] font-mono text-slate-500">
                      <span>
                        Target: {targetObj ? targetObj.domain : task.target_id ? `#${task.target_id}` : "Unlinked"}
                      </span>
                      {task.due_date && <span>Due: {task.due_date}</span>}
                      <span>Created: {new Date(task.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <select
                      value={task.status}
                      onChange={(e) => handleStatusChange(task.id, e.target.value)}
                      className="rounded border border-slate-700 bg-slate-800 px-2 py-1 font-mono text-xs text-slate-200 outline-none focus:border-cyan-500"
                    >
                      <option value="open">Open</option>
                      <option value="in_progress">In Progress</option>
                      <option value="done">Done</option>
                    </select>

                    <button
                      onClick={() => handleDeleteTask(task.id)}
                      title="Delete task"
                      className="rounded border border-slate-800 p-1 text-slate-500 hover:text-red-400 hover:border-red-800 text-xs"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Task Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-semibold text-white">Create Investigation Task</h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300">Task Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Probe IDOR on /api/v1/user/settings"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300">Priority</label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 outline-none focus:border-cyan-500"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300">Target</label>
                  <select
                    value={targetId}
                    onChange={(e) => setTargetId(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 outline-none focus:border-cyan-500"
                  >
                    <option value="">-- Unlinked --</option>
                    {targets.map((t) => (
                      <option key={t.id} value={String(t.id)}>
                        {t.domain}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300">Description</label>
                <textarea
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Provide test checklist, parameters, or endpoints to audit..."
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300">Due Date (Optional)</label>
                <input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 outline-none focus:border-cyan-500"
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
                  {busy ? "CREATING..." : "QUEUE TASK"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
