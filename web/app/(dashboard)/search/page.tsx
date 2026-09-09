"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { SearchResults, Target, Note, Finding } from "@/lib/types";

export default function GlobalSearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResults>({});
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  // Fallback cache
  const [allTargets, setAllTargets] = useState<Target[]>([]);
  const [allNotes, setAllNotes] = useState<Note[]>([]);
  const [allFindings, setAllFindings] = useState<Finding[]>([]);

  useEffect(() => {
    Promise.allSettled([
      apiFetch<Target[]>("/api/v1/targets"),
      apiFetch<Note[]>("/api/v1/research/notes"),
      apiFetch<Finding[]>("/api/v1/research/findings"),
    ]).then(([t, n, f]) => {
      if (t.status === "fulfilled" && Array.isArray(t.value)) setAllTargets(t.value);
      if (n.status === "fulfilled" && Array.isArray(n.value)) setAllNotes(n.value);
      if (f.status === "fulfilled" && Array.isArray(f.value)) setAllFindings(f.value);
    });
  }, []);

  const performSearch = useCallback(
    async (q: string) => {
      const cleanQ = q.trim().toLowerCase();
      if (!cleanQ) {
        setResults({});
        setSearched(false);
        return;
      }

      setLoading(true);
      setSearched(true);

      try {
        // Try unified API search endpoint
        const serverResults = await apiFetch<SearchResults>(
          `/api/v1/search?q=${encodeURIComponent(cleanQ)}`
        ).catch(() => null);

        if (serverResults && Object.keys(serverResults).length > 0) {
          setResults(serverResults);
        } else {
          // Perform comprehensive client-side indexing fallback
          const matchedTargets = allTargets
            .filter((t) => t.domain.toLowerCase().includes(cleanQ))
            .map((t) => ({
              id: t.id,
              type: "target" as const,
              title: t.domain,
              subtitle: `Monitoring: ${t.monitoring_status || "active"}`,
              url: `/targets/${t.id}`,
              badge: "TARGET",
              date: t.created_at,
            }));

          const matchedNotes = allNotes
            .filter(
              (n) =>
                n.title.toLowerCase().includes(cleanQ) ||
                (n.body && n.body.toLowerCase().includes(cleanQ)) ||
                (n.tags && n.tags.some((tag) => tag.toLowerCase().includes(cleanQ)))
            )
            .map((n) => ({
              id: n.id,
              type: "note" as const,
              title: n.title,
              subtitle: n.body?.slice(0, 100),
              url: `/research/notes`,
              badge: "NOTE",
              date: n.created_at,
            }));

          const matchedFindings = allFindings
            .filter(
              (f) =>
                f.title.toLowerCase().includes(cleanQ) ||
                (f.description && f.description.toLowerCase().includes(cleanQ)) ||
                (f.severity && f.severity.toLowerCase().includes(cleanQ))
            )
            .map((f) => ({
              id: f.id,
              type: "finding" as const,
              title: f.title,
              subtitle: f.description?.slice(0, 100),
              url: `/research/findings`,
              badge: f.severity || "FINDING",
              date: f.created_at,
            }));

          setResults({
            targets: matchedTargets,
            notes: matchedNotes,
            findings: matchedFindings,
            changes: [],
            assets: [],
            features: [],
          });
        }
      } catch {
        setResults({});
      } finally {
        setLoading(false);
      }
    },
    [allTargets, allNotes, allFindings]
  );

  // Debounced search
  useEffect(() => {
    const handler = setTimeout(() => {
      performSearch(query);
    }, 300);
    return () => clearTimeout(handler);
  }, [query, performSearch]);

  const totalResultsCount =
    (results.targets?.length || 0) +
    (results.changes?.length || 0) +
    (results.assets?.length || 0) +
    (results.features?.length || 0) +
    (results.notes?.length || 0) +
    (results.findings?.length || 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs uppercase tracking-wider text-cyan-400">
            DISCOVERY ENGINE
          </span>
        </div>
        <h2 className="mt-1 text-2xl font-bold tracking-tight text-white">
          Global Intelligence Search
        </h2>
        <p className="text-xs text-slate-400">
          Query targets, surface diffs, forensic evidence, notes, and findings.
        </p>
      </div>

      {/* Large Command Search Input */}
      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-cyan-400">
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          type="text"
          autoFocus
          placeholder="Search by domain, CVE, parameter, header, observation tag (Ctrl+K)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full rounded-2xl border border-slate-800 bg-slate-900/90 py-4 pl-12 pr-12 font-mono text-sm text-slate-100 placeholder-slate-500 shadow-xl outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
        />
        {query && (
          <button
            onClick={() => setQuery("")}
            className="absolute inset-y-0 right-0 flex items-center pr-4 text-slate-400 hover:text-white"
          >
            ✕
          </button>
        )}
      </div>

      {/* Search Status */}
      {searched && (
        <div className="flex items-center justify-between font-mono text-xs text-slate-400 px-1">
          <span>
            {loading
              ? "Scanning database..."
              : `Found ${totalResultsCount} results matching "${query}"`}
          </span>
        </div>
      )}

      {/* Categorized Results */}
      {loading ? (
        <div className="py-20 text-center font-mono text-xs text-cyan-400">
          QUERYING SECURITY GRAPH...
        </div>
      ) : searched && totalResultsCount === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 p-16 text-center text-xs text-slate-500 font-mono">
          NO MATCHING INTELLIGENCE RECORDS FOUND
        </div>
      ) : (
        <div className="space-y-6">
          {/* Targets */}
          {results.targets && results.targets.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
              <h3 className="font-mono text-xs font-bold uppercase text-cyan-400">
                TARGETS ({results.targets.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {results.targets.map((item) => (
                  <Link
                    key={item.id}
                    href={item.url}
                    className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/70 p-3 hover:border-cyan-500/50 transition"
                  >
                    <div>
                      <span className="font-mono text-xs font-semibold text-slate-100">
                        {item.title}
                      </span>
                      {item.subtitle && (
                        <p className="text-[11px] text-slate-400 mt-0.5">{item.subtitle}</p>
                      )}
                    </div>
                    <span className="font-mono text-[10px] text-slate-500">→</span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Surface Changes */}
          {results.changes && results.changes.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
              <h3 className="font-mono text-xs font-bold uppercase text-cyan-400">
                SURFACE CHANGES ({results.changes.length})
              </h3>
              <div className="space-y-2">
                {results.changes.map((item) => (
                  <Link
                    key={item.id}
                    href={item.url}
                    className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/70 p-3 hover:border-cyan-500/50 transition"
                  >
                    <div>
                      <span className="text-xs font-medium text-slate-100">{item.title}</span>
                      {item.subtitle && (
                        <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                          {item.subtitle}
                        </p>
                      )}
                    </div>
                    <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-amber-300">
                      {item.badge || "DIFF"}
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Research Notes */}
          {results.notes && results.notes.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
              <h3 className="font-mono text-xs font-bold uppercase text-cyan-400">
                RESEARCH NOTES ({results.notes.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {results.notes.map((item) => (
                  <Link
                    key={item.id}
                    href={item.url}
                    className="rounded-lg border border-slate-800 bg-slate-950/70 p-3 hover:border-cyan-500/50 transition block"
                  >
                    <span className="text-xs font-semibold text-slate-100">{item.title}</span>
                    {item.subtitle && (
                      <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                        {item.subtitle}
                      </p>
                    )}
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Findings */}
          {results.findings && results.findings.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
              <h3 className="font-mono text-xs font-bold uppercase text-red-400">
                FINDINGS ({results.findings.length})
              </h3>
              <div className="space-y-2">
                {results.findings.map((item) => (
                  <Link
                    key={item.id}
                    href={item.url}
                    className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/70 p-3 hover:border-red-500/50 transition"
                  >
                    <div>
                      <span className="text-xs font-semibold text-slate-100">{item.title}</span>
                      {item.subtitle && (
                        <p className="text-[11px] text-slate-400 mt-0.5">{item.subtitle}</p>
                      )}
                    </div>
                    <span className="rounded bg-red-950 px-2 py-0.5 font-mono text-[10px] text-red-300 border border-red-800">
                      {item.badge}
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
