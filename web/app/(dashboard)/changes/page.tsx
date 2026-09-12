"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Change } from "@/lib/types";
import ModernFilterDropdown, { FilterOption } from "@/components/ModernFilterDropdown";
import { AnimatedNumber } from "@/components/ui/InteractionPrimitives";
import { openThreatAnalyst } from "@/components/CyberAssistantChat";

interface ChangeStats {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  critical_high: number;
  investigating: number;
  resolved: number;
  ignored: number;
  interesting: number;
  unique_targets: number;
  categories: Record<string, number>;
}

export default function ChangesFeedPage() {
  const [changes, setChanges] = useState<Change[]>([]);
  const [stats, setStats] = useState<ChangeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPriority, setSelectedPriority] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "priority" | "relevance">("newest");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Inline Diff Inspector & Copy states
  const [expandedDiffId, setExpandedDiffId] = useState<number | null>(null);
  const [copiedAssetId, setCopiedAssetId] = useState<number | null>(null);

  // Status updating & toasts
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleCopyAsset = (assetText: string, changeId: number) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(assetText);
      setCopiedAssetId(changeId);
      showToast("Copied asset to clipboard");
      setTimeout(() => setCopiedAssetId(null), 2000);
    }
  };

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiFetch<ChangeStats>("/api/v1/changes/stats");
      setStats(data);
    } catch {
      // If stats endpoint fails, compute gracefully from changes
    }
  }, []);

  const fetchChanges = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch up to 50 detected changes for rich research exploration
      const params = new URLSearchParams();
      params.append("limit", "50");
      if (selectedCategory !== "ALL") params.append("category", selectedCategory);
      if (selectedPriority !== "ALL") params.append("priority", selectedPriority);
      if (selectedStatus !== "ALL") params.append("status", selectedStatus);
      if (searchQuery.trim()) params.append("search", searchQuery.trim());

      const data = await apiFetch<Change[]>(`/api/v1/changes?${params.toString()}`);
      setChanges(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load surface changes");
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, selectedPriority, selectedStatus, searchQuery]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchChanges();
      setCurrentPage(1);
    }, 200);
    return () => clearTimeout(timer);
  }, [fetchChanges]);

  // Status updater handler
  const handleUpdateStatus = async (changeId: number, newStatus: string) => {
    setUpdatingId(changeId);
    try {
      await apiFetch(`/api/v1/changes/${changeId}/status`, {
        method: "POST",
        body: JSON.stringify({ status: newStatus }),
      }).catch(async () => {
        await apiFetch(`/api/v1/changes/${changeId}`, {
          method: "PATCH",
          body: JSON.stringify({ status: newStatus }),
        });
      });

      // Update locally
      setChanges((prev) =>
        prev.map((c) => (c.id === changeId ? { ...c, status: newStatus } : c))
      );
      showToast(`Status updated to: ${newStatus.toUpperCase()}`);
      fetchStats();
    } catch {
      // Local optimistic update
      setChanges((prev) =>
        prev.map((c) => (c.id === changeId ? { ...c, status: newStatus } : c))
      );
      showToast(`Status set locally to: ${newStatus.toUpperCase()}`);
    } finally {
      setUpdatingId(null);
    }
  };

  // Filter and Sort changes client-side
  const filteredAndSortedChanges = useMemo(() => {
    let result = [...changes];

    // Priority filter (if not already filtered by backend)
    if (selectedPriority !== "ALL") {
      result = result.filter(
        (c) => (c.priority || "MEDIUM").toUpperCase() === selectedPriority.toUpperCase()
      );
    }

    // Category filter
    if (selectedCategory !== "ALL") {
      result = result.filter((c) => c.category === selectedCategory);
    }

    // Status filter
    if (selectedStatus !== "ALL") {
      result = result.filter((c) => (c.status || "interesting") === selectedStatus);
    }

    // Local Search Query (if any additional client matching needed)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (c) =>
          c.summary?.toLowerCase().includes(q) ||
          c.target_domain?.toLowerCase().includes(q) ||
          c.company_name?.toLowerCase().includes(q) ||
          c.category?.toLowerCase().includes(q) ||
          c.source_url?.toLowerCase().includes(q)
      );
    }

    // Sorting
    const priorityWeight: Record<string, number> = {
      CRITICAL: 5,
      HIGH: 4,
      MEDIUM: 3,
      LOW: 2,
      INFO: 1,
    };

    result.sort((a, b) => {
      if (sortBy === "priority") {
        const wA = priorityWeight[(a.priority || "MEDIUM").toUpperCase()] || 0;
        const wB = priorityWeight[(b.priority || "MEDIUM").toUpperCase()] || 0;
        return wB - wA;
      }
      if (sortBy === "relevance") {
        return (b.security_relevance || 0) - (a.security_relevance || 0);
      }
      if (sortBy === "oldest") {
        return new Date(a.detected_at).getTime() - new Date(b.detected_at).getTime();
      }
      // default: newest
      return new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime();
    });

    return result;
  }, [changes, selectedPriority, selectedCategory, selectedStatus, searchQuery, sortBy]);

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(filteredAndSortedChanges.length / pageSize));
  const paginatedChanges = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredAndSortedChanges.slice(start, start + pageSize);
  }, [filteredAndSortedChanges, currentPage, pageSize]);

  // Export handlers
  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify(filteredAndSortedChanges, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `attack_surface_changes_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Exported changes as JSON");
  };

  const handleExportCSV = () => {
    const headers = [
      "ID",
      "Target Domain",
      "Company Name",
      "Category",
      "Priority",
      "Status",
      "Relevance",
      "Confidence",
      "Detected At",
      "Summary",
      "Source URL",
    ];
    const rows = filteredAndSortedChanges.map((c) => [
      c.id,
      `"${c.target_domain || ""}"`,
      `"${c.company_name || ""}"`,
      `"${c.category || ""}"`,
      `"${c.priority || ""}"`,
      `"${c.status || ""}"`,
      c.security_relevance || 0,
      c.confidence || 0,
      `"${c.detected_at || ""}"`,
      `"${(c.summary || "").replace(/"/g, '""')}"`,
      `"${c.source_url || ""}"`,
    ]);
    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `attack_surface_changes_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Exported changes as CSV");
  };

  const formatRelativeTime = (isoString?: string) => {
    if (!isoString) return "Recently";
    try {
      const now = Date.now();
      const detected = new Date(isoString).getTime();
      const diffSec = Math.floor((now - detected) / 1000);
      if (diffSec < 60) return `${diffSec}s ago`;
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `${diffMin}m ago`;
      const diffHours = Math.floor(diffMin / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      const diffDays = Math.floor(diffHours / 24);
      if (diffDays < 30) return `${diffDays}d ago`;
      return new Date(isoString).toLocaleDateString();
    } catch {
      return "Recently";
    }
  };

  const getPriorityBadgeClass = (priority?: string) => {
    const p = (priority || "MEDIUM").toUpperCase();
    switch (p) {
      case "CRITICAL":
        return "bg-rose-500/15 text-rose-300 border-rose-500/30";
      case "HIGH":
        return "bg-amber-500/15 text-amber-300 border-amber-500/30";
      case "MEDIUM":
        return "bg-yellow-500/15 text-yellow-300 border-yellow-500/30";
      case "LOW":
        return "bg-cyan-500/15 text-cyan-300 border-cyan-500/30";
      default:
        return "bg-slate-700/30 text-slate-300 border-slate-700/50";
    }
  };

  const getStatusBadgeClass = (status?: string) => {
    const s = (status || "interesting").toLowerCase();
    switch (s) {
      case "investigating":
        return "bg-amber-500/15 text-amber-300 border-amber-500/30";
      case "resolved":
        return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
      case "ignored":
        return "bg-slate-700/40 text-slate-400 border-slate-700";
      default:
        return "bg-cyan-500/15 text-cyan-300 border-cyan-500/30";
    }
  };

  // Distinct categories available in current dataset or stats
  const availableCategories = useMemo(() => {
    if (stats?.categories && Object.keys(stats.categories).length > 0) {
      return Object.keys(stats.categories);
    }
    const set = new Set<string>();
    changes.forEach((c) => {
      if (c.category) set.add(c.category);
    });
    return Array.from(set);
  }, [stats, changes]);

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 rounded-xl border border-cyan-700 bg-slate-900 px-4 py-2.5 font-mono text-xs text-cyan-300 shadow-2xl backdrop-blur-md animate-fade-in">
          {toastMessage}
        </div>
      )}

      {/* Header & Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <Link href="/dashboard" className="hover:underline text-slate-400">
              DASHBOARD
            </Link>
            <span>/</span>
            <span>ATTACK SURFACE CHANGES</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
            <span>Attack Surface Changes</span>
            <span className="rounded-full bg-cyan-950/80 border border-cyan-800/60 px-2.5 py-0.5 text-xs font-mono font-medium text-cyan-300">
              {stats?.total ?? (loading ? 37 : changes.length)} Recorded Diffs
            </span>
          </h1>
          <p className="mt-1 text-xs text-slate-400 max-w-3xl">
            Granular differential observations, asset mutations, newly observed endpoints, and
            third-party code references across authorized monitored scopes.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              fetchStats();
              fetchChanges();
              showToast("Refreshing change feed...");
            }}
            className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-1.5 font-mono text-xs text-slate-300 hover:border-slate-700 hover:text-white transition"
            title="Refresh feed"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span>REFRESH</span>
          </button>

          <button
            onClick={handleExportCSV}
            className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-1.5 font-mono text-xs text-slate-300 hover:border-slate-700 hover:text-white transition"
          >
            <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>CSV</span>
          </button>

          <button
            onClick={handleExportJSON}
            className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-1.5 font-mono text-xs text-slate-300 hover:border-slate-700 hover:text-white transition"
          >
            <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            <span>JSON</span>
          </button>
        </div>
      </div>

      {/* Metrics Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="rounded-2xl border border-white/[0.08] bg-[#070b14]/75 p-4 shadow-xl backdrop-blur-xl card-25d">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
              Total Recorded Diffs
            </span>
            <span className="p-1 rounded bg-cyan-500/10 text-cyan-400 text-xs">⚡</span>
          </div>
          <div className="mt-2 text-2xl font-bold text-white font-display">
            <AnimatedNumber value={stats?.total ?? (loading ? 37 : changes.length)} />
          </div>
          <div className="mt-1 text-[11px] text-slate-400 font-mono">
            {availableCategories.length} distinct categories
          </div>
        </div>

        {/* Metric 2 */}
        <div className="rounded-2xl border border-white/[0.08] bg-[#070b14]/75 p-4 shadow-xl backdrop-blur-xl card-25d">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
              Critical &amp; High Priority
            </span>
            <span className="p-1 rounded bg-rose-500/10 text-rose-400 text-xs">🚨</span>
          </div>
          <div className="mt-2 text-2xl font-bold text-rose-400 font-display">
            <AnimatedNumber
              value={
                stats?.critical_high ??
                changes.filter((c) => ["CRITICAL", "HIGH"].includes((c.priority || "").toUpperCase())).length
              }
            />
          </div>
          <div className="mt-1 text-[11px] text-slate-400 font-mono">
            {stats?.critical ?? 0} critical, {stats?.high ?? 0} high
          </div>
        </div>

        {/* Metric 3 */}
        <div className="rounded-2xl border border-white/[0.08] bg-[#070b14]/75 p-4 shadow-xl backdrop-blur-xl card-25d">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
              Active Investigations
            </span>
            <span className="p-1 rounded bg-amber-500/10 text-amber-400 text-xs">🔍</span>
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-300 font-display">
            <AnimatedNumber
              value={stats?.investigating ?? changes.filter((c) => c.status === "investigating").length}
            />
          </div>
          <div className="mt-1 text-[11px] text-slate-400 font-mono">
            {stats?.resolved ?? 0} resolved / closed
          </div>
        </div>

        {/* Metric 4 */}
        <div className="rounded-2xl border border-white/[0.08] bg-[#070b14]/75 p-4 shadow-xl backdrop-blur-xl card-25d">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
              Scopes With Drift
            </span>
            <span className="p-1 rounded bg-emerald-500/10 text-emerald-400 text-xs">🎯</span>
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-400 font-display">
            <AnimatedNumber
              value={stats?.unique_targets ?? new Set(changes.map((c) => c.target_id)).size}
            />
          </div>
          <div className="mt-1 text-[11px] text-slate-400 font-mono">
            across monitored targets
          </div>
        </div>
      </div>

      {/* Filter and Control Bar */}
      <div className="rounded-2xl border border-white/[0.08] bg-[#070b14]/75 p-4 space-y-4 shadow-xl backdrop-blur-xl">
        {/* Row 1: Search & Sort */}
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <svg
              className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search changes by domain, company, summary, URL, or category..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950/80 pl-10 pr-8 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 font-mono"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white text-xs"
              >
                ✕
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
            <ModernFilterDropdown
              label="Category"
              value={selectedCategory}
              onChange={setSelectedCategory}
              align="right"
              options={[
                { value: "ALL", label: `All Categories (${availableCategories.length})` },
                ...availableCategories.map((cat) => ({
                  value: cat,
                  label: cat.replace(/_/g, " ").toUpperCase(),
                  badge: stats?.categories?.[cat] ? String(stats.categories[cat]) : undefined,
                })),
              ]}
            />

            <ModernFilterDropdown
              label="Sort"
              value={sortBy}
              onChange={(val) => setSortBy(val as any)}
              align="right"
              options={[
                { value: "newest", label: "Newest First" },
                { value: "oldest", label: "Oldest First" },
                { value: "priority", label: "Highest Priority" },
                { value: "relevance", label: "Highest Relevance" },
              ]}
            />
          </div>
        </div>

        {/* Row 2: Modern Filter Dropdowns for Priority & Status */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800/60 text-xs">
          <div className="flex flex-wrap items-center gap-2.5">
            <ModernFilterDropdown
              label="Priority"
              value={selectedPriority}
              onChange={setSelectedPriority}
              options={[
                { value: "ALL", label: "All Priorities" },
                { value: "CRITICAL", label: "Critical Priority", color: "rose" },
                { value: "HIGH", label: "High Priority", color: "amber" },
                { value: "MEDIUM", label: "Medium Priority", color: "cyan" },
                { value: "LOW", label: "Low Priority", color: "emerald" },
                { value: "INFO", label: "Informational", color: "purple" },
              ]}
            />

            <ModernFilterDropdown
              label="Status"
              value={selectedStatus}
              onChange={setSelectedStatus}
              options={[
                { value: "ALL", label: "All Workflow States" },
                { value: "interesting", label: "Interesting", color: "purple" },
                { value: "investigating", label: "Under Investigation", color: "amber" },
                { value: "resolved", label: "Resolved / Mitigated", color: "emerald" },
                { value: "ignored", label: "Ignored / False Positive", color: "cyan" },
              ]}
            />
          </div>

          <div className="text-[11px] font-mono text-slate-400">
            <span>Showing <strong className="text-white">{filteredAndSortedChanges.length}</strong> changes</span>
          </div>
        </div>
      </div>

      {/* Feed Information / Counter */}
      <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-1">
        <div>
          Showing <span className="text-white font-semibold">{paginatedChanges.length}</span> of{" "}
          <span className="text-white font-semibold">{filteredAndSortedChanges.length}</span> filtered diffs
          {stats?.total && (
            <span className="text-slate-400"> (total {stats.total} in registry)</span>
          )}
        </div>

        {(searchQuery ||
          selectedPriority !== "ALL" ||
          selectedCategory !== "ALL" ||
          selectedStatus !== "ALL") && (
          <button
            onClick={() => {
              setSearchQuery("");
              setSelectedPriority("ALL");
              setSelectedCategory("ALL");
              setSelectedStatus("ALL");
            }}
            className="text-cyan-400 hover:underline flex items-center gap-1"
          >
            <span>Reset filters</span>
            <span className="text-slate-400">✕</span>
          </button>
        )}
      </div>

      {/* Loading Skeleton */}
      {loading && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-5 animate-pulse"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="h-4 w-28 bg-slate-800 rounded" />
                  <div className="h-4 w-16 bg-slate-800 rounded" />
                </div>
                <div className="h-4 w-24 bg-slate-800 rounded" />
              </div>
              <div className="h-5 w-3/4 bg-slate-800 rounded mb-2" />
              <div className="h-3 w-1/2 bg-slate-800/60 rounded" />
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="rounded-xl border border-rose-800/60 bg-rose-950/30 p-6 text-center text-rose-300">
          <h3 className="font-semibold text-rose-200">Unable to load changes</h3>
          <p className="mt-1 text-xs">{error}</p>
          <button
            onClick={() => fetchChanges()}
            className="mt-3 inline-block rounded-lg bg-slate-800 px-4 py-2 font-mono text-xs text-slate-200 hover:bg-slate-700"
          >
            RETRY
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredAndSortedChanges.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 p-12 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-800 text-xl text-slate-400">
            ⚡
          </div>
          <h3 className="mt-4 font-semibold text-slate-200">No matching surface changes</h3>
          <p className="mt-1 text-xs text-slate-400 max-w-sm mx-auto">
            No changes matched your current filter criteria. Try adjusting your search query, priority,
            category, or status.
          </p>
          <button
            onClick={() => {
              setSearchQuery("");
              setSelectedPriority("ALL");
              setSelectedCategory("ALL");
              setSelectedStatus("ALL");
            }}
            className="mt-4 rounded-lg bg-cyan-500/10 border border-cyan-500/30 px-4 py-1.5 font-mono text-xs text-cyan-300 hover:bg-cyan-500/20 transition"
          >
            Clear All Filters
          </button>
        </div>
      )}

      {/* Changes List / Cards */}
      {!loading && !error && paginatedChanges.length > 0 && (
        <div className="space-y-3">
          {paginatedChanges.map((change) => {
            const priorityBadge = getPriorityBadgeClass(change.priority);
            const statusBadge = getStatusBadgeClass(change.status);
            const isUpdating = updatingId === change.id;

            return (
              <div
                key={change.id}
                className="group rounded-xl border border-slate-800/80 bg-slate-900/60 p-5 hover:border-slate-700 hover:bg-slate-900/90 transition shadow-sm"
              >
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Category */}
                    <span className="rounded bg-slate-950 px-2 py-0.5 font-mono text-[11px] font-bold uppercase text-cyan-400 border border-cyan-900/60">
                      {change.category?.replace(/_/g, " ") || "SURFACE CHANGE"}
                    </span>

                    {/* Priority */}
                    <span
                      className={`rounded px-2 py-0.5 font-mono text-[11px] font-bold border ${priorityBadge}`}
                    >
                      {change.priority || "MEDIUM"}
                    </span>

                    {/* Status Pill */}
                    <span
                      className={`rounded px-2 py-0.5 font-mono text-[11px] uppercase border ${statusBadge}`}
                    >
                      {change.status || "interesting"}
                    </span>

                    {/* Semantic Quality Badge */}
                    <span
                      className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold border ${
                        (change.confidence || 0) >= 0.85
                          ? "bg-cyan-950/60 text-cyan-300 border-cyan-800/60"
                          : (change.confidence || 0) >= 0.6
                          ? "bg-purple-950/60 text-purple-300 border-purple-800/60"
                          : "bg-slate-800/60 text-slate-400 border-slate-700/60"
                      }`}
                    >
                      {(change.confidence || 0) >= 0.85
                        ? "VERIFIED DRIFT"
                        : (change.confidence || 0) >= 0.6
                        ? "CORRELATED"
                        : "CANDIDATE"}
                    </span>

                    {/* Target Domain Link */}
                    {change.target_domain && (
                      <div className="flex items-center gap-1.5">
                        <Link
                          href={change.target_id ? `/targets/${change.target_id}` : "#"}
                          className="font-mono text-xs text-slate-300 hover:text-cyan-300 transition flex items-center gap-1 font-semibold"
                          title="View target details"
                        >
                          <span className="text-slate-600">•</span>
                          <span>{change.target_domain}</span>
                        </Link>
                        <button
                          type="button"
                          onClick={() => handleCopyAsset(change.target_domain!, change.id)}
                          className="text-[10px] text-slate-400 hover:text-cyan-300 p-0.5 rounded"
                          title="Copy target domain"
                        >
                          {copiedAssetId === change.id ? "✓" : "📋"}
                        </button>
                      </div>
                    )}

                    {/* Company Name */}
                    {change.company_name && (
                      <span className="rounded bg-slate-800/60 px-2 py-0.5 text-[11px] font-medium text-slate-300 border border-slate-700/60">
                        {change.company_name}
                      </span>
                    )}
                  </div>

                  {/* Relative Timestamp */}
                  <div className="font-mono text-[11px] text-slate-400 shrink-0">
                    {formatRelativeTime(change.detected_at)}
                  </div>
                </div>

                {/* Change Summary */}
                <div className="text-sm font-medium text-slate-100 leading-relaxed">
                  {change.summary}
                </div>

                {/* Source URL if available */}
                {change.source_url && (
                  <div className="mt-2 flex items-center gap-1 text-xs font-mono text-slate-400 truncate">
                    <span className="text-slate-400">Source:</span>
                    <a
                      href={change.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400/90 hover:underline truncate hover:text-cyan-300"
                    >
                      {change.source_url}
                    </a>
                  </div>
                )}

                {/* Inline Forensic Diff Preview Section */}
                {expandedDiffId === change.id && (
                  <div className="mt-4 rounded-xl border border-cyan-500/30 bg-black/60 p-4 font-mono text-xs space-y-3 animate-surface-in">
                    <div className="flex items-center justify-between border-b border-white/[0.08] pb-2 text-[11px] text-cyan-400 font-bold">
                      <div className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#22d3ee]" />
                        <span>FORENSIC DIFFERENTIAL SNAPSHOT</span>
                      </div>
                      <span className="text-slate-400 font-normal">Change ID #{change.id}</span>
                    </div>

                    {/* Diff content view */}
                    {change.diff_content ? (
                      <div className="max-h-60 overflow-y-auto rounded-lg bg-black/80 p-3 border border-white/[0.06] text-[11px] leading-relaxed">
                        {change.diff_content.split("\n").map((line, idx) => (
                          <div
                            key={idx}
                            className={
                              line.startsWith("+")
                                ? "text-emerald-400 bg-emerald-950/30"
                                : line.startsWith("-")
                                ? "text-rose-400 bg-rose-950/30"
                                : line.startsWith("@@")
                                ? "text-cyan-400 font-bold"
                                : "text-slate-300"
                            }
                          >
                            {line}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
                        <div className="rounded-lg bg-black/40 border border-white/[0.06] p-2.5">
                          <div className="text-slate-400 font-bold mb-1 text-[10px] uppercase">
                            Prior State Baseline
                          </div>
                          <div className="text-slate-300 break-all whitespace-pre-wrap max-h-36 overflow-y-auto">
                            {typeof change.before_state === "object"
                              ? JSON.stringify(change.before_state, null, 2)
                              : change.before_state || "No prior state recorded"}
                          </div>
                        </div>
                        <div className="rounded-lg bg-black/40 border border-white/[0.06] p-2.5">
                          <div className="text-emerald-400 font-bold mb-1 text-[10px] uppercase">
                            Observed Delta State
                          </div>
                          <div className="text-emerald-300 break-all whitespace-pre-wrap max-h-36 overflow-y-auto">
                            {typeof change.current_state === "object"
                              ? JSON.stringify(change.current_state, null, 2)
                              : change.current_state || change.summary}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Affected Assets tags */}
                    {change.affected_assets && change.affected_assets.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-white/[0.06]">
                        <span className="text-[10px] text-slate-400 uppercase">Affected Assets:</span>
                        {change.affected_assets.map((asset, i) => (
                          <span
                            key={i}
                            className="rounded bg-white/[0.05] border border-white/[0.08] px-2 py-0.5 text-[10px] text-cyan-300"
                          >
                            {asset}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Meta Details & Action Row */}
                <div className="mt-4 pt-3 border-t border-slate-800/60 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs">
                  {/* Confidence & Relevance Meters */}
                  <div className="flex items-center gap-4 text-[11px] font-mono text-slate-400">
                    <div className="flex items-center gap-1.5">
                      <span>Relevance:</span>
                      <span className="text-slate-200 font-semibold">
                        {change.security_relevance || 0}/100
                      </span>
                      <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden ml-1">
                        <div
                          className="h-full bg-cyan-400 rounded-full"
                          style={{ width: `${Math.min(100, change.security_relevance || 0)}%` }}
                        />
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span>Confidence:</span>
                      <span className="text-slate-200 font-semibold">
                        {Math.round((change.confidence || 0) * 100)}%
                      </span>
                    </div>
                  </div>

                  {/* Right Actions: AI Analyst, Inline Diff Toggle, Status, Full Diff Link */}
                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    {/* One-Click AI Threat Analyst */}
                    <button
                      type="button"
                      onClick={() =>
                        openThreatAnalyst(
                          `Perform threat triage on attack surface change #${change.id} on ${
                            change.target_domain || change.company_name || "monitored perimeter"
                          }: "${change.summary}". Category: ${change.category}. Security relevance: ${
                            change.security_relevance
                          }/100. Identify potential attack vectors, affected assets, and actionable validation steps.`,
                          `Diff #${change.id} · ${change.target_domain || "Perimeter"}`
                        )
                      }
                      className="rounded-lg bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 px-2.5 py-1.5 font-mono text-xs font-semibold text-purple-300 transition flex items-center gap-1.5 active:scale-95 shadow-sm"
                      title="Investigate this change with AI Threat Analyst"
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-purple-400 shadow-[0_0_6px_#c084fc]" />
                      <span>AI ANALYST</span>
                    </button>

                    {/* Inline Diff Preview Toggle */}
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedDiffId(expandedDiffId === change.id ? null : change.id)
                      }
                      className={`rounded-lg px-2.5 py-1.5 font-mono text-xs font-semibold transition border ${
                        expandedDiffId === change.id
                          ? "bg-cyan-500 text-slate-950 border-cyan-400"
                          : "bg-white/[0.05] text-slate-300 border-white/[0.08] hover:bg-white/[0.1] hover:text-white"
                      }`}
                    >
                      {expandedDiffId === change.id ? "HIDE DIFF" : "PREVIEW DIFF"}
                    </button>

                    {/* In-place Status Select */}
                    <div className="flex items-center gap-1 font-mono text-[11px]">
                      <select
                        disabled={isUpdating}
                        value={change.status || "interesting"}
                        onChange={(e) => handleUpdateStatus(change.id, e.target.value)}
                        className="rounded border border-slate-800 bg-slate-950 px-2 py-1 text-[11px] font-mono text-slate-300 focus:border-cyan-500 focus:outline-none disabled:opacity-50"
                      >
                        <option value="interesting">INTERESTING</option>
                        <option value="investigating">INVESTIGATING</option>
                        <option value="resolved">RESOLVED</option>
                        <option value="ignored">IGNORED</option>
                      </select>
                    </div>

                    {/* Forensic Diff Button */}
                    <Link
                      href={`/changes/${change.id}`}
                      className="rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 px-3 py-1.5 font-mono text-xs font-semibold text-cyan-300 transition flex items-center gap-1"
                    >
                      <span>FORENSIC DETAIL</span>
                      <span>&rarr;</span>
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Footer */}
      {!loading && !error && filteredAndSortedChanges.length > pageSize && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-800/80 font-mono text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span>Rows per page:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="rounded border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-300 focus:outline-none"
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="rounded border border-slate-800 bg-slate-900 px-3 py-1.5 text-slate-300 hover:border-slate-700 disabled:opacity-40 disabled:hover:border-slate-800"
            >
              &larr; Previous
            </button>
            <span>
              Page {currentPage} of {totalPages}
            </span>
            <button
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              className="rounded border border-slate-800 bg-slate-900 px-3 py-1.5 text-slate-300 hover:border-slate-700 disabled:opacity-40 disabled:hover:border-slate-800"
            >
              Next &rarr;
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
