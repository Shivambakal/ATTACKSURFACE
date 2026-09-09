"use client";

import React, { useState } from "react";
import Link from "next/link";

interface EndpointDoc {
  method: "GET" | "POST";
  path: string;
  summary: string;
  description: string;
  authRequired: boolean;
  params?: { name: string; type: string; required: boolean; desc: string }[];
  curlExample: string;
  pythonExample: string;
  nodeExample: string;
  responseSample: string;
}

const ENDPOINTS: EndpointDoc[] = [
  {
    method: "GET",
    path: "/api/v1/programs",
    summary: "List Bug Bounty Programs & Scopes",
    description: "Returns paginated list of synchronized bug bounty programs from HackerOne, Bugcrowd, and enterprise VDPs.",
    authRequired: false,
    params: [
      { name: "limit", type: "integer", required: false, desc: "Number of items to return (default 50, max 200)" },
      { name: "offset", type: "integer", required: false, desc: "Pagination offset" },
      { name: "q", type: "string", required: false, desc: "Search query across company and program names" },
      { name: "bounty_only", type: "boolean", required: false, desc: "Filter only monetary reward programs" },
    ],
    curlExample: `curl -X GET "https://api.attacksurface.online/api/v1/programs?limit=10&bounty_only=true"`,
    pythonExample: `import requests

res = requests.get("https://api.attacksurface.online/api/v1/programs", params={"limit": 10, "bounty_only": True})
programs = res.json()
print(f"Total programs returned: {programs['total']}")`,
    nodeExample: `const res = await fetch("https://api.attacksurface.online/api/v1/programs?limit=10&bounty_only=true");
const data = await res.json();
console.log(data.items);`,
    responseSample: `{
  "total": 2010,
  "items": [
    {
      "id": 1,
      "company_id": 14,
      "platform": "HACKERONE",
      "name": "Acme Security Program",
      "program_url": "https://hackerone.com/acme",
      "bounty_enabled": true,
      "min_bounty": 250,
      "max_bounty": 10000,
      "scope_rules_count": 14
    }
  ]
}`,
  },
  {
    method: "GET",
    path: "/api/v1/programs/stats",
    summary: "Get Global Program Statistics",
    description: "Returns aggregated statistics on synchronized platforms, total programs, scope rules, and change events.",
    authRequired: false,
    curlExample: `curl -X GET "https://api.attacksurface.online/api/v1/programs/stats"`,
    pythonExample: `import requests

stats = requests.get("https://api.attacksurface.online/api/v1/programs/stats").json()
print(f"Total programs: {stats['total_programs']}, Scope rules: {stats['total_scope_rules']}")`,
    nodeExample: `const res = await fetch("https://api.attacksurface.online/api/v1/programs/stats");
const stats = await res.json();`,
    responseSample: `{
  "total_programs": 2010,
  "bounty_programs": 1079,
  "vdp_programs": 931,
  "total_scope_rules": 14740,
  "canonical_companies_with_programs": 1432
}`,
  },
  {
    method: "GET",
    path: "/api/v1/security-intelligence/stats",
    summary: "Get Vulnerability & Security Telemetry Stats",
    description: "Returns metrics on actively exploited vulnerabilities (CISA KEV), security events, and severity distribution.",
    authRequired: false,
    curlExample: `curl -X GET "https://api.attacksurface.online/api/v1/security-intelligence/stats"`,
    pythonExample: `import requests

stats = requests.get("https://api.attacksurface.online/api/v1/security-intelligence/stats").json()
print(f"Actively exploited CVEs: {stats['actively_exploited_count']}")`,
    nodeExample: `const res = await fetch("https://api.attacksurface.online/api/v1/security-intelligence/stats");
const stats = await res.json();`,
    responseSample: `{
  "total_events": 3364,
  "actively_exploited_count": 1695,
  "by_severity": {
    "CRITICAL": 2,
    "HIGH": 2
  },
  "by_priority": {
    "CRITICAL": 4
  }
}`,
  },
  {
    method: "GET",
    path: "/api/v1/health",
    summary: "Platform Health & Diagnostics Check",
    description: "Returns operational health status of core API services, database connectivity, and timestamp.",
    authRequired: false,
    curlExample: `curl -X GET "https://api.attacksurface.online/api/v1/health"`,
    pythonExample: `import requests

health = requests.get("https://api.attacksurface.online/api/v1/health").json()
print(f"Status: {health['status']}, Time: {health['timestamp']}")`,
    nodeExample: `const res = await fetch("https://api.attacksurface.online/api/v1/health");
const health = await res.json();`,
    responseSample: `{
  "status": "ok",
  "timestamp": "2026-09-08T15:11:04.708681+00:00"
}`,
  },
];

