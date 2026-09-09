"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Script from "next/script";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { BillingPlan } from "@/lib/types";

interface PlansResponse {
  configured: boolean;
  environment: string;
  status_label: string;
  currency: string;
  has_yearly_billing: boolean;
  plans: BillingPlan[];
}

export default function CheckoutPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  const planParam = (searchParams.get("plan") || "researcher").toUpperCase();
  const intervalParam = (searchParams.get("interval") || "monthly").toLowerCase();

  const [plan, setPlan] = useState<BillingPlan | null>(null);
  const [plansData, setPlansData] = useState<PlansResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [paymentBusy, setPaymentBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchPlan() {
      setLoading(true);
      setError(null);
      try {
        const res = await apiFetch<PlansResponse>("/api/v1/billing/plans");
        setPlansData(res);
        const match = res.plans.find((p) => p.tier.toUpperCase() === planParam);
        if (match) {
          setPlan(match);
        } else {
          setError(`Invalid plan specified: "${planParam}". Please select a valid plan.`);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load plan details.");
      } finally {
        setLoading(false);
      }
    }
    fetchPlan();
  }, [planParam]);

  const price = plan
    ? intervalParam === "yearly"
      ? plan.yearly_price_inr ?? plan.monthly_price_inr * 12
      : plan.monthly_price_inr
    : 0;

  const handleCheckout = async () => {
    if (!plan) return;
    setPaymentBusy(true);
    setError(null);

    try {
      // 1. Initialize Order Server-Side
      const orderData = await apiFetch<any>("/api/v1/billing/create-order", {
        method: "POST",
        body: JSON.stringify({
          plan_tier: plan.tier.toUpperCase(),
          interval: intervalParam,
        }),
      });

      if (!orderData || !orderData.order_id) {
        throw new Error("Invalid response from billing service. Order ID was not returned.");
      }

      // 2. Configure Razorpay Standard Checkout
      const rzpOptions = {
        key: orderData.key_id,
        amount: orderData.amount, // in paise
        currency: orderData.currency || "INR",
        name: "AttackSurface Timeline",
        description: `${orderData.plan_name} (${intervalParam}) Subscription`,
        order_id: orderData.order_id,
        prefill: {
          email: user?.email || "",
        },
        theme: {
          color: "#06b6d4",
        },
        handler: async function (response: any) {
          try {
            // 3. Verify Payment Signature & Amount Server-Side
            const verifyRes = await apiFetch<any>("/api/v1/billing/verify-payment", {
              method: "POST",
              body: JSON.stringify({
                order_id: response.razorpay_order_id,
                payment_id: response.razorpay_payment_id,
                signature: response.razorpay_signature,
              }),
            });

            router.push(
              `/billing/success?order_id=${encodeURIComponent(
                response.razorpay_order_id
              )}&payment_id=${encodeURIComponent(response.razorpay_payment_id)}&tier=${encodeURIComponent(
                plan.tier
              )}`
            );
          } catch (verifyErr: any) {
            router.push(
              `/billing/failed?reason=${encodeURIComponent(
                verifyErr.message || "Payment verification failed"
              )}&order_id=${encodeURIComponent(response.razorpay_order_id)}`
            );
          }
        },
        modal: {
          ondismiss: function () {
            setPaymentBusy(false);
          },
        },
      };

      // 3. Launch Razorpay Modal
      if (typeof window !== "undefined" && (window as any).Razorpay) {
        const rzp = new (window as any).Razorpay(rzpOptions);
        rzp.on("payment.failed", function (failResponse: any) {
          const reason =
            failResponse.error?.description ||
            failResponse.error?.reason ||
            "Payment transaction failed at gateway";
          router.push(`/billing/failed?reason=${encodeURIComponent(reason)}`);
        });
        rzp.open();
      } else {
        throw new Error("Razorpay Checkout SDK is still loading. Please try again in a few seconds.");
      }
    } catch (err: any) {
      setError(err.message || "Checkout initialization failed");
      setPaymentBusy(false);
    }
  };

  return (
    <>
      <Script src="https://checkout.razorpay.com/v1/checkout.js" strategy="lazyOnload" />

      <div className="max-w-2xl mx-auto py-8 px-4">
        {/* Breadcrumb */}
        <div className="mb-6 flex items-center gap-2 text-xs text-slate-400 font-mono">
          <Link href="/pricing" className="hover:text-cyan-400 transition">
            Pricing
          </Link>
          <span>/</span>
          <span className="text-white font-semibold">Checkout</span>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 sm:p-8 space-y-6">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-widest text-cyan-400 font-bold">
              ORDER CONFIRMATION
            </span>
            <h1 className="text-2xl font-bold text-white mt-1">Review Your Subscription</h1>
            <p className="text-xs text-slate-400 mt-1">
              Complete your payment securely via Razorpay to unlock researcher entitlements immediately.
            </p>
          </div>

          {loading && (
            <div className="flex justify-center items-center py-12">
              <div className="w-6 h-6 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs">
              {error}
            </div>
          )}

          {!loading && plan && (
            <div className="space-y-6">
              {/* Order Summary Box */}
              <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-5 space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-bold text-white">{plan.name} Tier</h3>
                    <p className="text-xs text-slate-400 font-mono capitalize">
                      Billing Cycle: {intervalParam}
                    </p>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                    {plan.tier}
                  </span>
                </div>

                <div className="border-t border-slate-800 pt-3 space-y-2 text-xs">
                  <div className="flex justify-between text-slate-300">
                    <span>Base Subscription ({intervalParam}):</span>
                    <span className="font-mono font-semibold text-white">₹{price.toLocaleString("en-IN")}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Applicable Taxes / Fees:</span>
                    <span className="font-mono text-slate-300">₹0 (Included)</span>
                  </div>
                  {intervalParam === "yearly" && plan.savings_inr && (
                    <div className="flex justify-between text-emerald-400">
                      <span>Annual Discount:</span>
                      <span className="font-mono font-semibold">-₹{plan.savings_inr.toLocaleString("en-IN")}</span>
                    </div>
                  )}
                  <div className="border-t border-slate-800/80 pt-2 flex justify-between text-sm font-bold text-white">
                    <span>Total Amount Due:</span>
                    <span className="text-cyan-400 font-mono text-base">₹{price.toLocaleString("en-IN")}</span>
                  </div>
                </div>
              </div>

              {/* Gateway Notice */}
              <div className="rounded-xl bg-slate-950/40 border border-slate-800/80 p-4 text-xs text-slate-400 flex items-start gap-3">
                <span className="text-cyan-400 text-base mt-0.5">🔒</span>
                <div>
                  <p className="text-slate-200 font-semibold">Verified Payment Flow</p>
                  <p className="mt-0.5">
                    Payments are handled by Razorpay with end-to-end TLS encryption. Cards, UPI, NetBanking, and Wallets are supported.
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-3">
                <button
                  onClick={handleCheckout}
                  disabled={paymentBusy}
                  className="w-full py-3 px-4 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-sm transition shadow-[0_0_20px_rgba(6,182,212,0.3)] disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2"
                >
                  {paymentBusy ? (
                    <>
                      <div className="w-4 h-4 rounded-full border-2 border-slate-950 border-t-transparent animate-spin" />
                      <span>Opening Secure Razorpay Gateway...</span>
                    </>
                  ) : (
                    <span>Pay ₹{price.toLocaleString("en-IN")} via Razorpay &rarr;</span>
                  )}
                </button>

                <Link
                  href="/pricing"
                  className="block text-center text-xs text-slate-400 hover:text-slate-200 transition"
                >
                  Cancel and return to Pricing
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
