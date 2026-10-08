import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  ...(process.env.NETLIFY === "true"
    ? { typescript: { tsconfigPath: "tsconfig.netlify.json" } }
    : {}),
};

export default nextConfig;
