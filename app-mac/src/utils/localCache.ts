/**
 * 로컬 캐시 유틸리티
 * Why: localStorage를 사용한 데이터 영속화, 앱 재시작 시 복원 지원
 */
import type { Message, Schedule } from '../types';
import logger from './logger';

const MODULE = 'localCache';

// 캐시 키 상수
const CACHE_KEYS = {
  MESSAGES: 'angmini_messages',
  SCHEDULES: 'angmini_schedules',
  LAST_SYNC: 'angmini_last_sync',
  VERSION: 'angmini_cache_version',
} as const;

// 현재 캐시 버전 (스키마 변경 시 증가)
const CURRENT_VERSION = 1;

// 최대 저장 메시지 수
const MAX_MESSAGES = 100;

/**
 * 캐시 버전 확인 및 마이그레이션
 * Why: 스키마 변경 시 구버전 데이터를 안전하게 처리
 */
function checkAndMigrateCache(): void {
  try {
    const storedVersion = localStorage.getItem(CACHE_KEYS.VERSION);
    const version = storedVersion ? parseInt(storedVersion, 10) : 0;

    if (version < CURRENT_VERSION) {
      // 버전이 다르면 캐시 초기화 (향후 마이그레이션 로직 추가 가능)
      logger.info(MODULE, 'Cache version mismatch, clearing cache', {
        stored: version,
        current: CURRENT_VERSION,
      });
      clearAllCache();
      localStorage.setItem(CACHE_KEYS.VERSION, String(CURRENT_VERSION));
    }
  } catch (error) {
    logger.error(MODULE, 'Failed to check cache version', { error });
  }
}

/**
 * 메시지 캐시 저장
 * Why: 최근 대화 내역을 저장하여 앱 재시작 시 복원
 */
export function saveMessages(messages: Message[]): void {
  try {
    // 최근 N개만 저장 (메모리/스토리지 관리)
    const recentMessages = messages.slice(-MAX_MESSAGES);

    // Message 객체의 timestamp를 ISO 문자열로 변환 (직렬화용)
    const serializable = recentMessages.map((m) => ({
      ...m,
      timestamp: m.timestamp.toISOString(),
    }));

    localStorage.setItem(CACHE_KEYS.MESSAGES, JSON.stringify(serializable));
    logger.debug(MODULE, 'Messages saved to cache', { count: serializable.length });
  } catch (error) {
    logger.error(MODULE, 'Failed to save messages', { error });
  }
}

/**
 * 메시지 캐시 로드
 * Why: 앱 시작 시 이전 대화 내역 복원
 */
export function loadMessages(): Message[] {
  try {
    checkAndMigrateCache();

    const stored = localStorage.getItem(CACHE_KEYS.MESSAGES);
    if (!stored) {
      logger.debug(MODULE, 'No cached messages found');
      return [];
    }

    const parsed = JSON.parse(stored) as Array<{
      id: string;
      type: 'user' | 'bot' | 'system';
      content: string;
      timestamp: string;
    }>;

    // timestamp 문자열을 Date 객체로 변환
    const messages: Message[] = parsed.map((m) => ({
      ...m,
      timestamp: new Date(m.timestamp),
    }));

    logger.info(MODULE, 'Messages loaded from cache', { count: messages.length });
    return messages;
  } catch (error) {
    logger.error(MODULE, 'Failed to load messages', { error });
    return [];
  }
}

/**
 * 일정 캐시 저장
 * Why: 오프라인에서도 달력에 일정 표시 가능
 */
export function saveSchedules(schedules: Schedule[]): void {
  try {
    localStorage.setItem(CACHE_KEYS.SCHEDULES, JSON.stringify(schedules));
    localStorage.setItem(CACHE_KEYS.LAST_SYNC, new Date().toISOString());
    logger.debug(MODULE, 'Schedules saved to cache', { count: schedules.length });
  } catch (error) {
    logger.error(MODULE, 'Failed to save schedules', { error });
  }
}

/**
 * 일정 캐시 로드
 * Why: 앱 시작 시 캐시된 일정 데이터로 달력 표시
 */
export function loadSchedules(): Schedule[] {
  try {
    checkAndMigrateCache();

    const stored = localStorage.getItem(CACHE_KEYS.SCHEDULES);
    if (!stored) {
      logger.debug(MODULE, 'No cached schedules found');
      return [];
    }

    const schedules = JSON.parse(stored) as Schedule[];
    logger.info(MODULE, 'Schedules loaded from cache', { count: schedules.length });
    return schedules;
  } catch (error) {
    logger.error(MODULE, 'Failed to load schedules', { error });
    return [];
  }
}

/**
 * 마지막 동기화 시간 로드
 * Why: UI에서 마지막 동기화 시점 표시 또는 동기화 필요 여부 판단
 */
export function loadLastSyncTime(): Date | null {
  try {
    const stored = localStorage.getItem(CACHE_KEYS.LAST_SYNC);
    if (!stored) return null;
    return new Date(stored);
  } catch (error) {
    logger.error(MODULE, 'Failed to load last sync time', { error });
    return null;
  }
}

/**
 * 메시지 캐시 삭제
 */
export function clearMessages(): void {
  try {
    localStorage.removeItem(CACHE_KEYS.MESSAGES);
    logger.info(MODULE, 'Messages cache cleared');
  } catch (error) {
    logger.error(MODULE, 'Failed to clear messages cache', { error });
  }
}

/**
 * 일정 캐시 삭제
 */
export function clearSchedules(): void {
  try {
    localStorage.removeItem(CACHE_KEYS.SCHEDULES);
    localStorage.removeItem(CACHE_KEYS.LAST_SYNC);
    logger.info(MODULE, 'Schedules cache cleared');
  } catch (error) {
    logger.error(MODULE, 'Failed to clear schedules cache', { error });
  }
}

/**
 * 전체 캐시 삭제
 * Why: 설정 초기화 또는 문제 해결 시 사용
 */
export function clearAllCache(): void {
  try {
    Object.values(CACHE_KEYS).forEach((key) => {
      localStorage.removeItem(key);
    });
    logger.info(MODULE, 'All cache cleared');
  } catch (error) {
    logger.error(MODULE, 'Failed to clear all cache', { error });
  }
}

/**
 * 캐시 상태 확인
 * Why: 디버깅 및 상태 모니터링
 */
export function getCacheStatus(): {
  messagesCount: number;
  schedulesCount: number;
  lastSync: Date | null;
  version: number;
} {
  try {
    const messages = loadMessages();
    const schedules = loadSchedules();
    const lastSync = loadLastSyncTime();
    const version = parseInt(localStorage.getItem(CACHE_KEYS.VERSION) || '0', 10);

    return {
      messagesCount: messages.length,
      schedulesCount: schedules.length,
      lastSync,
      version,
    };
  } catch (error) {
    logger.error(MODULE, 'Failed to get cache status', { error });
    return {
      messagesCount: 0,
      schedulesCount: 0,
      lastSync: null,
      version: 0,
    };
  }
}
