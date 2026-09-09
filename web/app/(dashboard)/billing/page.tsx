"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { PaymentTransactionItem, SubscriptionInfo } from "@/lib/types";

export default function BillingPage() {
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [history, setHistory] = useState<PaymentTransactionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadBillingData() {
      setLoading(true);
      setError(null);
      try {
        const [subRes, histRes] = await Promise.allSettled([
          apiFetch<SubscriptionInfo>("/api/v1/billing/subscription"),
          apiFetch<PaymentTransactionItem[]>("/api/v1/billing/history"),
        ]);

        if (subRes.status === "fulfilled") {
          setSubscription(subRes.value);
        } else {
          setError("Failed to load active subscription status.");
        }

        if (histRes.status === "fulfilled" && Array.isArray(histRes.value)) {
          setHistory(histRes.value);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load billing details.");
      } finally {
        setLoading(false);
      }
    }
    loadBillingData();
  }, []);

  const formatDate = (isoStr?: string | null) => {
    if (!isoStr) return "—";
    try {
      return new Date(isoStr).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoStr;
    }
  };

  const getStatusBadge = (status: string, state: string) => {
    const combined = (status || state || "").toUpperCase();
    if (combined === "COMPLETED" || combined === "SUCCESS") {
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
          SUCCESS
        </span>
      );
    }
    if (combined === "FAILED") {
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40">
          FAILED
        </span>
      );
    }
    if (combined === "CANCELED") {
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-500/20 text-slate-400 border border-slate-500/40">
          CANCELED
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40">
        PENDING
      </span>
    );
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto py-4 px-2 sm:px-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Billing & Subscription</h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Manage your researcher entitlement, plan limits, and verified payment history.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/pricing"
            className="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs transition shadow-sm"
          >
            Upgrade / Change Plan
          </Link>
          <Link
            href="/billing/manage"
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs transition border border-slate-700"
          >
            Manage Subscription
          </Link>
        </div>
      </div>

      {loading && (
        <div className="flex justify-center items-center py-20">
          <div className="flex items-center gap-3 text-slate-400 font-mono text-sm">
            <div className="w-4 h-4 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
            <span>Loading billing information...</span>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {!loading && subscription && (
        <>
          {/* Subscription Overview Card */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <span className="text-xl font-bold text-white">
                    {subscription.plan?.name || subscription.tier} Plan
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 uppercase">
                    {subscription.tier}
                  </span>
                  {subscription.is_verified_payment ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      VERIFIED PAYMENT
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-800 text-slate-400 border border-slate-700">
                      COMMUNITY TIER
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400">
                  Provider: <span className="font-mono text-slate-300">{subscription.provider}</span> • Status:{" "}
                  <span className="font-mono text-emerald-400">{subscription.status}</span>
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
                <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-3">
                  <div className="text-slate-400 text-[10px] font-mono uppercase">Targets Limit</div>
                  <div className="text-base font-bold text-white mt-0.5">
                    {subscription.plan?.limits?.max_targets ?? 50}
                  </div>
                </div>
                <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-3">
                  <div className="text-slate-400 text-[10px] font-mono uppercase">Max Export Rows</div>
                  <div className="text-base font-bold text-white mt-0.5">
                    {(subscription.plan?.limits?.max_export_rows ?? 500).toLocaleString()}
                  </div>
                </div>
                <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-3 col-span-2 sm:col-span-1">
                  <div className="text-slate-400 text-[10px] font-mono uppercase">Period End</div>
                  <div className="text-xs font-mono font-semibold text-slate-200 mt-1">
                    {formatDate(subscription.current_period_end)}
                  </div>
                </div>
              </div>
            </div>

            {subscription.cancel_at_period_end && (
              <div className="mt-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
                <span>⚠️</span>
                <span>
                  Your subscription will cancel at the end of the current billing period ({formatDate(subscription.current_period_end)}). Auto-renew is disabled.
                </span>
              </div>
            )}
          </div>

          {/* Payment History Table */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">Payment Transaction History</h2>
              <span className="text-xs font-mono text-slate-400">
                {history.length} {history.length === 1 ? "Record" : "Records"}
              </span>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/80 border-b border-slate-800 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Order ID</th>
                      <th className="py-3 px-4">Payment ID</th>
                      <th className="py-3 px-4">Plan / Interval</th>
                      <th className="py-3 px-4">Amount</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Env</th>
                      <th className="py-3 px-4">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {history.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-slate-500">
                          No payment transactions recorded yet.
                        </td>
                      </tr>
                    ) : (
                      history.map((tx) => (
                        <tr key={tx.id} className="hover:bg-slate-800/30 transition">
                          <td className="py-3 px-4 text-cyan-400 font-semibold truncate max-w-[150px]">
                            {tx.order_id}
                          </td>
                          <td className="py-3 px-4 text-slate-300 truncate max-w-[150px]">
                            {tx.payment_id || <span className="text-slate-600">—</span>}
                          </td>
                          <td className="py-3 px-4 text-slate-200">
                            {tx.plan_tier || "RESEARCHER"}{" "}
                            <span className="text-slate-500">({tx.billing_interval || "monthly"})</span>
                          </td>
                          <td className="py-3 px-4 text-white font-bold">
                            ₹{tx.amount_inr?.toLocaleString("en-IN") ?? "0"}
                          </td>
                          <td className="py-3 px-4">
                            {getStatusBadge(tx.status, tx.payment_state)}
                          </td>
                          <td className="py-3 px-4 text-[10px] text-slate-400 uppercase">
                            {tx.environment || "test"}
                          </td>
                          <td className="py-3 px-4 text-slate-400">
                            {formatDate(tx.completed_at || tx.created_at)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
