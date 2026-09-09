"use client";

import React, { useState } from "react";
import Link from "next/link";

interface HierarchyNode {
  id: string;
  name: string;
  type: "APEX" | "SUBDOMAIN" | "SERVICE" | "ENDPOINT";
  scope: "IN_SCOPE" | "OUT_OF_SCOPE" | "UNDETERMINED";
  status: "ACTIVE" | "CHANGED" | "NEW";
  details: string;
  ipOrCname: string;
  ports: number[];
  children?: HierarchyNode[];
}

const SAMPLE_HIERARCHY: HierarchyNode = {
  id: "node-root",
  name: "enterprise-cloud.io",
  type: "APEX",
  scope: "IN_SCOPE",
  status: "ACTIVE",
  details: "Primary corporate apex registered under authoritative DNS. DNSSEC enabled.",
  ipOrCname: "104.21.55.10 (Cloudflare Anycast)",
  ports: [80, 443],
  children: [
    {
      id: "node-sub-1",
      name: "api.enterprise-cloud.io",
      type: "SUBDOMAIN",
      scope: "IN_SCOPE",
      status: "ACTIVE",
      details: "REST & GraphQL production gateway behind Cloudflare WAF.",
      ipOrCname: "104.21.55.10 (Cloudflare)",
      ports: [443],
      children: [
        {
          id: "node-ep-1",
          name: "/v2/auth/oauth2/token",
          type: "ENDPOINT",
          scope: "IN_SCOPE",
          status: "ACTIVE",
          details: "OAuth2 authentication handler. High-value security target.",
          ipOrCname: "Internal Upstream: 10.200.4.15",
          ports: [443],
        },
        {
          id: "node-ep-2",
          name: "/graphql",
          type: "ENDPOINT",
          scope: "IN_SCOPE",
          status: "CHANGED",
          details: "Schema updated 3 hours ago. New sensitive queries exposed.",
          ipOrCname: "Internal Upstream: 10.200.4.22",
          ports: [443],
        },
      ],
    },
    {
      id: "node-sub-2",
      name: "beta-fleet.enterprise-cloud.io",
      type: "SUBDOMAIN",
      scope: "IN_SCOPE",
      status: "NEW",
      details: "Discovered via Certificate Transparency log 42 minutes ago.",
      ipOrCname: "CNAME k8s-beta.us-west-2.elb.amazonaws.com",
      ports: [443, 8443],
      children: [
        {
          id: "node-ep-3",
          name: "/metrics & /actuator/health",
          type: "ENDPOINT",
          scope: "IN_SCOPE",
          status: "NEW",
          details: "Spring Boot Actuator endpoints accessible without authentication.",
          ipOrCname: "Amazon AWS ELB",
          ports: [8443],
        },
      ],
    },
    {
      id: "node-sub-3",
      name: "partner-portal.enterprise-cloud.io",
      type: "SUBDOMAIN",
      scope: "OUT_OF_SCOPE",
      status: "ACTIVE",
      details: "Third-party hosted Zendesk community platform. Explicitly out of scope.",
      ipOrCname: "CNAME enterprise-cloud.zendesk.com",
      ports: [443],
    },
  ],
};

