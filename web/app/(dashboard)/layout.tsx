"use client";

import React, { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { PreferencesProvider, usePreferences } from "@/lib/preferences";
import AdminSidebar from "@/components/AdminSidebar";
import NormalSidebar from "@/components/NormalSidebar";
import GlobalSpatialBackground from "@/components/GlobalSpatialBackground";
import CommandPalette from "@/components/CommandPalette";
import NotificationCenter from "@/components/NotificationCenter";
import { apiFetch } from "@/lib/api";
import PublicNav from "@/components/PublicNav";
import PublicFooter from "@/components/PublicFooter";
import ThemeToggle from "@/components/ThemeToggle";
import CyberAssistantChat from "@/components/CyberAssistantChat";
import StaggeredMenu, { StaggeredMenuItem } from "@/components/StaggeredMenu";

const PUBLIC_ACCESSIBLE_ROUTES = ["/programs", "/security-intelligence", "/pricing"];

function DashboardShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();
  const { preferences, updatePreferences } = usePreferences();
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [userMenuOpen, setUserMenuOpen] = useState<boolean>(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState<boolean>(false);
  const [notificationCenterOpen, setNotificationCenterOpen] = useState<boolean>(false);
  const [unreadAlertsCount, setUnreadAlertsCount] = useState<number>(0);

  const isPublicAccessible = PUBLIC_ACCESSIBLE_ROUTES.includes(pathname);

  // Poll alerts count periodically for header bell
  useEffect(() => {
    if (!user) return;
    const fetchUnread = async () => {
      try {
        const data = await apiFetch<any[]>("/api/v1/alerts");
        if (Array.isArray(data)) {
          setUnreadAlertsCount(data.filter((a) => !a.read).length);
        }
      } catch {
        // Fallback
      }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000);
    return () => clearInterval(interval);
  }, [user]);

  // Global Keyboard shortcuts: Ctrl+K / Cmd+K for Command Palette, [ for Sidebar collapse
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      } else if (e.key === "[" && !["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)) {
        e.preventDefault();
        setSidebarCollapsed((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Auth protection check
  useEffect(() => {
    if (!loading && !user && !isPublicAccessible) {
      router.push("/login");
    }
  }, [user, loading, router, isPublicAccessible]);

  // Public visitor mode for shared public routes when unauthenticated
  if (!user && isPublicAccessible) {
    return (
      <div className="min-h-screen bg-[#030712] text-slate-100 flex flex-col selection:bg-cyan-500 selection:text-slate-950">
        <PublicNav />
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
          {children}
        </main>
        <PublicFooter />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 font-mono text-xs text-cyan-400">
        <div className="flex flex-col items-center gap-3">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
          <span>AUTHENTICATING OPERATOR SESSION...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const isAdmin = user.role === "OWNER" || user.role === "ADMIN" || Boolean((user as any).is_admin);
  const isDirectAdminRoute =
    pathname.startsWith("/admin") ||
    pathname === "/providers" ||
    pathname === "/trial";
  const showAdminSidebar = isAdmin && isDirectAdminRoute;

  // Human title from pathname
  const getPageTitle = () => {
    if (pathname === "/admin") return "Admin Control Center";
    if (pathname === "/admin/operations") return "Operations Control Plane";
    if (pathname === "/admin/pipeline") return "9-Stage Pipeline Architecture";
    if (pathname === "/admin/providers" || pathname === "/providers") return "Provider Operations & Registry";
    if (pathname === "/admin/sources") return "Intelligence Sources Management";
    if (pathname === "/admin/sources/cisa-kev") return "CISA KEV Live Source Inspector";
    if (pathname === "/admin/data-truth") return "Data Truth & Zero-Fabrication Audit";
    if (pathname === "/admin/queues") return "Redis & RQ Queues Telemetry";
    if (pathname === "/admin/database") return "Database Registry & Statistics";
    if (pathname === "/admin/health") return "System Health & Diagnostics";
    if (pathname === "/admin/errors") return "Error Center & Remediation";
    if (pathname === "/admin/audit") return "Audit Log & Chronological Trace";
    if (pathname === "/admin/users") return "User & Role Access Management";
    if (pathname === "/admin/trial" || pathname === "/trial") return "50 Target Controlled Trial";
    if (pathname === "/dashboard") return "Operational Intelligence Overview";
    if (pathname.startsWith("/companies/")) return "Company Intelligence Detail";
    if (pathname === "/companies") return "Canonical Company Directory";
    if (pathname.startsWith("/targets/")) return "Target Analysis";
    if (pathname === "/targets") return "Monitored Targets";
    if (pathname.startsWith("/changes/")) return "Change Forensic Detail";
    if (pathname === "/changes") return "Attack Surface Changes";
    if (pathname.startsWith("/programs/")) return "Program Detail";
    if (pathname === "/programs") return "Public Programs Directory";
    if (pathname === "/security-knowledge") return "Security Knowledge Base";
    if (pathname === "/security-intelligence") return "Security Intelligence";
    if (pathname.startsWith("/research/notes")) return "Research Notes";
    if (pathname.startsWith("/research/tasks")) return "Research Tasks";
    if (pathname.startsWith("/research/findings")) return "Vulnerability Findings";
    if (pathname.startsWith("/research")) return "Research Workspace";
    if (pathname === "/exports") return "Researcher Export Center";
    if (pathname === "/watchlist") return "Entity Watchlist";
    if (pathname === "/alerts") return "Security Alerts";
    if (pathname === "/search") return "Global Intelligence Search";
    if (pathname === "/profile") return "Researcher Profile";
    if (pathname === "/settings") return "Platform Settings";
    return "AttackSurface Timeline";
  };

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  const staggeredNavItems: StaggeredMenuItem[] = [
    { label: "Dashboard Hub", ariaLabel: "Dashboard Hub", link: "/dashboard" },
    { label: "Company Intelligence", ariaLabel: "Company Intelligence", link: "/companies" },
    { label: "Attack Surface Targets", ariaLabel: "Attack Surface Targets", link: "/targets" },
    { label: "Public Programs", ariaLabel: "Public Security Programs", link: "/programs", badge: "2,010" },
    { label: "Surface Diff Forensic", ariaLabel: "Surface Diff Forensic", link: "/changes" },
    { label: "AI Threat Analyst", ariaLabel: "AI Threat Analyst", link: "/assistant", badge: "AI" },
    { label: "Research Workspace", ariaLabel: "Research Workspace", link: "/research" },
    { label: "Security Alerts", ariaLabel: "Security Alerts", link: "/alerts", badge: unreadAlertsCount > 0 ? `${unreadAlertsCount} New` : undefined },
    { label: "Security Knowledge", ariaLabel: "Security Knowledge", link: "/security-knowledge" },
    ...(isAdmin ? [{ label: "Admin Control Plane", ariaLabel: "Admin Control Plane", link: "/admin", badge: "Admin" }] : []),
    { label: "Platform Settings", ariaLabel: "Platform Settings", link: "/settings" },
  ];

  const staggeredSocialItems = [
    { label: "Security API Docs", link: "/docs" },
    { label: "Global Search", link: "/search" },
    { label: "Entity Watchlist", link: "/watchlist" },
    { label: "System Health", link: "/status" },
  ];

  return (
    <div className="dashboard-ambient relative min-h-screen overflow-hidden text-slate-100 selection:bg-cyan-500 selection:text-slate-950 font-sans">
      {/* ── PERSISTENT GLOBAL SPATIAL BACKGROUND ────────────────── */}
      <GlobalSpatialBackground />

      {/* ── GLOBAL COMMAND PALETTE MODAL ───────────────────────── */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
      />

      {/* ── NOTIFICATION DISPATCH DRAWER ────────────────────────── */}
      <NotificationCenter
        isOpen={notificationCenterOpen}
        onClose={() => setNotificationCenterOpen(false)}
      />

      {/* ── PLAYABLE COMMAND SIDEBAR ────────────────────────────── */}
      {showAdminSidebar ? (
        <AdminSidebar
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      ) : (
        <NormalSidebar
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          onOpenCommand={() => setCommandPaletteOpen(true)}
        />
      )}

      {/* ── MAIN CONTAINER WITH DYNAMIC PADDING ─────────────────── */}
      <div
        className={`relative z-10 flex min-h-screen flex-col transition-all duration-300 ease-[cubic-bezier(0.2,0.9,0.3,1)] ${
          sidebarCollapsed
            ? "pl-16"
            : showAdminSidebar
            ? "pl-64"
            : "pl-60"
        }`}
      >
        {/* Top Header Bar (Timeline OS HUD) */}
        <header
          className={`sticky top-0 z-30 flex h-16 items-center justify-between border-b px-4 sm:px-6 backdrop-blur-xl transition-colors ${
            showAdminSidebar
              ? "border-amber-500/20 bg-slate-950/75"
              : "border-slate-800/80 bg-slate-950/80"
          }`}
        >
          {/* Left: StaggeredMenu Animated Sidebar Drawer + Page Title */}
          <div className="flex items-center gap-3">
            <StaggeredMenu
              position="left"
              items={staggeredNavItems}
              socialItems={staggeredSocialItems}
              isFixed={true}
              accentColor="#00f0ff"
            />
            <span className="hidden lg:inline text-sm font-semibold tracking-tight text-slate-200 font-display">
              {getPageTitle()}
            </span>
          </div>

          {/* Center: Search or command... [⌘K] */}
          <button
            onClick={() => setCommandPaletteOpen(true)}
            className="hidden sm:flex items-center gap-3 rounded-full border border-slate-800 bg-slate-900/60 px-5 py-1.5 text-xs text-slate-400 hover:border-cyan-500/40 hover:text-white transition shadow-sm"
            title="Global Command Center (⌘K)"
          >
            <svg className="h-3.5 w-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span>Search or command...</span>
            <kbd className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-cyan-400 border border-slate-700">
              ⌘K
            </kbd>
          </button>

          {/* Right: Bell, Theme Toggle, User Avatar */}
          <div className="flex items-center gap-2.5">

            {/* Notification Dispatch Bell */}
            <button
              onClick={() => setNotificationCenterOpen(true)}
              className="relative rounded-xl border border-slate-800 bg-slate-900/80 p-2 text-slate-400 hover:border-cyan-500/40 hover:text-white transition"
              title="Intelligence Dispatch"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              {unreadAlertsCount > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 font-mono text-[9px] font-bold text-white shadow-[0_0_8px_#f43f5e]">
                  {unreadAlertsCount > 9 ? "9+" : unreadAlertsCount}
                </span>
              )}
            </button>

            {/* Theme Toggle (Light / Dark) */}
            <ThemeToggle />

            {/* User Avatar Circle */}
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="group flex items-center gap-2 rounded-full p-0.5 text-xs text-slate-300 transition hover:bg-white/[.06]"
              >
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full border font-mono font-bold text-xs shadow-md transition-transform group-hover:scale-105 ${
                    isAdmin
                      ? "border-amber-500/50 bg-amber-500/15 text-amber-300"
                      : "border-cyan-500/50 bg-cyan-500/15 text-cyan-300"
                  }`}
                >
                  {user.email.slice(0, 2).toUpperCase()}
                </div>
              </button>

              {userMenuOpen && (
                <div
                  onMouseLeave={() => setUserMenuOpen(false)}
                  className="animate-surface-in absolute right-0 mt-3 w-72 rounded-2xl border border-slate-800 bg-slate-950/95 p-2 shadow-2xl z-50 font-sans backdrop-blur-2xl"
                >
                  <div className="border-b border-slate-800 px-3 py-2.5">
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] font-mono text-slate-400">SESSION IDENTITY</p>
                      <span
                        className={`rounded px-1.5 py-0.2 font-mono text-[9px] font-bold border ${
                          isAdmin
                            ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
                            : "bg-cyan-500/20 text-cyan-300 border-cyan-500/30"
                        }`}
                      >
                        {user.role}
                      </span>
                    </div>
                    <p className="truncate text-xs font-medium text-slate-200 mt-0.5">{user.email}</p>
                  </div>

                  {isAdmin && (
                    <Link
                      href="/admin"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-amber-300 hover:bg-amber-500/10 transition"
                    >
                      <span>⚡</span>
                      <span>Admin Control Center &rarr;</span>
                    </Link>
                  )}

                  <Link
                    href="/profile"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs text-slate-300 hover:bg-slate-800/80 hover:text-white transition"
                  >
                    <span>👤</span>
                    <span>Personal Intelligence World</span>
                  </Link>

                  <Link
                    href="/settings"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs text-slate-300 hover:bg-slate-800/80 hover:text-white transition"
                  >
                    <span>⚙️</span>
                    <span>Platform Settings</span>
                  </Link>

                  <div className="my-1 border-t border-slate-800" />
                  <button
                    onClick={handleLogout}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs text-rose-400 hover:bg-rose-950/40 hover:text-rose-300 transition"
                  >
                    <span>🚪</span>
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="animate-surface-in flex-1 p-4 sm:p-6">
          {/* Route Protection Guard */}
          {!isAdmin && isDirectAdminRoute ? (
            <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
              <div className="inline-flex p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 font-mono text-xl font-bold">
                403 FORBIDDEN
              </div>
              <h2 className="text-xl font-bold text-white">Administrative Access Restricted</h2>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                The Admin Control Center requires an <span className="font-semibold text-slate-200">OWNER</span> or <span className="font-semibold text-slate-200">ADMIN</span> role.
              </p>
              <div className="pt-4">
                <button
                  onClick={() => router.push("/dashboard")}
                  className="rounded-xl bg-cyan-500 px-5 py-2.5 text-xs font-bold text-slate-950 hover:bg-cyan-400 transition"
                >
                  Return to Research Dashboard
                </button>
              </div>
            </div>
          ) : (
            children
          )}
        </main>

        {/* AI Cyber Threat Analyst Floating Assistant */}
        {pathname !== "/assistant" && <CyberAssistantChat />}

        {/* Global Footer */}
        <PublicFooter />
      </div>
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <PreferencesProvider>
      <DashboardShell>{children}</DashboardShell>
    </PreferencesProvider>
  );
}
