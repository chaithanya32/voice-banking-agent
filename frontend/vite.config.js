
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "localhost",
    port: 5173,
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/voice": "http://127.0.0.1:8000",
      "/conversation": "http://127.0.0.1:8000",
      "/payments": "http://127.0.0.1:8000",
      "/balance": "http://127.0.0.1:8000",
    },
  },
});
