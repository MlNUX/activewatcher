import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/ui/",
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/v1": "http://127.0.0.1:8712",
      "/health": "http://127.0.0.1:8712",
      "/meta": "http://127.0.0.1:8712"
    }
  }
});
