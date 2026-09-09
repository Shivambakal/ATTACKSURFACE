"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch, API } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface ExportJob {
  id: number;
  export_uuid: string;
  export_type: string;
  format: string;
  status: string;
  row_count: number;
  file_size_bytes: number;
  checksum_sha256: string | null;
  download_token: string;
  download_url: string;
  download_count: number;
  expires_at: string;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

interface Plan {
  tier: string;
  name: string;
  price_inr: number;
  billing_period: string;
  features: string[];
  limits: {
    max_targets: number;
    export_formats: string[];
    max_export_rows: number;
  };
}

interface BillingPlansResponse {
  configured: boolean;
  currency: string;
  plans: Plan[];
}

const EXPORT_PACKAGES = [
  {
    id: "COMPANY_INTELLIGENCE",
    title: "Company Intelligence",
    description: "Complete canonical corporate metadata, products, tech stack, and bug bounty scope.",
    badge: "CORE",
    formats: ["JSON", "CSV", "NDJSON", "ZIP"],
    recommendedFor: "Attack Surface Mapping",
  },
  {
    id: "VULNERABILITY_INTELLIGENCE",
    title: "Vulnerability Intelligence",
    description: "Exact CISA KEV catalog with required action, due dates, ransomware tags, and CWEs.",
    badge: "CISA KEV",
    formats: ["JSON", "CSV", "NDJSON", "ZIP"],
    recommendedFor: "Exploit Prioritization",
  },
  {
    id: "HISTORICAL_TIMELINE",
    title: "Historical Security Timeline",
    description: "Chronological security milestones, disclosures, and confirmed historical events.",
    badge: "TIMELINE",
    formats: ["JSON", "CSV", "NDJSON"],
    recommendedFor: "Trend Analysis",
  },
  {
    id: "ATTACK_SURFACE_CHANGES",
    title: "Attack Surface Changes",
    description: "Discovered subdomains, DNS diffs, API modifications, and certificate rotations.",
    badge: "DIFFS",
    formats: ["JSON", "CSV", "NDJSON"],
    recommendedFor: "Change Detection",
  },
  {
    id: "RESEARCH_SIGNALS",
    title: "Research Signals",
    description: "High-priority intelligence indicators with severity scores and verification trails.",
    badge: "SIGNALS",
    formats: ["JSON", "CSV"],
    recommendedFor: "Hunting & Recon",
  },
  {
    id: "SCOPE_EXPORT",
    title: "Authorized Scope Rules",
    description: "In-scope and out-of-scope targets, program policy links, and temporal validity.",
    badge: "SCOPE",
    formats: ["JSON", "CSV"],
    recommendedFor: "Rules of Engagement",
  },
  {
    id: "EVIDENCE_PACK",
    title: "Forensic Evidence Pack",
    description: "Cryptographic source hashes, raw snapshot identifiers, and entity relationship proof.",
    badge: "EVIDENCE",
    formats: ["JSON", "ZIP"],
    recommendedFor: "Compliance & Auditing",
  },
  {
    id: "FULL_RESEARCH_DATASET",
    title: "Full Research Dataset",
    description: "Complete archive spanning all intelligence layers, entities, events, and diffs.",
    badge: "FULL DUMP",
    formats: ["JSON", "ZIP"],
    recommendedFor: "Data Science & ETL",
  },
];

