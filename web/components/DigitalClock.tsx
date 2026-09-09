"use client";

import React, { useEffect, useState } from "react";

function AnimatedDigit({ digit }: { digit: string }) {
  return (
    <div className="relative inline-flex h-5 w-3 items-center justify-center overflow-hidden font-mono font-bold text-xs text-cyan-300">
      <div
        key={digit}
        className="animate-surface-in flex flex-col items-center justify-center"
      >
        <span>{digit}</span>
      </div>
    </div>
  );
}

export default function DigitalClock() {
  const [time, setTime] = useState<{
    hours: string;
    minutes: string;
    seconds: string;
    date: string;
    timezone: string;
  } | null>(null);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const h = String(now.getHours()).padStart(2, "0");
      const m = String(now.getMinutes()).padStart(2, "0");
      const s = String(now.getSeconds()).padStart(2, "0");

      const day = String(now.getDate()).padStart(2, "0");
      const month = now
        .toLocaleString("en-US", { month: "short" })
        .toUpperCase();
      const year = now.getFullYear();

      // Extract short timezone (e.g. UTC, EST, GMT+5:30)
      const tzMatch = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const tzShort =
        tzMatch.split("/").pop()?.replace(/_/g, " ").slice(0, 8).toUpperCase() ||
        "LOCAL";

      setTime({
        hours: h,
        minutes: m,
        seconds: s,
        date: `${day} ${month} ${year}`,
        timezone: tzShort,
      });
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  if (!time) {
    return (
      <div className="flex items-center gap-2 font-mono text-[11px] text-slate-500">
        <span>00:00:00</span>
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-2.5 rounded-xl border border-cyan-500/20 bg-slate-950/70 px-3 py-1 shadow-[0_0_15px_rgba(0,240,255,0.05)] backdrop-blur-md"
      title={`Live Synchronized Client Time: ${time.date} ${time.hours}:${time.minutes}:${time.seconds} (${time.timezone})`}
      aria-label="Live synchronized clock"
    >
      {/* Rhythmic Live Telemetry Indicator */}
      <span className="relative flex h-2 w-2 items-center justify-center">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-cyan-400" />
      </span>

      {/* Digits HUD */}
      <div className="flex items-center font-mono text-xs font-semibold tracking-wider">
        <AnimatedDigit digit={time.hours[0]} />
        <AnimatedDigit digit={time.hours[1]} />
        <span className="mx-0.5 text-cyan-500/60 font-bold">:</span>
        <AnimatedDigit digit={time.minutes[0]} />
        <AnimatedDigit digit={time.minutes[1]} />
        <span className="mx-0.5 text-cyan-500/60 font-bold">:</span>
        <AnimatedDigit digit={time.seconds[0]} />
        <AnimatedDigit digit={time.seconds[1]} />
      </div>

      <div className="hidden items-center gap-1.5 border-l border-slate-800 pl-2 text-[10px] font-mono sm:flex">
        <span className="text-slate-400">{time.date}</span>
        <span className="rounded bg-cyan-950/60 px-1 py-0.2 text-[9px] font-bold text-cyan-400 border border-cyan-800/40">
          {time.timezone}
        </span>
      </div>
    </div>
  );
}
