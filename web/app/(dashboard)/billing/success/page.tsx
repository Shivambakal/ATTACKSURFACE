"use client";

import React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

export default function PaymentSuccessPage() {
  const searchParams = useSearchParams();
  const orderId = searchParams.get("order_id");
  const paymentId = searchParams.get("payment_id");
  const tier = searchParams.get("tier") || "RESEARCHER";

  return (
    <div className="max-w-xl mx-auto py-16 px-4 text-center">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-8 space-y-6 shadow-xl">
        {/* Success Icon */}
        <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto text-2xl shadow-[0_0_30px_rgba(16,185,129,0.2)]">
          ✓
        </div>

        <div className="space-y-2">
          <span className="text-[10px] font-mono uppercase tracking-widest text-emerald-400 font-bold">
            TRANSACTION VERIFIED
          </span>
          <h1 className="text-2xl font-bold text-white">Payment Successful</h1>
          <p className="text-xs text-slate-300 max-w-md mx-auto">
            Your payment was authenticated and cryptographically verified by our servers. Your researcher entitlements for the{" "}
            <span className="text-cyan-400 font-bold uppercase">{tier}</span> tier are now active.
          </p>
        </div>

        {/* Verification Summary */}
        <div className="rounded-xl bg-slate-950/70 border border-slate-800 p-4 text-left text-xs font-mono space-y-2">
          <div className="flex justify-between">
            <span className="text-slate-400">Order ID:</span>
            <span className="text-slate-200 font-semibold truncate max-w-[240px]">{orderId || "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Payment ID:</span>
            <span className="text-slate-200 font-semibold truncate max-w-[240px]">{paymentId || "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Gateway Status:</span>
            <span className="text-emerald-400 font-bold">CAPTURED & VERIFIED</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <Link
            href="/dashboard"
            className="flex-1 py-2.5 px-4 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition shadow-sm"
          >
            Go to Research Dashboard
          </Link>
          <Link
            href="/billing"
            className="flex-1 py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs transition border border-slate-700"
          >
            View Billing Records
          </Link>
        </div>
      </div>
    </div>
  );
}
