import type { NextConfig } from "next";
// @ts-expect-error - next-pwa doesn't have TypeScript types
import withPWA from "next-pwa";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  turbopack: {
    root: "/Users/zhuge/dev/ai-assistant-prototype",
  },
};

export default process.env.NODE_ENV === "development"
  ? nextConfig
  : withPWA({
      dest: "public",
      disable: false,
      register: true,
      skipWaiting: true,
    })(nextConfig);
