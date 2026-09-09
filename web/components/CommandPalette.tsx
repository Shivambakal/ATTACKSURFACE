"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { usePreferences, AtmosphereMode, VisualDensity } from "@/lib/preferences";

interface CommandItem {
  id: string;
  category: "Navigate" | "System" | "Company" | "Target" | "Advisory" | "Change";
  title: string;
  subtitle?: string;
  badge?: string;
  badgeTone?: "cyan" | "amber" | "rose" | "emerald" | "purple" | "neutral";
  icon?: React.ReactNode | string;
  onSelect: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const { user } = useAuth();
  const { preferences, updatePreferences, toggleLiveMode } = usePreferences();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<CommandItem[]>([]);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Base items matching media_1788891721051.jpg
  const getStaticActions = useCallback((): CommandItem[] => {
    return [
      // ── Group: Navigate ──
      {
        id: "nav-companies",
        category: "Navigate",
        title: "Companies",
        subtitle: "Canonical organization attack surfaces",
        badge: "G C",
        badgeTone: "neutral",
        icon: "🏢",
        onSelect: () => {
          router.push("/companies");
          onClose();
        },
      },
      {
        id: "nav-targets",
        category: "Navigate",
        title: "Attack Surface",
        subtitle: "Enrolled targets and domains",
        badge: "G A",
        badgeTone: "neutral",
        icon: "🎯",
        onSelect: () => {
          router.push("/targets");
          onClose();
        },
      },
      {
        id: "nav-intel",
        category: "Navigate",
        title: "Security Intelligence",
        subtitle: "Threat feeds and intelligence",
        badge: "S I",
        badgeTone: "neutral",
        icon: "⚡",
        onSelect: () => {
          router.push("/security-intelligence");
          onClose();
        },
      },
      {
        id: "nav-vulnerabilities",
        category: "Navigate",
        title: "Vulnerabilities",
        subtitle: "Actively exploited catalog & CISA KEV",
        badge: "KEV",
        badgeTone: "rose",
        icon: "🛡️",
        onSelect: () => {
          router.push("/security-knowledge");
          onClose();
        },
      },
      {
        id: "nav-programs",
        category: "Navigate",
        title: "Programs",
        subtitle: "Public bug bounty programs directory",
        icon: "📋",
        onSelect: () => {
          router.push("/programs");
          onClose();
        },
      },
      {
        id: "nav-timeline",
        category: "Navigate",
        title: "Timeline",
        subtitle: "Surface diffs chronological stream",
        badge: "G T",
        badgeTone: "neutral",
        icon: "⏱️",
        onSelect: () => {
          router.push("/changes");
          onClose();
        },
      },
      {
        id: "nav-evidence",
        category: "Navigate",
        title: "Evidence",
        subtitle: "Raw verified data sources & probes",
        icon: "📄",
        onSelect: () => {
          router.push("/sources");
          onClose();
        },
      },
      {
        id: "nav-alerts",
        category: "Navigate",
        title: "Alerts",
        subtitle: "Real-time dispatch notifications",
        badge: "G L",
        badgeTone: "neutral",
        icon: "🔔",
        onSelect: () => {
          router.push("/alerts");
          onClose();
        },
      },
      {
        id: "nav-priorities",
        category: "Navigate",
        title: "My Priorities",
        subtitle: "Watchlist of prioritized targets",
        icon: "⭐",
        onSelect: () => {
          router.push("/watchlist");
          onClose();
        },
      },

      // ── Group: System ──
      {
        id: "sys-live",
        category: "System",
        title: `Live mode: ${preferences.liveMode ? "ON" : "OFF"}`,
        subtitle: "Toggle continuous live diff polling stream",
        badge: preferences.liveMode ? "ACTIVE" : "PAUSED",
        badgeTone: preferences.liveMode ? "emerald" : "amber",
        icon: "⚡",
        onSelect: () => {
          toggleLiveMode();
          onClose();
        },
      },
      {
        id: "sys-3d",
        category: "System",
        title: `3D atmosphere: ${preferences.threeDIntensity === "high" ? "ON" : "OFF"}`,
        subtitle: "Toggle spatial depth layers and physics",
        badge: preferences.threeDIntensity === "high" ? "HIGH" : "OFF",
        badgeTone: "cyan",
        icon: "✨",
        onSelect: () => {
          updatePreferences({
            threeDIntensity: preferences.threeDIntensity === "high" ? "off" : "high",
          });
          onClose();
        },
      },
      {
        id: "sys-motion",
        category: "System",
        title: `Motion: ${preferences.animationIntensity === "full" ? "Full" : "Reduced"}`,
        subtitle: "Adjust interface motion and particle speed",
        badge: preferences.animationIntensity.toUpperCase(),
        badgeTone: "cyan",
        icon: "🌐",
        onSelect: () => {
          updatePreferences({
            animationIntensity: preferences.animationIntensity === "full" ? "reduced" : "full",
          });
          onClose();
        },
      },
      {
        id: "sys-profile",
        category: "System",
        title: "Open profile",
        subtitle: "Researcher identity and preferences",
        icon: "👤",
        onSelect: () => {
          router.push("/profile");
          onClose();
        },
      },
    ];
  }, [preferences, toggleLiveMode, updatePreferences, router, onClose]);

