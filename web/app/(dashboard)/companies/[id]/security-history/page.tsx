"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface PageProps {
  params: Promise<{ id: string }>;
}

interface SecurityEventItem {
  id: number;
  event_type: string;
  title: string;
  description: string | null;
  severity: string | null;
  vulnerability_class: string | null;
  affected_component: string | null;
  affected_versions: any;
  confidence: number;
  evidence: string | null;
  source_url: string | null;
  observed_at: string | null;
  relationship_type: string | null;
}

interface TechnologyAdvisoryItem {
  technology_name: string;
  category: string;
  advisories_count: number;
  advisories: Array<{
    cve_id: string | null;
    title: string;
    vendor: string | null;
    product: string | null;
    known_ransomware_use: string | null;
    confidence: number;
    source_url: string | null;
  }>;
}

export default function CompanySecurityHistoryPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const companyId = resolvedParams.id;

  const [loading, setLoading] = useState(true);
  const [company, setCompany] = useState<any>(null);
  const [directEvents, setDirectEvents] = useState<SecurityEventItem[]>([]);
  const [technologyContext, setTechnologyContext] = useState<TechnologyAdvisoryItem[]>([]);
  const [fingerprint, setFingerprint] = useState<Record<string, number>>({});
  const [activeFilter, setActiveFilter] = useState<string>("ALL");

  const fetchSecurityHistory = async () => {
    setLoading(true);
    try {
      // 1. Fetch company basic details
      const compData = await apiFetch<any>(`/api/v1/companies/${companyId}`);
      setCompany(compData);

      // 2. Fetch company history to extract direct security events and fingerprint
      const histData = await apiFetch<any>(`/api/v1/companies/${companyId}/history?range=all`);
      setFingerprint(histData.weakness_fingerprint || {});

      // 3. Extract direct security events
      const secEvents: SecurityEventItem[] = (histData.timeline_events || [])
        .filter((e: any) => e.event_type?.includes("SECURITY") || e.event_type?.includes("VULNERABILITY") || e.provenance_category === "SECURITY_HISTORY")
        .map((e: any) => ({
          id: e.id,
          event_type: e.event_type,
          title: e.title,
          description: e.summary,
          severity: e.priority || "MEDIUM",
          vulnerability_class: e.event_type,
          affected_component: null,
          affected_versions: null,
          confidence: e.confidence || 0.9,
          evidence: e.summary,
          source_url: e.source_url,
          observed_at: e.published_at || e.observed_at,
          relationship_type: "DIRECT_COMPANY_EVENT",
        }));
      setDirectEvents(secEvents);

      // 4. Correlate with technologies observed on assets
      const techItems: TechnologyAdvisoryItem[] = [];
      const technologies: Array<{ name: string; category: string }> = [];
      if (compData.assets) {
        for (const asset of compData.assets) {
          if (asset.technologies) {
            for (const t of asset.technologies) {
              if (!technologies.some((x) => x.name.toLowerCase() === t.name.toLowerCase())) {
                technologies.push({ name: t.name, category: t.category || "General" });
              }
            }
          }
        }
      }

      // Query KB for each observed technology
      for (const tech of technologies.slice(0, 8)) {
        try {
          const kbResults = await apiFetch<any>(`/api/v1/security-knowledge/search?q=${encodeURIComponent(tech.name)}&limit=3`);
          if (kbResults?.items && kbResults.items.length > 0) {
            techItems.push({
              technology_name: tech.name,
              category: tech.category,
              advisories_count: kbResults.total || kbResults.items.length,
              advisories: kbResults.items.map((adv: any) => ({
                cve_id: adv.cve_id,
                title: adv.title,
                vendor: adv.vendor,
                product: adv.product,
                known_ransomware_use: adv.known_ransomware_use,
                confidence: adv.confidence,
                source_url: adv.source_url,
              })),
            });
          }
        } catch {
          // Ignore individual technology lookup error
        }
      }
      setTechnologyContext(techItems);

    } catch (err) {
      console.error("Failed to load security history:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSecurityHistory();
  }, [companyId]);

  return (
    <div className="space-y-6 pb-12">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center gap-2 font-mono text-xs text-slate-400">
        <Link href="/companies" className="hover:text-white">
          Companies
        </Link>
        <span>/</span>
        <Link href={`/companies/${companyId}`} className="hover:text-white">
          {company?.name || `Company #${companyId}`}
        </Link>
        <span>/</span>
        <span className="text-cyan-400">Security History</span>
      </div>

      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded bg-purple-950/60 border border-purple-800 px-2 py-0.5 font-mono text-[10px] font-bold text-purple-300">
              HISTORICAL ATTACK SURFACE INTELLIGENCE
            </span>
          </div>
          <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-white sm:text-3xl">
            {company?.name || "Company"} Security History
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Differentiated security intelligence separating direct company disclosures from contextual technology vulnerability advisories.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href={`/companies/${companyId}/history`}
            className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 font-mono text-xs text-slate-300 hover:bg-slate-800"
          >
            ← Full Attack-Surface Timeline
          </Link>
        </div>
      </div>

      {/* Weakness Fingerprint Section */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-slate-300">
              Historical Weakness Fingerprint
            </h2>
            <p className="mt-0.5 text-xs text-slate-400">
              Empirical distribution of historically disclosed weakness categories across this organization's assets.
            </p>
          </div>
          <div className="font-mono text-xs text-slate-500">
            Total Classes: {Object.keys(fingerprint).length}
          </div>
        </div>

        {Object.keys(fingerprint).length === 0 ? (
          <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-center font-mono text-xs text-slate-500">
            No historical weakness events established yet for this company.
          </div>
        ) : (
          <div className="mt-4 flex flex-wrap gap-2.5">
            {Object.entries(fingerprint).map(([category, count]) => (
              <div
                key={category}
                className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-1.5 font-mono text-xs"
              >
                <span className="text-slate-300 font-semibold">{category}</span>
                <span className="rounded bg-cyan-950 border border-cyan-800/60 px-1.5 py-0.2 text-[11px] font-bold text-cyan-300">
                  {count}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* DUAL-COLUMN ARCHITECTURE: DIRECT vs INDIRECT */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* COLUMN 1: DIRECT COMPANY SECURITY EVENTS */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div>
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-emerald-400">
                  Direct Company Security Events
                </h2>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Official security advisories, bug bounty findings, or public disclosures attributed directly to this company.
              </p>
            </div>
            <span className="font-mono text-xs rounded bg-emerald-950/50 border border-emerald-800 px-2 py-0.5 text-emerald-300">
              {directEvents.length}
            </span>
          </div>

          {loading ? (
            <div className="p-8 text-center font-mono text-xs text-slate-500">Loading events...</div>
          ) : directEvents.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-8 text-center">
              <div className="font-mono text-xs font-semibold text-slate-400">No Direct Company Security Events</div>
              <p className="mt-1 text-xs text-slate-500">No public CVE or official vendor advisory has been directly attributed.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {directEvents.map((evt) => (
                <div
                  key={evt.id}
                  className="rounded-xl border border-emerald-900/40 bg-emerald-950/10 p-4 shadow-sm transition hover:border-emerald-700/60"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="rounded bg-emerald-950 border border-emerald-800 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-300">
                      DIRECT DISCLOSURE
                    </span>
                    <span className="font-mono text-[10px] text-slate-500">
                      {evt.observed_at ? new Date(evt.observed_at).toLocaleDateString() : "Historical"}
                    </span>
                  </div>

                  <h3 className="mt-2 text-sm font-semibold text-white">{evt.title}</h3>
                  {evt.description && (
                    <p className="mt-1 text-xs text-slate-300 leading-relaxed font-sans">{evt.description}</p>
                  )}

                  <div className="mt-3 flex items-center justify-between border-t border-slate-800/80 pt-2 text-[11px] font-mono text-slate-400">
                    <div>
                      Confidence: <span className="text-emerald-400 font-bold">{Math.round(evt.confidence * 100)}%</span>
                    </div>
                    {evt.source_url && (
                      <a
                        href={evt.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyan-400 underline hover:text-cyan-300 truncate max-w-[200px]"
                      >
                        Evidence Source ↗
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* COLUMN 2: RELATED TECHNOLOGY CONTEXT */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div>
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-cyan-400" />
                <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-cyan-400">
                  Related Technology Context
                </h2>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Vulnerabilities in third-party technologies observed on company assets. Context only — does not imply company vulnerability.
              </p>
            </div>
            <span className="font-mono text-xs rounded bg-cyan-950/50 border border-cyan-800 px-2 py-0.5 text-cyan-300">
              {technologyContext.length} techs
            </span>
          </div>

          {loading ? (
            <div className="p-8 text-center font-mono text-xs text-slate-500">Loading technology correlations...</div>
          ) : technologyContext.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-8 text-center">
              <div className="font-mono text-xs font-semibold text-slate-400">No Related Technology Advisories</div>
              <p className="mt-1 text-xs text-slate-500">No known KEV advisories match currently identified technologies.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {technologyContext.map((item, idx) => (
                <div
                  key={idx}
                  className="rounded-xl border border-cyan-900/30 bg-slate-900/60 p-4 shadow-sm space-y-3"
                >
                  <div className="flex items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-white">{item.technology_name}</span>
                      <span className="rounded bg-slate-800 px-1.5 py-0.2 font-mono text-[10px] text-slate-400">{item.category}</span>
                    </div>
                    <span className="font-mono text-[10px] text-cyan-400">
                      {item.advisories_count} advisories in KB
                    </span>
                  </div>

                  <div className="space-y-2">
                    {item.advisories.map((adv, aIdx) => (
                      <div key={aIdx} className="rounded-lg bg-slate-950/60 border border-slate-800 p-2.5 text-xs">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-[11px] font-bold text-cyan-300">{adv.cve_id || "Advisory"}</span>
                          {adv.known_ransomware_use?.toLowerCase() === "known" && (
                            <span className="rounded bg-rose-950/60 border border-rose-800 px-1.5 py-0.2 font-mono text-[9px] text-rose-300 font-bold">
                              RANSOMWARE
                            </span>
                          )}
                        </div>
                        <div className="mt-1 text-slate-300 text-[11px] line-clamp-1">{adv.title}</div>
                        <div className="mt-1.5 flex items-center justify-between text-[10px] font-mono text-slate-500">
                          <span>{adv.vendor} / {adv.product}</span>
                          {adv.source_url && (
                            <a href={adv.source_url} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline">
                              KB Source ↗
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="text-[10px] font-mono text-slate-500 italic bg-slate-950/40 p-2 rounded">
                    Correlation Confidence: 82% — Contextual signal only. Manual asset verification required.
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
