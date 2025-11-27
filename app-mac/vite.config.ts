import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// @ts-expect-error process is a nodejs global
const host = process.env.TAURI_DEV_HOST;

// .env 파일 로드 (상위 디렉토리)
import { config } from "dotenv";
import { resolve } from "path";
config({ path: resolve(__dirname, "../.env") });

// https://vite.dev/config/
export default defineConfig(async () => ({
  plugins: [react()],

  // 백엔드와 동일한 환경변수명 사용 (VITE_ 접두사 불필요)
  define: {
    "import.meta.env.DISCORD_BOT_TOKEN": JSON.stringify(process.env.DISCORD_BOT_TOKEN || ""),
    "import.meta.env.DISCORD_CHANNEL_ID": JSON.stringify(process.env.DISCORD_CHANNEL_ID || ""),
    "import.meta.env.DISCORD_BOT_USER_ID": JSON.stringify(process.env.DISCORD_BOT_USER_ID || ""),
  },

  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent Vite from obscuring rust errors
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host
      ? {
          protocol: "ws",
          host,
          port: 1421,
        }
      : undefined,
    watch: {
      // 3. tell Vite to ignore watching `src-tauri`
      ignored: ["**/src-tauri/**"],
    },
  },
}));
