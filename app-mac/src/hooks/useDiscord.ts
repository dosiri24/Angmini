/**
 * Discord API 연동 훅
 * Why: Discord 채널을 통해 백엔드와 메시지 송수신
 * Note: Tauri HTTP plugin을 사용하여 CORS 문제 우회
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import { fetch } from '@tauri-apps/plugin-http';
import logger from '../utils/logger';

const MODULE = 'useDiscord';
const DISCORD_API_BASE = 'https://discord.com/api/v10';
const STORAGE_KEY = 'angmini_discord_config';
const POLL_INTERVAL = 1500; // 1.5초 간격 폴링

// 프론트엔드 메시지 마킹용 prefix
// Why: 봇 토큰으로 보내므로 백엔드가 "자기 메시지"로 인식하는 문제 해결
// 백엔드는 이 prefix가 있으면 처리하고, 없으면 자신의 응답으로 무시
const USER_MESSAGE_PREFIX = '[DESKTOP_USER] ';

// 환경변수에서 기본값 로드 (백엔드와 동일한 변수명 사용)
const ENV_CONFIG = {
  botToken: import.meta.env.DISCORD_BOT_TOKEN || '',
  channelId: import.meta.env.DISCORD_CHANNEL_ID || '',
  botUserId: import.meta.env.DISCORD_BOT_USER_ID || '',
};

logger.info(MODULE, 'ENV_CONFIG loaded', {
  botToken: ENV_CONFIG.botToken ? `SET (${ENV_CONFIG.botToken.slice(0, 10)}...)` : 'EMPTY',
  channelId: ENV_CONFIG.channelId || 'EMPTY',
  botUserId: ENV_CONFIG.botUserId || 'EMPTY',
});

interface DiscordConfig {
  botToken: string;
  channelId: string;
  botUserId: string; // 봇의 응답만 필터링하기 위함
}

interface DiscordMessage {
  id: string;
  content: string;
  author: {
    id: string;
    username: string;
    bot?: boolean;
  };
  timestamp: string;
}

interface UseDiscordReturn {
  isConfigured: boolean;
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<boolean>;
  onBotMessage: (callback: (content: string) => void) => void;
  configure: (config: DiscordConfig) => void;
  clearConfig: () => void;
}

// 초기 설정값 결정: localStorage > 환경변수
function getInitialConfig(): DiscordConfig | null {
  logger.debug(MODULE, 'getInitialConfig() called');

  // localStorage 우선
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      logger.info(MODULE, 'Config loaded from localStorage', { channelId: parsed.channelId });
      return parsed;
    } catch (e) {
      logger.warn(MODULE, 'Failed to parse localStorage config, removing', { error: String(e) });
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  // 환경변수에서 로드
  if (ENV_CONFIG.botToken && ENV_CONFIG.channelId && ENV_CONFIG.botUserId) {
    logger.info(MODULE, 'Config loaded from ENV', { channelId: ENV_CONFIG.channelId });
    return ENV_CONFIG;
  }

  logger.warn(MODULE, 'No valid config found');
  return null;
}

export function useDiscord(): UseDiscordReturn {
  logger.debug(MODULE, 'useDiscord hook initializing');

  const [config, setConfig] = useState<DiscordConfig | null>(getInitialConfig);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastMessageIdRef = useRef<string | null>(null);
  const botMessageCallbackRef = useRef<((content: string) => void) | null>(null);
  // 우리가 보낸 메시지 ID 추적 (폴링 시 중복 표시 방지)
  const sentMessageIdsRef = useRef<Set<string>>(new Set());

  logger.debug(MODULE, 'Initial state', {
    isConfigured: !!config,
    channelId: config?.channelId || 'null'
  });

  // 설정 저장
  const configure = useCallback((newConfig: DiscordConfig) => {
    logger.info(MODULE, 'configure() called', { channelId: newConfig.channelId });
    setConfig(newConfig);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newConfig));
    setError(null);
  }, []);

  // 설정 초기화
  const clearConfig = useCallback(() => {
    logger.info(MODULE, 'clearConfig() called');
    setConfig(null);
    localStorage.removeItem(STORAGE_KEY);
    lastMessageIdRef.current = null;
  }, []);

  // 메시지 전송
  const sendMessage = useCallback(
    async (content: string): Promise<boolean> => {
      logger.info(MODULE, 'sendMessage() called', { contentLength: content.length });

      if (!config) {
        logger.error(MODULE, 'sendMessage failed: no config');
        setError('Discord 설정이 필요합니다');
        return false;
      }

      setIsLoading(true);
      setError(null);

      const url = `${DISCORD_API_BASE}/channels/${config.channelId}/messages`;
      logger.debug(MODULE, 'Sending POST request', { url });

      try {
        // prefix 추가하여 백엔드가 사용자 메시지로 인식하도록 함
        const prefixedContent = `${USER_MESSAGE_PREFIX}${content}`;
        logger.debug(MODULE, 'Calling Tauri fetch...', { prefixedContent: prefixedContent.slice(0, 50) });

        const response = await fetch(url, {
          method: 'POST',
          headers: {
            Authorization: `Bot ${config.botToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ content: prefixedContent }),
        });

        logger.debug(MODULE, 'Fetch response received', {
          status: response.status,
          ok: response.ok
        });

        if (!response.ok) {
          const errorText = await response.text();
          logger.error(MODULE, 'Discord API error response', {
            status: response.status,
            body: errorText
          });
          let errorData;
          try {
            errorData = JSON.parse(errorText);
          } catch {
            errorData = { message: errorText };
          }
          throw new Error(errorData.message || `HTTP ${response.status}`);
        }

        const responseData = await response.json();
        logger.info(MODULE, 'Message sent successfully', { messageId: responseData.id });
        // 보낸 메시지 ID 저장 (폴링 시 중복 표시 방지)
        sentMessageIdsRef.current.add(responseData.id);
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : '전송 실패';
        logger.error(MODULE, 'sendMessage exception', {
          error: message,
          stack: err instanceof Error ? err.stack : undefined
        });
        setError(message);
        return false;
      } finally {
        setIsLoading(false);
        logger.debug(MODULE, 'sendMessage completed');
      }
    },
    [config]
  );

  // 봇 메시지 콜백 등록
  const onBotMessage = useCallback(
    (callback: (content: string) => void) => {
      logger.debug(MODULE, 'onBotMessage callback registered');
      botMessageCallbackRef.current = callback;
    },
    []
  );

  // 새 메시지 폴링
  useEffect(() => {
    logger.info(MODULE, 'Polling useEffect triggered', { hasConfig: !!config });

    if (!config) {
      logger.debug(MODULE, 'No config, skipping polling setup');
      return;
    }

    let pollCount = 0;

    const pollMessages = async () => {
      pollCount++;
      logger.debug(MODULE, `pollMessages() #${pollCount}`);

      try {
        const url = new URL(
          `${DISCORD_API_BASE}/channels/${config.channelId}/messages`
        );
        url.searchParams.set('limit', '10');
        if (lastMessageIdRef.current) {
          url.searchParams.set('after', lastMessageIdRef.current);
        }

        logger.debug(MODULE, 'Polling GET request', {
          url: url.toString(),
          afterId: lastMessageIdRef.current
        });

        const response = await fetch(url.toString(), {
          headers: {
            Authorization: `Bot ${config.botToken}`,
          },
        });

        logger.debug(MODULE, 'Poll response', { status: response.status });

        if (!response.ok) {
          logger.warn(MODULE, 'Poll request failed', { status: response.status });
          return;
        }

        const messages: DiscordMessage[] = await response.json();
        logger.debug(MODULE, 'Poll received messages', { count: messages.length });

        if (messages.length === 0) return;

        // 오래된 순으로 정렬 (API는 최신순으로 반환)
        const sortedMessages = messages.reverse();

        // 마지막 메시지 ID 업데이트
        const latestId = sortedMessages[sortedMessages.length - 1].id;
        lastMessageIdRef.current = latestId;
        logger.debug(MODULE, 'Updated lastMessageId', { latestId });

        // 봇 메시지만 필터링하여 콜백 호출
        for (const msg of sortedMessages) {
          logger.debug(MODULE, 'Processing message', {
            id: msg.id,
            authorId: msg.author.id,
            isBot: msg.author.bot,
            targetBotId: config.botUserId,
            isSentByUs: sentMessageIdsRef.current.has(msg.id)
          });

          // 우리가 보낸 메시지는 스킵 (중복 표시 방지)
          if (sentMessageIdsRef.current.has(msg.id)) {
            logger.debug(MODULE, 'Skipping our own sent message', { id: msg.id });
            continue;
          }

          // 봇이 작성한 메시지이고, 설정된 봇 ID와 일치하면 콜백 호출
          if (msg.author.bot && msg.author.id === config.botUserId) {
            logger.info(MODULE, 'Bot message detected, calling callback', {
              contentPreview: msg.content.slice(0, 50)
            });
            botMessageCallbackRef.current?.(msg.content);
          }
        }
      } catch (err) {
        logger.error(MODULE, 'pollMessages exception', {
          error: err instanceof Error ? err.message : String(err),
          stack: err instanceof Error ? err.stack : undefined
        });
      }
    };

    // 초기 실행 시 마지막 메시지 ID 설정 (기존 메시지 무시)
    const initLastMessageId = async () => {
      logger.info(MODULE, 'initLastMessageId() called');

      try {
        const url = `${DISCORD_API_BASE}/channels/${config.channelId}/messages?limit=1`;
        logger.debug(MODULE, 'Init fetch', { url });

        const response = await fetch(url, {
          headers: {
            Authorization: `Bot ${config.botToken}`,
          },
        });

        logger.debug(MODULE, 'Init response', { status: response.status, ok: response.ok });

        if (response.ok) {
          const messages: DiscordMessage[] = await response.json();
          if (messages.length > 0) {
            lastMessageIdRef.current = messages[0].id;
            logger.info(MODULE, 'Initialized lastMessageId', { id: messages[0].id });
          } else {
            logger.info(MODULE, 'No existing messages in channel');
          }
        } else {
          const errorText = await response.text();
          logger.error(MODULE, 'Init request failed', {
            status: response.status,
            body: errorText
          });
        }
      } catch (err) {
        logger.error(MODULE, 'initLastMessageId exception', {
          error: err instanceof Error ? err.message : String(err),
          stack: err instanceof Error ? err.stack : undefined
        });
      }
    };

    let intervalId: ReturnType<typeof setInterval> | null = null;
    let isCancelled = false;

    // 초기화 완료 후 폴링 시작 (타이밍 이슈 방지)
    const startPolling = async () => {
      logger.info(MODULE, 'Starting polling initialization');
      await initLastMessageId();

      // cleanup 중에 취소되었으면 폴링 시작하지 않음
      if (isCancelled) {
        logger.debug(MODULE, 'Polling cancelled before start');
        return;
      }

      logger.info(MODULE, 'Setting up polling interval', { interval: POLL_INTERVAL });
      intervalId = setInterval(pollMessages, POLL_INTERVAL);
    };

    startPolling();

    return () => {
      logger.info(MODULE, 'Cleaning up polling interval');
      isCancelled = true;
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [config]);

  logger.debug(MODULE, 'useDiscord returning', { isConfigured: !!config });

  return {
    isConfigured: !!config,
    isLoading,
    error,
    sendMessage,
    onBotMessage,
    configure,
    clearConfig,
  };
}