export default function AttackSurfacePage() {
  const [selectedNode, setSelectedNode] = useState<HierarchyNode>(SAMPLE_HIERARCHY.children![1]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Hero Header */}
      <div className="max-w-3xl space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          PERIMETER MAPPING ARCHITECTURE
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          Total Visibility Over <span className="text-cyan-400">Expanding Perimeters</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          Modern enterprise attack surfaces shift on every commit. AttackSurface constructs continuous hierarchical models from apex domains down to microservice endpoints, mapping scope compliance and asset risk in real-time.
        </p>
      </div>

      {/* Asset Hierarchy Explorer */}
      <div className="mt-14 space-y-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Hierarchical Asset &amp; Scope Map</h2>
            <p className="text-xs text-slate-300">
              Click any node in the asset tree below to inspect its live perimeter telemetry, scope eligibility, and delta state.
            </p>
          </div>

          <div className="flex items-center gap-3 font-mono text-xs">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              <span className="text-slate-300">In-Scope</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-rose-400" />
              <span className="text-slate-300">Out-of-Scope</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="text-cyan-400 font-bold">New Delta</span>
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Tree View Left (Span 7) */}
          <div className="lg:col-span-7 rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 backdrop-blur-xl">
            <div className="text-[11px] font-mono text-slate-300 uppercase tracking-wider border-b border-white/[0.08] pb-3 flex justify-between">
              <span>Canonical Asset Tree</span>
              <span>Click node to inspect</span>
            </div>

            <div className="mt-4 space-y-3 font-mono text-xs">
              {/* Apex Node */}
              <div
                onClick={() => setSelectedNode(SAMPLE_HIERARCHY)}
                className={`cursor-pointer rounded-xl p-3 border transition-all ${
                  selectedNode.id === SAMPLE_HIERARCHY.id
                    ? "bg-cyan-500/15 border-cyan-500/40 text-cyan-200"
                    : "bg-white/[0.02] border-white/[0.06] text-white hover:border-white/[0.2]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-cyan-400">🌐 APEX</span>
                    <span className="font-bold">{SAMPLE_HIERARCHY.name}</span>
                  </div>
                  <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-400 font-bold border border-emerald-500/20">
                    IN-SCOPE
                  </span>
                </div>
              </div>

              {/* Subdomain Nodes */}
              {SAMPLE_HIERARCHY.children?.map((sub) => (
                <div key={sub.id} className="ml-6 space-y-2 border-l border-white/[0.1] pl-4">
                  <div
                    onClick={() => setSelectedNode(sub)}
                    className={`cursor-pointer rounded-xl p-3 border transition-all ${
                      selectedNode.id === sub.id
                        ? "bg-cyan-500/15 border-cyan-500/40 text-cyan-200"
                        : "bg-white/[0.02] border-white/[0.06] text-slate-300 hover:border-white/[0.2] hover:text-white"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-slate-300">↳ SUB</span>
                        <span className="font-semibold">{sub.name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {sub.status === "NEW" && (
                          <span className="rounded bg-cyan-500/20 px-1.5 py-0.2 text-[9px] text-cyan-300 border border-cyan-500/40 font-bold animate-pulse">
                            NEW
                          </span>
                        )}
                        <span
                          className={`rounded px-2 py-0.5 text-[10px] font-bold border ${
                            sub.scope === "IN_SCOPE"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                          }`}
                        >
                          {sub.scope.replace("_", "-")}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Endpoints */}
                  {sub.children && (
                    <div className="ml-6 space-y-1.5 border-l border-white/[0.1] pl-4">
                      {sub.children.map((ep) => (
                        <div
                          key={ep.id}
                          onClick={() => setSelectedNode(ep)}
                          className={`cursor-pointer rounded-lg p-2 border transition-all text-[11px] ${
                            selectedNode.id === ep.id
                              ? "bg-cyan-500/15 border-cyan-500/40 text-cyan-200"
                              : "bg-white/[0.01] border-white/[0.04] text-slate-300 hover:border-white/[0.15] hover:text-white"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5">
                              <span className="text-slate-400">⮑</span>
                              <span>{ep.name}</span>
                            </div>
                            {ep.status === "CHANGED" && (
                              <span className="rounded bg-amber-500/20 px-1.5 py-0.2 text-[9px] text-amber-300 border border-amber-500/30">
                                CHANGED
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Node Inspector Right (Span 5) */}
          <div className="lg:col-span-5 rounded-3xl border border-white/[0.08] bg-[#02050b] p-6 backdrop-blur-xl space-y-5">
            <div className="border-b border-white/[0.08] pb-4">
              <span className="font-mono text-[10px] text-cyan-400 uppercase tracking-wider block">
                PERIMETER TELEMETRY INSPECTOR
              </span>
              <h3 className="mt-1 text-lg font-bold text-white break-all">{selectedNode.name}</h3>
              <div className="mt-2 flex flex-wrap gap-2 font-mono text-[10px]">
                <span className="rounded bg-white/[0.05] border border-white/[0.1] px-2 py-0.5 text-slate-300">
                  TYPE: {selectedNode.type}
                </span>
                <span
                  className={`rounded px-2 py-0.5 border font-bold ${
                    selectedNode.scope === "IN_SCOPE"
                      ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                      : "bg-rose-500/20 text-rose-300 border-rose-500/30"
                  }`}
                >
                  {selectedNode.scope}
                </span>
              </div>
            </div>

            <div className="space-y-4 text-xs font-mono">
              <div>
                <span className="text-slate-300 uppercase block text-[10px]">Infrastructure Route / Pointer</span>
                <p className="mt-1 text-slate-200 bg-white/[0.03] border border-white/[0.06] p-2.5 rounded-xl break-all">
                  {selectedNode.ipOrCname}
                </p>
              </div>

              <div>
                <span className="text-slate-300 uppercase block text-[10px]">Exposed Service Ports</span>
                <div className="mt-1 flex gap-2">
                  {selectedNode.ports.map((p) => (
                    <span key={p} className="rounded bg-cyan-950/60 border border-cyan-500/30 px-2 py-1 text-cyan-300">
                      Port {p}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-slate-300 uppercase block text-[10px]">Perimeter Analysis &amp; Findings</span>
                <p className="mt-1 font-sans text-xs text-slate-300 leading-relaxed bg-white/[0.03] border border-white/[0.06] p-3 rounded-xl">
                  {selectedNode.details}
                </p>
              </div>
            </div>

            <div className="pt-2">
              <Link
                href="/signup"
                className="w-full text-center block rounded-xl bg-cyan-500 py-2.5 font-mono text-xs font-bold text-slate-950 hover:bg-cyan-400 transition"
              >
                Track This Target Live &rarr;
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
