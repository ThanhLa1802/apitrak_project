import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],
    server: {
        host: "0.0.0.0",
        port: 3000,
        hmr: {
            // Required for HMR to reach the browser through Docker on Windows
            host: "localhost",
        },
        watch: {
            // Docker volumes on Windows don't emit inotify events — use polling
            usePolling: true,
        },
    },
});
