/**
 * 봇 응답에서 일정 데이터를 추출하는 파싱 유틸리티
 * Why: 봇 응답의 [SCHEDULE_DATA]...[/SCHEDULE_DATA] 마커에서 JSON 배열 추출
 * Note: 자연어 키워드 파싱이 아닌, 구조화된 마커 기반 추출 (CLAUDE.md 준수)
 */
import type { Schedule, ScheduleFromServer, ScheduleCategory } from '../types';
import logger from './logger';

const MODULE = 'scheduleParser';

// 마커 정의
const SCHEDULE_DATA_START = '[SCHEDULE_DATA]';
const SCHEDULE_DATA_END = '[/SCHEDULE_DATA]';

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
function convertServerSchedule(server: ScheduleFromServer): Schedule {
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
