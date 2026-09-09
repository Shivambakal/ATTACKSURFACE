import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import CookieBanner from "@/components/CookieBanner";

export const metadata: Metadata = {
  metadataBase: new URL("https://attacksurface.online"),
  title: {
    template: "%s | AttackSurface Timeline",
    default: "AttackSurface Timeline — Bug Bounty Research Intelligence",
  },
  description:
    "Differential attack surface monitoring and security intelligence platform for authorized researchers.",
  openGraph: {
    title: "AttackSurface Timeline — Bug Bounty Research Intelligence",
    description: "Differential attack surface monitoring and security intelligence platform for authorized researchers.",
    url: "https://attacksurface.online",
    siteName: "AttackSurface Timeline",
    type: "website",
  },
  alternates: {
    canonical: "https://attacksurface.online",
  },
};

export const viewport: Viewport = {
  themeColor: "#020617",
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased selection:bg-cyan-500 selection:text-slate-950">
        <AuthProvider>
          {children}
          <CookieBanner />
        </AuthProvider>
      </body>
    </html>
  );
}
