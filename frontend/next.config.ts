import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  
  // Add this for React Markdown compatibility
  webpack: (config) => {
    config.resolve.fallback = { fs: false, path: false };
    return config;
  },
};

export default nextConfig;