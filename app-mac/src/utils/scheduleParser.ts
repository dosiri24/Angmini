/**
 * 봇 응답에서 일정 데이터를 추출하는 파싱 유틸리티
 * Why: 봇 응답의 [SCHEDULE_DATA]...[/SCHEDULE_DATA] 마커에서 JSON 배열 추출
 *      [SCHEDULE_SYNC]...[/SCHEDULE_SYNC] 마커에서 동기화 이벤트 추출
 * Note: 자연어 키워드 파싱이 아닌, 구조화된 마커 기반 추출 (CLAUDE.md 준수)
 */
import type {
  Schedule,
  ScheduleFromServer,
  ScheduleCategory,
  SyncEvent,
  ScheduleSyncEvent,
  ScheduleFullSyncEvent,
} from '../types';
import logger from './logger';

const MODULE = 'scheduleParser';

// 마커 정의
const SCHEDULE_DATA_START = '[SCHEDULE_DATA]';
const SCHEDULE_DATA_END = '[/SCHEDULE_DATA]';
const SCHEDULE_SYNC_START = '[SCHEDULE_SYNC]';
const SCHEDULE_SYNC_END = '[/SCHEDULE_SYNC]';

// 유효한 카테고리 목록
const VALID_CATEGORIES: ScheduleCategory[] = ['학업', '약속', '개인', '업무', '루틴', '기타'];

/**
 * 봇 응답에서 일정 데이터 마커가 있는지 확인
 */
export function hasScheduleData(content: string): boolean {
  return content.includes(SCHEDULE_DATA_START) && content.includes(SCHEDULE_DATA_END);
}

/**
 * 봇 응답에서 일정 JSON 배열을 추출
 * @param content 봇 응답 전체 문자열
 * @returns 파싱된 Schedule 배열 또는 빈 배열
 */
export function parseScheduleData(content: string): Schedule[] {
  logger.debug(MODULE, 'parseScheduleData called', { contentLength: content.length });

  if (!hasScheduleData(content)) {
    logger.debug(MODULE, 'No schedule data markers found');
    return [];
  }

  try {
    // 마커 사이의 JSON 문자열 추출
    const startIdx = content.indexOf(SCHEDULE_DATA_START) + SCHEDULE_DATA_START.length;
    const endIdx = content.indexOf(SCHEDULE_DATA_END);

    if (startIdx >= endIdx) {
      logger.warn(MODULE, 'Invalid marker positions', { startIdx, endIdx });
      return [];
    }

    const jsonStr = content.slice(startIdx, endIdx).trim();
    logger.debug(MODULE, 'Extracted JSON string', { jsonStr: jsonStr.slice(0, 100) });

    // JSON 파싱
    const rawSchedules: ScheduleFromServer[] = JSON.parse(jsonStr);

    if (!Array.isArray(rawSchedules)) {
      logger.warn(MODULE, 'Parsed data is not an array');
      return [];
    }

    // 서버 형식 → 클라이언트 형식 변환
    const schedules: Schedule[] = rawSchedules.map(convertServerSchedule);
    logger.info(MODULE, 'Successfully parsed schedules', { count: schedules.length });

    return schedules;
  } catch (error) {
    logger.error(MODULE, 'Failed to parse schedule data', {
      error: error instanceof Error ? error.message : String(error),
    });
    return [];
  }
}

/**
 * 서버 형식(snake_case) → 클라이언트 형식(camelCase) 변환
 */
export function convertServerSchedule(server: ScheduleFromServer): Schedule {
  // 카테고리 검증 및 기본값 처리
  const category = VALID_CATEGORIES.includes(server.category as ScheduleCategory)
    ? (server.category as ScheduleCategory)
    : '기타';

  // 상태 검증
  const status = server.status === '완료' ? '완료' : '대기';

  return {
    id: server.id,
    title: server.title,
    date: server.date,
    startTime: server.start_time,
    endTime: server.end_time,
    location: server.location,
    memo: server.memo,
    category,
    status,
  };
}

/**
 * 봇 응답에서 SCHEDULE_DATA 마커를 제거하고 자연어 부분만 반환
 * Why: UI에 표시할 때는 마커 없이 깔끔하게 표시
 */
export function stripScheduleDataMarker(content: string): string {
  if (!hasScheduleData(content)) {
    return content;
  }

  const startIdx = content.indexOf(SCHEDULE_DATA_START);
  const endIdx = content.indexOf(SCHEDULE_DATA_END) + SCHEDULE_DATA_END.length;

  // 마커 영역 제거
  const before = content.slice(0, startIdx).trimEnd();
  const after = content.slice(endIdx).trimStart();

  return (before + (after ? '\n' + after : '')).trim();
}

