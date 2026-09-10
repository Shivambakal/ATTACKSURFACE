import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Keep browser requests same-origin so the session cookie survives the
    // frontend/API boundary.  The production fallback makes a Vercel deploy
    // usable even when API_INTERNAL_URL has not yet been added in its project
    // settings; local development continues to use the local API.
    const apiTarget =
      process.env.API_INTERNAL_URL ||
      // Compatibility with the existing Vercel project variable. It stays
      // server-only and is used solely by this same-origin rewrite.
      process.env.EXT_PUBLIC_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      (process.env.NODE_ENV === "production"
        ? "https://attacksurface-api.onrender.com"
        : "http://127.0.0.1:8000");
    return [
      {
        source: "/api/:path*",
        destination: `${apiTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
