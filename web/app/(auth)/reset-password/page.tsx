"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch } from "@/lib/api";

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!token) {
      setErrorMessage("No password reset token was provided. Please request a new link.");
      return;
    }

    if (newPassword.length < 8) {
      setErrorMessage("Password must be at least 8 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage("Passwords do not match. Please re-enter.");
      return;
    }

    setBusy(true);

    try {
      await apiFetch<{ message: string }>("/api/v1/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({
          token: token.trim(),
          new_password: newPassword,
        }),
      });
      setSuccess(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to reset password. The link may have expired.";
      setErrorMessage(msg);
    } finally {
      setBusy(false);
    }
  };

  if (!token && !success) {
    return (
      <div className="space-y-4">
        <div className="mb-4">
          <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-amber-400 mb-1">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            TOKEN MISSING
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Invalid Reset Link</h2>
          <p className="mt-1.5 text-sm text-slate-300">
            No cryptographic reset token was detected in your URL. Please verify the link from your email or request a new one.
          </p>
        </div>

        <Link
          href="/forgot-password"
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-cyan-500 py-2.5 px-4 text-xs font-semibold text-slate-950 hover:bg-cyan-400 transition font-mono tracking-wide"
        >
          Request New Reset Link →
        </Link>

        <div className="pt-2 text-center">
          <Link
            href="/login"
            className="text-xs text-slate-400 hover:text-slate-200 font-mono"
          >
            ← Back to Sign In
          </Link>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="space-y-5 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-2xl">
          ✓
        </div>

        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Password Updated</h2>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            Your credentials have been securely updated. All previous active sessions have been revoked for your security.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-[11px] font-mono text-slate-400">
          A confirmation notice has been dispatched to your email address.
        </div>

        <button
          type="button"
          onClick={() => router.push("/login")}
          className="w-full rounded-lg bg-cyan-500 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 font-mono tracking-wide"
        >
          SIGN IN WITH NEW PASSWORD →
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-cyan-400 mb-1">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
          CREDENTIAL ROTATION
        </div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Set New Password</h2>
        <p className="mt-1.5 text-sm text-slate-300">
          Enter and verify your new master password to regain access to your intelligence workspace.
        </p>
      </div>

      {errorMessage && (
        <div className="mb-4 rounded-xl border border-red-500/40 bg-red-950/40 p-3 text-sm text-red-300 space-y-2">
          <div className="flex items-center gap-1.5 font-semibold text-red-200 text-xs">
            <span>⚠</span> Authentication Error
          </div>
          <p className="text-xs text-red-300 leading-relaxed">{errorMessage}</p>
          {errorMessage.toLowerCase().includes("expired") && (
            <div className="pt-1">
              <Link
                href="/forgot-password"
                className="text-xs text-cyan-300 hover:underline font-mono"
              >
                Request a fresh reset link →
              </Link>
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-300">
            New Password
          </label>
          <input
            type="password"
            required
            autoFocus
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Min. 8 characters"
            className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300">
            Confirm New Password
          </label>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Re-enter password"
            className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
          />
        </div>

        {/* Password strength checklist */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-[11px] font-mono space-y-1">
          <div className="text-slate-400 font-semibold mb-1">Requirement:</div>
          <div className={newPassword.length >= 8 ? "text-emerald-400" : "text-slate-500"}>
            {newPassword.length >= 8 ? "✓" : "○"} At least 8 characters
          </div>
          <div className={newPassword && confirmPassword && newPassword === confirmPassword ? "text-emerald-400" : "text-slate-500"}>
            {newPassword && confirmPassword && newPassword === confirmPassword ? "✓" : "○"} Passwords match
          </div>
        </div>

        <button
          type="submit"
          disabled={busy || newPassword.length < 8 || newPassword !== confirmPassword}
          className="w-full rounded-lg bg-cyan-500 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 disabled:opacity-50 font-mono tracking-wide"
        >
          {busy ? "ROTATING CREDENTIALS..." : "UPDATE PASSWORD →"}
        </button>

        <div className="pt-2 text-center">
          <Link
            href="/login"
            className="text-xs text-slate-400 hover:text-slate-200 font-mono"
          >
            ← Cancel and Return to Sign In
          </Link>
        </div>
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-center text-xs font-mono text-cyan-400">
          VALIDATING CRYPTOGRAPHIC TOKEN...
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
