"use client";

import React, { useEffect, useState, useRef } from "react";
import { usePathname } from "next/navigation";
import {
  DockerIcon,
  KubernetesIcon,
  AwsIcon,
  CloudflareIcon,
  GitHubIcon,
  PythonIcon,
  ReactIcon,
  NextJsIcon,
  TypeScriptIcon,
  PostgresIcon,
  RedisIcon,
  GraphQLIcon,
  LinuxIcon,
  CyberShieldIcon,
  TlsLockIcon,
  DnsIcon,
  ApiNetworkIcon,
  BountyBugIcon,
} from "./TechIcons";

interface TechNode {
  id: string;
  name: string;
  category: string;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
  xPercent: number;
  yPercent: number;
  zDepth: number;
  scale: number;
  floatDelay: string;
  floatDuration: string;
}

const TECH_NODES: TechNode[] = [
  // Top Layer
  { id: "docker", name: "Docker", category: "Ingestion Fleet", icon: DockerIcon, accentColor: "#0db7ed", xPercent: 12, yPercent: 12, zDepth: 40, scale: 1.0, floatDelay: "0s", floatDuration: "6.2s" },
  { id: "k8s", name: "Kubernetes", category: "Cluster Ingress", icon: KubernetesIcon, accentColor: "#326ce5", xPercent: 34, yPercent: 8, zDepth: 70, scale: 1.05, floatDelay: "1.2s", floatDuration: "7.1s" },
  { id: "aws", name: "AWS Cloud", category: "Compute Mesh", icon: AwsIcon, accentColor: "#ff9900", xPercent: 62, yPercent: 10, zDepth: 30, scale: 0.98, floatDelay: "0.5s", floatDuration: "6.8s" },
  { id: "cloudflare", name: "Cloudflare", category: "WAF & Edge", icon: CloudflareIcon, accentColor: "#f38020", xPercent: 84, yPercent: 14, zDepth: 60, scale: 1.02, floatDelay: "2.1s", floatDuration: "5.9s" },

  // Mid-Upper Layer
  { id: "python", name: "Python", category: "Temporal Diffing", icon: PythonIcon, accentColor: "#3776ab", xPercent: 6, yPercent: 32, zDepth: 50, scale: 1.0, floatDelay: "1.8s", floatDuration: "6.5s" },
  { id: "shield", name: "Safe Harbor", category: "Zero Weaponization", icon: CyberShieldIcon, accentColor: "#10b981", xPercent: 24, yPercent: 26, zDepth: 80, scale: 1.08, floatDelay: "0.2s", floatDuration: "7.4s" },
  { id: "dns", name: "DNS RFC 1035", category: "Zone Surveillance", icon: DnsIcon, accentColor: "#06b6d4", xPercent: 74, yPercent: 28, zDepth: 45, scale: 0.96, floatDelay: "2.7s", floatDuration: "6.0s" },
  { id: "github", name: "GitHub", category: "VCS Telemetry", icon: GitHubIcon, accentColor: "#24292e", xPercent: 91, yPercent: 36, zDepth: 35, scale: 0.94, floatDelay: "0.9s", floatDuration: "6.7s" },

  // Mid-Center Layer
  { id: "nextjs", name: "Next.js 15", category: "Edge SSR", icon: NextJsIcon, accentColor: "#0f172a", xPercent: 18, yPercent: 50, zDepth: 20, scale: 0.92, floatDelay: "3.1s", floatDuration: "7.8s" },
  { id: "graphql", name: "GraphQL", category: "Schema Drift", icon: GraphQLIcon, accentColor: "#e10098", xPercent: 82, yPercent: 48, zDepth: 65, scale: 1.03, floatDelay: "1.4s", floatDuration: "6.3s" },

  // Mid-Lower Layer
  { id: "postgres", name: "PostgreSQL", category: "Data Truth", icon: PostgresIcon, accentColor: "#336791", xPercent: 8, yPercent: 68, zDepth: 55, scale: 1.0, floatDelay: "2.4s", floatDuration: "6.6s" },
  { id: "redis", name: "Redis", category: "In-Memory RQ", icon: RedisIcon, accentColor: "#dc382d", xPercent: 28, yPercent: 72, zDepth: 40, scale: 0.97, floatDelay: "0.7s", floatDuration: "5.8s" },
  { id: "typescript", name: "TypeScript", category: "Strict Contracts", icon: TypeScriptIcon, accentColor: "#3178c6", xPercent: 70, yPercent: 66, zDepth: 50, scale: 0.99, floatDelay: "1.9s", floatDuration: "7.0s" },
  { id: "api", name: "REST API", category: "Live Feeds", icon: ApiNetworkIcon, accentColor: "#6366f1", xPercent: 90, yPercent: 68, zDepth: 60, scale: 1.01, floatDelay: "0.3s", floatDuration: "6.1s" },

  // Bottom Layer
  { id: "tls", name: "TLS 1.3 / CT", category: "Certificate Logs", icon: TlsLockIcon, accentColor: "#8b5cf6", xPercent: 14, yPercent: 86, zDepth: 75, scale: 1.04, floatDelay: "2.8s", floatDuration: "7.3s" },
  { id: "react", name: "React 19", category: "Spatial UI", icon: ReactIcon, accentColor: "#61dafb", xPercent: 42, yPercent: 88, zDepth: 35, scale: 0.95, floatDelay: "1.1s", floatDuration: "6.4s" },
  { id: "linux", name: "Linux Core", category: "Raw Sockets", icon: LinuxIcon, accentColor: "#f59e0b", xPercent: 60, yPercent: 86, zDepth: 45, scale: 0.98, floatDelay: "0.6s", floatDuration: "6.9s" },
  { id: "bounty", name: "Bounty Radar", category: "2,010 Scopes", icon: BountyBugIcon, accentColor: "#f43f5e", xPercent: 85, yPercent: 88, zDepth: 70, scale: 1.02, floatDelay: "2.3s", floatDuration: "6.5s" },
];

