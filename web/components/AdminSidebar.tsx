"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import AttackSurfaceLogo from "@/components/AttackSurfaceLogo";

interface AdminSidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export default function AdminSidebar({ collapsed, onToggleCollapse }: AdminSidebarProps) {
  const pathname = usePathname();
  const { user } = useAuth();

  const adminNav = [
    {
      name: "Overview",
      href: "/admin",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
      ),
      badge: "HUB",
    },
    {
      name: "Operations",
      href: "/admin/operations",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
      badge: null,
    },
    {
      name: "Pipeline",
      href: "/admin/pipeline",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
      badge: "9-STG",
    },
    {
      name: "Providers",
      href: "/admin/providers",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      ),
      badge: null,
    },
    {
      name: "Sources",
      href: "/admin/sources",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" />
        </svg>
      ),
      badge: "LIVE",
    },
    {
      name: "Data Truth Audit",
      href: "/admin/data-truth",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      badge: "TRUTH",
    },
    {
      name: "Queues & Workers",
      href: "/admin/queues",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
        </svg>
      ),
      badge: "RQ",
    },
    {
      name: "Database Registry",
      href: "/admin/database",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
        </svg>
      ),
      badge: null,
    },
    {
      name: "System Health",
      href: "/admin/health",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      ),
      badge: "LIVE",
    },
    {
      name: "Errors & Alerts",
      href: "/admin/errors",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
      badge: null,
    },
    {
      name: "Audit Log",
      href: "/admin/audit",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
        </svg>
      ),
      badge: null,
    },
    {
      name: "Users & Roles",
      href: "/admin/users",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      ),
      badge: "RBAC",
    },
    {
      name: "50 Target Trial",
      href: "/admin/trial",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7h16M7 4v3m10-3v3M6 11h4m-4 4h4m4-4h4m-4 4h4M5 20h14a1 1 0 001-1V7H4v12a1 1 0 001 1z" />
        </svg>
      ),
      badge: "24H",
    },
  ];

  const secondaryNav = [
    {
      name: "Profile",
      href: "/profile",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      ),
    },
    {
      name: "Settings",
      href: "/settings",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
    },
  ];

  const [isHovered, setIsHovered] = React.useState<boolean>(false);
  const hoverTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    setIsHovered(true);
  };

  const handleMouseLeave = () => {
    hoverTimeoutRef.current = setTimeout(() => {
      setIsHovered(false);
    }, 160);
  };

  const isExpanded = !collapsed || isHovered;

  const isActive = (href: string) => {
    if (href === "/admin") return pathname === "/admin";
    return pathname.startsWith(href);
  };

  return (
    <aside
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={`fixed top-0 bottom-0 left-0 z-40 flex flex-col rounded-r-3xl overflow-hidden border-r border-amber-500/25 backdrop-blur-2xl bg-[#0c0e18]/85 [data-theme=white-aesthetic]:bg-white/90 [data-theme=white-aesthetic]:border-amber-400/40 shadow-[14px_0_45px_rgba(0,0,0,0.4)] transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        isExpanded ? "w-64" : "w-16"
      }`}
    >
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between border-b border-amber-500/20 px-3.5 bg-amber-500/[0.03]">
        <AttackSurfaceLogo
          size={isExpanded ? "md" : "sm"}
          showText={isExpanded}
          href="/admin"
        />

        {isExpanded && (
          <button
            onClick={onToggleCollapse}
            title={collapsed ? "Pin sidebar open" : "Collapse to hover mode"}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800/80 transition-colors cursor-pointer"
          >
            <svg
              className="w-4 h-4 transition-transform duration-200"
              style={{ transform: collapsed ? "rotate(180deg)" : "rotate(0deg)" }}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
          </button>
        )}
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 space-y-3 overflow-y-auto px-2 py-3 scrollbar-none">
        {/* Mode Switcher */}
        <div className="mb-2 px-1">
          {isExpanded ? (
            <div className="grid grid-cols-2 gap-1 p-1 bg-slate-900/90 rounded-xl border border-amber-500/25">
              <div className="py-1 px-2 rounded-lg text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 text-center">
                ⚡ ADMIN
              </div>
              <Link
                href="/dashboard"
                className="py-1 px-2 rounded-lg text-[10px] font-mono text-cyan-400 hover:text-cyan-300 text-center hover:bg-cyan-500/10 transition flex items-center justify-center gap-1 font-bold"
              >
                <span>🌐</span>
                <span>PLATFORM</span>
              </Link>
            </div>
          ) : (
            <Link
              href="/dashboard"
              title="Switch to Research Platform"
              className="flex items-center justify-center p-2 rounded-lg text-cyan-400 hover:bg-cyan-950/40 transition border border-cyan-500/30"
            >
              🌐
            </Link>
          )}
        </div>

        {/* Section 1: ADMIN CONSOLE */}
        <div>
          {!collapsed && (
            <div className="px-3 pb-1.5 pt-1 text-[10px] font-mono uppercase tracking-wider text-amber-400/90 font-bold flex items-center justify-between">
              <span>ADMIN CONSOLE</span>
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
            </div>
          )}
          <div className="space-y-0.5">
            {adminNav.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  title={collapsed ? item.name : undefined}
                  className={`group flex items-center gap-3 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    active
                      ? "bg-amber-500/15 text-amber-300 border border-amber-500/30 shadow-[inset_0_1px_0_rgba(255,255,255,.08)]"
                      : "text-slate-300 hover:bg-white/[.05] hover:text-white"
                  }`}
                >
                  <span className={`shrink-0 ${active ? "text-amber-400" : "text-slate-400 group-hover:text-amber-300"}`}>
                    {item.icon}
                  </span>
                  {!collapsed && <span className="truncate">{item.name}</span>}
                  {!collapsed && Boolean(item.badge) && (
                    <span className="ml-auto rounded-full bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-mono font-bold text-amber-300 border border-amber-500/30">
                      {item.badge}
                    </span>
                  )}
                  {collapsed && Boolean(item.badge) && (
                    <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-amber-400" />
                  )}
                </Link>
              );
            })}
          </div>
        </div>

        {/* Separator */}
        <div className="border-t border-slate-800/80 px-3" />

        {/* Secondary Navigation */}
        <div className="space-y-0.5">
          {secondaryNav.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                title={collapsed ? item.name : undefined}
                className={`group flex items-center gap-3 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  active
                    ? "bg-slate-800 text-white"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                }`}
              >
                <span className={`shrink-0 ${active ? "text-cyan-400" : "text-slate-400 group-hover:text-slate-300"}`}>
                  {item.icon}
                </span>
                {!collapsed && <span className="truncate">{item.name}</span>}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* User info footer */}
      {!collapsed && user && (
        <div className="border-t border-amber-500/20 px-3.5 py-2.5 bg-slate-950/50">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 uppercase tracking-wider">
                <span>SEC //</span>
                <span className="text-amber-400 font-medium">{user.role || "OWNER"}</span>
              </div>
              <div className="truncate text-xs font-mono text-slate-300 mt-0.5" title={user.email}>
                {user.email}
              </div>
            </div>
            <div className="shrink-0 flex items-center gap-1.5 text-[9px] font-mono text-amber-400/90 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
              <span>CONTROL</span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
