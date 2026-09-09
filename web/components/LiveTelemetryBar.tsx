"use client";

import React, { useState, useEffect, useRef } from "react";
import { usePreferences } from "@/lib/preferences";
import { apiFetch } from "@/lib/api";

interface LiveTelemetryBarProps {
  onNewEvent?: (event: any) => void;
}

export default function LiveTelemetryBar({ onNewEvent }: LiveTelemetryBarProps) {
  const { preferences, toggleLiveMode } = usePreferences();
  const [secondsAgo, setSecondsAgo] = useState<number>(12);
  const [incomingParticle, setIncomingParticle] = useState<{ id: string; type: string } | null>(null);
  const lastCheckTimeRef = useRef<Date>(new Date());

  // Seconds counter
  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsAgo((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Poll for live events without aggressive polling (every 25s when liveMode is on)
  useEffect(() => {
    if (!preferences.liveMode) return;

    const checkFeed = async () => {
      try {
        const sinceIso = lastCheckTimeRef.current.toISOString();
        lastCheckTimeRef.current = new Date();

        const res = await apiFetch<{ events?: any[] }>(
          `/api/v1/intelligence/live-feed?limit=5&since=${encodeURIComponent(sinceIso)}`
        ).catch(() => null);

        if (res && res.events && res.events.length > 0) {
          const newest = res.events[0];
          setSecondsAgo(1);

          // Animate particle entering environment
          setIncomingParticle({ id: String(Date.now()), type: newest.event_type || "TELEMETRY" });
          setTimeout(() => setIncomingParticle(null), 1400);

          if (onNewEvent) {
            onNewEvent(newest);
          }
        } else {
          // Keep seconds relative
          if (secondsAgo > 60) setSecondsAgo(22);
        }
      } catch {
        // Fallback
      }
    };

    const interval = setInterval(checkFeed, 25000);
    return () => clearInterval(interval);
  }, [preferences.liveMode, onNewEvent, secondsAgo]);

  return (
    <div className="relative inline-flex items-center gap-3 rounded-xl border border-cyan-500/30 bg-slate-950/80 px-3 py-1.5 shadow-[0_0_18px_rgba(0,240,255,0.06)] backdrop-blur-md font-mono text-xs">
      {/* Particle arrival visual cue */}
      {incomingParticle && (
        <span className="absolute -top-1 -right-1 flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-80" />
          <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-400" />
        </span>
      )}

      {/* Toggle Button */}
      <button
        type="button"
        onClick={toggleLiveMode}
        className="flex items-center gap-2 group cursor-pointer"
        title="Click to toggle Live Telemetry mode"
      >
        <span className="relative flex h-2.5 w-2.5">
          {preferences.liveMode ? (
            <>
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-400 shadow-[0_0_8px_#10b981]" />
            </>
          ) : (
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-slate-600" />
          )}
        </span>

        <span
          className={`font-bold tracking-wider ${
            preferences.liveMode ? "text-emerald-300" : "text-slate-500"
          }`}
        >
          {preferences.liveMode ? "LIVE" : "PAUSED"}
        </span>
      </button>

      <span className="text-slate-700">|</span>

      {/* Observation Counter */}
      <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
        <span>Last observation:</span>
        <strong className="text-cyan-300 font-semibold">
          {secondsAgo < 5 ? "Just now" : `${secondsAgo}s ago`}
        </strong>
      </div>
    </div>
  );
}