  // Live entity search
  useEffect(() => {
    if (!isOpen) return;

    const trimmed = query.trim().toLowerCase();
    if (!trimmed) {
      setResults(getStaticActions());
      setSelectedIndex(0);
      return;
    }

    let active = true;
    setLoading(true);

    const timer = setTimeout(async () => {
      try {
        const [compRes, targetRes, changesRes] = await Promise.allSettled([
          apiFetch<{ items: any[] }>(`/api/v1/companies?limit=6&q=${encodeURIComponent(trimmed)}`),
          apiFetch<any[]>(`/api/v1/targets?limit=6`),
          apiFetch<any[]>(`/api/v1/changes?limit=6&search=${encodeURIComponent(trimmed)}`),
        ]);

        if (!active) return;

        const dynamicItems: CommandItem[] = [];

        // Companies
        if (compRes.status === "fulfilled" && compRes.value?.items) {
          for (const c of compRes.value.items.slice(0, 4)) {
            dynamicItems.push({
              id: `comp-${c.id}`,
              category: "Company",
              title: c.name,
              subtitle: c.canonical_domain || c.industry || "Organization",
              badge: c.bug_bounty_url ? "BOUNTY" : "DISCLOSURE",
              badgeTone: c.bug_bounty_url ? "emerald" : "cyan",
              icon: "🏢",
              onSelect: () => {
                router.push(`/companies/${c.id}`);
                onClose();
              },
            });
          }
        }

        // Targets
        if (targetRes.status === "fulfilled" && Array.isArray(targetRes.value)) {
          const matchedTargets = targetRes.value
            .filter((t) => t.domain?.toLowerCase().includes(trimmed) || t.company_name?.toLowerCase().includes(trimmed))
            .slice(0, 3);
          for (const t of matchedTargets) {
            dynamicItems.push({
              id: `target-${t.id}`,
              category: "Target",
              title: t.domain,
              subtitle: t.company_name ? `Target for ${t.company_name}` : "Monitored scope",
              badge: "TARGET",
              badgeTone: "cyan",
              icon: "🎯",
              onSelect: () => {
                router.push(`/targets`);
                onClose();
              },
            });
          }
        }

        // Changes
        if (changesRes.status === "fulfilled" && Array.isArray(changesRes.value)) {
          for (const ch of changesRes.value.slice(0, 3)) {
            dynamicItems.push({
              id: `ch-${ch.id}`,
              category: "Change",
              title: ch.summary || "Attack Surface Change",
              subtitle: `${ch.target_domain || "Asset"} • ${ch.category || "DIFF"}`,
              badge: ch.priority || "CHANGE",
              badgeTone: ch.priority === "CRITICAL" ? "rose" : ch.priority === "HIGH" ? "amber" : "cyan",
              icon: "⚡",
              onSelect: () => {
                router.push(`/changes/${ch.id}`);
                onClose();
              },
            });
          }
        }

        // Filtered static actions
        const matchedActions = getStaticActions().filter(
          (a) => a.title.toLowerCase().includes(trimmed) || a.subtitle?.toLowerCase().includes(trimmed)
        );

        setResults([...dynamicItems, ...matchedActions]);
        setSelectedIndex(0);
      } catch {
        setResults(getStaticActions());
      } finally {
        if (active) setLoading(false);
      }
    }, 150);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [query, isOpen, getStaticActions, router, onClose]);

  // Keyboard navigation & global shortcuts (G C, G A, S I, G T, G L)
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (results.length > 0 ? (prev + 1) % results.length : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (results.length > 0 ? (prev - 1 + results.length) % results.length : 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[selectedIndex]) {
        results[selectedIndex].onSelect();
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  // Group results for categorized rendering when query is empty or by category
  const categories = Array.from(new Set(results.map((r) => r.category)));

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4 bg-slate-950/70 backdrop-blur-xl animate-surface-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Global Command Palette"
    >
      <div
        className="w-full max-w-xl rounded-2xl border border-slate-800/90 bg-slate-950/95 shadow-[0_25px_70px_rgba(0,0,0,0.8),0_0_40px_rgba(0,240,255,0.08)] overflow-hidden font-sans"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar (matching media_1788891721051.jpg) */}
        <div className="flex items-center gap-3 border-b border-slate-800/80 px-4 py-3 bg-slate-900/30">
          <svg className="h-4 w-4 text-slate-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search companies, assets..."
            className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none font-sans"
          />
          {loading && (
            <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent shrink-0" />
          )}
          <kbd className="rounded bg-slate-800/90 px-1.5 py-0.5 font-mono text-[10px] text-slate-400 border border-slate-700">
            esc
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-[420px] overflow-y-auto p-2 scrollbar-thin">
          {results.length === 0 ? (
            <div className="py-12 text-center text-slate-500 font-mono text-xs">
              NO COMMANDS OR INTELLIGENCE OBJECTS MATCHED "{query}"
            </div>
          ) : (
            categories.map((cat) => {
              const catItems = results.filter((r) => r.category === cat);
              return (
                <div key={cat} className="mb-2 last:mb-0">
                  <div className="px-3 py-1 text-[10px] font-mono font-semibold tracking-wider text-slate-500 uppercase">
                    {cat}
                  </div>
                  <div className="space-y-0.5">
                    {catItems.map((item) => {
                      const overallIdx = results.findIndex((r) => r.id === item.id);
                      const isSelected = overallIdx === selectedIndex;
                      return (
                        <div
                          key={item.id}
                          onClick={() => item.onSelect()}
                          onMouseEnter={() => setSelectedIndex(overallIdx)}
                          className={`flex items-center justify-between gap-3 rounded-xl px-3 py-2 cursor-pointer transition-all duration-100 ${
                            isSelected
                              ? "bg-slate-900/90 text-white border border-cyan-500/30 shadow-[0_0_15px_rgba(0,240,255,0.05)]"
                              : "text-slate-300 hover:bg-slate-900/40 border border-transparent"
                          }`}
                        >
                          <div className="flex items-center gap-2.5 overflow-hidden">
                            <span className="text-sm shrink-0 opacity-80">{item.icon || "•"}</span>
                            <span className="text-xs font-medium truncate text-slate-200">
                              {item.title}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            {item.badge && (
                              <kbd
                                className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-medium border ${
                                  item.badgeTone === "rose"
                                    ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                                    : item.badgeTone === "emerald"
                                    ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                                    : item.badgeTone === "amber"
                                    ? "bg-amber-500/15 text-amber-300 border-amber-500/30"
                                    : item.badgeTone === "cyan"
                                    ? "bg-cyan-500/15 text-cyan-300 border-cyan-500/30"
                                    : "bg-slate-800/80 text-slate-400 border-slate-700/80"
                                }`}
                              >
                                {item.badge}
                              </kbd>
                            )}
                            {isSelected && (
                              <span className="font-mono text-[10px] text-cyan-400">↵</span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts helper (matching media_1788891721051.jpg) */}
        <div className="flex items-center justify-between border-t border-slate-800/80 px-4 py-2 bg-slate-950 text-[10px] font-mono text-slate-500">
          <div className="flex items-center gap-3">
            <span>
              <strong className="text-slate-400">↑↓</strong> navigate
            </span>
            <span>
              <strong className="text-slate-400">↵</strong> select
            </span>
          </div>
          <div className="text-slate-500 font-mono text-[10px]">
            <kbd className="rounded bg-slate-800/80 px-1 py-0.5 text-slate-400 border border-slate-700 mr-1">⌘k</kbd> to toggle
          </div>
        </div>
      </div>
    </div>
  );
}
