"use client";

import { useEffect, useState } from "react";

/**
 * Hook to detect whether reduced motion is requested either by OS setting
 * (prefers-reduced-motion: reduce) or by user preference setting.
 */
export function useReducedMotion(userOverride?: boolean): boolean {
  const [systemReduced, setSystemReduced] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    setSystemReduced(mql.matches);

    const onChange = (e: MediaQueryListEvent) => {
      setSystemReduced(e.matches);
    };

    if (mql.addEventListener) {
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    } else {
      // Fallback for older WebKit
      mql.addListener(onChange);
      return () => mql.removeListener(onChange);
    }
  }, []);

  return userOverride !== undefined ? userOverride : systemReduced;
}
