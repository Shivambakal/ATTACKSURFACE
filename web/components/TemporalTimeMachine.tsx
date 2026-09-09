"use client";

import React, { useState, useEffect, useRef } from "react";
import { TimelineEvent } from "@/lib/types";

interface TemporalTimeMachineProps {
  events: TimelineEvent[];
  selectedYear: string; // "ALL" or "2020", "2021", etc., or "NOW"
  onSelectYear: (year: string) => void;
  onEventPulse?: (event: TimelineEvent) => void;
}

const YEARS = ["2020", "2021", "2022", "2023", "2024", "2025", "2026", "NOW"];

export default function TemporalTimeMachine({
  events,
  selectedYear,
  onSelectYear,
  onEventPulse,
}: TemporalTimeMachineProps) {
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const playIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Group events by year
  const eventsByYear = React.useMemo(() => {
    const map: Record<string, TimelineEvent[]> = {};
    for (const yr of YEARS) map[yr] = [];

    for (const ev of events) {
      const dateStr = ev.published_at || ev.observed_at;
      if (dateStr) {
        try {
          const yr = new Date(dateStr).getFullYear().toString();
          if (map[yr]) {
            map[yr].push(ev);
          } else {
            // If earlier than 2020, cluster into 2020
            if (parseInt(yr, 10) < 2020) map["2020"].push(ev);
            else map["NOW"].push(ev);
          }
        } catch {
          map["NOW"].push(ev);
        }
      } else {
        map["NOW"].push(ev);
      }
    }
    return map;
  }, [events]);

  // Handle Play/Pause Temporal Replay
  const togglePlay = () => {
    if (isPlaying) {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
      setIsPlaying(false);
    } else {
      setIsPlaying(true);
      let currentIndex = YEARS.indexOf(selectedYear);
      if (currentIndex === -1 || currentIndex === YEARS.length - 1) {
        currentIndex = 0;
      }

      const step = () => {
        const nextYr = YEARS[currentIndex];
        onSelectYear(nextYr);

        // Pulse an event from this year if available
        const yearEvents = eventsByYear[nextYr] || [];
        if (yearEvents.length > 0 && onEventPulse) {
          onEventPulse(yearEvents[0]);
        }

        currentIndex++;
        if (currentIndex >= YEARS.length) {
          if (playIntervalRef.current) clearInterval(playIntervalRef.current);
          setIsPlaying(false);
        }
      };

      step();
      playIntervalRef.current = setInterval(step, 1600);
    }
  };

  useEffect(() => {
    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    };
  }, []);

  const activeEventsCount =
    selectedYear === "ALL"
      ? events.length
      : (eventsByYear[selectedYear] || []).length;

  return (
    <div className="rounded-2xl border border-cyan-500/30 bg-slate-950/90 p-4 shadow-[0_15px_40px_rgba(0,0,0,0.6)] backdrop-blur-xl">
      {/* Top Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={togglePlay}
            className={`flex items-center gap-2 rounded-xl px-3.5 py-1.5 font-mono text-xs font-bold transition-all shadow-md ${
              isPlaying
                ? "bg-rose-500 text-white shadow-rose-500/30 animate-pulse"
                : "bg-cyan-500 text-slate-950 hover:bg-cyan-400 shadow-cyan-500/20"
            }`}
          >
            <span>{isPlaying ? "⏸ PAUSE REPLAY" : "▶ REPLAY CHRONOLOGY"}</span>
          </button>

          <button
            type="button"
            onClick={() => onSelectYear("ALL")}
            className={`rounded-lg px-2.5 py-1 font-mono text-xs transition ${
              selectedYear === "ALL"
                ? "bg-cyan-950 text-cyan-300 border border-cyan-500/40 font-bold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            VIEW ALL YEARS ({events.length})
          </button>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-slate-400">TEMPORAL POSITION:</span>
          <span className="font-bold text-cyan-300">
            {selectedYear === "ALL" ? "FULL HISTORY" : selectedYear}
          </span>
          <span className="text-slate-500">•</span>
          <span className="text-slate-400">
            {activeEventsCount} verified observations
          </span>
        </div>
      </div>

      {/* Temporal Timeline Rail */}
      <div className="mt-4 px-2">
        <div className="relative flex items-center justify-between">
          {/* Rail Track Line */}
          <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 h-1 rounded-full bg-slate-800" />
          <div
            className="absolute left-0 top-1/2 -translate-y-1/2 h-1 rounded-full bg-gradient-to-r from-cyan-500 via-purple-500 to-cyan-400 transition-all duration-300"
            style={{
              width:
                selectedYear === "ALL"
                  ? "100%"
                  : `${(YEARS.indexOf(selectedYear) / (YEARS.length - 1)) * 100}%`,
            }}
          />

          {/* Year Markers */}
          {YEARS.map((yr, idx) => {
            const isSelected = selectedYear === yr;
            const count = (eventsByYear[yr] || []).length;
            const hasData = count > 0;

            return (
              <div
                key={yr}
                onClick={() => onSelectYear(yr)}
                className="relative z-10 flex flex-col items-center cursor-pointer group"
              >
                {/* Micro Dot on Rail */}
                <div
                  className={`h-4 w-4 rounded-full border-2 transition-all duration-200 flex items-center justify-center ${
                    isSelected
                      ? "border-cyan-400 bg-cyan-950 scale-125 shadow-[0_0_12px_#00f0ff]"
                      : hasData
                      ? "border-slate-600 bg-slate-900 group-hover:border-cyan-400 group-hover:scale-110"
                      : "border-slate-800 bg-slate-950"
                  }`}
                >
                  {hasData && (
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        isSelected ? "bg-cyan-400 animate-ping" : "bg-slate-400"
                      }`}
                    />
                  )}
                </div>

                {/* Year Label */}
                <span
                  className={`mt-2 font-mono text-[11px] transition-colors ${
                    isSelected
                      ? "font-bold text-cyan-300"
                      : "text-slate-500 group-hover:text-slate-300"
                  }`}
                >
                  {yr}
                </span>

                {/* Event Count Pill */}
                {count > 0 && (
                  <span
                    className={`mt-0.5 rounded px-1 text-[9px] font-mono ${
                      isSelected
                        ? "bg-cyan-500/20 text-cyan-300"
                        : "text-slate-400"
                    }`}
                  >
                    {count}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Zero State for Specific Year */}
      {selectedYear !== "ALL" && activeEventsCount === 0 && (
        <div className="mt-4 rounded-xl border border-slate-800/80 bg-slate-900/30 p-2 text-center text-xs font-mono text-slate-400">
          No verified historical observation for {selectedYear}. Reconstructs baseline from prior recorded telemetry.
        </div>
      )}
    </div>
  );
}
