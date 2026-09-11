"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

function LoginContent() {
  const searchParams = useSearchParams();
  const oauthError = searchParams.get("error");
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Forgot password state
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotStatus, setForgotStatus] = useState<string | null>(null);
  const [forgotBusy, setForgotBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setBusy(true);

    try {
      const loggedIn = await login(email, password);
      try {
        sessionStorage.setItem("just_logged_in", "true");
      } catch {}
      if (loggedIn.role === "OWNER" || loggedIn.role === "ADMIN" || loggedIn.is_admin) {
        window.location.href = "/admin";
      } else {
        window.location.href = "/dashboard";
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      setErrorMessage(msg);
    } finally {
      setBusy(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setForgotBusy(true);
    setForgotStatus(null);

    try {
      const res = await apiFetch<{ message: string }>("/api/v1/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: forgotEmail || email }),
      });
      setForgotStatus(res.message || "Password reset instructions sent if email exists.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Could not process request";
      setForgotStatus(msg);
    } finally {
      setForgotBusy(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white tracking-tight">Sign In</h2>
        <p className="mt-1.5 text-sm text-slate-300">
          Enter your authorized credentials to access continuous attack surface intelligence.
        </p>
      </div>

      {oauthError === "google_oauth_config_required" && (
        <div className="mb-5 rounded-2xl border border-cyan-500/40 bg-cyan-950/40 p-4 text-xs text-cyan-200 space-y-2">
          <div className="font-bold flex items-center gap-1.5 text-cyan-300 text-sm">
            <span>🌐</span> Google OAuth Configuration Ready
          </div>
          <p className="text-slate-300 leading-relaxed text-xs">
            To enable 1-click Google Sign-In for <strong className="text-white">https://attacksurface.online/</strong>, add your Google Cloud credentials to the server environment:
          </p>
          <div className="rounded-xl bg-slate-950/90 border border-cyan-500/30 p-2.5 font-mono text-[11px] text-cyan-300 space-y-1">
            <div>GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com</div>
            <div>GOOGLE_CLIENT_SECRET=your-client-secret</div>
            <div>GOOGLE_REDIRECT_URI=https://attacksurface.online/api/v1/auth/google/callback</div>
          </div>
          <p className="text-[11px] text-slate-400">
            In Google Cloud Console, configure Authorized redirect URI: <code className="text-white font-mono font-bold">https://attacksurface.online/api/v1/auth/google/callback</code>
          </p>
        </div>
      )}

      {oauthError && oauthError !== "google_oauth_config_required" && (
        <div className="mb-4 rounded-xl border border-amber-500/40 bg-amber-950/40 p-3 text-xs text-amber-200">
          Google Sign-In notice ({oauthError}). Please try again or sign in with password below.
        </div>
      )}

      {errorMessage && (
        <div className="mb-4 rounded-xl border border-red-500/40 bg-red-950/40 p-3 text-sm text-red-300">
          <span className="font-semibold text-red-200">Error: </span>
          {errorMessage}
        </div>
      )}

      {/* Continue with Google */}
      <button
        type="button"
        onClick={() => {
          window.location.href = "/api/v1/auth/google";
        }}
        className="w-full flex items-center justify-center gap-3 rounded-lg border border-slate-700 bg-slate-800/90 py-2.5 px-4 text-xs font-semibold text-slate-100 hover:bg-slate-700/80 transition active:scale-[0.99] mb-4"
      >
        <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24">
          <path
            fill="#EA4335"
            d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"
          />
          <path
            fill="#4285F4"
            d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"
          />
          <path
            fill="#FBBC05"
            d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12 0 12s.7 2.3 1.9 4.7l3.7-2.9z"
          />
          <path
            fill="#34A853"
            d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16c1.8 3.7 5.6 7 10.1 7z"
          />
        </svg>
        <span>Continue with Google</span>
      </button>

      <div className="relative my-4 flex items-center justify-center text-xs">
        <div className="w-full border-t border-slate-800" />
        <span className="bg-slate-900 px-2 text-[10px] font-mono uppercase text-slate-500 shrink-0">
          or sign in with password
        </span>
        <div className="w-full border-t border-slate-800" />
      </div>

      {!showForgot ? (
        <form onSubmit={handleSubmit} autoComplete="on" className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300">
              Email Address
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

          <div>
            <div className="flex items-center justify-between">
              <label className="block text-xs font-medium text-slate-300">
                Password
              </label>
              <Link
                href="/forgot-password"
                className="text-xs text-cyan-400 hover:text-cyan-300 hover:underline"
              >
                Forgot password?
              </Link>
            </div>
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-cyan-500 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 disabled:opacity-50 font-mono tracking-wide"
          >
            {busy ? "AUTHENTICATING..." : "SIGN IN →"}
          </button>
        </form>
      ) : (
        <form onSubmit={handleForgotPassword} autoComplete="on" className="space-y-4">
          <div className="rounded-lg border border-cyan-900/50 bg-cyan-950/20 p-3 text-xs text-cyan-300">
            Enter your account email to receive reset instructions.
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">
              Account Email
            </label>
            <input
              type="email"
              required
              autoComplete="email"
              value={forgotEmail}
              onChange={(e) => setForgotEmail(e.target.value)}
              placeholder="researcher@attacksurface.online"
              className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          {forgotStatus && (
            <p className="text-xs text-slate-300 bg-slate-800 p-2.5 rounded border border-slate-700">
              {forgotStatus}
            </p>
          )}

          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={forgotBusy}
              className="flex-1 rounded-lg bg-cyan-500 py-2 text-xs font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-50"
            >
              {forgotBusy ? "Sending..." : "Send Reset Link"}
            </button>
            <button
              type="button"
              onClick={() => setShowForgot(false)}
              className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            >
              Back to Sign In
            </button>
          </div>
        </form>
      )}

      <div className="mt-6 border-t border-slate-800 pt-5 text-center text-xs text-slate-400">
        Need an authorized account?{" "}
        <Link
          href="/signup"
          className="font-medium text-cyan-400 hover:text-cyan-300 hover:underline"
        >
          Create account
        </Link>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs font-mono text-cyan-400">LOADING AUTHENTICATOR...</div>}>
      <LoginContent />
    </Suspense>
  );
}