// ============================================================
// 동기화 이벤트 파싱 (SCHEDULE_SYNC 마커)
// ============================================================

/**
 * 봇 응답에서 동기화 이벤트 마커가 있는지 확인
 */
export function hasSyncEvent(content: string): boolean {
  return content.includes(SCHEDULE_SYNC_START) && content.includes(SCHEDULE_SYNC_END);
}

/**
 * 봇 응답에서 동기화 이벤트를 추출
 * @param content 봇 응답 전체 문자열
 * @returns SyncEvent 또는 null
 */
export function parseSyncEvent(content: string): SyncEvent | null {
  logger.debug(MODULE, 'parseSyncEvent called', { contentLength: content.length });

  if (!hasSyncEvent(content)) {
    logger.debug(MODULE, 'No sync event markers found');
    return null;
  }

  try {
    // 마커 사이의 JSON 문자열 추출
    const startIdx = content.indexOf(SCHEDULE_SYNC_START) + SCHEDULE_SYNC_START.length;
    const endIdx = content.indexOf(SCHEDULE_SYNC_END);

    if (startIdx >= endIdx) {
      logger.warn(MODULE, 'Invalid sync marker positions', { startIdx, endIdx });
      return null;
    }

    const jsonStr = content.slice(startIdx, endIdx).trim();
    logger.debug(MODULE, 'Extracted sync JSON string', { jsonStr: jsonStr.slice(0, 100) });

    // JSON 파싱
    const rawEvent = JSON.parse(jsonStr);

    // action 필드 검증
    if (!rawEvent.action) {
      logger.warn(MODULE, 'Sync event missing action field');
      return null;
    }

    // action 타입에 따라 처리
    if (rawEvent.action === 'full_sync') {
      // 전체 동기화
      if (!Array.isArray(rawEvent.schedules)) {
        logger.warn(MODULE, 'Full sync event missing schedules array');
        return null;
      }
      const event: ScheduleFullSyncEvent = {
        action: 'full_sync',
        schedules: rawEvent.schedules,
        sync_timestamp: rawEvent.sync_timestamp || new Date().toISOString(),
      };
      logger.info(MODULE, 'Parsed full sync event', { count: event.schedules.length });
      return event;
    } else {
      // 단일 일정 변경 (add, update, delete)
      if (!rawEvent.schedule) {
        logger.warn(MODULE, 'Sync event missing schedule field');
        return null;
      }
      const event: ScheduleSyncEvent = {
        action: rawEvent.action as 'add' | 'update' | 'delete',
        schedule: rawEvent.schedule,
        sync_timestamp: rawEvent.sync_timestamp || new Date().toISOString(),
      };
      logger.info(MODULE, 'Parsed sync event', { action: event.action, id: event.schedule.id });
      return event;
    }
  } catch (error) {
    logger.error(MODULE, 'Failed to parse sync event', {
      error: error instanceof Error ? error.message : String(error),
    });
    return null;
  }
}

/**
 * 동기화 이벤트에서 Schedule 배열로 변환 (클라이언트 형식)
 */
export function convertSyncEventToSchedules(event: SyncEvent): Schedule[] {
  if (event.action === 'full_sync') {
    return event.schedules.map(convertServerSchedule);
  } else if (event.action === 'delete') {
    // delete의 경우 빈 배열 반환 (삭제 처리는 별도)
    return [];
  } else {
    return [convertServerSchedule(event.schedule)];
  }
}

/**
 * 봇 응답에서 SCHEDULE_SYNC 마커를 제거하고 자연어 부분만 반환
 */
export function stripSyncEventMarker(content: string): string {
  if (!hasSyncEvent(content)) {
    return content;
  }

  const startIdx = content.indexOf(SCHEDULE_SYNC_START);
  const endIdx = content.indexOf(SCHEDULE_SYNC_END) + SCHEDULE_SYNC_END.length;

  const before = content.slice(0, startIdx).trimEnd();
  const after = content.slice(endIdx).trimStart();

  return (before + (after ? '\n' + after : '')).trim();
}

/**
 * 모든 마커를 제거 (SCHEDULE_DATA + SCHEDULE_SYNC)
 */
export function stripAllMarkers(content: string): string {
  let result = stripScheduleDataMarker(content);
  result = stripSyncEventMarker(result);
  return result;
}
