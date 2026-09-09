"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Target, TimelineEvent } from "@/lib/types";

export default function TargetTimelinePage() {
  const params = useParams();
  const targetId = params?.id as string;

  const [target, setTarget] = useState<Target | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [selectedPriority, setSelectedPriority] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");

  const loadTimeline = useCallback(async () => {
    if (!targetId) return;
    setLoading(true);
    setError(null);

    try {
      const [targetRes, eventsRes] = await Promise.allSettled([
        apiFetch<Target>(`/api/v1/targets/${targetId}`),
        apiFetch<TimelineEvent[]>(`/api/v1/targets/${targetId}/timeline`),
      ]);

      if (targetRes.status === "fulfilled") {
        setTarget(targetRes.value);
      }
      if (eventsRes.status === "fulfilled") {
        setEvents(Array.isArray(eventsRes.value) ? eventsRes.value : []);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load timeline events");
    } finally {
      setLoading(false);
    }
  }, [targetId]);

  useEffect(() => {
    loadTimeline();
  }, [loadTimeline]);

  const eventTypes = [
    "ALL",
    "asset_discovered",
    "dns_change",
    "header_change",
    "endpoint_added",
    "tech_detected",
    "cve_match",
    "surface_diff",
  ];

  const priorities = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];

  const filteredEvents = events.filter((evt) => {
    const matchesType = selectedType === "ALL" || evt.event_type === selectedType;
    const matchesPriority =
      selectedPriority === "ALL" || evt.priority?.toUpperCase() === selectedPriority;
    const matchesSearch =
      evt.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      evt.summary?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      evt.source?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesType && matchesPriority && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Link
              href={`/targets/${targetId}`}
              className="text-xs font-mono text-cyan-400 hover:text-cyan-300"
            >
              ← BACK TO OVERVIEW
            </Link>
          </div>
          <h2 className="mt-1 text-2xl font-mono font-bold tracking-tight text-white">
            Security Timeline
          </h2>
          <p className="text-xs text-slate-400">
            Chronological audit of attack surface observations for{" "}
            <span className="font-mono text-cyan-300">{target?.domain || `Target #${targetId}`}</span>
          </p>
        </div>

        <button
          onClick={loadTimeline}
          className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 font-mono text-xs text-slate-300 hover:bg-slate-800"
        >
          ↻ REFRESH TIMELINE
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <input
            type="text"
            placeholder="Search timeline events by title, summary, source..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full max-w-md rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 font-mono text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-500"
          />

          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-slate-400">PRIORITY:</span>
            {priorities.map((p) => (
              <button
                key={p}
                onClick={() => setSelectedPriority(p)}
                className={`rounded px-2 py-0.5 font-mono text-[10px] font-semibold transition ${
                  selectedPriority === p
                    ? "bg-cyan-500 text-slate-950"
                    : "bg-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Event Type Pills */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-slate-800/60">
          <span className="font-mono text-[10px] text-slate-400 mr-1">EVENT TYPE:</span>
          {eventTypes.map((type) => (
            <button
              key={type}
              onClick={() => setSelectedType(type)}
              className={`rounded-full px-2.5 py-0.5 font-mono text-[10px] transition ${
                selectedType === type
                  ? "bg-cyan-950 border border-cyan-400 text-cyan-300"
                  : "bg-slate-800/70 text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              {type.replaceAll("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Timeline Stream */}
      <div className="relative">
        {/* Vertical timeline spine */}
        <div className="absolute bottom-0 left-6 top-0 w-0.5 bg-slate-800" />

        {loading ? (
          <div className="py-20 text-center font-mono text-xs text-cyan-400">
            COMPILING CHRONOLOGICAL TIMELINE...
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="ml-12 rounded-xl border border-dashed border-slate-800 p-8 text-center text-xs text-slate-500 font-mono">
            NO TIMELINE EVENTS FOUND MATCHING CURRENT FILTER PARAMETERS
          </div>
        ) : (
          <div className="space-y-6">
            {filteredEvents.map((evt) => {
              const priorityClass =
                evt.priority === "CRITICAL"
                  ? "border-red-500/50 bg-red-950/20"
                  : evt.priority === "HIGH"
                  ? "border-amber-500/50 bg-amber-950/20"
                  : "border-slate-800 bg-slate-900/80";

              return (
                <div key={evt.id} className="relative flex items-start gap-6 group">
                  {/* Timeline Node Icon */}
                  <div className="relative z-10 flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-cyan-500/40 bg-slate-950 text-cyan-400 shadow-md">
                    <span className="font-mono text-xs font-bold">
                      {evt.relevance_score || "•"}
                    </span>
                  </div>

                  {/* Event Card */}
                  <div
                    className={`flex-1 rounded-xl border ${priorityClass} p-4 shadow-sm backdrop-blur-sm transition group-hover:border-slate-700`}
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded bg-cyan-950 px-2 py-0.5 font-mono text-[10px] font-bold uppercase text-cyan-400 border border-cyan-800/60">
                            {evt.event_type}
                          </span>
                          <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-300">
                            SOURCE: {evt.source}
                          </span>
                          {evt.priority && (
                            <span
                              className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                                evt.priority === "CRITICAL"
                                  ? "bg-red-900/60 text-red-300"
                                  : evt.priority === "HIGH"
                                  ? "bg-amber-900/60 text-amber-300"
                                  : "bg-slate-800 text-slate-400"
                              }`}
                            >
                              {evt.priority}
                            </span>
                          )}
                        </div>

                        <h3 className="text-sm font-semibold text-slate-100">{evt.title}</h3>
                        <p className="text-xs text-slate-300">{evt.summary}</p>
                      </div>

                      <div className="shrink-0 text-right font-mono text-xs">
                        <div className="text-amber-300 font-bold">
                          {evt.relevance_score}/100{" "}
                          <span className="text-[10px] text-slate-500">score</span>
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {Math.round((evt.confidence || 0) * 100)}% confidence
                        </div>
                      </div>
                    </div>

                    {/* Source URL & Timestamps */}
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/70 pt-2 text-[11px] font-mono text-slate-500">
                      {evt.source_url ? (
                        <a
                          href={evt.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="max-w-md truncate text-cyan-400 hover:underline"
                        >
                          🔗 {evt.source_url}
                        </a>
                      ) : (
                        <span>Verified Passive Observation</span>
                      )}

                      <div className="flex items-center gap-3">
                        <span>Observed: {new Date(evt.observed_at).toLocaleString()}</span>
                        {evt.published_at && (
                          <span>Published: {new Date(evt.published_at).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
