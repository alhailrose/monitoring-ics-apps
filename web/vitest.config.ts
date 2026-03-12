import { defineConfig } from "vitest/config"

export default defineConfig({
  resolve: {
    alias: {
      "next/link": new URL("./src/next/link.tsx", import.meta.url).pathname,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./vitest.setup.ts",
  },
})
