/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Stabilise webpack chunk IDs so the dev-server .next cache doesn't
  // reference stale chunk files after hot-reloads (fixes "Cannot find
  // module './138.js'" errors).
  webpack: (config, { isServer }) => {
    // Use deterministic chunk/module IDs instead of numeric
    config.optimization = {
      ...config.optimization,
      moduleIds: "deterministic",
      chunkIds: "deterministic",
    };

    // Exclude heavy WASM bundles from server compilation
    if (isServer) {
      config.externals = config.externals || [];
      config.externals.push("@mediapipe/tasks-vision");
    }

    return config;
  },
};

export default nextConfig;
