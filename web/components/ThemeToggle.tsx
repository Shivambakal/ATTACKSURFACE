"use client";

import React, { useEffect, useState } from "react";

export default function ThemeToggle({ className = "" }: { className?: string }) {
  const [theme, setTheme] = useState<"white-aesthetic" | "cyber-dark">("cyber-dark");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = window.localStorage.getItem("ast_theme_preference");
    const active = saved === "white-aesthetic" ? "white-aesthetic" : "cyber-dark";
    setTheme(active);
    applyTheme(active);
  }, []);

  const applyTheme = (newTheme: "white-aesthetic" | "cyber-dark") => {
    if (typeof document === "undefined") return;
    document.documentElement.dataset.theme = newTheme;
    if (newTheme === "white-aesthetic") {
      document.documentElement.classList.add("theme-white-aesthetic");
      document.documentElement.classList.remove("dark");
    } else {
      document.documentElement.classList.remove("theme-white-aesthetic");
      document.documentElement.classList.add("dark");
    }
    window.localStorage.setItem("ast_theme_preference", newTheme);
  };

  const handleToggle = () => {
    const nextTheme = theme === "white-aesthetic" ? "cyber-dark" : "white-aesthetic";
    setTheme(nextTheme);
    applyTheme(nextTheme);
  };

  if (!mounted) {
    return (
      <div className={`h-9 w-9 rounded-2xl bg-white/[0.05] border border-white/[0.08] animate-pulse shrink-0 ${className}`} />
    );
  }

  const isWhite = theme === "white-aesthetic";

  return (
    <button
      onClick={handleToggle}
      className={`group relative flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border transition-all duration-300 active:scale-90 cursor-pointer ${
        isWhite
          ? "bg-slate-100/90 text-slate-700 border-slate-300/80 hover:bg-white hover:border-slate-400 hover:text-slate-900 shadow-sm"
          : "bg-[#12141c]/90 text-slate-300 border-slate-800/90 hover:bg-[#181a24] hover:border-slate-700 hover:text-white shadow-sm"
      } ${className}`}
      title={isWhite ? "Switch to Dark Mode" : "Switch to Light Mode"}
      aria-label={isWhite ? "Switch to Dark Mode" : "Switch to Light Mode"}
    >
      <div className="relative flex h-4 w-4 items-center justify-center transition-transform duration-500 ease-out group-hover:rotate-45">
        {isWhite ? (
          // Moon icon when in light mode (with smooth entrance animation)
          <svg
            className="h-4 w-4 transition-all duration-500 transform rotate-0 scale-100"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        ) : (
          // Sun icon matching user's image (with smooth entrance animation)
          <svg
            className="h-4 w-4 transition-all duration-500 transform rotate-0 scale-100"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2" />
            <path d="M12 20v2" />
            <path d="M4.93 4.93l1.41 1.41" />
            <path d="M17.66 17.66l1.41 1.41" />
            <path d="M2 12h2" />
            <path d="M20 12h2" />
            <path d="M4.93 19.07l1.41-1.41" />
            <path d="M17.66 6.34l1.41-1.41" />
          </svg>
        )}
      </div>
    </button>
  );
}
