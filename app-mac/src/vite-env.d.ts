/// <reference types="vite/client" />

/**
 * Vite 환경변수 타입 정의
 * Why: TypeScript가 import.meta.env의 커스텀 변수를 인식하도록 함
 */
interface ImportMetaEnv {
  readonly DISCORD_BOT_TOKEN: string;
  readonly DISCORD_CHANNEL_ID: string;
  readonly DISCORD_BOT_USER_ID: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
