"use client";

import React, { useEffect, useState, useRef } from "react";

function readIsWhiteTheme(): boolean {
  if (typeof document === "undefined") return false;
  return (
    document.documentElement.classList.contains("theme-white-aesthetic") ||
    document.documentElement.dataset.theme === "white-aesthetic"
  );
}

export default function WhiteAesthetic3DBackground() {
  const [isWhiteAesthetic, setIsWhiteAesthetic] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const checkTheme = () => setIsWhiteAesthetic(readIsWhiteTheme());
    checkTheme();
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class", "data-theme"],
    });
    return () => observer.disconnect();
  }, []);

  // High-performance GPU-only mouse parallax without React re-renders
  useEffect(() => {
    let animFrame: number | null = null;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;
    let isRunning = false;

    const applyPhysics = () => {
      currentX += (targetX - currentX) * 0.06;
      currentY += (targetY - currentY) * 0.06;

      if (containerRef.current) {
        containerRef.current.style.setProperty("--mx", `${currentX.toFixed(2)}px`);
        containerRef.current.style.setProperty("--my", `${currentY.toFixed(2)}px`);
      }

      // If close to target, stop loop to save 100% CPU/battery
      if (Math.abs(targetX - currentX) < 0.02 && Math.abs(targetY - currentY) < 0.02) {
        isRunning = false;
        animFrame = null;
        return;
      }

      animFrame = requestAnimationFrame(applyPhysics);
    };

    const handlePointerMove = (e: MouseEvent) => {
      const { innerWidth, innerHeight } = window;
      targetX = (e.clientX / innerWidth - 0.5) * 35;
      targetY = (e.clientY / innerHeight - 0.5) * 25;

      if (!isRunning) {
        isRunning = true;
        animFrame = requestAnimationFrame(applyPhysics);
      }
    };

    window.addEventListener("mousemove", handlePointerMove, { passive: true });

    return () => {
      window.removeEventListener("mousemove", handlePointerMove);
      if (animFrame !== null) {
        cancelAnimationFrame(animFrame);
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={`fixed inset-0 pointer-events-none z-0 overflow-hidden transition-colors duration-700 ${
        isWhiteAesthetic ? "bg-[#f8fafc]" : "bg-[#000000]"
      }`}
      style={{
        perspective: "1200px",
        // Default CSS variable fallbacks
        ["--mx" as any]: "0px",
        ["--my" as any]: "0px",
      }}
      aria-hidden="true"
    >
      <div
        className={`absolute inset-0 transition-opacity duration-1000 ${
          isWhiteAesthetic ? "opacity-100" : "opacity-80"
        }`}
      >
        <div
          className="absolute -top-32 -left-32 w-[600px] h-[600px] rounded-full blur-[120px] pointer-events-none will-change-transform"
          style={{
            background: isWhiteAesthetic
              ? "radial-gradient(circle, rgba(6, 182, 212, 0.12) 0%, transparent 70%)"
              : "radial-gradient(circle, rgba(6, 182, 212, 0.18) 0%, transparent 70%)",
            transform: "translate3d(calc(var(--mx) * 1.2), calc(var(--my) * 1.2), 0)",
          }}
        />
        <div
          className="absolute top-1/3 -right-32 w-[700px] h-[700px] rounded-full blur-[130px] pointer-events-none will-change-transform"
          style={{
            background: isWhiteAesthetic
              ? "radial-gradient(circle, rgba(59, 130, 246, 0.10) 0%, transparent 70%)"
              : "radial-gradient(circle, rgba(139, 92, 246, 0.16) 0%, transparent 70%)",
            transform: "translate3d(calc(var(--mx) * -0.8), calc(var(--my) * -0.8), 0)",
          }}
        />
        <div
          className="absolute -bottom-40 left-1/3 w-[800px] h-[600px] rounded-full blur-[140px] pointer-events-none will-change-transform"
          style={{
            background: isWhiteAesthetic
              ? "radial-gradient(circle, rgba(99, 102, 241, 0.06) 0%, transparent 70%)"
              : "radial-gradient(circle, rgba(6, 182, 212, 0.12) 0%, transparent 70%)",
          }}
        />
      </div>

      <div
        className={`absolute inset-0 pointer-events-none transition-opacity duration-500 will-change-transform ${
          isWhiteAesthetic ? "opacity-20" : "opacity-55"
        }`}
        style={{
          transform: "rotateX(55deg) translate3d(calc(var(--mx) * 0.4), calc(var(--my) * 0.4 + 100px), -100px)",
          transformOrigin: "bottom center",
          backgroundImage: isWhiteAesthetic
            ? `linear-gradient(to right, rgba(148, 163, 184, 0.10) 1px, transparent 1px),
               linear-gradient(to bottom, rgba(148, 163, 184, 0.10) 1px, transparent 1px)`
            : `linear-gradient(to right, rgba(255, 255, 255, 0.035) 1px, transparent 1px),
               linear-gradient(to bottom, rgba(255, 255, 255, 0.035) 1px, transparent 1px)`,
          backgroundSize: "64px 64px",
          maskImage: "radial-gradient(ellipse 80% 60% at 50% 60%, black 20%, transparent 80%)",
          WebkitMaskImage: "radial-gradient(ellipse 80% 60% at 50% 60%, black 20%, transparent 80%)",
        }}
      />
    </div>
  );
}
