import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/optimize": "http://localhost:8000",
      "/optimizations": "http://localhost:8000",
      "/analysis": "http://localhost:8000",
      "/metrics": "http://localhost:8000",
      "/health": "http://localhost:8000"
    }
  }
});
