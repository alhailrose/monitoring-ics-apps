import { fileURLToPath, URL } from "node:url"

import { defineConfig } from "vite"

const apiProxyTarget =
  process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000"

export default defineConfig({
  resolve: {
    alias: {
      "next/link": fileURLToPath(new URL("./src/next/link.tsx", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 4173,
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
  },
})
