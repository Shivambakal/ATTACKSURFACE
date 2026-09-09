"use client";

import React, { useEffect, useState } from "react";

export default function ThemeToggle({ className = "" }: { className?: string }) {
  const [theme, setTheme] = useState<"white-aesthetic" | "cyber-dark">("white-aesthetic");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = window.localStorage.getItem("ast_theme_preference");
    const active = saved === "cyber-dark" ? "cyber-dark" : "white-aesthetic";
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
      <div className={`h-8 w-28 rounded-xl bg-white/[0.05] animate-pulse ${className}`} />
    );
  }

  const isWhite = theme === "white-aesthetic";

  return (
    <button
      onClick={handleToggle}
      className={`group flex items-center gap-2 rounded-xl px-3 py-1.5 font-mono text-xs font-semibold transition-all duration-300 border ${
        isWhite
          ? "bg-white/90 text-slate-800 border-slate-300 shadow-sm hover:border-cyan-500 hover:text-cyan-600"
          : "bg-slate-900/80 text-cyan-300 border-slate-800 shadow-sm hover:border-cyan-500/50 hover:text-cyan-200"
      } ${className}`}
      title="Switch between White Aesthetic and Cyber Dark"
    >
      <span className="text-sm">
        {isWhite ? "☀️" : "🌙"}
      </span>
      <span>
        {isWhite ? "White 3D" : "Dark 3D"}
      </span>
    </button>
  );
}
