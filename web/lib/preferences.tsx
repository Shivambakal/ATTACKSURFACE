"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";

export type VisualDensity = "comfortable" | "compact" | "dense";
export type AtmosphereMode = "aurora" | "data_field" | "deep_space" | "grid" | "particle_network" | "minimal" | "off";
export type AnimationIntensity = "full" | "reduced" | "minimal";
export type ThreeDIntensity = "high" | "low" | "off";
export type SidebarMode = "expanded" | "collapsed";
export type PriorityZone = "CRITICAL" | "HIGH" | "WATCH" | "BACKGROUND";

export interface UserPreferences {
  visualDensity: VisualDensity;
  atmosphere: AtmosphereMode;
  animationIntensity: AnimationIntensity;
  threeDIntensity: ThreeDIntensity;
  sidebarMode: SidebarMode;
  soundEnabled: boolean;
  liveMode: boolean;
  companyPriorities: Record<string, PriorityZone>;
  pinnedCompanies: string[];
  defaultTimeRange: "ALL" | "1Y" | "6M" | "3M" | "1M";
}

const DEFAULT_PREFERENCES: UserPreferences = {
  visualDensity: "comfortable",
  atmosphere: "aurora",
  animationIntensity: "full",
  threeDIntensity: "high",
  sidebarMode: "expanded",
  soundEnabled: false,
  liveMode: true,
  companyPriorities: {},
  pinnedCompanies: [],
  defaultTimeRange: "ALL",
};

interface PreferencesContextType {
  preferences: UserPreferences;
  updatePreferences: (patch: Partial<UserPreferences>) => Promise<void>;
  setCompanyPriority: (companyId: string | number, priority: PriorityZone) => Promise<void>;
  togglePinCompany: (companyId: string | number) => Promise<void>;
  toggleLiveMode: () => void;
  toggleSound: () => void;
  loading: boolean;
}

const PreferencesContext = createContext<PreferencesContextType>({
  preferences: DEFAULT_PREFERENCES,
  updatePreferences: async () => {},
  setCompanyPriority: async () => {},
  togglePinCompany: async () => {},
  toggleLiveMode: () => {},
  toggleSound: () => {},
  loading: true,
});

const STORAGE_KEY = "ast_workspace_preferences_v2";

export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFERENCES);
  const [loading, setLoading] = useState<boolean>(true);

  // Load preferences from localStorage first (fast render), then sync from API profile handles
  useEffect(() => {
    let initial = DEFAULT_PREFERENCES;
    try {
      const cached = window.localStorage.getItem(STORAGE_KEY);
      if (cached) {
        initial = { ...DEFAULT_PREFERENCES, ...JSON.parse(cached) };
        setPreferences(initial);
      }
    } catch {
      // Ignore localStorage parse error
    }

    // Reflect density and atmosphere in document attributes
    if (typeof document !== "undefined") {
      document.documentElement.dataset.density = initial.visualDensity;
      document.documentElement.dataset.atmosphere = initial.atmosphere;
      document.documentElement.dataset.motion = initial.animationIntensity;
    }

    // Background sync from backend profile handles
    const syncFromProfile = async () => {
      try {
        const profile = await apiFetch<any>("/api/v1/profile");
        if (profile && profile.handles && profile.handles.preferences) {
          const serverPrefs = profile.handles.preferences;
          const merged: UserPreferences = {
            ...initial,
            ...serverPrefs,
            companyPriorities: {
              ...(initial.companyPriorities || {}),
              ...(profile.handles.priorities || serverPrefs.companyPriorities || {}),
            },
          };
          setPreferences(merged);
          window.localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
          document.documentElement.dataset.density = merged.visualDensity;
          document.documentElement.dataset.atmosphere = merged.atmosphere;
          document.documentElement.dataset.motion = merged.animationIntensity;
        }
      } catch {
        // Fall back to localStorage if offline/guest
      } finally {
        setLoading(false);
      }
    };

    syncFromProfile();
  }, []);

  const persist = useCallback(async (newPrefs: UserPreferences) => {
    setPreferences(newPrefs);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(newPrefs));
      if (typeof document !== "undefined") {
        document.documentElement.dataset.density = newPrefs.visualDensity;
        document.documentElement.dataset.atmosphere = newPrefs.atmosphere;
        document.documentElement.dataset.motion = newPrefs.animationIntensity;
      }

      // Persist to backend UserProfile.handles["preferences"] and ["priorities"]
      await apiFetch("/api/v1/profile", {
        method: "PUT",
        body: JSON.stringify({
          handles: {
            preferences: {
              visualDensity: newPrefs.visualDensity,
              atmosphere: newPrefs.atmosphere,
              animationIntensity: newPrefs.animationIntensity,
              threeDIntensity: newPrefs.threeDIntensity,
              sidebarMode: newPrefs.sidebarMode,
              soundEnabled: newPrefs.soundEnabled,
              liveMode: newPrefs.liveMode,
              pinnedCompanies: newPrefs.pinnedCompanies,
              defaultTimeRange: newPrefs.defaultTimeRange,
            },
            priorities: newPrefs.companyPriorities,
          },
        }),
      }).catch(() => {
        // Safe silent fallback if network or endpoint unavailable
      });
    } catch {
      // localStorage failure fallback
    }
  }, []);

  const updatePreferences = useCallback(
    async (patch: Partial<UserPreferences>) => {
      const next = { ...preferences, ...patch };
      await persist(next);
    },
    [preferences, persist]
  );

  const setCompanyPriority = useCallback(
    async (companyId: string | number, priority: PriorityZone) => {
      const nextPriorities = {
        ...preferences.companyPriorities,
        [String(companyId)]: priority,
      };
      await updatePreferences({ companyPriorities: nextPriorities });
    },
    [preferences, updatePreferences]
  );

  const togglePinCompany = useCallback(
    async (companyId: string | number) => {
      const idStr = String(companyId);
      const isPinned = preferences.pinnedCompanies.includes(idStr);
      const nextPinned = isPinned
        ? preferences.pinnedCompanies.filter((id) => id !== idStr)
        : [...preferences.pinnedCompanies, idStr];
      await updatePreferences({ pinnedCompanies: nextPinned });
    },
    [preferences, updatePreferences]
  );

  const toggleLiveMode = useCallback(() => {
    updatePreferences({ liveMode: !preferences.liveMode });
  }, [preferences.liveMode, updatePreferences]);

  const toggleSound = useCallback(() => {
    updatePreferences({ soundEnabled: !preferences.soundEnabled });
  }, [preferences.soundEnabled, updatePreferences]);

  return (
    <PreferencesContext.Provider
      value={{
        preferences,
        updatePreferences,
        setCompanyPriority,
        togglePinCompany,
        toggleLiveMode,
        toggleSound,
        loading,
      }}
    >
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences() {
  return useContext(PreferencesContext);
}
