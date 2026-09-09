"use client";

import React, { useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErrorMessage(null);

    try {
      await apiFetch<{ message: string }>("/api/v1/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      // Anti-enumeration: always display success card
      setSubmitted(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to process request";
      setErrorMessage(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-cyan-400 mb-1">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
          CREDENTIAL RECOVERY
        </div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Reset Password</h2>
        <p className="mt-1.5 text-sm text-slate-300">
          Enter your registered researcher email address to receive cryptographic password reset instructions.
        </p>
      </div>

      {errorMessage && (
        <div className="mb-4 rounded-xl border border-red-500/40 bg-red-950/40 p-3 text-sm text-red-300">
          <span className="font-semibold text-red-200">Error: </span>
          {errorMessage}
        </div>
      )}

      {submitted ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-cyan-500/40 bg-cyan-950/30 p-5 text-sm text-slate-200 space-y-3">
            <div className="flex items-center gap-2 text-cyan-300 font-semibold font-mono text-xs uppercase tracking-wider">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500/20 text-cyan-400 text-xs">
                ✓
              </span>
              Instructions Dispatched
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              If an active account exists for <strong className="text-white font-mono">{email}</strong>, we have dispatched a single-use, 30-minute password reset link via Resend.
            </p>
            <div className="border-t border-cyan-500/20 pt-3 text-[11px] text-slate-400 font-mono space-y-1">
              <div>• Check your inbox and spam filters.</div>
              <div>• For security, reset links expire in 30 minutes.</div>
              <div>• Existing active sessions will be revoked upon reset.</div>
            </div>
          </div>

          <div className="pt-2">
            <Link
              href="/login"
              className="w-full flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800/90 py-2.5 px-4 text-xs font-semibold text-slate-200 hover:bg-slate-700/80 transition"
            >
              ← Back to Sign In
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300">
              Researcher Email Address
            </label>
            <input
              type="email"
              required
              autoFocus
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="researcher@attacksurface.online"
              className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-[11px] font-mono text-slate-400 space-y-1">
            <div className="text-slate-300 font-semibold">Security Safeguards:</div>
            <div>• Cryptographic SHA-256 single-use tokens</div>
            <div>• Strict 30-minute token validity</div>
            <div>• Zero-enumeration privacy protocol</div>
          </div>

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-cyan-500 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 disabled:opacity-50 font-mono tracking-wide"
          >
            {busy ? "DISPATCHING INSTRUCTIONS..." : "SEND RESET INSTRUCTIONS →"}
          </button>

          <div className="pt-2 text-center">
            <Link
              href="/login"
              className="text-xs text-cyan-400 hover:text-cyan-300 hover:underline font-mono"
            >
              ← Return to Sign In
            </Link>
          </div>
        </form>
      )}

      <div className="mt-6 border-t border-slate-800 pt-4 text-center text-[11px] text-slate-500 font-mono">
        Need emergency operator access? Contact{" "}
        <a
          href="mailto:attacksurface.alerts@gmail.com"
          className="text-cyan-400 hover:underline"
        >
          attacksurface.alerts@gmail.com
        </a>
      </div>
    </div>
  );
}
