"use client";

import React from "react";
import { useAuth } from "@/lib/auth";
import AdminSidebar from "./AdminSidebar";
import NormalSidebar from "./NormalSidebar";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export default function Sidebar({ collapsed, onToggleCollapse }: SidebarProps) {
  const { user } = useAuth();
  const isAdmin = user?.role === "OWNER" || user?.role === "ADMIN";

  if (isAdmin) {
    return <AdminSidebar collapsed={collapsed} onToggleCollapse={onToggleCollapse} />;
  }

  return <NormalSidebar collapsed={collapsed} onToggleCollapse={onToggleCollapse} />;
}

export { AdminSidebar, NormalSidebar };
