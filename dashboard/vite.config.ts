import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import cesium from "vite-plugin-cesium";

export default defineConfig({
  // @ts-ignore
  plugins: [tailwindcss(), react(), cesium()],
  worker: {
    format: "es",
  },
  build: {
    target: "esnext",
  }
});
