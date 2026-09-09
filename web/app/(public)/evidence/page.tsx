"use client";

import React, { useState } from "react";
import Link from "next/link";

interface EvidenceBundle {
  claimId: string;
  claim: string;
  entity: string;
  confidence: number;
  observedAt: string;
  method: string;
  sha256: string;
  rawPayload: string;
  upstreamSource: string;
  impactScore: string;
}

const SAMPLE_EVIDENCE: EvidenceBundle[] = [
  {
    claimId: "EVD-2026-9810",
    claim: "Subdomain Takeover Precondition: Dangling CNAME to Unclaimed Azure Traffic Manager",
    entity: "telemetry-collector.enterprise-target.com",
    confidence: 99.4,
    observedAt: "2026-09-08T14:48:19.102Z",
    method: "Authoritative DNS Resolver via Root DNS RFC 1035",
    sha256: "d5a84e27bbd56f4e1f7e029f6de39486c478a870d0fa85ff0327429188e44c21",
    rawPayload: `; <<>> DiG 9.18.1-1ubuntu1.3-Ubuntu <<>> telemetry-collector.enterprise-target.com CNAME
;; ANSWER SECTION:
telemetry-collector.enterprise-target.com. 300 IN CNAME corp-telemetry.trafficmanager.net.

;; AUTHORITY SECTION:
trafficmanager.net.	60	IN	SOA	tm1.trafficmanager.net. (
				2026090801 ; serial
				900        ; refresh (15 minutes)
				300        ; retry (5 minutes)
				604800     ; expire (1 week)
				60         ; minimum (1 minute)
				)
;; Query time: 14 msec
;; SERVER: 8.8.8.8#53(8.8.8.8)
;; MSG SIZE  rcvd: 142
;; STATUS: NXDOMAIN (Target profile de-allocated)`,
    upstreamSource: "Authoritative Root DNS Server (Azure TrafficManager)",
    impactScore: "HIGH · SUBDOMAIN TAKEOVER VECTOR",
  },
  {
    claimId: "EVD-2026-9811",
    claim: "Origin IP Bypass: Cloudflare WAF Circumvention via Direct TLS Handshake",
    entity: "198.51.100.42 (Direct Origin Host)",
    confidence: 100.0,
    observedAt: "2026-09-08T15:10:04.441Z",
    method: "TLS 1.3 Handshake & SNI Negotiation",
    sha256: "b10a8db164e0754105b7a99be72e3fe5ec9630c6a83685e13a078028ff7bf50a",
    rawPayload: `CONNECT 198.51.100.42:443
TLS_VERSION: TLSv1.3
CIPHER_SUITE: TLS_AES_256_GCM_SHA384
SERVER_CERTIFICATE_SUBJECT: CN=checkout.enterprise-target.com
SERVER_CERTIFICATE_ISSUER: Let's Encrypt Authority X3
SERVER_CERTIFICATE_SERIAL: 03:fe:8a:92:44:b1:10:9c
CERT_FINGERPRINT_SHA256: 48:32:11:ff:8c:4a:2e:91...
HTTP/1.1 200 OK
Server: nginx/1.24.0
Content-Type: text/html; charset=UTF-8
X-Powered-By: Express
(Direct origin returns production checkout page without Cloudflare cookie)`,
    upstreamSource: "Direct TCP Socket Probe (Port 443)",
    impactScore: "CRITICAL · DIRECT ORIGIN EXPOSURE",
  },
];

