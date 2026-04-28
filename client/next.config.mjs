import { existsSync, readFileSync } from "fs";
import { join } from "path";

/** Load client/_env.local into process.env (same keys as .env.local; optional alternate filename). */
function loadUnderscoreEnvLocal() {
  const p = join(process.cwd(), "_env.local");
  if (!existsSync(p)) return;
  const text = readFileSync(p, "utf8");
  for (const line of text.split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const eq = t.indexOf("=");
    if (eq <= 0) continue;
    const key = t.slice(0, eq).trim();
    let val = t.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (key && process.env[key] === undefined) {
      process.env[key] = val;
    }
  }
}

loadUnderscoreEnvLocal();

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
