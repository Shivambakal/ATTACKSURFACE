"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { WatchlistEntry, Target } from "@/lib/types";

export default function WatchlistPage() {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add entity to watchlist modal
  const [showModal, setShowModal] = useState(false);
  const [entityType, setEntityType] = useState("target");
  const [entityId, setEntityId] = useState("");
  const [busy, setBusy] = useState(false);

  const loadWatchlist = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [watchRes, targetRes] = await Promise.allSettled([
        apiFetch<WatchlistEntry[]>("/api/v1/watchlist"),
        apiFetch<Target[]>("/api/v1/targets"),
      ]);

      if (watchRes.status === "fulfilled") setEntries(Array.isArray(watchRes.value) ? watchRes.value : []);
      if (targetRes.status === "fulfilled") setTargets(Array.isArray(targetRes.value) ? targetRes.value : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWatchlist();
  }, [loadWatchlist]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!entityId.trim()) return;
    setBusy(true);

    try {
      const created = await apiFetch<WatchlistEntry>("/api/v1/watchlist", {
        method: "POST",
        body: JSON.stringify({
          entity_type: entityType,
          entity_id: Number(entityId),
        }),
      });
      setEntries((prev) => [created, ...prev]);
      setShowModal(false);
      setEntityId("");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to add to watchlist");
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async (id: number) => {
    try {
      await apiFetch(`/api/v1/watchlist/${id}`, { method: "DELETE" }).catch(async () => {
        // Fallback with body if needed
        const entry = entries.find((e) => e.id === id);
        if (entry) {
          await apiFetch(`/api/v1/watchlist`, {
            method: "DELETE",
            body: JSON.stringify({ entity_type: entry.entity_type, entity_id: entry.entity_id }),
          });
        }
      });
      setEntries((prev) => prev.filter((e) => e.id !== id));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Could not remove from watchlist");
    }
  };

  // Group by entity_type
  const grouped: Record<string, WatchlistEntry[]> = {};
  entries.forEach((entry) => {
    const type = entry.entity_type || "other";
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push(entry);
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs uppercase tracking-wider text-cyan-400">
              RADAR
            </span>
          </div>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-white">
            High-Priority Entity Watchlist
          </h2>
          <p className="text-xs text-slate-400">
            Monitored targets and high-priority assets flagged for notifications.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 hover:bg-cyan-400"
        >
          + PIN ENTITY
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Watchlist Groups */}
      {loading ? (
        <div className="py-20 text-center font-mono text-xs text-cyan-400">
          RETRIEVING WATCHLIST MONITOR...
        </div>
      ) : entries.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 p-16 text-center text-xs text-slate-500 font-mono">
          NO PINNED ENTITIES ON YOUR WATCHLIST. CLICK &apos;+ PIN ENTITY&apos; OR STAR A CHANGE FORENSIC CARD.
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([type, items]) => (
            <div key={type} className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
              <div className="flex items-center gap-2 border-b border-slate-800/80 pb-2">
                <span className="h-2 w-2 rounded-full bg-cyan-400" />
                <h3 className="font-mono text-xs font-bold uppercase text-white tracking-wider">
                  WATCHED {type.toUpperCase()}S ({items.length})
                </h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {items.map((item) => {
                  const targetMatch =
                    type === "target" ? targets.find((t) => t.id === item.entity_id) : null;

                  return (
                    <div
                      key={item.id}
                      className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/70 p-3"
                    >
                      <div className="space-y-0.5 min-w-0 pr-2">
                        <span className="font-mono text-[10px] text-cyan-400 uppercase">
                          {type} #{item.entity_id}
                        </span>
                        <div className="truncate text-xs font-semibold text-slate-200">
                          {targetMatch ? targetMatch.domain : item.label || `Entity #${item.entity_id}`}
                        </div>
                        <span className="font-mono text-[10px] text-slate-500 block">
                          Added {new Date(item.created_at).toLocaleDateString()}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {type === "target" && (
                          <Link
                            href={`/targets/${item.entity_id}`}
                            className="rounded border border-slate-700 bg-slate-800 px-2 py-1 font-mono text-[10px] text-slate-300 hover:text-cyan-300"
                          >
                            VIEW
                          </Link>
                        )}
                        {type === "change" && (
                          <Link
                            href={`/changes/${item.entity_id}`}
                            className="rounded border border-slate-700 bg-slate-800 px-2 py-1 font-mono text-[10px] text-slate-300 hover:text-cyan-300"
                          >
                            DIFF
                          </Link>
                        )}
                        <button
                          onClick={() => handleRemove(item.id)}
                          title="Remove from watchlist"
                          className="rounded border border-slate-800 p-1 text-slate-500 hover:text-red-400"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Entity Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-semibold text-white">Add Entity to Watchlist</h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleAdd} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300">Entity Type</label>
                <select
                  value={entityType}
                  onChange={(e) => setEntityType(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 outline-none focus:border-cyan-500"
                >
                  <option value="target">Target Domain</option>
                  <option value="change">Surface Change</option>
                  <option value="asset">Public Asset</option>
                  <option value="technology">Technology Component</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300">Entity ID</label>
                <input
                  type="number"
                  required
                  placeholder="e.g. 1"
                  value={entityId}
                  onChange={(e) => setEntityId(e.target.value)}
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
                  disabled={busy || !entityId.trim()}
                  className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
                >
                  {busy ? "PINNING..." : "PIN TO WATCHLIST"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
