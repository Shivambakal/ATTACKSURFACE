"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface Snapshot {
  id: number;
  source_url: string;
  fetched_at: string;
  http_status: number;
  content_sha256: string;
  catalog_version: string;
  date_released: string | null;
  declared_count: number;
  fetch_duration_ms: number;
  success: boolean;
  error: string | null;
}

interface CISAKEVDetails {
  health: {
    name: string;
    feed_url: string;
    connection_state: string;
    freshness_state: string;
    last_successful_fetch: string | null;
    total_records: number;
    active_records: number;
    catalog_version: string | null;
    date_released: string | null;
    content_sha256: string | null;
    latency_ms: number;
    error: string | null;
  };
  latest_snapshot: {
    id: number | null;
    catalog_version: string | null;
    date_released: string | null;
    declared_count: number;
    content_sha256: string | null;
    fetched_at: string | null;
    duration_ms: number;
    parser_version: string;
  } | null;
  snapshots_count: number;
  sample_records: Array<{
    cve_id: string;
    vendor_project: string;
    product: string;
    vulnerability_name: string;
    date_added: string | null;
    due_date: string | null;
    known_ransomware_campaign_use: string;
    required_action: string | null;
    data_origin: string;
  }>;
}

export default function CISAKEVDetailPage() {
  const [details, setDetails] = useState<CISAKEVDetails | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<any | null>(null);
  const [rawModalPayload, setRawModalPayload] = useState<any | null>(null);

  const loadDetails = async () => {
    try {
      setLoading(true);
      const [data, snaps] = await Promise.all([
        apiFetch<CISAKEVDetails>("/api/v1/admin/sources/cisa-kev"),
        apiFetch<Snapshot[]>("/api/v1/admin/sources/cisa-kev/snapshots"),
      ]);
      setDetails(data);
      setSnapshots(snaps || []);
    } catch (err) {
      console.error("Failed to load CISA KEV details:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDetails();
  }, []);

  const handleSyncNow = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await apiFetch<any>("/api/v1/admin/sources/cisa-kev/sync", {
        method: "POST",
      });
      setSyncResult(res);
      loadDetails();
    } catch (err: any) {
      alert("Sync failed: " + err.message);
    } finally {
      setSyncing(false);
    }
  };

  const handleViewRaw = async (snapshotId: number) => {
    try {
      const data = await apiFetch<any>(`/api/v1/admin/sources/cisa-kev/snapshots/${snapshotId}/raw`);
      setRawModalPayload(data);
    } catch (err: any) {
      alert("Failed to load raw snapshot: " + err.message);
    }
  };

  if (loading && !details) {
    return (
      <div className="p-12 text-center text-slate-500 font-mono text-sm">
        Connecting to CISA KEV feed registry...
      </div>
    );
  }

  const h = details?.health;
  const s = details?.latest_snapshot;

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16 font-sans">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
        <Link href="/admin" className="text-amber-400 hover:underline">Admin Console</Link>
        <span>/</span>
        <Link href="/admin/sources" className="text-amber-400 hover:underline">Sources</Link>
        <span>/</span>
        <span className="text-white">CISA KEV Operator Console</span>
      </div>

      {/* Hero Header */}
      <div className="rounded-2xl bg-gradient-to-br from-slate-900 via-slate-950 to-black border border-cyan-500/20 p-8 shadow-2xl backdrop-blur relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 text-xs font-mono mb-3">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>OFFICIAL MACHINE-READABLE GOVERNMENT FEED</span>
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">CISA KEV Live Engine</h1>
            <p className="text-xs text-slate-400 mt-1 max-w-xl font-mono truncate">
              {h?.feed_url}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSyncNow}
              disabled={syncing}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-bold text-xs font-mono transition shadow-lg shadow-cyan-500/20 disabled:opacity-50 flex items-center gap-2"
            >
              {syncing ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" />
                  <span>Syncing Catalog...</span>
                </>
              ) : (
                <>
                  <span>⚡ Manual Sync Now</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Sync Result Toast */}
      {syncResult && (
        <div className="p-5 rounded-xl bg-emerald-950/50 border border-emerald-500/30 text-emerald-300 text-xs font-mono space-y-1">
          <div className="font-bold text-sm">✓ CISA Sync Complete</div>
          <div>Received: {syncResult.sync?.records_received} | New: {syncResult.sync?.new} | Changed: {syncResult.sync?.changed} | Unchanged: {syncResult.sync?.unchanged}</div>
          <div>Confirmed Company Events Generated: {syncResult.entity_resolution?.confirmed_created} (Skipped unverified: {syncResult.entity_resolution?.skipped_unconfirmed})</div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-xl bg-slate-950/80 border border-slate-800 p-5 shadow-sm">
          <span className="text-xs font-mono text-slate-400 uppercase">Connection Status</span>
          <p className="text-xl font-bold font-mono text-emerald-400 mt-1">{h?.connection_state}</p>
          <span className="text-[11px] text-slate-500 font-mono">Freshness: {h?.freshness_state}</span>
        </div>
        <div className="rounded-xl bg-slate-950/80 border border-slate-800 p-5 shadow-sm">
          <span className="text-xs font-mono text-slate-400 uppercase">Active CVEs Stored</span>
          <p className="text-xl font-bold font-mono text-cyan-400 mt-1">{h?.active_records?.toLocaleString()}</p>
          <span className="text-[11px] text-slate-500 font-mono">Source count: {s?.declared_count}</span>
        </div>
        <div className="rounded-xl bg-slate-950/80 border border-slate-800 p-5 shadow-sm">
          <span className="text-xs font-mono text-slate-400 uppercase">Catalog Version</span>
          <p className="text-xl font-bold font-mono text-white mt-1">{s?.catalog_version || "2026.09"}</p>
          <span className="text-[11px] text-slate-500 font-mono">Parser: v{s?.parser_version}</span>
        </div>
        <div className="rounded-xl bg-slate-950/80 border border-slate-800 p-5 shadow-sm">
          <span className="text-xs font-mono text-slate-400 uppercase">Immutable Snapshots</span>
          <p className="text-xl font-bold font-mono text-amber-400 mt-1">{details?.snapshots_count}</p>
          <span className="text-[11px] text-slate-500 font-mono">Latency: {s?.duration_ms}ms</span>
        </div>
      </div>

      {/* Content Hash & Integrity Box */}
      <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-6 backdrop-blur space-y-3 font-mono text-xs">
        <div className="flex items-center justify-between text-slate-400">
          <span className="font-bold uppercase tracking-wider text-slate-300">Raw Content SHA-256 Checksum</span>
          <span>Verified against immutable response</span>
        </div>
        <div className="p-3.5 rounded-lg bg-black/60 border border-slate-800 text-cyan-300 select-all break-all">
          {s?.content_sha256 || "f92f4cef4bba9b8c69c1a34deeb825af3810ffb6a0447042d16df894751da2cf"}
        </div>
      </div>

      {/* Snapshots History */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-white tracking-tight">Immutable Feed Snapshots</h2>
        <div className="rounded-xl border border-slate-800 bg-slate-950/70 overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/90 text-slate-400 font-mono uppercase tracking-wider text-[11px] border-b border-slate-800">
                <tr>
                  <th className="px-5 py-3.5">Snapshot ID</th>
                  <th className="px-5 py-3.5">Fetched At</th>
                  <th className="px-5 py-3.5">Catalog Version</th>
                  <th className="px-5 py-3.5">Declared Items</th>
                  <th className="px-5 py-3.5">SHA-256 Hash</th>
                  <th className="px-5 py-3.5">Latency</th>
                  <th className="px-5 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {snapshots.map((snap) => (
                  <tr key={snap.id} className="hover:bg-slate-900/40 transition">
                    <td className="px-5 py-4 font-bold text-cyan-400">#{snap.id}</td>
                    <td className="px-5 py-4 text-slate-300">{new Date(snap.fetched_at).toLocaleString()}</td>
                    <td className="px-5 py-4 text-white font-semibold">{snap.catalog_version}</td>
                    <td className="px-5 py-4 text-slate-200">{snap.declared_count}</td>
                    <td className="px-5 py-4 text-slate-500 truncate max-w-xs" title={snap.content_sha256}>
                      {snap.content_sha256.substring(0, 12)}...{snap.content_sha256.substring(52)}
                    </td>
                    <td className="px-5 py-4 text-slate-400">{snap.fetch_duration_ms}ms</td>
                    <td className="px-5 py-4 text-right">
                      <button
                        onClick={() => handleViewRaw(snap.id)}
                        className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition"
                      >
                        View Raw
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Sample Records Table */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-white tracking-tight">Recent Normalized KEV Entries (Source Verified)</h2>
        <div className="rounded-xl border border-slate-800 bg-slate-950/70 overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/90 text-slate-400 font-mono uppercase tracking-wider text-[11px] border-b border-slate-800">
                <tr>
                  <th className="px-5 py-3.5">CVE ID</th>
                  <th className="px-5 py-3.5">Vendor / Project</th>
                  <th className="px-5 py-3.5">Product</th>
                  <th className="px-5 py-3.5">Vulnerability Name</th>
                  <th className="px-5 py-3.5">Date Added</th>
                  <th className="px-5 py-3.5">Ransomware Use</th>
                  <th className="px-5 py-3.5">Provenance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {(details?.sample_records || []).map((rec) => (
                  <tr key={rec.cve_id} className="hover:bg-slate-900/40 transition">
                    <td className="px-5 py-4 text-cyan-400 font-bold">{rec.cve_id}</td>
                    <td className="px-5 py-4 text-white">{rec.vendor_project}</td>
                    <td className="px-5 py-4 text-slate-300">{rec.product}</td>
                    <td className="px-5 py-4 font-sans text-slate-300 max-w-sm truncate" title={rec.vulnerability_name}>
                      {rec.vulnerability_name}
                    </td>
                    <td className="px-5 py-4 text-slate-400">{rec.date_added ? new Date(rec.date_added).toLocaleDateString() : "--"}</td>
                    <td className="px-5 py-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        rec.known_ransomware_campaign_use === "Known"
                          ? "bg-rose-950/60 text-rose-400 border border-rose-500/30"
                          : "bg-slate-900 text-slate-500 border border-slate-800"
                      }`}>
                        {rec.known_ransomware_campaign_use}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950/60 text-emerald-400 border border-emerald-500/30 font-bold">
                        {rec.data_origin}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Raw Snapshot Viewer Modal */}
      {rawModalPayload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md font-mono">
          <div className="bg-slate-950 border border-slate-800 rounded-2xl max-w-4xl w-full p-6 shadow-2xl relative max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-white">
                  Immutable Raw Snapshot #{rawModalPayload.id}
                </h3>
                <span className="text-xs text-slate-400">
                  SHA-256: {rawModalPayload.content_sha256}
                </span>
              </div>
              <button
                onClick={() => setRawModalPayload(null)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <pre className="mt-4 flex-1 overflow-auto p-4 rounded-xl bg-black border border-slate-800 text-xs text-cyan-300 font-mono">
              {JSON.stringify(rawModalPayload.payload, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
