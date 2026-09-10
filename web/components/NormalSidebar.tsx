"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import AttackSurfaceLogo from "@/components/AttackSurfaceLogo";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Alert } from "@/lib/types";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  onOpenCommand?: () => void;
}

interface NavItem {
  name: string;
  href: string;
  icon: React.ReactNode;
  badge?: string | number | null;
  badgeTone?: "cyan" | "amber" | "rose" | "purple";
  shortcut?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export default function NormalSidebar({ collapsed, onToggleCollapse, onOpenCommand }: SidebarProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const [unreadAlerts, setUnreadAlerts] = useState<number>(0);

  useEffect(() => {
    let isMounted = true;
    const checkAlerts = async () => {
      try {
        const alerts = await apiFetch<Alert[]>("/api/v1/alerts");
        if (isMounted && Array.isArray(alerts)) {
          const unread = alerts.filter((a) => !a.read).length;
          setUnreadAlerts(unread);
        }
      } catch {
        // Silently ignore if offline
      }
    };
    checkAlerts();
    const interval = setInterval(checkAlerts, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [pathname]);

  const navSections: NavSection[] = [
    {
      title: "COMMAND",
      items: [
        {
          name: "Dashboard",
          href: "/dashboard",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <rect x="3" y="3" width="7" height="7" rx="1.5" strokeWidth={1.8} />
              <rect x="14" y="3" width="7" height="7" rx="1.5" strokeWidth={1.8} />
              <rect x="14" y="14" width="7" height="7" rx="1.5" strokeWidth={1.8} />
              <rect x="3" y="14" width="7" height="7" rx="1.5" strokeWidth={1.8} />
            </svg>
          ),
        },
        {
          name: "Search",
          href: "/search",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          ),
        },
        {
          name: "AI Threat Analyst",
          href: "/assistant",
          icon: (
            <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          ),
          badge: "AI",
          badgeTone: "cyan",
        },
        {
          name: "Alerts",
          href: "/alerts",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
          ),
          badge: unreadAlerts > 0 ? unreadAlerts : null,
          badgeTone: "rose",
        },
      ],
    },
    {
      title: "INTELLIGENCE",
      items: [
        {
          name: "Companies",
          href: "/companies",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          ),
        },
        {
          name: "Attack Surface",
          href: "/targets",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="9" strokeWidth={1.8} />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 3v4m0 10v4M3 12h4m10 0h4m-7 0a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          ),
        },
        {
          name: "Security Intel",
          href: "/security-intelligence",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          ),
        },
        {
          name: "Vulnerabilities",
          href: "/security-knowledge",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          ),
        },
        {
          name: "Programs",
          href: "/programs",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          ),
        },
        {
          name: "Timeline",
          href: "/changes",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          ),
        },
        {
          name: "Evidence",
          href: "/sources",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          ),
        },
      ],
    },
    {
      title: "WORKSPACE",
      items: [
        {
          name: "My Priorities",
          href: "/watchlist",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
            </svg>
          ),
        },
        {
          name: "Saved",
          href: "/research/findings",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            </svg>
          ),
        },
        {
          name: "Compare",
          href: "/research",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          ),
        },
        {
          name: "Notes",
          href: "/research/notes",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          ),
        },
      ],
    },
    {
      title: "ACCOUNT",
      items: [
        {
          name: "Profile",
          href: "/profile",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          ),
        },
        {
          name: "Settings",
          href: "/settings",
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          ),
        },
      ],
    },
  ];

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  return (
    <aside
      className={`fixed top-0 bottom-0 left-0 z-40 flex flex-col border-r border-slate-800/80 bg-slate-950/80 backdrop-blur-2xl transition-all duration-300 ease-[cubic-bezier(0.2,0.9,0.3,1)] ${
        collapsed ? "w-16" : "w-60"
      }`}
    >
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between border-b border-slate-800/80 px-3.5 shrink-0">
        <AttackSurfaceLogo
          size={collapsed ? "sm" : "md"}
          showText={!collapsed}
          href="/dashboard"
        />
      </div>


      {/* Main Categorized Navigation */}
      <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-2 scrollbar-none">
        {navSections.map((section) => (
          <div key={section.title} className="space-y-1">
            {!collapsed && (
              <div className="px-2 pb-1 text-[10px] font-mono font-semibold tracking-wider text-slate-500 uppercase">
                {section.title}
              </div>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    title={collapsed ? item.name : undefined}
                    className={`group relative flex items-center gap-3 rounded-xl px-2.5 py-1.5 text-xs font-medium transition-all duration-150 ${
                      active
                        ? "bg-cyan-950/40 text-cyan-300 border border-cyan-500/30 shadow-[0_0_15px_rgba(0,240,255,0.06)]"
                        : "text-slate-400 hover:bg-white/[.04] hover:text-slate-100"
                    }`}
                  >
                    {active && (
                      <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-cyan-400 shadow-[0_0_8px_#00f0ff]" />
                    )}
                    <span className={`shrink-0 transition-colors ${active ? "text-cyan-400" : "text-slate-400 group-hover:text-slate-200"}`}>
                      {item.icon}
                    </span>
                    {!collapsed && (
                      <span className="truncate font-sans tracking-tight">
                        {item.name}
                      </span>
                    )}
                    {!collapsed && Boolean(item.badge) && (
                      <span
                        className={`ml-auto rounded px-1.5 py-0.2 text-[9px] font-mono font-bold border ${
                          item.badgeTone === "rose"
                            ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                            : "bg-cyan-500/15 text-cyan-300 border-cyan-500/30"
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom Collapse Bar */}
      <div className="border-t border-slate-800/80 px-3 py-2 bg-slate-950/40 shrink-0">
        <div className="flex items-center justify-between">
          {!collapsed ? (
            <span className="font-mono text-[10px] text-slate-500 uppercase tracking-wider">
              Navigation
            </span>
          ) : (
            <span className="w-1" />
          )}

          <button
            onClick={onToggleCollapse}
            title={collapsed ? "Expand sidebar ( [ )" : "Collapse sidebar ( [ )"}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-white/[.06] transition font-mono text-xs flex items-center gap-1 cursor-pointer"
          >
            <span>{collapsed ? "»" : "«"}</span>
            {!collapsed && <kbd className="text-[10px] text-slate-600 font-sans">[</kbd>}
          </button>
        </div>
      </div>
    </aside>
  );
}
