"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { BillingPlan, SubscriptionInfo } from "@/lib/types";

interface PlansResponse {
  configured: boolean;
  environment: string;
  status_label: string;
  currency: string;
  has_yearly_billing: boolean;
  plans: BillingPlan[];
}

export default function PricingPage() {
  const [plansData, setPlansData] = useState<PlansResponse | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [interval, setInterval] = useState<"monthly" | "yearly">("monthly");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPricing() {
      setLoading(true);
      setError(null);
      try {
        const [plansRes, subRes] = await Promise.allSettled([
          apiFetch<PlansResponse>("/api/v1/billing/plans"),
          apiFetch<SubscriptionInfo>("/api/v1/billing/subscription"),
        ]);

        if (plansRes.status === "fulfilled") {
          setPlansData(plansRes.value);
        } else {
          setError("Unable to load billing plans. Please check gateway connection.");
        }

        if (subRes.status === "fulfilled") {
          setSubscription(subRes.value);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load pricing information");
      } finally {
        setLoading(false);
      }
    }
    loadPricing();
  }, []);

  const currentTier = subscription?.tier?.toUpperCase() || "FREE";

  return (
    <div className="space-y-8 max-w-7xl mx-auto py-4 px-2 sm:px-4">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-mono font-semibold">
          <span>RESEARCH MONETIZATION & ACCESS</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
          Transparent, Researcher-Grade Pricing
        </h1>
        <p className="text-slate-400 max-w-2xl mx-auto text-sm sm:text-base">
          Access official CISA KEV feeds, continuous attack surface delta tracking, multi-source consensus, and complete export intelligence.
        </p>

        {/* Environment Badge */}
        {plansData && (
          <div className="flex justify-center items-center gap-2 pt-1">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium ${
                plansData.environment === "live"
                  ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                  : plansData.environment === "test"
                  ? "bg-amber-500/10 border border-amber-500/30 text-amber-400"
                  : "bg-slate-800 border border-slate-700 text-slate-400"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  plansData.environment === "live"
                    ? "bg-emerald-400 animate-pulse"
                    : plansData.environment === "test"
                    ? "bg-amber-400 animate-pulse"
                    : "bg-slate-500"
                }`}
              />
              {plansData.status_label}
            </span>
          </div>
        )}

        {/* Billing Interval Toggle */}
        <div className="pt-4 flex justify-center items-center">
          <div className="inline-flex items-center p-1 bg-slate-900 border border-slate-800 rounded-xl">
            <button
              onClick={() => setInterval("monthly")}
              className={`px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition ${
                interval === "monthly"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Monthly Billing
            </button>
            <button
              onClick={() => setInterval("yearly")}
              className={`px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition flex items-center gap-2 ${
                interval === "yearly"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <span>Yearly Billing</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider">
                Save ~17%
              </span>
            </button>
          </div>
        </div>
      </div>

      {loading && (
        <div className="flex justify-center items-center py-20">
          <div className="flex items-center gap-3 text-slate-400 font-mono text-sm">
            <div className="w-4 h-4 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
            <span>Loading billing catalog...</span>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm max-w-xl mx-auto text-center">
          {error}
        </div>
      )}

      {/* Pricing Cards Grid */}
      {!loading && plansData?.plans && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {plansData.plans.map((plan) => {
            const isCurrent = currentTier === plan.tier.toUpperCase();
            const isPro = plan.tier.toUpperCase() === "PRO";
            const price =
              interval === "yearly"
                ? plan.yearly_price_inr ?? plan.monthly_price_inr * 12
                : plan.monthly_price_inr;
            const savings = interval === "yearly" ? plan.savings_inr : 0;

            return (
              <div
                key={plan.tier}
                className={`relative flex flex-col rounded-2xl border transition-all duration-200 ${
                  isPro
                    ? "bg-slate-900/90 border-cyan-500/50 shadow-[0_0_30px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500/30"
                    : "bg-slate-900/50 border-slate-800 hover:border-slate-700"
                }`}
              >
                {isPro && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 text-[10px] font-mono font-bold tracking-wider uppercase shadow-md">
                    MOST POPULAR
                  </div>
                )}

                <div className="p-6 flex-1 flex flex-col">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-bold text-white">{plan.name}</h3>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">
                        {plan.limits.max_targets} Targets Included
                      </p>
                    </div>
                    {isCurrent && (
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                        ACTIVE
                      </span>
                    )}
                  </div>

                  {/* Price */}
                  <div className="my-4">
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-extrabold text-white tracking-tight">
                        ₹{price.toLocaleString("en-IN")}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        /{interval === "yearly" ? "yr" : "mo"}
                      </span>
                    </div>
                    {interval === "yearly" && savings && savings > 0 ? (
                      <p className="text-[11px] font-mono text-emerald-400 mt-1">
                        Save ₹{savings.toLocaleString("en-IN")} annually
                      </p>
                    ) : (
                      <p className="text-[11px] text-slate-500 font-mono mt-1">
                        Billed {interval}
                      </p>
                    )}
                  </div>

                  {/* CTA Button */}
                  <div className="my-3">
                    {isCurrent ? (
                      <button
                        disabled
                        className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold text-slate-400 bg-slate-800/80 border border-slate-700 cursor-default"
                      >
                        Current Plan
                      </button>
                    ) : plan.tier.toUpperCase() === "FREE" ? (
                      <Link
                        href="/billing"
                        className="block w-full py-2.5 px-4 rounded-xl text-xs font-semibold text-center text-slate-300 bg-slate-800 hover:bg-slate-700 transition border border-slate-700"
                      >
                        Free Tier
                      </Link>
                    ) : (
                      <Link
                        href={`/billing/checkout?plan=${plan.tier.toLowerCase()}&interval=${interval}`}
                        className={`block w-full py-2.5 px-4 rounded-xl text-xs font-semibold text-center transition shadow-sm ${
                          isPro
                            ? "bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold shadow-[0_0_15px_rgba(6,182,212,0.3)]"
                            : "bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 hover:border-slate-600"
                        }`}
                      >
                        Upgrade to {plan.name}
                      </Link>
                    )}
                  </div>

                  {/* Feature Checklist */}
                  <div className="mt-6 space-y-2.5 border-t border-slate-800/80 pt-4 flex-1">
                    <p className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-bold">
                      Features Included:
                    </p>
                    <ul className="space-y-2 text-xs text-slate-300">
                      {plan.features.map((feat, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <svg
                            className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                          <span className="leading-tight">{feat}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Limits summary */}
                  <div className="mt-4 pt-3 border-t border-slate-800/60 text-[11px] font-mono text-slate-400 space-y-1">
                    <div className="flex justify-between">
                      <span>Export Formats:</span>
                      <span className="text-slate-300">{plan.limits.export_formats.join(", ")}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Max Export Rows:</span>
                      <span className="text-slate-300">{plan.limits.max_export_rows.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Bottom Trust & Verification Note */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-slate-400">
        <div className="space-y-1">
          <h4 className="font-semibold text-slate-200 flex items-center gap-2">
            <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            Cryptographically Verified Billing & Razorpay Integration
          </h4>
          <p>
            Orders are initialized server-side with fixed prices. Every checkout is verified against official Razorpay APIs using HMAC-SHA256 signatures with zero synthetic payment records.
          </p>
        </div>
        <Link
          href="/billing"
          className="shrink-0 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition border border-slate-700"
        >
          View Billing History &rarr;
        </Link>
      </div>
    </div>
  );
}
