import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // RAG chat can exceed the default 30s rewrite-proxy timeout while the
  // upstream LLM answers (free OpenRouter models regularly take 40-60s).
  experimental: {
    proxyTimeout: 120_000,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
