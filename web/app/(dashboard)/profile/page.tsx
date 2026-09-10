"use client";

import React, { useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { Profile } from "@/lib/types";
import { usePreferences } from "@/lib/preferences";

export default function ProfilePage() {
  const { preferences } = usePreferences();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Profile Form Fields
  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [bio, setBio] = useState("");
  const [country, setCountry] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [language, setLanguage] = useState("en");
  const [researcherType, setResearcherType] = useState("Bug Bounty Hunter");
  const [experienceLevel, setExperienceLevel] = useState("Senior");
  const [vulnClasses, setVulnClasses] = useState<string[]>([]);
  const [technologies, setTechnologies] = useState<string[]>([]);
  const [publicProfile, setPublicProfile] = useState(false);

  // Handles & Target Domains
  const [hackerone, setHackerone] = useState("");
  const [bugcrowd, setBugcrowd] = useState("");
  const [github, setGithub] = useState("");
  const [twitter, setTwitter] = useState("");
  const [website, setWebsite] = useState("");

  // Verification telemetry states
  const [verifiedHandles, setVerifiedHandles] = useState<Record<string, any>>({});
  const [verifyingPlatform, setVerifyingPlatform] = useState<string | null>(null);
  const [verifyErrors, setVerifyErrors] = useState<Record<string, string>>({});

  // Input helpers
  const [vulnInput, setVulnInput] = useState("");
  const [techInput, setTechInput] = useState("");

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<Profile>("/api/v1/profile");
      if (data) {
        setDisplayName(data.display_name || "");
        setUsername(data.username || "");
        setBio(data.bio || "");
        setCountry(data.country || "");
        setTimezone(data.timezone || "UTC");
        setLanguage(data.language || "en");
        setResearcherType(data.researcher_type || "Bug Bounty Hunter");
        setExperienceLevel(data.experience_level || "Senior");
        setVulnClasses(data.favorite_vuln_classes || ["IDOR", "SSRF", "Auth Bypass"]);
        setTechnologies(data.favorite_technologies || ["Cloudflare", "Next.js", "GraphQL"]);
        setPublicProfile(Boolean(data.public_profile));

        if (data.handles) {
          setHackerone(data.handles.hackerone || "");
          setBugcrowd(data.handles.bugcrowd || "");
          setGithub(data.handles.github || "");
          setTwitter(data.handles.twitter || "");
          setWebsite(data.handles.website || "");
          if (data.handles.verified && typeof data.handles.verified === "object") {
            setVerifiedHandles(data.handles.verified as Record<string, any>);
          }
        }
      }
    } catch {
      setVulnClasses(["IDOR", "SSRF", "Auth Bypass"]);
      setTechnologies(["Cloudflare", "Next.js", "GraphQL"]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const payload = {
      display_name: displayName,
      username,
      bio,
      country,
      timezone,
      language,
      researcher_type: researcherType,
      experience_level: experienceLevel,
      favorite_vuln_classes: vulnClasses,
      favorite_technologies: technologies,
      public_profile: publicProfile,
      handles: {
        hackerone,
        bugcrowd,
        github,
        twitter,
        website,
        verified: verifiedHandles,
        preferences: {
          visualDensity: preferences.visualDensity,
          atmosphere: preferences.atmosphere,
          animationIntensity: preferences.animationIntensity,
          threeDIntensity: preferences.threeDIntensity,
          sidebarMode: preferences.sidebarMode,
          soundEnabled: preferences.soundEnabled,
          liveMode: preferences.liveMode,
          defaultTimeRange: preferences.defaultTimeRange,
        },
      },
    };

    try {
      await apiFetch("/api/v1/profile", {
        method: "PUT",
        body: JSON.stringify(payload),
      }).catch(async () => {
        await apiFetch("/api/v1/profile", {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      });

      setToast("Workspace environment and credentials saved successfully.");
      setTimeout(() => setToast(null), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const handleVerify = async (platform: string, handleValue: string) => {
    const val = handleValue.trim();
    if (!val) return;
    setVerifyingPlatform(platform);
    setVerifyErrors((prev) => ({ ...prev, [platform]: "" }));
    try {
      const res = await apiFetch<any>("/api/v1/profile/verify-handle", {
        method: "POST",
        body: JSON.stringify({ platform, handle: val }),
      });
      setVerifiedHandles((prev) => ({ ...prev, [platform]: res }));
      if (res.status === "VERIFIED") {
        setToast(`Verified authentic ${platform.toUpperCase()} telemetry.`);
        setTimeout(() => setToast(null), 3500);
      } else {
        setVerifyErrors((prev) => ({ ...prev, [platform]: res.error || "Identity check failed" }));
      }
    } catch (err: unknown) {
      setVerifyErrors((prev) => ({
        ...prev,
        [platform]: err instanceof Error ? err.message : "Verification request failed",
      }));
    } finally {
      setVerifyingPlatform(null);
    }
  };

  const addVulnClass = () => {
    const val = vulnInput.trim();
    if (val && !vulnClasses.includes(val)) {
      setVulnClasses([...vulnClasses, val]);
      setVulnInput("");
    }
  };

  const removeVulnClass = (cls: string) => {
    setVulnClasses(vulnClasses.filter((v) => v !== cls));
  };

  const addTechnology = () => {
    const val = techInput.trim();
    if (val && !technologies.includes(val)) {
      setTechnologies([...technologies, val]);
      setTechInput("");
    }
  };

  const removeTechnology = (tech: string) => {
    setTechnologies(technologies.filter((t) => t !== tech));
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center font-mono text-xs text-cyan-400">
        INITIALIZING OPERATOR WORKSPACE ENVIRONMENT...
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-16 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs uppercase tracking-wider text-cyan-400 font-bold">
              OPERATOR COMMAND WORLD
            </span>
          </div>
          <h1 className="mt-1 text-2xl font-black tracking-tight text-white font-display">
            Personal Intelligence Environment
          </h1>
          <p className="text-xs text-slate-400">
            Configure spatial atmospheric fields, micro-interaction density, acoustic telemetry, and researcher handles.
          </p>
        </div>

        {toast && (
          <div className="animate-surface-in rounded-xl border border-emerald-500/40 bg-emerald-950/60 px-4 py-2 text-xs font-mono font-bold text-emerald-300">
            ✓ {toast}
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-950/40 p-4 text-xs font-mono text-rose-300">
          {error}
        </div>
      )}


      {/* ── SECTION 2: RESEARCHER PROFILE & IDENTITY ─────────── */}
      <form onSubmit={handleSave} className="space-y-6">
        <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6 sm:p-8 shadow-xl backdrop-blur-xl space-y-6">
          <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#10b981]" />
              <h2 className="text-base font-bold text-white font-display tracking-tight">
                Researcher Identity &amp; Authorizations
              </h2>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-slate-300 font-semibold mb-1">Display Name</label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. Shiva"
                className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2.5 text-white focus:border-cyan-500 outline-none"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">Handle / Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. operator_01"
                className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2.5 text-white font-mono focus:border-cyan-500 outline-none"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-slate-300 font-semibold mb-1">Research Bio &amp; Specialty</label>
              <textarea
                rows={3}
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="Differential attack surface analysis, authentication logic flaws..."
                className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2.5 text-white focus:border-cyan-500 outline-none"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">Country</label>
              <input
                type="text"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                placeholder="e.g. United States"
                className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2.5 text-white focus:border-cyan-500 outline-none"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">Timezone</label>
              <input
                type="text"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                placeholder="e.g. UTC"
                className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2.5 text-white font-mono focus:border-cyan-500 outline-none"
              />
            </div>
          </div>

          {/* Research Handles & Verification */}
          <div className="border-t border-slate-800 pt-5 space-y-4">
            <div>
              <h3 className="font-mono text-xs uppercase text-slate-300 font-bold">
                Platform Handles &amp; Identity Verification
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Live verification via GitHub API, DNS lookup, and platform checks. No fake figures.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              {/* GitHub */}
              <div className="space-y-1.5">
                <label className="block text-slate-400 font-mono">GitHub Username</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={github}
                    onChange={(e) => setGithub(e.target.value)}
                    placeholder="github_username"
                    className="flex-1 rounded-xl bg-slate-900 border border-slate-800 px-3 py-2 text-white font-mono focus:border-cyan-500 outline-none text-xs"
                  />
                  <button
                    type="button"
                    onClick={() => handleVerify("github", github)}
                    disabled={!github.trim() || verifyingPlatform === "github"}
                    className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono text-xs font-semibold disabled:opacity-40 transition"
                  >
                    {verifyingPlatform === "github" ? "Checking..." : "Verify"}
                  </button>
                </div>
                {verifiedHandles.github?.status === "VERIFIED" ? (
                  <div className="text-[11px] text-emerald-400 font-mono flex items-center gap-1.5 pt-0.5">
                    <span>✓ Verified:</span>
                    <span>{verifiedHandles.github.public_repos} repos</span>
                    <span>•</span>
                    <span>{verifiedHandles.github.followers} followers</span>
                  </div>
                ) : verifiedHandles.github?.status || verifyErrors.github ? (
                  <div className="text-[11px] text-rose-400 font-mono pt-0.5">
                    ✕ {verifiedHandles.github?.error || verifyErrors.github || "Unverified handle"}
                  </div>
                ) : null}
              </div>

              {/* Personal Domain / Website */}
              <div className="space-y-1.5">
                <label className="block text-slate-400 font-mono">Personal Domain / Website</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={website}
                    onChange={(e) => setWebsite(e.target.value)}
                    placeholder="example.com or https://..."
                    className="flex-1 rounded-xl bg-slate-900 border border-slate-800 px-3 py-2 text-white font-mono focus:border-cyan-500 outline-none text-xs"
                  />
                  <button
                    type="button"
                    onClick={() => handleVerify("website", website)}
                    disabled={!website.trim() || verifyingPlatform === "website"}
                    className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono text-xs font-semibold disabled:opacity-40 transition"
                  >
                    {verifyingPlatform === "website" ? "Checking..." : "Verify"}
                  </button>
                </div>
                {verifiedHandles.website?.status === "VERIFIED" ? (
                  <div className="text-[11px] text-emerald-400 font-mono flex items-center gap-1.5 pt-0.5">
                    <span>✓ DNS Resolved:</span>
                    <span>IP {verifiedHandles.website.resolved_ips?.[0]}</span>
                    <span>(HTTP {verifiedHandles.website.http_status})</span>
                  </div>
                ) : verifiedHandles.website?.status || verifyErrors.website ? (
                  <div className="text-[11px] text-rose-400 font-mono pt-0.5">
                    ✕ {verifiedHandles.website?.error || verifyErrors.website || "Domain unresolvable"}
                  </div>
                ) : null}
              </div>

              {/* HackerOne */}
              <div className="space-y-1.5">
                <label className="block text-slate-400 font-mono">HackerOne Handle</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={hackerone}
                    onChange={(e) => setHackerone(e.target.value)}
                    placeholder="hackerone_handle"
                    className="flex-1 rounded-xl bg-slate-900 border border-slate-800 px-3 py-2 text-white font-mono focus:border-cyan-500 outline-none text-xs"
                  />
                  <button
                    type="button"
                    onClick={() => handleVerify("hackerone", hackerone)}
                    disabled={!hackerone.trim() || verifyingPlatform === "hackerone"}
                    className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono text-xs font-semibold disabled:opacity-40 transition"
                  >
                    {verifyingPlatform === "hackerone" ? "Checking..." : "Verify"}
                  </button>
                </div>
                {verifiedHandles.hackerone?.status === "VERIFIED" ? (
                  <div className="text-[11px] text-emerald-400 font-mono pt-0.5">
                    ✓ Verified public HackerOne profile
                  </div>
                ) : verifiedHandles.hackerone?.status || verifyErrors.hackerone ? (
                  <div className="text-[11px] text-rose-400 font-mono pt-0.5">
                    ✕ {verifiedHandles.hackerone?.error || verifyErrors.hackerone || "Profile not found"}
                  </div>
                ) : null}
              </div>

              {/* Bugcrowd */}
              <div className="space-y-1.5">
                <label className="block text-slate-400 font-mono">Bugcrowd Handle</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={bugcrowd}
                    onChange={(e) => setBugcrowd(e.target.value)}
                    placeholder="bugcrowd_handle"
                    className="flex-1 rounded-xl bg-slate-900 border border-slate-800 px-3 py-2 text-white font-mono focus:border-cyan-500 outline-none text-xs"
                  />
                  <button
                    type="button"
                    onClick={() => handleVerify("bugcrowd", bugcrowd)}
                    disabled={!bugcrowd.trim() || verifyingPlatform === "bugcrowd"}
                    className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono text-xs font-semibold disabled:opacity-40 transition"
                  >
                    {verifyingPlatform === "bugcrowd" ? "Checking..." : "Verify"}
                  </button>
                </div>
                {verifiedHandles.bugcrowd?.status === "VERIFIED" ? (
                  <div className="text-[11px] text-emerald-400 font-mono pt-0.5">
                    ✓ Verified public Bugcrowd profile
                  </div>
                ) : verifiedHandles.bugcrowd?.status || verifyErrors.bugcrowd ? (
                  <div className="text-[11px] text-rose-400 font-mono pt-0.5">
                    ✕ {verifiedHandles.bugcrowd?.error || verifyErrors.bugcrowd || "Profile not found"}
                  </div>
                ) : null}
              </div>

              {/* Twitter / X */}
              <div className="space-y-1.5 sm:col-span-2">
                <label className="block text-slate-400 font-mono">Twitter / X Handle</label>
                <input
                  type="text"
                  value={twitter}
                  onChange={(e) => setTwitter(e.target.value)}
                  placeholder="@handle"
                  className="w-full sm:w-1/2 rounded-xl bg-slate-900 border border-slate-800 px-3 py-2 text-white font-mono focus:border-cyan-500 outline-none text-xs"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-slate-800">
            <button
              type="submit"
              disabled={saving}
              className="rounded-xl bg-cyan-500 px-6 py-2.5 font-mono text-xs font-bold text-slate-950 hover:bg-cyan-400 transition disabled:opacity-50 active:scale-95"
            >
              {saving ? "SAVING..." : "SAVE PROFILE"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