export default function WhiteAesthetic3DBackground() {
  const [mouseOffset, setMouseOffset] = useState({ x: 0, y: 0 });
  const [isWhiteAesthetic, setIsWhiteAesthetic] = useState(true);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Monitor theme changes
  useEffect(() => {
    const checkTheme = () => {
      if (typeof document !== "undefined") {
        const isWhite =
          document.documentElement.classList.contains("theme-white-aesthetic") ||
          document.documentElement.dataset.theme === "white-aesthetic" ||
          !document.documentElement.classList.contains("dark");
        setIsWhiteAesthetic(isWhite);
      }
    };

    checkTheme();
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class", "data-theme"] });
    return () => observer.disconnect();
  }, []);

  // Smooth mouse parallax
  useEffect(() => {
    let animFrame: number;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const handlePointerMove = (e: MouseEvent) => {
      const { innerWidth, innerHeight } = window;
      targetX = (e.clientX / innerWidth - 0.5) * 35; // max 35px parallax
      targetY = (e.clientY / innerHeight - 0.5) * 25; // max 25px parallax
    };

    const updatePhysics = () => {
      currentX += (targetX - currentX) * 0.05;
      currentY += (targetY - currentY) * 0.05;
      setMouseOffset({ x: currentX, y: currentY });
      animFrame = requestAnimationFrame(updatePhysics);
    };

    window.addEventListener("mousemove", handlePointerMove, { passive: true });
    animFrame = requestAnimationFrame(updatePhysics);

    return () => {
      window.removeEventListener("mousemove", handlePointerMove);
      cancelAnimationFrame(animFrame);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={`fixed inset-0 pointer-events-none z-0 overflow-hidden transition-colors duration-700 ${
        isWhiteAesthetic
          ? "bg-[#f8fafc] text-slate-800"
          : "bg-[#02050b] text-slate-100"
      }`}
      style={{ perspective: "1200px" }}
      aria-hidden="true"
    >
      {/* ── 1. AMBIENT 3D RADIAL SPOTLIGHTS ─────────────────────── */}
      <div
        className={`absolute inset-0 transition-opacity duration-1000 ${
          isWhiteAesthetic ? "opacity-100" : "opacity-80"
        }`}
      >
        {/* Soft Cyan Ambient Glow */}
        <div
          className="absolute -top-32 -left-32 w-[600px] h-[600px] rounded-full blur-[140px] pointer-events-none transition-transform duration-700 ease-out"
          style={{
            background: isWhiteAesthetic
              ? "radial-gradient(circle, rgba(6, 182, 212, 0.14) 0%, rgba(255, 255, 255, 0) 70%)"
              : "radial-gradient(circle, rgba(6, 182, 212, 0.20) 0%, rgba(0, 0, 0, 0) 70%)",
            transform: `translate3d(${mouseOffset.x * 1.2}px, ${mouseOffset.y * 1.2}px, 0)`,
          }}
        />

        {/* Soft Electric Blue Ambient Glow */}
        <div
          className="absolute top-1/3 -right-32 w-[700px] h-[700px] rounded-full blur-[150px] pointer-events-none transition-transform duration-700 ease-out"
          style={{
            background: isWhiteAesthetic
              ? "radial-gradient(circle, rgba(59, 130, 246, 0.12) 0%, rgba(255, 255, 255, 0) 70%)"
              : "radial-gradient(circle, rgba(139, 92, 246, 0.18) 0%, rgba(0, 0, 0, 0) 70%)",
            transform: `translate3d(${-mouseOffset.x * 0.8}px, ${-mouseOffset.y * 0.8}px, 0)`,
          }}
        />

        {/* Soft Platinum / Violet Floor Spotlight */}
        <div
          className="absolute -bottom-40 left-1/3 w-[800px] h-[600px] rounded-full blur-[160px] pointer-events-none"
          style={{
            background: isWhiteAesthetic
              ? "radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, rgba(255, 255, 255, 0) 70%)"
              : "radial-gradient(circle, rgba(6, 182, 212, 0.15) 0%, rgba(0, 0, 0, 0) 70%)",
          }}
        />
      </div>

      {/* ── 2. PERSPECTIVE 3D GRID FLOOR ────────────────────────── */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          transform: `rotateX(55deg) translate3d(${mouseOffset.x * 0.4}px, ${mouseOffset.y * 0.4 + 100}px, -100px)`,
          transformOrigin: "bottom center",
          backgroundImage: isWhiteAesthetic
            ? `linear-gradient(to right, rgba(148, 163, 184, 0.15) 1px, transparent 1px),
               linear-gradient(to bottom, rgba(148, 163, 184, 0.15) 1px, transparent 1px)`
            : `linear-gradient(to right, rgba(255, 255, 255, 0.05) 1px, transparent 1px),
               linear-gradient(to bottom, rgba(255, 255, 255, 0.05) 1px, transparent 1px)`,
          backgroundSize: "64px 64px",
          maskImage: "radial-gradient(ellipse 80% 60% at 50% 60%, black 20%, transparent 80%)",
          WebkitMaskImage: "radial-gradient(ellipse 80% 60% at 50% 60%, black 20%, transparent 80%)",
        }}
      />

      {/* ── 3. SVG CIRCUIT CONNECTION STREAM ───────────────────── */}
      <svg className="absolute inset-0 h-full w-full pointer-events-none opacity-40">
        <defs>
          <linearGradient id="circuitGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={isWhiteAesthetic ? "#06b6d4" : "#00f0ff"} stopOpacity="0.4" />
            <stop offset="50%" stopColor={isWhiteAesthetic ? "#3b82f6" : "#8b5cf6"} stopOpacity="0.25" />
            <stop offset="100%" stopColor={isWhiteAesthetic ? "#8b5cf6" : "#00f0ff"} stopOpacity="0.4" />
          </linearGradient>
        </defs>

        <path
          d="M 120 120 Q 300 80, 480 140 T 800 120 T 1150 160"
          stroke="url(#circuitGrad)"
          strokeWidth="1.2"
          fill="none"
          strokeDasharray="4 6"
        />
        <path
          d="M 150 450 Q 400 380, 700 480 T 1100 420"
          stroke="url(#circuitGrad)"
          strokeWidth="1.2"
          fill="none"
          strokeDasharray="5 5"
        />
        <path
          d="M 200 850 Q 550 780, 850 860 T 1200 820"
          stroke="url(#circuitGrad)"
          strokeWidth="1.2"
          fill="none"
          strokeDasharray="4 6"
        />
      </svg>

      {/* ── 4. 18 FLOATING 3D MODERN TECH CARDS ─────────────────── */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          transform: `rotateX(${-mouseOffset.y * 0.12}deg) rotateY(${mouseOffset.x * 0.12}deg)`,
          transformStyle: "preserve-3d",
          transition: "transform 0.1s ease-out",
        }}
      >
        {TECH_NODES.map((tech) => {
          const IconComponent = tech.icon;
          const parallaxX = (mouseOffset.x * tech.zDepth) / 100;
          const parallaxY = (mouseOffset.y * tech.zDepth) / 100;

          return (
            <div
              key={tech.id}
              className="absolute select-none pointer-events-none transition-all duration-300"
              style={{
                left: `${tech.xPercent}%`,
                top: `${tech.yPercent}%`,
                transform: `translate3d(${parallaxX}px, ${parallaxY}px, ${tech.zDepth}px) scale(${tech.scale})`,
                animation: `floatKeyframe ${tech.floatDuration} ease-in-out infinite alternate`,
                animationDelay: tech.floatDelay,
              }}
            >
              <div
                className={`flex items-center gap-2.5 rounded-2xl px-3.5 py-2 transition-all duration-300 ${
                  isWhiteAesthetic
                    ? "bg-white/90 border border-slate-200/90 shadow-[0_8px_24px_rgba(15,23,42,0.06),0_1px_2px_rgba(15,23,42,0.04)] backdrop-blur-xl"
                    : "bg-slate-900/75 border border-white/[0.12] shadow-[0_8px_24px_rgba(0,0,0,0.5)] backdrop-blur-xl"
                }`}
              >
                {/* Tech Icon Container */}
                <div
                  className="flex h-7 w-7 items-center justify-center rounded-xl transition-all"
                  style={{
                    backgroundColor: isWhiteAesthetic
                      ? `${tech.accentColor}18`
                      : `${tech.accentColor}25`,
                    borderColor: `${tech.accentColor}40`,
                    borderWidth: "1px",
                  }}
                >
                  <IconComponent className="h-4 w-4" />
                </div>

                {/* Tech Info */}
                <div className="flex flex-col">
                  <span
                    className={`font-mono text-xs font-bold leading-tight tracking-tight ${
                      isWhiteAesthetic ? "text-slate-800" : "text-slate-100"
                    }`}
                  >
                    {tech.name}
                  </span>
                  <span
                    className="font-mono text-[9px] uppercase tracking-widest"
                    style={{ color: tech.accentColor }}
                  >
                    {tech.category}
                  </span>
                </div>

                {/* Subtle Pulse Indicator */}
                <span
                  className="h-1.5 w-1.5 rounded-full animate-pulse ml-1"
                  style={{ backgroundColor: tech.accentColor }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Floating Keyframe Animation Style */}
      <style jsx>{`
        @keyframes floatKeyframe {
          0% {
            transform: translateY(0px) rotate(0deg);
          }
          50% {
            transform: translateY(-10px) rotate(0.5deg);
          }
          100% {
            transform: translateY(6px) rotate(-0.5deg);
          }
        }
      `}</style>
    </div>
  );
}
