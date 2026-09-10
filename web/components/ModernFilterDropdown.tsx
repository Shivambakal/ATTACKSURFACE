"use client";

import React, { useState, useRef, useEffect } from "react";

export interface FilterOption {
  value: string;
  label: string;
  badge?: string | number;
  icon?: React.ReactNode;
  color?: string; // e.g. "rose", "amber", "cyan", "purple", "emerald"
}

interface ModernFilterDropdownProps {
  label: string;
  options: FilterOption[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
  align?: "left" | "right";
  icon?: React.ReactNode;
}

export default function ModernFilterDropdown({
  label,
  options,
  value,
  onChange,
  className = "",
  align = "left",
  icon,
}: ModernFilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setIsOpen(false);
    }
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  const selectedOption = options.find((opt) => opt.value === value) || options[0];
  const isFiltered = value && value !== "ALL" && value !== "" && value !== "7D";

  return (
    <div className={`relative inline-block text-left font-sans ${className}`} ref={containerRef}>
      {/* Trigger Button (Dribbble Filter UI) */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        className={`group inline-flex items-center gap-2.5 rounded-2xl border px-3.5 py-2 text-xs font-semibold transition-all duration-200 cursor-pointer shadow-sm hover:shadow-md backdrop-blur-xl ${
          isOpen
            ? "border-cyan-500/70 bg-cyan-500/10 text-cyan-300 ring-2 ring-cyan-500/20"
            : isFiltered
            ? "border-cyan-500/50 dark:bg-slate-900/90 bg-cyan-50/80 dark:text-cyan-300 text-cyan-800 ring-1 ring-cyan-500/20"
            : "dark:border-slate-800 border-slate-200/90 dark:bg-slate-950/80 bg-white/90 dark:text-slate-300 text-slate-700 hover:dark:border-slate-700 hover:border-slate-300 dark:hover:bg-slate-900/90 hover:bg-slate-50"
        }`}
      >
        {/* Leading Icon */}
        {icon ? (
          <span className="shrink-0 text-slate-400 group-hover:text-cyan-400 transition-colors">
            {icon}
          </span>
        ) : (
          <svg
            className={`h-3.5 w-3.5 shrink-0 transition-colors ${
              isFiltered ? "text-cyan-400" : "dark:text-slate-400 text-slate-500 group-hover:text-cyan-400"
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
          </svg>
        )}

        {/* Label and Value */}
        <span className="text-[11px] font-mono uppercase tracking-wider dark:text-slate-400 text-slate-500">
          {label}:
        </span>
        <span className="font-bold whitespace-nowrap">
          {selectedOption ? selectedOption.label : value}
        </span>

        {/* Active Badge if filtered */}
        {isFiltered && (
          <span className="flex h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee] shrink-0" />
        )}

        {/* Animated Chevron */}
        <svg
          className={`h-3.5 w-3.5 shrink-0 transition-transform duration-200 ${
            isOpen ? "rotate-180 text-cyan-400" : "dark:text-slate-500 text-slate-400 group-hover:text-slate-300"
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Floating Animated Dropdown Menu */}
      {isOpen && (
        <div
          className={`absolute z-50 mt-2 min-w-[210px] rounded-2xl border p-1.5 shadow-2xl backdrop-blur-2xl transition-all duration-150 animate-in fade-in zoom-in-95 ${
            align === "right" ? "right-0" : "left-0"
          } dark:border-slate-800/90 border-slate-200/90 dark:bg-slate-950/95 bg-white/95 text-slate-200`}
          style={{
            boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.05)",
          }}
        >
          {/* Header pill inside dropdown */}
          <div className="flex items-center justify-between px-3 py-1.5 mb-1 border-b dark:border-slate-800/80 border-slate-100">
            <span className="text-[10px] font-mono uppercase tracking-wider dark:text-slate-400 text-slate-400 font-semibold">
              Filter by {label}
            </span>
            {isFiltered && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onChange(options[0]?.value || "ALL");
                  setIsOpen(false);
                }}
                className="text-[10px] font-mono text-cyan-400 hover:text-cyan-300 underline cursor-pointer"
              >
                Reset
              </button>
            )}
          </div>

          {/* Option Items */}
          <div className="max-h-64 overflow-y-auto space-y-0.5 pr-0.5 custom-scrollbar">
            {options.map((option) => {
              const isSelected = option.value === value;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => {
                    onChange(option.value);
                    setIsOpen(false);
                  }}
                  className={`w-full group flex items-center justify-between rounded-xl px-3 py-2 text-xs font-medium transition-colors text-left cursor-pointer ${
                    isSelected
                      ? "dark:bg-cyan-500/15 bg-cyan-50 dark:text-cyan-300 text-cyan-900 font-bold"
                      : "dark:text-slate-300 text-slate-700 dark:hover:bg-slate-900 hover:bg-slate-100 dark:hover:text-white hover:text-slate-950"
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    {/* Status dot or icon */}
                    {option.icon ? (
                      <span className="shrink-0">{option.icon}</span>
                    ) : option.color ? (
                      <span
                        className={`h-2 w-2 rounded-full shrink-0 ${
                          option.color === "rose"
                            ? "bg-rose-500"
                            : option.color === "amber"
                            ? "bg-amber-500"
                            : option.color === "purple"
                            ? "bg-purple-500"
                            : option.color === "emerald"
                            ? "bg-emerald-500"
                            : "bg-cyan-500"
                        }`}
                      />
                    ) : (
                      <span
                        className={`h-1.5 w-1.5 rounded-full shrink-0 transition-opacity ${
                          isSelected ? "bg-cyan-400" : "dark:bg-slate-600 bg-slate-300 opacity-40 group-hover:opacity-100"
                        }`}
                      />
                    )}

                    <span className="truncate">{option.label}</span>
                  </div>

                  {/* Badge or Checkmark */}
                  <div className="flex items-center gap-1.5 shrink-0 ml-2">
                    {option.badge !== undefined && (
                      <span
                        className={`rounded-md px-1.5 py-0.5 font-mono text-[10px] ${
                          isSelected
                            ? "dark:bg-cyan-500/20 bg-cyan-200/60 dark:text-cyan-200 text-cyan-800 font-bold"
                            : "dark:bg-slate-800 bg-slate-100 dark:text-slate-400 text-slate-500"
                        }`}
                      >
                        {option.badge}
                      </span>
                    )}

                    {isSelected && (
                      <svg className="h-4 w-4 text-cyan-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