export default function ApiPage() {
  const [selectedEndpoint, setSelectedEndpoint] = useState<EndpointDoc>(ENDPOINTS[0]);
  const [language, setLanguage] = useState<"curl" | "python" | "node">("curl");

  return (
    <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="max-w-3xl space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          DEVELOPER API REFERENCE
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          AttackSurface <span className="text-cyan-400">REST API</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          Automate target tracking, ingest verified scope rules, and pull temporal differentials directly into your security tooling and custom research scripts.
        </p>

        <div className="pt-2 flex items-center gap-3 font-mono text-xs text-slate-400">
          <span>Base URL:</span>
          <code className="rounded bg-white/[0.05] border border-white/[0.1] px-2.5 py-1 text-cyan-300">
            https://api.attacksurface.online/api/v1
          </code>
        </div>
      </div>

      {/* Main Endpoints Section */}
      <div className="mt-12 grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* Endpoint Selector (Span 4) */}
        <div className="lg:col-span-4 space-y-2 font-mono text-xs">
          <div className="text-[11px] text-slate-300 uppercase tracking-wider px-3 pb-2 border-b border-white/[0.08]">
            Available Endpoints
          </div>

          {ENDPOINTS.map((ep) => (
            <button
              key={ep.path}
              onClick={() => setSelectedEndpoint(ep)}
              className={`w-full text-left rounded-xl p-3 transition-all ${
                selectedEndpoint.path === ep.path
                  ? "bg-cyan-500/15 border border-cyan-500/30 text-white font-semibold"
                  : "bg-white/[0.02] border border-white/[0.06] text-slate-300 hover:border-white/[0.2] hover:text-white"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="rounded bg-emerald-500/20 px-1.5 py-0.2 text-[10px] font-bold text-emerald-400">
                  {ep.method}
                </span>
                <span className="truncate">{ep.path}</span>
              </div>
              <p className="font-sans text-[11px] text-slate-300 mt-1 truncate">{ep.summary}</p>
            </button>
          ))}
        </div>

        {/* Endpoint Detail Pane (Span 8) */}
        <div className="lg:col-span-8 rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-6">
          <div className="border-b border-white/[0.08] pb-4">
            <div className="flex items-center gap-2 font-mono">
              <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-bold text-emerald-400">
                {selectedEndpoint.method}
              </span>
              <span className="text-sm sm:text-base font-bold text-white">{selectedEndpoint.path}</span>
            </div>
            <p className="mt-2 text-sm text-slate-300">{selectedEndpoint.description}</p>
          </div>

          {/* Parameters Table */}
          {selectedEndpoint.params && (
            <div>
              <h3 className="font-mono text-xs uppercase tracking-wider text-slate-300 mb-3">
                Query Parameters
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs">
                  <thead className="border-b border-white/[0.08] text-slate-300 text-[10px]">
                    <tr>
                      <th className="pb-2">Parameter</th>
                      <th className="pb-2">Type</th>
                      <th className="pb-2">Required</th>
                      <th className="pb-2">Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {selectedEndpoint.params.map((p) => (
                      <tr key={p.name}>
                        <td className="py-2.5 text-cyan-300 font-bold">{p.name}</td>
                        <td className="py-2.5 text-slate-400">{p.type}</td>
                        <td className="py-2.5">
                          {p.required ? (
                            <span className="text-rose-400">Yes</span>
                          ) : (
                            <span className="text-slate-400">No</span>
                          )}
                        </td>
                        <td className="py-2.5 font-sans text-slate-300 text-[11px]">{p.desc}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Code Example Tabs */}
          <div>
            <div className="flex items-center justify-between font-mono text-xs mb-2">
              <span className="text-slate-300 uppercase text-[11px]">Request Example</span>
              <div className="flex gap-1 rounded-lg bg-white/[0.04] p-0.5 border border-white/[0.08]">
                {(["curl", "python", "node"] as const).map((lang) => (
                  <button
                    key={lang}
                    onClick={() => setLanguage(lang)}
                    className={`rounded px-2.5 py-1 text-[11px] transition-all uppercase ${
                      language === lang
                        ? "bg-cyan-500 text-slate-950 font-bold"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {lang}
                  </button>
                ))}
              </div>
            </div>

            <pre className="rounded-2xl border border-white/[0.08] bg-[#02050b] p-4 font-mono text-xs text-cyan-300 overflow-x-auto leading-relaxed">
              {language === "curl" && selectedEndpoint.curlExample}
              {language === "python" && selectedEndpoint.pythonExample}
              {language === "node" && selectedEndpoint.nodeExample}
            </pre>
          </div>

          {/* Response Example */}
          <div>
            <span className="font-mono text-xs text-slate-300 uppercase block mb-2 text-[11px]">
              Response Payload (200 OK)
            </span>
            <pre className="rounded-2xl border border-white/[0.08] bg-[#02050b] p-4 font-mono text-xs text-emerald-300/90 overflow-x-auto leading-relaxed">
              {selectedEndpoint.responseSample}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
