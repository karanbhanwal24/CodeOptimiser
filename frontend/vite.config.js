import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/optimize": "http://localhost:8001",
      "/analysis": "http://localhost:8001",
      "/metrics": "http://localhost:8001",
      "/health": "http://localhost:8001"
    }
  }
});
