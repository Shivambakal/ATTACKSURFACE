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
      process.env.EXT_PUBLIC_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "https://attacksurface-api.vercel.app";
    return [
      {
        source: "/api/:path*",
        destination: `${apiTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
