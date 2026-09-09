"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Target } from "@/lib/types";

export default function TargetsPage() {
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  // Add Target modal state
  const [showModal, setShowModal] = useState(false);
  const [companyName, setCompanyName] = useState("");
  const [domain, setDomain] = useState("");
  const [programSource, setProgramSource] = useState("Bugcrowd");
  const [authorizationSource, setAuthorizationSource] = useState("");
  const [scope, setScope] = useState("");
  const [scopeType, setScopeType] = useState("DOMAIN");
  const [notes, setNotes] = useState("");
  const [authorized, setAuthorized] = useState(false);
  const [creating, setCreating] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [bulkImporting, setBulkImporting] = useState(false);

  // Snapshot state
  const [snapshotLoadingId, setSnapshotLoadingId] = useState<number | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const fetchTargets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<Target[]>("/api/v1/targets");
      setTargets(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load targets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTargets();
  }, [fetchTargets]);

  const handleAddTarget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authorized) {
      setModalError("Authorization acknowledgement is required.");
      return;
    }
    if (!companyName.trim()) {
      setModalError("Company name is required.");
      return;
    }
    if (!authorizationSource.trim()) {
      setModalError("Authorization source is required (e.g. Bug Bounty Policy URL, Security.txt).");
      return;
    }

    setCreating(true);
    setModalError(null);

    try {
      const scopeList = scope
        .split(/[\n,]+/)
        .map((s) => s.trim())
        .filter(Boolean);

      const created = await apiFetch<Target>("/api/v1/targets", {
        method: "POST",
        body: JSON.stringify({
          domain: domain.trim().toLowerCase(),
          company_name: companyName.trim(),
          program_source: programSource.trim(),
          authorization_source: authorizationSource.trim(),
          scope: scopeList.length > 0 ? scopeList : [domain.trim().toLowerCase()],
          scope_type: scopeType,
          notes: notes.trim() || undefined,
          authorization_confirmed: authorized,
        }),
      });
      setTargets((prev) => [created, ...prev.filter((t) => t.id !== created.id)]);
      setShowModal(false);
      setCompanyName("");
      setDomain("");
      setProgramSource("Bugcrowd");
      setAuthorizationSource("");
      setScope("");
      setScopeType("DOMAIN");
      setNotes("");
      setAuthorized(false);
      setActionNotice(`Target ${created.domain} enrolled with verified authorization. You can now take a snapshot.`);
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to create target");
    } finally {
      setCreating(false);
    }
  };

  const handleBulkImport = async () => {
    setBulkImporting(true);
    setActionNotice("Importing 50 verified bug-bounty targets from authorized registry...");
    try {
      const res = await apiFetch<{
        message: string;
        imported_count: number;
        existing_count: number;
        total_targets: number;
      }>("/api/v1/targets/bulk-import", {
        method: "POST",
      });
      setActionNotice(
        `Bulk import complete: ${res.imported_count} new targets imported, ${res.existing_count} already existed (${res.total_targets} total registered).`
      );
      await fetchTargets();
    } catch (err: unknown) {
      setActionNotice(`Bulk import failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setBulkImporting(false);
    }
  };

  const handleTakeSnapshot = async (targetId: number, domainName: string) => {
    setSnapshotLoadingId(targetId);
    setActionNotice(`Initiating permitted public collection for ${domainName}...`);
    try {
      const res = await apiFetch<{ status: string }>(`/api/v1/targets/${targetId}/snapshots`, {
        method: "POST",
      });
      setActionNotice(`Snapshot ${res.status || "completed"} for ${domainName}.`);
      fetchTargets();
    } catch (err: unknown) {
      setActionNotice(`Collection failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setSnapshotLoadingId(null);
    }
  };

  const filteredTargets = targets.filter((target) => {
    const matchesSearch =
      target.domain.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (target.company_name && target.company_name.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesStatus =
      statusFilter === "ALL" ||
      target.monitoring_status?.toUpperCase() === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Monitored Target Domains</h2>
          <p className="text-xs text-slate-400">
            Registered authorized assets under continuous differential attack-surface tracking.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 transition hover:bg-cyan-400"
          >
            <span className="text-base leading-none">+</span>
            <span>ADD NEW TARGET</span>
          </button>
        </div>
      </div>

      {actionNotice && (
        <div className="flex items-center justify-between rounded-lg border border-cyan-800 bg-cyan-950/60 p-3 text-xs text-cyan-200">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-cyan-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/40 p-4 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-3">
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Filter by domain name (e.g. app.corp.com)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 font-mono text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-500"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              className="absolute right-2.5 top-2.5 text-xs text-slate-400 hover:text-white"
            >
              ✕
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-slate-400">STATUS:</span>
          {["ALL", "ACTIVE", "PAUSED"].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`rounded px-2.5 py-1 font-mono text-[10px] font-semibold transition ${
                statusFilter === status
                  ? "bg-cyan-500 text-slate-950"
                  : "bg-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Target Table */}
      <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/40 shadow">
        {loading ? (
          <div className="py-16 text-center font-mono text-xs text-slate-400">
            RETRIEVING TARGET REGISTRY...
          </div>
        ) : filteredTargets.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-sm text-slate-400">No targets found matching criteria.</p>
            <p className="mt-1 text-xs text-slate-500">
              {searchTerm ? "Try adjusting your search filter." : "Click Add Target to register your first domain."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-sans">
              <thead className="border-b border-slate-800 bg-slate-950/60 font-mono text-[11px] text-slate-400">
                <tr>
                  <th className="px-5 py-3">DOMAIN / ASSET</th>
                  <th className="px-4 py-3">COMPANY &amp; PROGRAM</th>
                  <th className="px-4 py-3">AUTHORIZATION SOURCE</th>
                  <th className="px-4 py-3">STATUS</th>
                  <th className="px-4 py-3">ENROLLED</th>
                  <th className="px-4 py-3 text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs">
                {filteredTargets.map((target) => (
                  <tr
                    key={target.id}
                    className="group hover:bg-slate-800/40 transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <Link
                        href={`/targets/${target.id}`}
                        className="font-mono font-semibold text-slate-100 group-hover:text-cyan-400 transition"
                      >
                        {target.domain}
                      </Link>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] font-mono text-slate-500">
                          ID: #{target.id}
                        </span>
                        {target.scope_type && (
                          <span className="rounded bg-slate-800 px-1.5 py-0.2 font-mono text-[9px] text-cyan-400 border border-slate-700">
                            {target.scope_type}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="px-4 py-3.5">
                      <span className="font-medium text-slate-200 block">
                        {target.company_name || "Independent"}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {target.program_source || "Public Scope"}
                      </span>
                    </td>

                    <td className="px-4 py-3.5">
                      <div className="max-w-[180px] truncate text-[11px] text-slate-300 font-mono" title={target.authorization_source || undefined}>
                        {target.authorization_source || "Bug Bounty Policy"}
                      </div>
                      <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-mono">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                        RECORD PROVEN
                      </span>
                    </td>

                    <td className="px-4 py-3.5">
                      <span className="font-mono text-[11px] uppercase text-slate-300">
                        {target.monitoring_status || "ACTIVE"}
                      </span>
                    </td>

                    <td className="px-4 py-3.5 font-mono text-slate-400 text-[11px]">
                      {new Date(target.created_at).toLocaleDateString()}
                    </td>

                    <td className="px-4 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleTakeSnapshot(target.id, target.domain)}
                          disabled={snapshotLoadingId === target.id}
                          className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 font-mono text-[11px] text-slate-300 hover:border-cyan-500 hover:text-cyan-300 disabled:opacity-40"
                        >
                          {snapshotLoadingId === target.id ? "COLLECTING..." : "TAKE SNAPSHOT"}
                        </button>
                        <Link
                          href={`/targets/${target.id}`}
                          className="rounded bg-cyan-500/10 border border-cyan-500/30 px-2.5 py-1 font-mono text-[11px] font-semibold text-cyan-300 hover:bg-cyan-500 hover:text-slate-950 transition"
                        >
                          VIEW OVERVIEW →
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Target Modal Dialog */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl my-8">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="font-semibold text-white">Add Authorized Research Target</h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Internal authorization record will be created to verify permitted continuous monitoring.
                </p>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {modalError && (
              <div className="mt-3 rounded border border-red-800 bg-red-950/40 p-2.5 text-xs text-red-300">
                {modalError}
              </div>
            )}

            <form onSubmit={handleAddTarget} className="mt-4 space-y-4 text-left">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300">
                    Company / Organization <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    autoFocus
                    placeholder="e.g. GitHub / Microsoft"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300">
                    Primary Target Domain <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. api.github.com"
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300">
                    Program / Source
                  </label>
                  <select
                    value={programSource}
                    onChange={(e) => setProgramSource(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 outline-none focus:border-cyan-500"
                  >
                    <option value="Bugcrowd">Bugcrowd</option>
                    <option value="HackerOne">HackerOne</option>
                    <option value="Intigriti">Intigriti</option>
                    <option value="Direct Disclosure">Direct Disclosure</option>
                    <option value="Security.txt">Security.txt Policy</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300">
                    Scope Type
                  </label>
                  <select
                    value={scopeType}
                    onChange={(e) => setScopeType(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 outline-none focus:border-cyan-500"
                  >
                    <option value="DOMAIN">DOMAIN (Single Host)</option>
                    <option value="WILDCARD">WILDCARD (*.domain)</option>
                    <option value="URL">URL (Specific Web App)</option>
                    <option value="CIDR">CIDR (IP Range)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300">
                  Authorization Source / Policy URL <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. https://bugcrowd.com/engagements/target or security.txt memo"
                  value={authorizationSource}
                  onChange={(e) => setAuthorizationSource(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300">
                  Authorized Scope Rules (comma or newline separated)
                </label>
                <textarea
                  rows={2}
                  placeholder="*.github.com, api.github.com, *.githubusercontent.com"
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300">
                  Operator Notes / Scope Constraints (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. In-scope tier 1 assets; exclude out-of-scope third-party CDNs"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-500"
                />
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3.5 space-y-2">
                <label className="flex items-start gap-2.5 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={authorized}
                    onChange={(e) => setAuthorized(e.target.checked)}
                    className="mt-0.5 rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-cyan-400"
                  />
                  <span className="leading-snug">
                    I confirm this target is authorized under an active bug bounty scope or authorized disclosure policy. An immutable authorization audit record will be logged.
                  </span>
                </label>
                <p className="text-[10px] text-slate-500 font-mono pl-6">
                  Passive GET-only collection policy. Rate-limited, robots.txt strictly respected.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !domain.trim() || !companyName.trim() || !authorizationSource.trim() || !authorized}
                  className="rounded-lg bg-cyan-500 px-4 py-2 font-mono text-xs font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-40"
                >
                  {creating ? "AUTHORIZING..." : "CREATE TARGET & LOG AUTHORIZATION →"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