export default function ExportsPage() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState<ExportJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPackage, setSelectedPackage] = useState<string>("COMPANY_INTELLIGENCE");
  const [selectedFormat, setSelectedFormat] = useState<string>("JSON");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [billingInfo, setBillingInfo] = useState<BillingPlansResponse | null>(null);
  const [currentSubscription, setCurrentSubscription] = useState<any>(null);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [checkoutStatus, setCheckoutStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [pendingDownloadJob, setPendingDownloadJob] = useState<ExportJob | null>(null);

  const fetchExports = async () => {
    try {
      setLoading(true);
      const data = await apiFetch<ExportJob[]>("/api/v1/exports");
      setJobs(data || []);
    } catch (err) {
      console.error("Failed to load exports:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPlans = async () => {
    try {
      const data = await apiFetch<BillingPlansResponse>("/api/v1/billing/plans");
      setBillingInfo(data);
    } catch (err) {
      console.error("Failed to load billing plans:", err);
    }
  };

  const fetchSubscription = async () => {
    try {
      const data = await apiFetch<any>("/api/v1/billing/subscription");
      setCurrentSubscription(data);
    } catch (err) {
      console.error("Failed to load subscription:", err);
    }
  };

  useEffect(() => {
    fetchExports();
    fetchPlans();
    fetchSubscription();
  }, []);

  const loadRazorpayScript = (): Promise<boolean> => {
    return new Promise((resolve) => {
      if (typeof window === "undefined") return resolve(false);
      if ((window as any).Razorpay) return resolve(true);
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  const handleInitiateCheckout = async (tier: string, name: string) => {
    setCheckoutLoading(tier);
    setCheckoutStatus(null);
    try {
      const scriptReady = await loadRazorpayScript();
      if (!scriptReady) {
        setCheckoutStatus({ type: "error", message: "Failed to load payment gateway script." });
        setCheckoutLoading(null);
        return;
      }

      const orderData = await apiFetch<any>("/api/v1/billing/create-order", {
        method: "POST",
        body: JSON.stringify({ plan_tier: tier }),
      });

      const options = {
        key: orderData.key_id,
        amount: orderData.amount,
        currency: orderData.currency,
        name: "AttackSurface Timeline",
        description: `${orderData.plan_name} Subscription`,
        order_id: orderData.order_id,
        handler: async function (response: any) {
          try {
            const verifyRes = await apiFetch<any>("/api/v1/billing/verify-payment", {
              method: "POST",
              body: JSON.stringify({
                order_id: response.razorpay_order_id,
                payment_id: response.razorpay_payment_id,
                signature: response.razorpay_signature,
              }),
            });
            setCheckoutStatus({
              type: "success",
              message: verifyRes.message || `Upgraded to ${orderData.plan_name} successfully! Starting download...`,
            });
            await fetchSubscription();
            await fetchPlans();

            if (pendingDownloadJob) {
              const target = pendingDownloadJob;
              setPendingDownloadJob(null);
              setTimeout(() => {
                setShowPlanModal(false);
                executeDownload(target);
              }, 1200);
            }
          } catch (verifyErr: any) {
            setCheckoutStatus({
              type: "error",
              message: verifyErr.message || "Payment signature verification failed.",
            });
          }
        },
        prefill: {
          name: user?.email ? user.email.split("@")[0] : "Security Researcher",
          email: user?.email || "shivam8668bakal@gmail.com",
        },
        theme: {
          color: "#06b6d4",
        },
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.on("payment.failed", function (failResponse: any) {
        setCheckoutStatus({
          type: "error",
          message: failResponse.error?.description || "Payment failed or was cancelled.",
        });
      });
      rzp.open();
    } catch (err: any) {
      setCheckoutStatus({ type: "error", message: err.message || "Failed to start checkout." });
    } finally {
      setCheckoutLoading(null);
    }
  };

  const handleSandboxUnlock = async (tier: string = "PRO") => {
    setCheckoutLoading(tier);
    try {
      await apiFetch("/api/v1/profile", {
        method: "PATCH",
        body: JSON.stringify({
          handles: {
            selected_plan: tier,
            subscription_active: true,
            unlocked_at: new Date().toISOString(),
          },
        }),
      });
      setCurrentSubscription({ plan_tier: tier, tier, is_active: true });
      setCheckoutStatus({
        type: "success",
        message: `Plan activated! Starting export download...`,
      });
      if (pendingDownloadJob) {
        const target = pendingDownloadJob;
        setPendingDownloadJob(null);
        setTimeout(() => {
          setShowPlanModal(false);
          executeDownload(target);
        }, 1000);
      } else {
        setTimeout(() => setShowPlanModal(false), 1000);
      }
    } catch (err: any) {
      setCheckoutStatus({ type: "error", message: err.message || "Failed to activate plan." });
    } finally {
      setCheckoutLoading(null);
    }
  };

  const handleCreateExport = async () => {
    setIsSubmitting(true);
    setSuccessMessage(null);
    setErrorMessage(null);
    try {
      const newJob = await apiFetch<ExportJob>("/api/v1/exports/create", {
        method: "POST",
        body: JSON.stringify({
          export_type: selectedPackage,
          format: selectedFormat,
          filters: { limit: 5000 },
          scope: "ALL",
        }),
      });
      setSuccessMessage(`Export generated successfully: ${newJob.row_count} records packaged.`);
      fetchExports();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to trigger export generation.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const executeDownload = async (job: ExportJob) => {
    setDownloadingId(job.id);
    setErrorMessage(null);
    try {
      const downloadTarget = job.download_url.startsWith("http")
        ? job.download_url
        : `${API}${job.download_url}`;

      const res = await fetch(downloadTarget, {
        credentials: "include",
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `Download failed with HTTP ${res.status}` }));
        throw new Error(err.detail || `Download failed with HTTP ${res.status}`);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const ext = job.format.toLowerCase();
      const filename = `${job.export_type.toLowerCase()}_${job.export_uuid.substring(0, 8)}.${ext}`;

      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);

      setSuccessMessage(`Downloaded ${filename} successfully (${formatBytes(job.file_size_bytes)}).`);
    } catch (err: any) {
      console.error("Export download error:", err);
      setErrorMessage(err.message || "Failed to download export file.");
    } finally {
      setDownloadingId(null);
    }
  };

  const handleDownload = async (job: ExportJob) => {
    // Check if user is active paid subscriber or admin
    const isPaid =
      user?.role === "ADMIN" ||
      user?.role === "OWNER" ||
      user?.is_admin ||
      (currentSubscription?.plan_tier && currentSubscription.plan_tier !== "FREE") ||
      (currentSubscription?.tier && currentSubscription.tier !== "FREE") ||
      currentSubscription?.is_active === true;

    if (!isPaid) {
      setPendingDownloadJob(job);
      setShowPlanModal(true);
      return;
    }

    await executeDownload(job);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Breadcrumb & Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <Link href="/dashboard" className="text-cyan-400 hover:underline">Dashboard</Link>
          <span>/</span>
          <span className="text-white">Researcher Export Center</span>
        </div>
        <button
          onClick={() => setShowPlanModal(true)}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 text-amber-300 text-xs font-medium hover:bg-amber-500/30 transition shadow-sm"
        >
          <span>⚡ {currentSubscription?.plan?.name || "Community Researcher"} — Subscription & Entitlements</span>
        </button>
      </div>

      {/* AMOLED 2.5D Hero Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900/90 via-slate-950 to-black border border-cyan-500/20 p-8 shadow-2xl backdrop-blur-xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 text-xs font-mono mb-3">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span>CRYPTOGRAPHIC INTEGRITY • SHA-256 SIGNED</span>
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Researcher Export Center</h1>
            <p className="text-sm text-slate-400 mt-2 max-w-2xl leading-relaxed">
              Export verified corporate attack surface intelligence, live CISA KEV catalogs, forensic evidence packs,
              and historical security timelines with guaranteed provenance and zero synthetic records.
            </p>
          </div>
          <button
            onClick={fetchExports}
            disabled={loading}
            className="self-start md:self-auto px-4 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-xs font-medium text-slate-200 transition"
          >
            {loading ? "Refreshing..." : "↻ Refresh History"}
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-950/50 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between font-mono">
          <span>✓ {successMessage}</span>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-500 hover:text-emerald-300">✕</button>
        </div>
      )}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-500/30 text-rose-400 text-xs flex items-center justify-between font-mono">
          <span>⚠ {errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="text-rose-500 hover:text-rose-300">✕</button>
        </div>
      )}

      {/* Package Selection Matrix */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
          <span>1. Choose Intelligence Package</span>
          <span className="text-xs font-mono text-slate-500 font-normal">(Select 1 of 8 verified datasets)</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {EXPORT_PACKAGES.map((pkg) => {
            const isSelected = selectedPackage === pkg.id;
            return (
              <div
                key={pkg.id}
                onClick={() => setSelectedPackage(pkg.id)}
                className={`cursor-pointer group relative rounded-xl p-5 transition-all duration-300 border ${
                  isSelected
                    ? "bg-slate-900/90 border-cyan-500 shadow-lg shadow-cyan-500/10 ring-1 ring-cyan-500"
                    : "bg-slate-950/70 border-slate-800 hover:border-slate-700 hover:bg-slate-900/50"
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-3">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
                    isSelected ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40" : "bg-slate-800 text-slate-400"
                  }`}>
                    {pkg.badge}
                  </span>
                  <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                    isSelected ? "border-cyan-400 bg-cyan-400" : "border-slate-700"
                  }`}>
                    {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-black" />}
                  </div>
                </div>
                <h3 className="text-sm font-semibold text-white group-hover:text-cyan-300 transition-colors">
                  {pkg.title}
                </h3>
                <p className="text-xs text-slate-400 mt-1.5 line-clamp-2 leading-relaxed">
                  {pkg.description}
                </p>
                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                  <span>{pkg.formats.join(" • ")}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Format & Execution Controls */}
      <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-6 backdrop-blur">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <span className="text-xs font-mono uppercase text-slate-400 tracking-wider">Format & Serialization</span>
            <div className="flex flex-wrap items-center gap-2 mt-2">
              {["JSON", "CSV", "NDJSON", "ZIP"].map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => setSelectedFormat(fmt)}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition ${
                    selectedFormat === fmt
                      ? "bg-cyan-500 text-black font-bold shadow-md shadow-cyan-500/20"
                      : "bg-slate-800/80 text-slate-300 hover:bg-slate-700 border border-slate-700"
                  }`}
                >
                  {fmt}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleCreateExport}
            disabled={isSubmitting}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-bold text-sm transition shadow-xl shadow-cyan-500/20 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <span className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
                <span>Generating Artifact...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span>Generate {selectedFormat} Export</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Export History Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white tracking-tight">Your Export History</h2>
          <span className="text-xs font-mono text-slate-500">{jobs.length} total generated artifacts</span>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/70 overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/90 text-slate-400 font-mono uppercase tracking-wider text-[11px] border-b border-slate-800">
                <tr>
                  <th className="px-5 py-3.5">Export Package</th>
                  <th className="px-5 py-3.5">Format</th>
                  <th className="px-5 py-3.5">Rows</th>
                  <th className="px-5 py-3.5">Size</th>
                  <th className="px-5 py-3.5">SHA-256 Checksum</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-8 text-center text-slate-500">
                      Loading export history...
                    </td>
                  </tr>
                ) : jobs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-8 text-center text-slate-500">
                      No exports generated yet. Select a package above to package intelligence.
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-slate-900/40 transition">
                      <td className="px-5 py-4 font-sans font-medium text-white">
                        {job.export_type.replace(/_/g, " ")}
                      </td>
                      <td className="px-5 py-4">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">
                          {job.format}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-cyan-400 font-bold">{job.row_count}</td>
                      <td className="px-5 py-4 text-slate-400">{formatBytes(job.file_size_bytes)}</td>
                      <td className="px-5 py-4 text-slate-500 text-[11px]">
                        {job.checksum_sha256 ? (
                          <span title={job.checksum_sha256}>
                            {job.checksum_sha256.substring(0, 10)}...{job.checksum_sha256.substring(54)}
                          </span>
                        ) : (
                          "--"
                        )}
                      </td>
                      <td className="px-5 py-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          job.status === "READY"
                            ? "bg-emerald-950/60 text-emerald-400 border border-emerald-500/30"
                            : job.status === "FAILED"
                            ? "bg-rose-950/60 text-rose-400 border border-rose-500/30"
                            : "bg-amber-950/60 text-amber-400 border border-amber-500/30"
                        }`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-right">
                        {job.status === "READY" ? (
                          <button
                            onClick={() => handleDownload(job)}
                            disabled={downloadingId === job.id}
                            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-xs font-sans font-medium transition disabled:opacity-50"
                          >
                            {downloadingId === job.id ? (
                              <>
                                <span className="w-3 h-3 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
                                <span>Downloading...</span>
                              </>
                            ) : (
                              <>
                                <span>Download</span>
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                              </>
                            )}
                          </button>
                        ) : (
                          <span className="text-slate-600 text-xs">Unavailable</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Subscription & Entitlements Modal */}
      {showPlanModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="bg-slate-950 border border-slate-800 rounded-2xl max-w-4xl w-full p-8 shadow-2xl relative">
            <button
              onClick={() => setShowPlanModal(false)}
              className="absolute top-6 right-6 text-slate-400 hover:text-white"
            >
              ✕
            </button>

            <div className="text-center max-w-xl mx-auto mb-6">
              <span className="px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 text-xs font-mono">
                {pendingDownloadJob ? "SUBSCRIPTION REQUIRED TO DOWNLOAD" : "RESEARCHER INTELLIGENCE TIERS"}
              </span>
              <h2 className="text-2xl font-bold text-white mt-3">
                {pendingDownloadJob ? "Unlock Instant Export Download" : "Choose Your Intelligence Package"}
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                {pendingDownloadJob
                  ? `An active subscription is required to download ${pendingDownloadJob.export_type} (${pendingDownloadJob.format}). Upgrading below immediately activates access and begins your download.`
                  : "Authoritative data depth, historical range, and export format entitlements."}
              </p>
            </div>

            {/* Gateway status notice */}
            {billingInfo && !billingInfo.configured ? (
              <div className="mb-6 p-4 rounded-xl bg-cyan-950/30 border border-cyan-500/30 text-cyan-200 text-xs flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg">⚡</span>
                  <div>
                    <span className="font-bold uppercase tracking-wide">DIRECT ACTIVATION READY: </span>
                    Select your preferred tier below to activate intelligence export capabilities. Your file download will trigger automatically.
                  </div>
                </div>
              </div>
            ) : (
              <div className="mb-6 p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg">⚡</span>
                  <div>
                    <span className="font-bold uppercase tracking-wide">SECURE PAYMENT GATEWAY ACTIVE: </span>
                    Complete checkout to unlock high-volume exports. Download begins immediately upon verification.
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-400 font-mono text-[10px] font-bold border border-emerald-500/30 whitespace-nowrap">
                  LIVE READY
                </span>
              </div>
            )}

            {/* Checkout alert status */}
            {checkoutStatus && (
              <div className={`mb-6 p-4 rounded-xl text-xs flex items-center justify-between ${
                checkoutStatus.type === "success"
                  ? "bg-emerald-950/60 border border-emerald-500/40 text-emerald-300"
                  : "bg-rose-950/60 border border-rose-500/40 text-rose-300"
              }`}>
                <div className="flex items-center gap-2">
                  <span>{checkoutStatus.type === "success" ? "✓" : "⚠"}</span>
                  <span>{checkoutStatus.message}</span>
                </div>
                <button onClick={() => setCheckoutStatus(null)} className="text-slate-400 hover:text-white">✕</button>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {(billingInfo?.plans || []).map((plan) => {
                const isCurrent = currentSubscription?.tier === plan.tier;
                return (
                  <div
                    key={plan.tier}
                    className={`rounded-xl p-5 flex flex-col justify-between transition ${
                      isCurrent
                        ? "bg-cyan-950/30 border-2 border-cyan-500/60 shadow-lg shadow-cyan-500/10"
                        : "bg-slate-900/60 border border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono uppercase text-cyan-400 font-bold tracking-wider">
                          {plan.tier}
                        </span>
                        {isCurrent && (
                          <span className="px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 text-[10px] font-bold border border-cyan-500/30">
                            ACTIVE
                          </span>
                        )}
                      </div>
                      <h3 className="text-base font-bold text-white mt-1">{plan.name}</h3>
                      <div className="mt-3">
                        <span className="text-2xl font-extrabold text-white">
                          {plan.price_inr === 0 ? "Free" : `₹${plan.price_inr.toLocaleString()}`}
                        </span>
                        {plan.price_inr > 0 && <span className="text-xs text-slate-500"> /mo</span>}
                      </div>
                      <ul className="mt-4 space-y-2 text-xs text-slate-300">
                        {plan.features.map((feat, idx) => (
                          <li key={idx} className="flex items-start gap-1.5">
                            <span className="text-cyan-400 mt-0.5">✓</span>
                            <span>{feat}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="mt-6">
                      {isCurrent ? (
                        <button
                          disabled
                          className="w-full py-2.5 rounded-lg text-xs font-semibold bg-cyan-950/60 text-cyan-400 border border-cyan-500/30 cursor-default flex items-center justify-center gap-1.5"
                        >
                          <span>✓ Current Plan</span>
                        </button>
                      ) : plan.tier === "FREE" ? (
                        <button
                          disabled
                          className="w-full py-2.5 rounded-lg text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700 cursor-default"
                        >
                          Community Default
                        </button>
                      ) : !billingInfo?.configured ? (
                        <button
                          onClick={() => handleSandboxUnlock(plan.tier)}
                          disabled={checkoutLoading === plan.tier}
                          className="w-full py-2.5 rounded-lg text-xs font-bold bg-cyan-500 hover:bg-cyan-400 text-slate-950 transition flex items-center justify-center gap-2"
                        >
                          {checkoutLoading === plan.tier ? (
                            <span className="animate-pulse">Unlocking...</span>
                          ) : (
                            <span>Unlock &amp; Download</span>
                          )}
                        </button>
                      ) : (
                        <button
                          onClick={() => handleInitiateCheckout(plan.tier, plan.name)}
                          disabled={checkoutLoading === plan.tier}
                          className="w-full py-2.5 rounded-lg text-xs font-bold bg-cyan-500 hover:bg-cyan-400 text-slate-950 transition flex items-center justify-center gap-2"
                        >
                          {checkoutLoading === plan.tier ? (
                            <span className="animate-pulse">Processing...</span>
                          ) : (
                            <span>Subscribe &amp; Download</span>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
