/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  webpack: (config, { isServer, dev }) => {
    // Exclude heavy WASM bundles from server compilation
    if (isServer) {
      config.externals = config.externals || [];
      config.externals.push("@mediapipe/tasks-vision");
    }

    // Windows occasionally fails temporary cache-file renames in dev mode
    // (ENOENT in .next/cache/webpack). Disable filesystem cache for dev only.
    if (dev) {
      config.cache = false;
    }

    return config;
  },
};

export default nextConfig;
