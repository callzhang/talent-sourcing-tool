import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/main.tsx", "src/types.ts", "src/**/*.test.{ts,tsx}"],
      thresholds: {
        functions: 100,
        lines: 100,
        statements: 100
      }
    }
  }
});
