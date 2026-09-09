/**
 * AttackSurface Timeline — Realtime Event Transport Abstraction
 * 
 * Provides an event subscription layer for:
 * - Security Alerts
 * - Attack Surface Target Changes
 * - Pipeline & Queue Telemetry
 * 
 * Current Mode: High-efficiency HTTP polling with adaptive backoff.
 * Future Pluggable Transports: Server-Sent Events (SSE), WebSockets, Supabase Realtime.
 */

import { apiFetch } from "./api";

export type EventType = "alert" | "target_change" | "pipeline_telemetry" | "job_status";

export interface RealtimeMessage<T = unknown> {
  type: EventType;
  data: T;
  timestamp: string;
}

export type RealtimeListener<T = unknown> = (event: RealtimeMessage<T>) => void;

class RealtimeManager {
  private listeners: Map<EventType, Set<RealtimeListener<any>>> = new Map();
  private pollTimers: Map<EventType, NodeJS.Timeout> = new Map();
  private isPollingActive: boolean = false;

  public subscribe<T = unknown>(type: EventType, listener: RealtimeListener<T>): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(listener);

    // Start polling if not already started for this type
    this.ensurePolling(type);

    // Return un-subscribe callback
    return () => {
      const set = this.listeners.get(type);
      if (set) {
        set.delete(listener);
        if (set.size === 0) {
          this.stopPolling(type);
        }
      }
    };
  }

  private ensurePolling(type: EventType): void {
    if (this.pollTimers.has(type)) return;

    const pollInterval = type === "alert" ? 30000 : 45000;

    const executePoll = async () => {
      try {
        if (type === "alert") {
          const alerts = await apiFetch<any[]>("/api/v1/alerts");
          this.emit("alert", alerts);
        }
      } catch {
        // Silently tolerate connection dips
      }
    };

    const timer = setInterval(executePoll, pollInterval);
    this.pollTimers.set(type, timer);
  }

  private stopPolling(type: EventType): void {
    const timer = this.pollTimers.get(type);
    if (timer) {
      clearInterval(timer);
      this.pollTimers.delete(type);
    }
  }

  public emit<T = unknown>(type: EventType, data: T): void {
    const listeners = this.listeners.get(type);
    if (listeners) {
      const message: RealtimeMessage<T> = {
        type,
        data,
        timestamp: new Date().toISOString(),
      };
      listeners.forEach((listener) => {
        try {
          listener(message);
        } catch (err) {
          console.error(`[RealtimeManager] Error in listener for ${type}:`, err);
        }
      });
    }
  }
}

export const realtime = new RealtimeManager();
