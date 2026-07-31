import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backendProxyTarget = process.env.BACKEND_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    // The production alias can briefly serve a previous HTML document during a
    // deployment transition. Stable entry names prevent that document from
    // requesting an asset that no longer exists in the current deployment.
    rollupOptions: {
      output: {
        // v2 invalidates the original immutable app.js response already held
        // by existing browsers. Future stable entry assets revalidate on load.
        entryFileNames: "assets/app-v2.js",
        chunkFileNames: "assets/chunk-[name].js",
        assetFileNames: "assets/[name]-v2[extname]",
      },
    },
  },
  server: {
    proxy: {
      "/api": {
        target: backendProxyTarget,
        changeOrigin: true,
      },
    },
  },
});
