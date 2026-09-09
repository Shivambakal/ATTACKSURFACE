"use client";

import React, { useEffect, useState } from "react";

interface IntelligenceNetworkProps {
  targets: number;
  changes: number;
  signals: number;
}

const nodes = [
  { label: "domains", x: "14%", y: "30%", delay: "0s", tone: "node-a" },
  { label: "api surface", x: "34%", y: "18%", delay: ".7s", tone: "node-b" },
  { label: "products", x: "55%", y: "38%", delay: "1.2s", tone: "node-c" },
  { label: "technologies", x: "76%", y: "24%", delay: "1.8s", tone: "node-d" },
  { label: "change detected", x: "67%", y: "72%", delay: "2.3s", tone: "node-hot" },
  { label: "research signal", x: "32%", y: "78%", delay: "2.8s", tone: "node-hot" },
];

export default function IntelligenceNetwork({ targets, changes, signals }: IntelligenceNetworkProps) {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handlePointer = (event: PointerEvent) => {
      setTilt({
        x: (event.clientX / window.innerWidth - 0.5) * 8,
        y: (event.clientY / window.innerHeight - 0.5) * -6,
      });
    };
    window.addEventListener("pointermove", handlePointer, { passive: true });
    return () => window.removeEventListener("pointermove", handlePointer);
  }, []);

  return (
    <section className="network-hero" aria-label="Attack surface intelligence network">
      <div className="network-copy">
        <p className="network-kicker"><span className="signal-pulse" /> LIVE SURFACE INTELLIGENCE</p>
        <h2>See what<br /><em>changed.</em></h2>
        <p className="network-deck">Continuous intelligence for the modern attack surface.</p>
        <div className="network-stats">
          <span><strong>{targets}</strong> targets</span>
          <span><strong>{changes}</strong> changes</span>
          <span><strong>{signals}</strong> signals</span>
        </div>
      </div>
      <div className="network-stage" style={{ transform: `perspective(1000px) rotateX(${tilt.y}deg) rotateY(${tilt.x}deg)` }}>
        <div className="network-halo" />
        <div className="network-grid" />
        <div className="network-orbit orbit-one" />
        <div className="network-orbit orbit-two" />
        <svg className="network-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <path d="M14 30 L34 18 L55 38 L76 24 M55 38 L67 72 L32 78 L14 30 M34 18 L32 78" />
          <path className="line-active" d="M67 72 L32 78" />
        </svg>
        {nodes.map((node) => (
          <div key={node.label} className={`network-node ${node.tone}`} style={{ left: node.x, top: node.y, animationDelay: node.delay }}>
            <span className="node-core" />
            <span className="node-label">{node.label}</span>
          </div>
        ))}
        <div className="network-caption"><span>01</span> DISCOVER <i /> OBSERVE <i /> DETECT CHANGE</div>
      </div>
    </section>
  );
}
