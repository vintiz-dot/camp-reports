import { resolve } from "node:path";
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

// base "./" -> works on GitHub Pages project sites and custom domains alike
export default defineConfig({
  base: "./",
  plugins: [tailwindcss()],
  build: {
    outDir: resolve(__dirname, "../docs"),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        student: resolve(__dirname, "student.html"),
      },
    },
  },
});
