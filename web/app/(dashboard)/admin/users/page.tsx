"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface AdminUser {
  id: number;
  email: string;
  role: string;
  is_admin: boolean;
  is_active: boolean;
  is_verified: boolean;
  created_at: string | null;
  session_count: number;
}

export default function AdminUsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  // Role modification state
  const [updatingUserId, setUpdatingUserId] = useState<number | null>(null);
  const [selectedRole, setSelectedRole] = useState<string>("");

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiFetch<AdminUser[]>("/api/v1/admin/users");
      setUsers(Array.isArray(res) ? res : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load user registry");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleRoleUpdate = async (userId: number, newRole: string) => {
    if (!newRole) return;
    setUpdatingUserId(userId);
    setError(null);
    setSuccessMessage(null);

    try {
      const res = await apiFetch<{
        success: boolean;
        user_id: number;
        email: string;
        role: string;
        is_admin: boolean;
        revoked_sessions: number;
      }>(`/api/v1/admin/users/${userId}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role: newRole }),
      });

      setSuccessMessage(
        `Updated ${res.email} to ${res.role} (is_admin=${res.is_admin}). ${res.revoked_sessions} active session(s) revoked.`
      );
      await loadUsers();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update user role");
    } finally {
      setUpdatingUserId(null);
    }
  };

  const filteredUsers = users.filter((u) =>
    u.email.toLowerCase().includes(search.toLowerCase().trim())
  );

  const getRoleBadge = (role: string) => {
    switch (role?.toUpperCase()) {
      case "OWNER":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "ADMIN":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      case "RESEARCHER":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/30";
      case "VIEWER":
        return "bg-slate-500/10 text-slate-400 border-slate-500/30";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Link
              href="/admin"
              className="text-xs font-mono text-slate-400 hover:text-slate-200 transition"
            >
              ADMIN
            </Link>
            <span className="text-xs text-slate-600">/</span>
            <span className="text-xs font-mono text-cyan-400">USERS</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
            Users &amp; Role-Based Access Control (RBAC)
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage administrative privilege boundaries, assign roles (OWNER, ADMIN, RESEARCHER, VIEWER), and revoke sessions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadUsers}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-xs font-mono text-slate-200 transition disabled:opacity-50 flex items-center gap-2"
          >
            <svg
              className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Refresh Users
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300 font-mono">
          [RBAC Error]: {error}
        </div>
      )}

      {successMessage && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs text-emerald-300 font-mono">
          [Success]: {successMessage}
        </div>
      )}

      {/* RBAC Rules Notice */}
      <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4 text-xs font-mono text-cyan-300/90 space-y-1">
        <div className="font-bold flex items-center gap-2 text-cyan-400">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          Strict RBAC Enforcement &amp; Session Invalidation
        </div>
        <p className="text-slate-400">
          Changing a user&apos;s role immediately syncs <code className="text-cyan-300">is_admin</code> and revokes all active session tokens in Redis/Postgres.
          The user will be required to re-authenticate with their new authorization boundaries.
        </p>
      </div>

      {/* Search Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative w-full max-w-sm">
          <input
            type="text"
            placeholder="Search users by email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2.5 top-2 text-xs text-slate-400 hover:text-white"
            >
              &times;
            </button>
          )}
        </div>
        <div className="text-xs font-mono text-slate-500">
          Total Users: {users.length}
        </div>
      </div>

      {/* User Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 overflow-hidden backdrop-blur-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="border-b border-slate-800 bg-slate-950/60 text-slate-400">
              <tr>
                <th className="py-3 px-4 font-semibold">User / Email</th>
                <th className="py-3 px-4 font-semibold">Current Role</th>
                <th className="py-3 px-4 font-semibold">Admin Flag</th>
                <th className="py-3 px-4 font-semibold">Active Sessions</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold">Created</th>
                <th className="py-3 px-4 font-semibold text-right">Modify Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No users matching criteria.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => {
                  const isCurrent = currentUser?.id === u.id;
                  const isBusy = updatingUserId === u.id;

                  return (
                    <tr key={u.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-white">{u.email}</span>
                          {isCurrent && (
                            <span className="px-1.5 py-0.2 rounded text-[9px] bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                              YOU
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-slate-500">ID #{u.id}</span>
                      </td>

                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[11px] font-bold border ${getRoleBadge(
                            u.role
                          )}`}
                        >
                          {u.role}
                        </span>
                      </td>

                      <td className="py-3 px-4">
                        {u.is_admin ? (
                          <span className="text-emerald-400 font-semibold flex items-center gap-1">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                            TRUE
                          </span>
                        ) : (
                          <span className="text-slate-500">FALSE</span>
                        )}
                      </td>

                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded bg-slate-800/80 text-slate-300 border border-slate-700/60">
                          {u.session_count} active
                        </span>
                      </td>

                      <td className="py-3 px-4">
                        {u.is_active ? (
                          <span className="text-emerald-400">ACTIVE</span>
                        ) : (
                          <span className="text-rose-400">DISABLED</span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-slate-500 text-[11px]">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : "--"}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <div className="inline-flex items-center gap-2">
                          <select
                            defaultValue={u.role}
                            disabled={isBusy}
                            onChange={(e) => {
                              const newRole = e.target.value;
                              if (newRole !== u.role) {
                                if (
                                  confirm(
                                    `Change role of ${u.email} from ${u.role} to ${newRole}? This will invalidate all active sessions for this user.`
                                  )
                                ) {
                                  handleRoleUpdate(u.id, newRole);
                                } else {
                                  e.target.value = u.role;
                                }
                              }
                            }}
                            className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-white focus:outline-none focus:border-cyan-500 disabled:opacity-50"
                          >
                            <option value="OWNER">OWNER</option>
                            <option value="ADMIN">ADMIN</option>
                            <option value="RESEARCHER">RESEARCHER</option>
                            <option value="VIEWER">VIEWER</option>
                          </select>
                          {isBusy && (
                            <span className="text-cyan-400 text-xs animate-spin">⟳</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
