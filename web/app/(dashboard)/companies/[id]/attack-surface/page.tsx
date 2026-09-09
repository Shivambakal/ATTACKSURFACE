"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { AttackSurfaceGraph, GraphNode } from "@/lib/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function AttackSurfaceGraphPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const companyId = resolvedParams.id;

  const [graphData, setGraphData] = useState<AttackSurfaceGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedScope, setSelectedScope] = useState<string>("ALL");
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const fetchGraph = async () => {
    setLoading(true);
    try {
      let url = `/api/v1/companies/${companyId}/attack-surface`;
      if (selectedScope !== "ALL") {
        url += `?scope=${selectedScope}`;
      }
      const data = await apiFetch<AttackSurfaceGraph>(url);
      setGraphData(data);
    } catch (err) {
      console.error("Failed to load attack surface graph:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [companyId, selectedScope]);

  if (loading || !graphData) {
    return (
      <div className="space-y-4">
        <div className="h-20 rounded-xl border border-slate-800 bg-slate-900/60 animate-pulse" />
        <div className="h-[600px] rounded-2xl border border-slate-800 bg-slate-900/40 animate-pulse" />
      </div>
    );
  }

  // Filter nodes according to selectedType
  const displayedNodes = graphData.nodes.filter((n) => {
    if (selectedType === "ALL") return true;
    if (selectedType === "DOMAIN") return ["ROOT_DOMAIN", "SUBDOMAIN"].includes(n.type);
    return n.type === selectedType;
  });

  // Group nodes by hierarchical layer for clean visual rendering
  const companyNode = graphData.nodes.find((n) => n.type === "COMPANY");
  const productNodes = displayedNodes.filter((n) => n.type === "PRODUCT");
  const assetNodes = displayedNodes.filter((n) => ["ROOT_DOMAIN", "SUBDOMAIN", "WEB_APPLICATION", "SECURITY_PORTAL"].includes(n.type));
  const apiNodes = displayedNodes.filter((n) => n.type === "API");
  const featureNodes = displayedNodes.filter((n) => n.type === "FEATURE");
  const signalNodes = displayedNodes.filter((n) => n.type === "RESEARCH_SIGNAL");

  const getNodeColor = (node: GraphNode) => {
    if (node.type === "COMPANY") return "border-cyan-500 bg-cyan-950/80 text-cyan-200";
    if (node.type === "PRODUCT") return "border-blue-500 bg-blue-950/80 text-blue-200";
    if (node.type === "RESEARCH_SIGNAL") {
      return node.priority === "CRITICAL"
        ? "border-red-500 bg-red-950/80 text-red-200"
        : "border-amber-500 bg-amber-950/80 text-amber-200";
    }
    if (node.scope === "IN_SCOPE") return "border-emerald-500 bg-emerald-950/70 text-emerald-200";
    if (node.scope === "RELATED") return "border-amber-600 bg-amber-950/70 text-amber-200";
    if (node.scope === "OUT_OF_SCOPE") return "border-red-600 bg-red-950/70 text-red-200";
    return "border-slate-700 bg-slate-900/80 text-slate-300";
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Navigation */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex items-center gap-3">
          <Link
            href={`/companies/${companyId}`}
            className="rounded-lg border border-slate-800 bg-slate-950 p-2 text-slate-400 hover:text-white transition-colors"
            title="Back to Command Center"
          >
            ←
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white tracking-tight">ATTACK SURFACE GRAPH</h1>
              <span className="rounded bg-cyan-950 px-2 py-0.5 font-mono text-xs text-cyan-400 border border-cyan-800/60">
                {graphData.company.canonical_domain}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Interactive relationship map: Company → Products → Assets → APIs & Features → Prioritized Signals.
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 font-mono text-xs">
          {/* Scope Filter */}
          <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950 p-1">
            <span className="px-2 text-slate-500">Scope:</span>
            {["ALL", "IN_SCOPE", "RELATED", "OUT_OF_SCOPE"].map((sc) => (
              <button
                key={sc}
                onClick={() => setSelectedScope(sc)}
                className={`rounded px-2.5 py-1 font-semibold transition-colors ${
                  selectedScope === sc
                    ? "bg-slate-800 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {sc}
              </button>
            ))}
          </div>

          {/* Type Filter */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-slate-300 focus:border-cyan-500 focus:outline-none"
          >
            <option value="ALL">All Entities ({graphData.stats.total_nodes})</option>
            <option value="PRODUCT">Products ({graphData.stats.products_count})</option>
            <option value="DOMAIN">Assets & Domains ({graphData.stats.assets_count})</option>
            <option value="API">APIs ({graphData.stats.apis_count})</option>
            <option value="FEATURE">Features ({graphData.stats.features_count})</option>
            <option value="RESEARCH_SIGNAL">Signals ({graphData.stats.signals_count})</option>
          </select>
        </div>
      </div>

      {/* Main Graph Canvas & Inspection Drawer */}
      <div className="relative flex flex-col lg:flex-row gap-6">
        {/* Graph Canvas */}
        <div className="flex-1 rounded-2xl border border-slate-800 bg-slate-950 p-6 overflow-x-auto min-h-[600px] shadow-2xl">
          <div className="flex flex-col items-center space-y-10 min-w-[750px]">
            {/* LEVEL 1: ROOT COMPANY */}
            {companyNode && (
              <div className="flex flex-col items-center">
                <div
                  onClick={() => setSelectedNode(companyNode)}
                  className={`cursor-pointer rounded-2xl border-2 px-8 py-4 shadow-xl text-center transition-all hover:scale-105 ${getNodeColor(
                    companyNode
                  )} ${selectedNode?.id === companyNode.id ? "ring-2 ring-cyan-400" : ""}`}
                >
                  <span className="block font-mono text-[10px] tracking-widest uppercase text-cyan-400 font-semibold">
                    ORGANIZATION ROOT
                  </span>
                  <span className="block text-lg font-extrabold text-white mt-0.5">{companyNode.label}</span>
                  <span className="block font-mono text-xs text-slate-400">{companyNode.canonical_domain}</span>
                </div>
                <div className="h-6 w-0.5 bg-slate-800" />
              </div>
            )}

            {/* LEVEL 2: PRODUCTS */}
            {productNodes.length > 0 && (
              <div className="w-full flex flex-col items-center">
                <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2 font-semibold">
                  ── PRODUCTS & PLATFORMS ({productNodes.length}) ──
                </span>
                <div className="flex flex-wrap justify-center gap-3">
                  {productNodes.map((p) => (
                    <div
                      key={p.id}
                      onClick={() => setSelectedNode(p)}
                      className={`cursor-pointer rounded-xl border px-4 py-2 text-center text-xs font-mono transition-all hover:scale-105 ${getNodeColor(
                        p
                      )} ${selectedNode?.id === p.id ? "ring-2 ring-cyan-400" : ""}`}
                    >
                      <span className="font-bold block text-slate-100">{p.label}</span>
                      <span className="text-[10px] text-slate-400">PRODUCT</span>
                    </div>
                  ))}
                </div>
                <div className="h-6 w-0.5 bg-slate-800 mt-3" />
              </div>
            )}

            {/* LEVEL 3: ASSETS & DOMAINS */}
            {assetNodes.length > 0 && (
              <div className="w-full flex flex-col items-center">
                <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2 font-semibold">
                  ── ASSETS & PUBLIC DOMAINS ({assetNodes.length}) ──
                </span>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 w-full">
                  {assetNodes.map((a) => (
                    <div
                      key={a.id}
                      onClick={() => setSelectedNode(a)}
                      className={`cursor-pointer rounded-xl border p-3 font-mono text-xs transition-all hover:scale-105 ${getNodeColor(
                        a
                      )} ${selectedNode?.id === a.id ? "ring-2 ring-cyan-400" : ""}`}
                    >
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <span className="text-[10px] font-semibold text-slate-400">{a.type}</span>
                        <span className="text-[10px] font-bold">
                          {a.scope === "IN_SCOPE" ? "✅" : a.scope === "RELATED" ? "⚠️" : a.scope === "OUT_OF_SCOPE" ? "⛔" : "❓"}
                        </span>
                      </div>
                      <span className="font-bold block text-white truncate">{a.label}</span>
                      <div className="mt-1.5 flex items-center justify-between text-[10px] text-slate-400">
                        <span>Confidence</span>
                        <span className="text-amber-300 font-bold">{Math.round(a.confidence * 100)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="h-6 w-0.5 bg-slate-800 mt-3" />
              </div>
            )}

            {/* LEVEL 4: APIs & FEATURES */}
            {(apiNodes.length > 0 || featureNodes.length > 0) && (
              <div className="w-full flex flex-col items-center">
                <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2 font-semibold">
                  ── EXPOSED APIS & SENSITIVE CAPABILITIES ({apiNodes.length + featureNodes.length}) ──
                </span>
                <div className="flex flex-wrap justify-center gap-2">
                  {apiNodes.map((api) => (
                    <div
                      key={api.id}
                      onClick={() => setSelectedNode(api)}
                      className={`cursor-pointer rounded-lg border px-3 py-1.5 font-mono text-xs transition-all hover:scale-105 border-cyan-800/80 bg-cyan-950/40 text-cyan-200 ${
                        selectedNode?.id === api.id ? "ring-2 ring-cyan-400" : ""
                      }`}
                    >
                      <span className="font-bold">{api.label}</span>
                    </div>
                  ))}
                  {featureNodes.map((feat) => (
                    <div
                      key={feat.id}
                      onClick={() => setSelectedNode(feat)}
                      className={`cursor-pointer rounded-lg border px-3 py-1.5 font-mono text-xs transition-all hover:scale-105 border-slate-700 bg-slate-900 text-slate-200 ${
                        selectedNode?.id === feat.id ? "ring-2 ring-cyan-400" : ""
                      }`}
                    >
                      <span>{feat.label}</span>
                    </div>
                  ))}
                </div>
                <div className="h-6 w-0.5 bg-slate-800 mt-3" />
              </div>
            )}

            {/* LEVEL 5: RESEARCH SIGNALS */}
            {signalNodes.length > 0 && (
              <div className="w-full flex flex-col items-center">
                <span className="text-[10px] font-mono uppercase tracking-widest text-amber-400 mb-2 font-bold">
                  ── RESEARCH SIGNALS & PRIORITIZED LEADS ({signalNodes.length}) ──
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
                  {signalNodes.map((sig) => (
                    <div
                      key={sig.id}
                      onClick={() => setSelectedNode(sig)}
                      className={`cursor-pointer rounded-xl border p-3 font-mono text-xs transition-all hover:scale-105 ${getNodeColor(
                        sig
                      )} ${selectedNode?.id === sig.id ? "ring-2 ring-cyan-400" : ""}`}
                    >
                      <div className="flex items-center justify-between text-[10px] mb-1">
                        <span className="font-bold text-amber-400">PRIORITY: {sig.priority}</span>
                        <span className="font-bold text-white">Score: {sig.relevance_score}/100</span>
                      </div>
                      <span className="font-bold block text-white">{sig.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Node Inspection Drawer */}
        {selectedNode && (
          <div className="w-full lg:w-96 rounded-2xl border border-slate-800 bg-slate-900/90 p-5 shadow-2xl backdrop-blur-md self-start space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
                  NODE DETAILS
                </span>
                <h3 className="font-bold text-white text-base truncate">{selectedNode.label}</h3>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="rounded-lg p-1 text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div>
                <span className="text-slate-500 block text-[10px]">Entity Type</span>
                <span className="text-slate-200 font-bold">{selectedNode.type}</span>
              </div>

              <div>
                <span className="text-slate-500 block text-[10px]">Scope Status</span>
                <span className="font-bold text-white">
                  {selectedNode.scope === "IN_SCOPE" ? "✅ IN_SCOPE" : selectedNode.scope === "RELATED" ? "⚠️ RELATED (VERIFY)" : selectedNode.scope === "OUT_OF_SCOPE" ? "⛔ OUT_OF_SCOPE" : selectedNode.scope}
                </span>
              </div>

              <div>
                <span className="text-slate-500 block text-[10px]">Confidence</span>
                <span className="text-amber-300 font-bold">{Math.round(selectedNode.confidence * 100)}%</span>
              </div>

              {selectedNode.details && (
                <div className="rounded-lg bg-slate-950 p-3 space-y-2 border border-slate-800/80">
                  <span className="text-[10px] text-slate-500 block">Metadata & Provenance</span>
                  {Object.entries(selectedNode.details).map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-2 text-[11px]">
                      <span className="text-slate-400 capitalize">{k.replace("_", " ")}:</span>
                      <span className="text-slate-200 text-right truncate max-w-[180px]">{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="border-t border-slate-800 pt-3">
              <Link
                href={`/companies/${companyId}`}
                className="block w-full rounded-lg bg-slate-800 py-2 text-center font-mono text-xs font-semibold text-slate-200 hover:bg-slate-700 transition-colors"
              >
                VIEW FULL DETAIL
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
