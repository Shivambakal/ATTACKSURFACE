import React from "react";
import PublicNav from "@/components/PublicNav";
import PublicFooter from "@/components/PublicFooter";
import WhiteAesthetic3DBackground from "@/components/WhiteAesthetic3DBackground";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative min-h-screen selection:bg-cyan-500 selection:text-slate-950 flex flex-col transition-colors duration-500 bg-black text-slate-100">
      <WhiteAesthetic3DBackground />
      <div className="relative z-10 flex flex-col min-h-screen">
        <PublicNav />
        <main className="flex-1 w-full">{children}</main>
        <PublicFooter />
      </div>
    </div>
  );
}
