import type { NextConfig } from "next";

const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.ygoprodeck.com",
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/static/cards/:path*",
        destination: `${BACKEND_URL}/static/cards/:path*`,
      },
    ];
  },
};

export default nextConfig;
