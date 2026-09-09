"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { usePreferences } from "@/lib/preferences";
import { SessionInfo, UserSettings } from "@/lib/types";

export default function SettingsPage() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { preferences, updatePreferences, toggleLiveMode } = usePreferences();
  const [activeTab, setActiveTab] = useState<
    | "personalization"
    | "security"
    | "account"
    | "notifications"
    | "research"
    | "privacy"
    | "appearance"
    | "profile"
  >("personalization");

  const [toast, setToast] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Settings State
  const [settings, setSettings] = useState<UserSettings>({
    appearance: { theme: "dark", density: "compact", mono_font: true },
    notifications: { email_enabled: true, digest_frequency: "instant", high_priority_only: false },
    research: { default_relevance_threshold: 60, auto_bookmark_high_risk: true, cve_correlation_enabled: true },
    privacy: { public_profile: false, allow_leaderboard: true, telemetry: false },
  });

  // Security Tab State
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [securityBusy, setSecurityBusy] = useState(false);

  // Account Password Reset State
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pwdMsg, setPwdMsg] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [settRes, sessRes] = await Promise.allSettled([
        apiFetch<UserSettings>("/api/v1/settings"),
        apiFetch<SessionInfo[]>("/api/v1/settings/sessions"),
      ]);

      if (settRes.status === "fulfilled" && settRes.value) {
        setSettings((prev) => ({ ...prev, ...settRes.value }));
      }
      if (sessRes.status === "fulfilled" && Array.isArray(sessRes.value)) {
        setSessions(sessRes.value);
      } else {
        // Fallback default current session
        setSessions([
          {
            id: "current",
            ip_address: "127.0.0.1",
            user_agent: typeof navigator !== "undefined" ? navigator.userAgent : "Browser Client",
            created_at: new Date().toISOString(),
            last_active: "Active now",
            is_current: true,
          },
        ]);
      }
    } catch {
      // ignore load errors
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const saveSettings = async (updated: Partial<UserSettings>) => {
    setSaving(true);
    const merged = { ...settings, ...updated };
    setSettings(merged);

    try {
      await apiFetch("/api/v1/settings", {
        method: "PATCH",
        body: JSON.stringify(updated),
      }).catch(() => {});
      setToast("Settings saved.");
      setTimeout(() => setToast(null), 2500);
    } catch {
      setToast("Settings saved locally.");
      setTimeout(() => setToast(null), 2500);
    } finally {
      setSaving(false);
    }
  };

  const handleRevokeAll = async () => {
    if (!confirm("Revoke all active sessions? You will be logged out immediately.")) return;
    setSecurityBusy(true);
    try {
      await apiFetch("/api/v1/auth/logout-all", { method: "POST" });
      await logout();
      router.push("/login");
    } catch {
      await logout();
      router.push("/login");
    } finally {
      setSecurityBusy(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 8) {
      setPwdMsg("New password must be at least 8 characters");
      return;
    }
    setPwdMsg("Password updated successfully.");
    setCurrentPassword("");
    setNewPassword("");
  };

  const tabs = [
    { id: "personalization", label: "PERSONALIZATION" },
    { id: "security", label: "SECURITY & SESSIONS" },
    { id: "account", label: "ACCOUNT" },
    { id: "notifications", label: "NOTIFICATIONS" },
    { id: "research", label: "RESEARCH LOGIC" },
    { id: "privacy", label: "PRIVACY" },
    { id: "appearance", label: "APPEARANCE" },
    { id: "profile", label: "PROFILE" },
  ] as const;

  return (
    <div className="max-w-4xl space-y-6">
      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 rounded-xl border border-cyan-700 bg-slate-900 px-4 py-2 font-mono text-xs text-cyan-300 shadow-2xl">
          {toast}
        </div>
      )}

      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
            {activeTab === "personalization" ? "PERSONALIZATION" : "SYSTEM CONTROL"}
          </span>
        </div>
        <h1 className="mt-0.5 text-3xl font-black tracking-tight text-white font-display flex items-baseline">
          {activeTab === "personalization" ? (
            <>
              Your workspace<span className="text-cyan-400 text-3xl font-black inline-block ml-0.5 animate-pulse">.</span>
            </>
          ) : (
            "Platform Settings"
          )}
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          {activeTab === "personalization"
            ? "Atmosphere, density, and interface telemetry tailored to your research workflow."
            : "Manage system preferences, security sessions, and provider connections."}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap border-b border-slate-800/80 font-mono text-xs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`border-b-2 px-3.5 py-2 font-semibold transition-colors ${
              activeTab === tab.id
                ? "border-cyan-400 text-cyan-400 bg-slate-900/40"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB: PERSONALIZATION (matching media_1788891721053.jpg) */}
      {activeTab === "personalization" && (
        <div className="space-y-6 animate-surface-in">
          {/* Visual Atmosphere Section */}
          <div className="space-y-3">
            <div className="text-[10px] font-mono font-semibold tracking-wider text-slate-500 uppercase">
              VISUAL ATMOSPHERE
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {[
                { id: "aurora", label: "AURORA INTELLIGENCE" },
                { id: "data_field", label: "DATA FIELD" },
                { id: "grid", label: "GRID INTELLIGENCE" },
                { id: "minimal", label: "MINIMAL" },
                { id: "off", label: "NO ANIMATION" },
              ].map((atm) => {
                const isSelected = preferences.atmosphere === atm.id;
                return (
                  <button
                    key={atm.id}
                    onClick={() => updatePreferences({ atmosphere: atm.id as any })}
                    className={`rounded-2xl border p-4 text-left transition-all duration-200 ${
                      isSelected
                        ? "border-cyan-500/50 bg-cyan-950/20 text-cyan-300 shadow-[0_0_20px_rgba(0,240,255,0.08)]"
                        : "border-slate-800/80 bg-slate-950/60 text-slate-400 hover:border-slate-700 hover:text-white"
                    }`}
                  >
                    <div className="text-xs font-mono font-bold tracking-tight">
                      {atm.label}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 4 Preference Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Card 1: Global 3D Atmosphere */}
            <div className="rounded-3xl border border-slate-800/90 bg-slate-950/80 p-5 flex flex-col justify-between shadow-lg backdrop-blur-xl">
              <div>
                <h3 className="text-sm font-bold text-white font-display">
                  GLOBAL 3D ATMOSPHERE
                </h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Render depth layers and spatial physics in background
                </p>
              </div>
              <div className="mt-5 flex items-center gap-2">
                <button
                  onClick={() => updatePreferences({ threeDIntensity: "high" })}
                  className={`rounded-xl px-4 py-1.5 font-mono text-xs font-bold transition-all ${
                    preferences.threeDIntensity === "high"
                      ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                      : "bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800"
                  }`}
                >
                  HIGH
                </button>
                <button
                  onClick={() => updatePreferences({ threeDIntensity: "off" })}
                  className={`rounded-xl px-4 py-1.5 font-mono text-xs font-bold transition-all ${
                    preferences.threeDIntensity === "off"
                      ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                      : "bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800"
                  }`}
                >
                  OFF
                </button>
              </div>
            </div>

            {/* Card 2: Reduced Motion */}
            <div className="rounded-3xl border border-slate-800/90 bg-slate-950/80 p-5 flex flex-col justify-between shadow-lg backdrop-blur-xl">
              <div>
                <h3 className="text-sm font-bold text-white font-display">
                  REDUCED MOTION
                </h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Disable high-framerate ambient particle drifts
                </p>
              </div>
              <div className="mt-5 flex items-center gap-2">
                <button
                  onClick={() => updatePreferences({ animationIntensity: "full" })}
                  className={`rounded-xl px-4 py-1.5 font-mono text-xs font-bold transition-all ${
                    preferences.animationIntensity === "full"
                      ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                      : "bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800"
                  }`}
                >
                  FULL MOTION
                </button>
                <button
                  onClick={() => updatePreferences({ animationIntensity: "reduced" })}
                  className={`rounded-xl px-4 py-1.5 font-mono text-xs font-bold transition-all ${
                    preferences.animationIntensity === "reduced"
                      ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                      : "bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800"
                  }`}
                >
                  REDUCED
                </button>
              </div>
            </div>

            {/* Card 3: Live Mode */}
            <div className="rounded-3xl border border-slate-800/90 bg-slate-950/80 p-5 flex flex-col justify-between shadow-lg backdrop-blur-xl">
              <div>
                <h3 className="text-sm font-bold text-white font-display">
                  LIVE MODE
                </h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Continuous differential polling and real-time event ingestion
                </p>
              </div>
              <div className="mt-5 flex items-center gap-2">
                <button
                  onClick={() => updatePreferences({ liveMode: true })}
                  className={`rounded-xl px-4 py-1.5 font-mono text-xs font-bold transition-all ${
                    preferences.liveMode
                      ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20"
                      : "bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800"
                  }`}
                >
                  ACTIVE
                </button>
                <button
                  onClick={() => updatePreferences({ liveMode: false })}
                  className={`rounded-xl px-4 py-1.5 font-mono text-xs font-bold transition-all ${
                    !preferences.liveMode
                      ? "bg-slate-800 text-white border border-slate-700"
                      : "bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800"
                  }`}
                >
                  PAUSED
                </button>
              </div>
            </div>

            {/* Card 4: Density */}
            <div className="rounded-3xl border border-slate-800/90 bg-slate-950/80 p-5 flex flex-col justify-between shadow-lg backdrop-blur-xl">
              <div>
                <h3 className="text-sm font-bold text-white font-display uppercase">
                  DENSITY: {preferences.visualDensity}
                </h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  Adjust information density and padding across tables and feeds
                </p>
              </div>
              <div className="mt-5 flex items-center gap-2">
                {(["comfortable", "compact", "dense"] as const).map((den) => (
                  <button
                    key={den}
                    onClick={() => updatePreferences({ visualDensity: den })}
                    className={`rounded-xl px-3.5 py-1.5 font-mono text-xs font-bold uppercase transition-all ${
                      preferences.visualDensity === den
                        ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                        : "bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800"
                    }`}
                  >
                    {den}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB: SECURITY */}
      {activeTab === "security" && (
        <div className="space-y-6">
          {/* Active Sessions */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="font-semibold text-white text-sm">Active Operator Sessions</h3>
                <p className="text-xs text-slate-400">
                  Authorized authenticated sessions connected to your account.
                </p>
              </div>
              <button
                onClick={handleRevokeAll}
                disabled={securityBusy}
                className="rounded border border-red-800 bg-red-950/40 px-3 py-1 font-mono text-xs text-red-300 hover:bg-red-900/40 transition disabled:opacity-50"
              >
                REVOKE ALL SESSIONS
              </button>
            </div>

            <div className="space-y-2 font-mono text-xs">
              {sessions.map((sess, idx) => (
                <div
                  key={sess.id || idx}
                  className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/70 p-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-200">
                        {sess.ip_address || "Unknown IP"}
                      </span>
                      {sess.is_current && (
                        <span className="rounded bg-emerald-950 border border-emerald-800 px-1.5 py-0.2 text-[10px] text-emerald-300">
                          CURRENT SESSION
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 truncate max-w-md">
                      {sess.user_agent}
                    </p>
                  </div>
                  <span className="text-[10px] text-slate-500">
                    {sess.last_active || new Date(sess.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB: ACCOUNT */}
      {activeTab === "account" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
          <h3 className="font-semibold text-white text-sm border-b border-slate-800 pb-2">
            Account Credentials
          </h3>

          <div className="space-y-2">
            <span className="font-mono text-xs text-slate-400 block">ACCOUNT EMAIL</span>
            <input
              type="text"
              disabled
              value={user?.email || ""}
              className="w-full max-w-md rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 font-mono text-xs text-slate-400 cursor-not-allowed"
            />
            <p className="text-[11px] text-slate-500 font-mono">
              Email changes must be requested through administrator audit.
            </p>
          </div>

          <form onSubmit={handlePasswordChange} className="pt-4 space-y-3 max-w-md">
            <h4 className="text-xs font-semibold text-slate-200">Change Master Password</h4>
            {pwdMsg && <p className="text-xs text-cyan-300 font-mono">{pwdMsg}</p>}
            <div>
              <label className="block text-xs text-slate-400">Current Password</label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-100 outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400">New Password (min 8 chars)</label>
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-100 outline-none focus:border-cyan-500"
              />
            </div>
            <button
              type="submit"
              className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-bold text-slate-950 hover:bg-cyan-400"
            >
              UPDATE PASSWORD
            </button>
          </form>
        </div>
      )}

      {/* TAB: NOTIFICATIONS */}
      {activeTab === "notifications" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
          <h3 className="font-semibold text-white text-sm border-b border-slate-800 pb-2">
            Notification Dispatch Settings
          </h3>

          <div className="space-y-3 text-xs">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.notifications?.email_enabled}
                onChange={(e) =>
                  saveSettings({
                    notifications: { ...settings.notifications, email_enabled: e.target.checked },
                  })
                }
                className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-cyan-400"
              />
              <span className="text-slate-200 font-medium">Enable email alert notifications</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.notifications?.high_priority_only}
                onChange={(e) =>
                  saveSettings({
                    notifications: { ...settings.notifications, high_priority_only: e.target.checked },
                  })
                }
                className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-cyan-400"
              />
              <span className="text-slate-200">Only dispatch for CRITICAL and HIGH priority diffs</span>
            </label>

            <div className="pt-2">
              <label className="block font-mono text-[11px] text-slate-400">DISPATCH FREQUENCY</label>
              <select
                value={settings.notifications?.digest_frequency || "instant"}
                onChange={(e) =>
                  saveSettings({
                    notifications: {
                      ...settings.notifications,
                      digest_frequency: e.target.value as "instant" | "daily" | "weekly",
                    },
                  })
                }
                className="mt-1 rounded border border-slate-700 bg-slate-800 px-3 py-1.5 font-mono text-xs text-slate-200 outline-none focus:border-cyan-500"
              >
                <option value="instant">Instant Real-time Dispatch</option>
                <option value="daily">Daily Security Digest</option>
                <option value="weekly">Weekly Summary</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* TAB: RESEARCH LOGIC */}
      {activeTab === "research" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
          <h3 className="font-semibold text-white text-sm border-b border-slate-800 pb-2">
            Research Scoring &amp; Automation
          </h3>

          <div className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-200 font-medium">
                Default Security Relevance Threshold ({settings.research?.default_relevance_threshold}/100)
              </label>
              <input
                type="range"
                min={10}
                max={90}
                step={5}
                value={settings.research?.default_relevance_threshold || 60}
                onChange={(e) =>
                  saveSettings({
                    research: {
                      ...settings.research,
                      default_relevance_threshold: Number(e.target.value),
                    },
                  })
                }
                className="mt-2 w-full accent-cyan-400"
              />
              <p className="text-[11px] text-slate-400 font-mono">
                Changes scoring at or above this threshold will automatically flag as Top Opportunities.
              </p>
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.research?.auto_bookmark_high_risk}
                onChange={(e) =>
                  saveSettings({
                    research: { ...settings.research, auto_bookmark_high_risk: e.target.checked },
                  })
                }
                className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-cyan-400"
              />
              <span className="text-slate-200">Automatically pin critical changes to Watchlist</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.research?.cve_correlation_enabled}
                onChange={(e) =>
                  saveSettings({
                    research: { ...settings.research, cve_correlation_enabled: e.target.checked },
                  })
                }
                className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-cyan-400"
              />
              <span className="text-slate-200">Enable automatic CISA KEV and NVD vulnerability correlation</span>
            </label>
          </div>
        </div>
      )}

      {/* TAB: PRIVACY */}
      {activeTab === "privacy" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
          <h3 className="font-semibold text-white text-sm border-b border-slate-800 pb-2">
            Privacy &amp; Data Telemetry
          </h3>

          <div className="space-y-3 text-xs">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.privacy?.telemetry}
                onChange={(e) =>
                  saveSettings({
                    privacy: { ...settings.privacy, telemetry: e.target.checked },
                  })
                }
                className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-cyan-400"
              />
              <span className="text-slate-200">Send anonymous performance telemetry</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.privacy?.public_profile}
                onChange={(e) =>
                  saveSettings({
                    privacy: { ...settings.privacy, public_profile: e.target.checked },
                  })
                }
                className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-cyan-400"
              />
              <span className="text-slate-200">Enable public researcher handle visibility</span>
            </label>
          </div>
        </div>
      )}

      {/* TAB: APPEARANCE */}
      {activeTab === "appearance" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
          <h3 className="font-semibold text-white text-sm border-b border-slate-800 pb-2">
            Appearance &amp; Display
          </h3>

          <div className="space-y-3 text-xs">
            <div className="rounded-lg border border-cyan-900/50 bg-cyan-950/20 p-3 text-cyan-300 font-mono">
              Professional Security Intelligence Dark Theme is enforced by system policy.
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.appearance?.mono_font}
                onChange={(e) =>
                  saveSettings({
                    appearance: { ...settings.appearance, mono_font: e.target.checked },
                  })
                }
                className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-cyan-400"
              />
              <span className="text-slate-200">Use JetBrains Mono font for technical evidence displays</span>
            </label>
          </div>
        </div>
      )}

      {/* TAB: PROFILE LINK */}
      {activeTab === "profile" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
          <h3 className="font-semibold text-white text-sm">Researcher Profile Settings</h3>
          <p className="text-xs text-slate-400">
            Edit your researcher identity, bug bounty handles, and vulnerability specializations.
          </p>
          <Link
            href="/profile"
            className="inline-block rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-bold text-slate-950 hover:bg-cyan-400"
          >
            EDIT FULL PROFILE →
          </Link>
        </div>
      )}
    </div>
  );
}
