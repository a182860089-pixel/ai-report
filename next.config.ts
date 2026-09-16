import type { NextConfig } from "next";

// Server components and browser /api/v1 rewrites share API_BASE (see .env.local).
const API_ORIGIN = (process.env.API_BASE || process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000").replace(
  /\/$/,
  ""
);

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${API_ORIGIN}/api/v1/:path*`
      }
    ];
  }
};

export default nextConfig;
