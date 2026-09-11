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
  const [mouseOffset, setMouseOffset] = useState({ x: 0, y: 0 });
  // Default dark until ThemeToggle applies a saved preference — avoids a flash of
  // light canvas behind white/cyan auth titles that would make them unreadable.
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

  useEffect(() => {
    let animFrame: number;
    let lastPaint = 0;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const handlePointerMove = (e: MouseEvent) => {
      const { innerWidth, innerHeight } = window;
      targetX = (e.clientX / innerWidth - 0.5) * 35;
      targetY = (e.clientY / innerHeight - 0.5) * 25;
    };

    const updatePhysics = (timestamp: number) => {
      currentX += (targetX - currentX) * 0.05;
      currentY += (targetY - currentY) * 0.05;
      if (timestamp - lastPaint >= 33) {
        lastPaint = timestamp;
        setMouseOffset({ x: currentX, y: currentY });
      }
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
        isWhiteAesthetic ? "bg-[#f8fafc]" : "bg-[#000000]"
      }`}
      style={{ perspective: "1200px" }}
      aria-hidden="true"
    >
      <div
        className={`absolute inset-0 transition-opacity duration-1000 ${
          isWhiteAesthetic ? "opacity-100" : "opacity-80"
        }`}
      >
        <div
          className="absolute -top-32 -left-32 w-[600px] h-[600px] rounded-full blur-[140px] pointer-events-none"
          style={{
            background: isWhiteAesthetic
              ? "radial-gradient(circle, rgba(6, 182, 212, 0.12) 0%, transparent 70%)"
              : "radial-gradient(circle, rgba(6, 182, 212, 0.18) 0%, transparent 70%)",
            transform: `translate3d(${mouseOffset.x * 1.2}px, ${mouseOffset.y * 1.2}px, 0)`,
          }}
        />
        <div
          className="absolute top-1/3 -right-32 w-[700px] h-[700px] rounded-full blur-[150px] pointer-events-none"
          style={{
            background: isWhiteAesthetic
              ? "radial-gradient(circle, rgba(59, 130, 246, 0.10) 0%, transparent 70%)"
              : "radial-gradient(circle, rgba(139, 92, 246, 0.16) 0%, transparent 70%)",
            transform: `translate3d(${-mouseOffset.x * 0.8}px, ${-mouseOffset.y * 0.8}px, 0)`,
          }}
        />
        <div
          className="absolute -bottom-40 left-1/3 w-[800px] h-[600px] rounded-full blur-[160px] pointer-events-none"
          style={{
            background: isWhiteAesthetic
              ? "radial-gradient(circle, rgba(99, 102, 241, 0.06) 0%, transparent 70%)"
              : "radial-gradient(circle, rgba(6, 182, 212, 0.12) 0%, transparent 70%)",
          }}
        />
      </div>

      <div
        className={`absolute inset-0 pointer-events-none transition-opacity duration-500 ${
          isWhiteAesthetic ? "opacity-20" : "opacity-55"
        }`}
        style={{
          transform: `rotateX(55deg) translate3d(${mouseOffset.x * 0.4}px, ${mouseOffset.y * 0.4 + 100}px, -100px)`,
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
