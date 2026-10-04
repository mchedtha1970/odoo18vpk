import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/vpk_mobile_barcode/static/app/",
  build: {
    outDir: "../static/app",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/vpk_barcode": "http://127.0.0.1:8069",
      "/web": "http://127.0.0.1:8069",
    },
  },
});
