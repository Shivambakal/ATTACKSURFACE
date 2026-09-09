"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { SubscriptionInfo } from "@/lib/types";

export default function ManageSubscriptionPage() {
  const router = useRouter();
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [canceling, setCanceling] = useState(false);
  const [cancelModal, setCancelModal] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    async function fetchSub() {
      setLoading(true);
      try {
        const sub = await apiFetch<SubscriptionInfo>("/api/v1/billing/subscription");
        setSubscription(sub);
      } catch (err: any) {
        setMessage({ type: "error", text: err.message || "Failed to load subscription." });
      } finally {
        setLoading(false);
      }
    }
    fetchSub();
  }, []);

  const handleCancelSubscription = async () => {
    setCanceling(true);
    try {
      const res = await apiFetch<any>("/api/v1/billing/cancel", { method: "POST" });
      setMessage({ type: "success", text: res.message || "Auto-renew has been disabled." });
      setSubscription((prev) => (prev ? { ...prev, cancel_at_period_end: true } : null));
      setCancelModal(false);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to cancel subscription." });
    } finally {
      setCanceling(false);
    }
  };

  const formatDate = (isoStr?: string | null) => {
    if (!isoStr) return "End of billing cycle";
    try {
      return new Date(isoStr).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
        <Link href="/billing" className="hover:text-cyan-400 transition">
          Billing
        </Link>
        <span>/</span>
        <span className="text-white font-semibold">Manage Subscription</span>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 sm:p-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Subscription Management</h1>
          <p className="text-xs text-slate-400 mt-1">
            Review your plan status, renewal schedules, and auto-renewal preferences.
          </p>
        </div>

        {message && (
          <div
            className={`p-4 rounded-xl text-xs ${
              message.type === "success"
                ? "bg-emerald-950/40 border border-emerald-800/60 text-emerald-300"
                : "bg-rose-950/40 border border-rose-800/60 text-rose-300"
            }`}
          >
            {message.text}
          </div>
        )}

        {loading && (
          <div className="flex justify-center items-center py-12">
            <div className="w-6 h-6 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
          </div>
        )}

        {!loading && subscription && (
          <div className="space-y-6">
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-5 space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm font-semibold text-slate-300">Active Tier</span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  {subscription.tier}
                </span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400">Subscription Status</span>
                <span className="font-mono text-emerald-400 font-bold uppercase">{subscription.status}</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400">Current Period Expiration</span>
                <span className="font-mono text-slate-200">{formatDate(subscription.current_period_end)}</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400">Renewal Mode</span>
                <span className="font-mono text-slate-200">
                  {subscription.cancel_at_period_end ? (
                    <span className="text-amber-400">Will Cancel at Period End</span>
                  ) : (
                    <span className="text-emerald-400">Active Auto-Renew</span>
                  )}
                </span>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <Link
                href="/pricing"
                className="flex-1 py-2.5 px-4 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs text-center transition"
              >
                Change Plan
              </Link>
              {subscription.tier.toUpperCase() !== "FREE" && !subscription.cancel_at_period_end && (
                <button
                  onClick={() => setCancelModal(true)}
                  className="py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-rose-950/40 text-slate-300 hover:text-rose-300 font-medium text-xs transition border border-slate-700 hover:border-rose-700"
                >
                  Cancel Auto-Renew
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      {cancelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-4">
            <h3 className="text-lg font-bold text-white">Disable Auto-Renew?</h3>
            <p className="text-xs text-slate-300">
              Your subscription will remain fully active until{" "}
              <span className="font-semibold text-white">{formatDate(subscription?.current_period_end)}</span>. After this date, your account will transition back to the Free Community Tier.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setCancelModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
              >
                Keep Active
              </button>
              <button
                onClick={handleCancelSubscription}
                disabled={canceling}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition disabled:opacity-50"
              >
                {canceling ? "Processing..." : "Confirm Cancellation"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
