import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Bundles the shared Markdown renderer for the Django admin preview (architecture 8, 9).
export default defineConfig({
  plugins: [react()],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  build: {
    outDir: "../backend/apps/content/static/content/admin",
    emptyOutDir: false,
    copyPublicDir: false,
    lib: {
      entry: "src/admin-preview/main.tsx",
      formats: ["iife"],
      name: "BuditelMarkdownPreview",
      fileName: () => "markdown-preview.js",
    },
  },
});
