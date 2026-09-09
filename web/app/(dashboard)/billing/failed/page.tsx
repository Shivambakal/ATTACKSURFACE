"use client";

import React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

export default function PaymentFailedPage() {
  const searchParams = useSearchParams();
  const reason = searchParams.get("reason") || "Payment was declined or cancelled by the user.";
  const orderId = searchParams.get("order_id");

  return (
    <div className="max-w-xl mx-auto py-16 px-4 text-center">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-8 space-y-6 shadow-xl">
        {/* Failure Icon */}
        <div className="w-16 h-16 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center justify-center mx-auto text-2xl shadow-[0_0_30px_rgba(244,63,94,0.2)]">
          ✕
        </div>

        <div className="space-y-2">
          <span className="text-[10px] font-mono uppercase tracking-widest text-rose-400 font-bold">
            TRANSACTION INCOMPLETE
          </span>
          <h1 className="text-2xl font-bold text-white">Payment Did Not Complete</h1>
          <p className="text-xs text-rose-300 max-w-md mx-auto">{reason}</p>
        </div>

        {orderId && (
          <div className="rounded-xl bg-slate-950/70 border border-slate-800 p-3 text-left text-xs font-mono text-slate-400">
            Order Reference: <span className="text-slate-200">{orderId}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <Link
            href="/pricing"
            className="flex-1 py-2.5 px-4 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition shadow-sm"
          >
            Retry from Pricing
          </Link>
          <Link
            href="/billing"
            className="flex-1 py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs transition border border-slate-700"
          >
            Return to Billing
          </Link>
        </div>
      </div>
    </div>
  );
}
