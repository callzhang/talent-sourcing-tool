import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backendProxyTarget = process.env.BACKEND_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: backendProxyTarget,
        changeOrigin: true,
      },
    },
  },
});
