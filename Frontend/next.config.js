const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // Aggressive alias resolution for Vercel compatibility
    config.resolve.alias = {
      ...config.resolve.alias,
      "@": path.resolve(__dirname),
      "@/lib": path.resolve(__dirname, "lib"),
      "@/hooks": path.resolve(__dirname, "hooks"),
      "@/components": path.resolve(__dirname, "components"),
    };
    
    // Ensure proper module resolution
    config.resolve.modules = [
      path.resolve(__dirname),
      "node_modules"
    ];

    return config;
  },
};

module.exports = nextConfig;