export default function EvidencePage() {
  const [selectedBundle, setSelectedBundle] = useState<EvidenceBundle>(SAMPLE_EVIDENCE[0]);
  const [copied, setCopied] = useState(false);

  const handleCopyHash = () => {
    navigator.clipboard.writeText(selectedBundle.sha256);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="max-w-3xl space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          CRYPTOGRAPHIC VERIFICATION
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          The Evidence Engine: <span className="text-cyan-400">Verifiable Ground Truth</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          Every delta on AttackSurface is grounded in cryptographic proof. We preserve raw socket handshakes, DNS authoritative zone records, and HTTP headers with SHA-256 validation so researchers can submit rock-solid bug bounty reports.
        </p>
      </div>

      {/* Claim to Observation Chain Diagram */}
      <div className="mt-14 rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl">
        <h2 className="font-mono text-xs uppercase tracking-widest text-cyan-400 mb-6">
          The 7-Link Evidence Chain
        </h2>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7 font-mono text-xs">
          {[
            { step: "01", label: "Claim", desc: "Hypothesis" },
            { step: "02", label: "Entity", desc: "Asset Target" },
            { step: "03", label: "Observation", desc: "Non-intrusive probe" },
            { step: "04", label: "Telemetry", desc: "Raw wire bytes" },
            { step: "05", label: "Timestamp", desc: "RFC 3339 UTC" },
            { step: "06", label: "SHA-256", desc: "Hash Integrity" },
            { step: "07", label: "Confidence", desc: "0-100% Score" },
          ].map((item, idx) => (
            <div
              key={item.step}
              className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-3 text-center space-y-1 relative"
            >
              <span className="text-[10px] text-cyan-400 font-bold block">{item.step}</span>
              <span className="font-bold text-white block">{item.label}</span>
              <span className="text-[10px] text-slate-300 block">{item.desc}</span>
              {idx < 6 && (
                <span className="hidden lg:block absolute -right-2 top-1/2 -translate-y-1/2 text-slate-400 text-xs">
                  &rarr;
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Interactive Evidence Inspector */}
      <div className="mt-16 space-y-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Live Evidence Bundle Inspector</h2>
            <p className="text-xs text-slate-300">
              Select an evidence bundle to review raw observation telemetry and cryptographic signatures.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {SAMPLE_EVIDENCE.map((item) => (
              <button
                key={item.claimId}
                onClick={() => setSelectedBundle(item)}
                className={`rounded-xl px-3 py-1.5 font-mono text-xs transition-all ${
                  selectedBundle.claimId === item.claimId
                    ? "bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/20"
                    : "bg-white/[0.04] text-slate-300 hover:bg-white/[0.08] hover:text-white border border-white/[0.06]"
                }`}
              >
                {item.claimId}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-white/[0.1] bg-slate-950/90 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-cyan-400">{selectedBundle.claimId}</span>
                <span className="rounded bg-cyan-500/15 border border-cyan-500/30 px-2 py-0.5 font-mono text-[10px] text-cyan-300">
                  CONFIDENCE: {selectedBundle.confidence}%
                </span>
                <span className="rounded bg-rose-500/20 border border-rose-500/30 px-2 py-0.5 font-mono text-[10px] font-bold text-rose-300">
                  {selectedBundle.impactScore}
                </span>
              </div>
              <h3 className="mt-2 text-lg font-bold text-white sm:text-xl">{selectedBundle.claim}</h3>
              <p className="mt-1 font-mono text-xs text-slate-300">Target: {selectedBundle.entity}</p>
            </div>

            <div className="text-right font-mono text-xs">
              <span className="text-slate-300 block text-[10px]">OBSERVATION TIMESTAMP</span>
              <span className="text-slate-200 block mt-0.5">{selectedBundle.observedAt}</span>
            </div>
          </div>

          {/* Raw Payload Section */}
          <div>
            <div className="flex items-center justify-between font-mono text-xs text-slate-300 mb-2">
              <span>RAW SOCKET / DNS TELEMETRY CAPTURE</span>
              <span>SOURCE: {selectedBundle.upstreamSource}</span>
            </div>
            <pre className="rounded-2xl border border-white/[0.08] bg-[#02050b] p-5 font-mono text-xs text-slate-300 overflow-x-auto leading-relaxed whitespace-pre-wrap">
              {selectedBundle.rawPayload}
            </pre>
          </div>

          {/* Checksum Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 font-mono text-xs">
            <div className="truncate w-full sm:w-auto">
              <span className="text-slate-300 uppercase block text-[10px]">Cryptographic Checksum (SHA-256)</span>
              <span className="text-cyan-400 truncate block mt-0.5">{selectedBundle.sha256}</span>
            </div>

            <button
              onClick={handleCopyHash}
              className="rounded-lg bg-white/[0.05] border border-white/[0.1] px-3 py-1.5 text-slate-300 hover:text-white hover:bg-white/[0.1] transition-all shrink-0"
            >
              {copied ? "Copied ✓" : "Copy Hash"}
            </button>
          </div>

          <div className="pt-2 text-right">
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-2.5 font-mono text-xs font-bold text-slate-950 hover:bg-cyan-400 transition"
            >
              <span>Export Evidence for Reports</span>
              <span>&rarr;</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
