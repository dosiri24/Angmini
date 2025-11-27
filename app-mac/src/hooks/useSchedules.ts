/**
 * 일정 상태 관리 훅
 * Why: 봇 응답에서 추출한 일정 데이터를 중앙 관리하고 달력에 제공
 *      로컬 캐시 지원으로 오프라인 조회 및 앱 재시작 시 복원 가능
 *      동기화 이벤트 처리로 백엔드 DB와 실시간 동기화
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import type { Schedule } from '../types';
import {
  parseScheduleData,
  hasScheduleData,
  hasSyncEvent,
  parseSyncEvent,
  convertSyncEventToSchedules,
  convertServerSchedule,
} from '../utils/scheduleParser';
import {
  loadSchedules,
  saveSchedules,
  loadLastSyncTime,
  clearSchedules as clearCachedSchedules,
} from '../utils/localCache';
import logger from '../utils/logger';

const MODULE = 'useSchedules';

interface UseSchedulesReturn {
  schedules: Schedule[];
  // 봇 메시지를 처리하여 일정 데이터 추출 및 저장 (SCHEDULE_DATA + SCHEDULE_SYNC 모두 처리)
  processMessage: (content: string) => boolean;
  // 동기화 이벤트만 처리 (SCHEDULE_SYNC)
  processSyncEvent: (content: string) => boolean;
  // 특정 날짜의 일정 필터링
  getSchedulesForDate: (date: string) => Schedule[];
  // 특정 기간의 일정 필터링
  getSchedulesInRange: (startDate: string, endDate: string) => Schedule[];
  // 일정이 있는 날짜 목록 반환
  getDatesWithSchedules: () => Set<string>;
  // 수동으로 일정 추가 (로컬 캐시 복원 등에 사용)
  setSchedules: (schedules: Schedule[]) => void;
  // 일정 초기화
  clearSchedules: () => void;
  // 마지막 동기화 시간
  lastSyncTime: Date | null;
}

export function useSchedules(): UseSchedulesReturn {
  // 초기값을 캐시에서 로드
  const [schedules, setSchedulesState] = useState<Schedule[]>(() => loadSchedules());
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(() => loadLastSyncTime());
  const isInitialMount = useRef(true);

  // 일정 변경 시 자동 저장 (초기 로드 제외)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    saveSchedules(schedules);
  }, [schedules]);

  // 동기화 이벤트 처리 (SCHEDULE_SYNC)
  const processSyncEvent = useCallback((content: string): boolean => {
    if (!hasSyncEvent(content)) {
      logger.debug(MODULE, 'Message has no sync event');
      return false;
    }

    const syncEvent = parseSyncEvent(content);
    if (!syncEvent) {
      logger.warn(MODULE, 'Failed to parse sync event from message');
      return false;
    }

    // action 타입에 따라 처리
    if (syncEvent.action === 'full_sync') {
      // 전체 동기화: 기존 데이터를 완전히 대체
      const newSchedules = convertSyncEventToSchedules(syncEvent);
      setSchedulesState(newSchedules);
      logger.info(MODULE, 'Full sync completed', { count: newSchedules.length });
    } else if (syncEvent.action === 'add') {
      // 추가: 새 일정 추가
      const newSchedule = convertServerSchedule(syncEvent.schedule);
      setSchedulesState((prev) => {
        // 이미 존재하면 업데이트, 없으면 추가
        const exists = prev.some((s) => s.id === newSchedule.id);
        if (exists) {
          return prev.map((s) => (s.id === newSchedule.id ? newSchedule : s));
        }
        return [...prev, newSchedule];
      });
      logger.info(MODULE, 'Schedule added via sync', { id: newSchedule.id, title: newSchedule.title });
    } else if (syncEvent.action === 'update') {
      // 수정: 기존 일정 업데이트
      const updatedSchedule = convertServerSchedule(syncEvent.schedule);
      setSchedulesState((prev) =>
        prev.map((s) => (s.id === updatedSchedule.id ? updatedSchedule : s))
      );
      logger.info(MODULE, 'Schedule updated via sync', { id: updatedSchedule.id });
    } else if (syncEvent.action === 'delete') {
      // 삭제: 일정 제거
      const scheduleId = syncEvent.schedule.id;
      setSchedulesState((prev) => prev.filter((s) => s.id !== scheduleId));
      logger.info(MODULE, 'Schedule deleted via sync', { id: scheduleId });
    }

    setLastSyncTime(new Date());
    return true;
  }, []);

  // 봇 메시지 처리 - 일정 데이터 추출 및 저장 (SCHEDULE_DATA + SCHEDULE_SYNC 모두 처리)
  const processMessage = useCallback((content: string): boolean => {
    let processed = false;

    // 먼저 동기화 이벤트 확인 (우선순위 높음)
    if (hasSyncEvent(content)) {
      processed = processSyncEvent(content);
    }

    // SCHEDULE_DATA도 처리 (기존 방식 호환)
    if (hasScheduleData(content)) {
      const parsedSchedules = parseScheduleData(content);
      if (parsedSchedules.length > 0) {
        // 새로운 일정 데이터로 업데이트 (기존 데이터와 병합)
        setSchedulesState((prev) => {
          // ID 기준으로 중복 제거하며 병합
          const existingIds = new Set(prev.map((s) => s.id));
          const newSchedules = parsedSchedules.filter((s) => !existingIds.has(s.id));
          const updatedExisting = prev.map((existing) => {
            const updated = parsedSchedules.find((s) => s.id === existing.id);
            return updated || existing;
          });

          const merged = [...updatedExisting, ...newSchedules];
          logger.info(MODULE, 'Schedules updated from SCHEDULE_DATA', {
            prevCount: prev.length,
            newCount: merged.length,
            added: newSchedules.length,
          });
          return merged;
        });

        setLastSyncTime(new Date());
        processed = true;
      }
    }

    if (!processed) {
      logger.debug(MODULE, 'Message has no schedule data or sync event');
    }

    return processed;
  }, [processSyncEvent]);

  // 특정 날짜의 일정 필터링
  const getSchedulesForDate = useCallback(
    (date: string): Schedule[] => {
      return schedules.filter((s) => s.date === date);
    },
    [schedules]
  );

  // 특정 기간의 일정 필터링
  const getSchedulesInRange = useCallback(
    (startDate: string, endDate: string): Schedule[] => {
      return schedules.filter((s) => s.date >= startDate && s.date <= endDate);
    },
    [schedules]
  );

  // 일정이 있는 날짜 목록
  const getDatesWithSchedules = useCallback((): Set<string> => {
    return new Set(schedules.map((s) => s.date));
  }, [schedules]);

  // 일정 설정 (외부에서 직접 설정)
  const setSchedules = useCallback((newSchedules: Schedule[]) => {
    setSchedulesState(newSchedules);
    logger.info(MODULE, 'Schedules set directly', { count: newSchedules.length });
  }, []);

  // 일정 초기화 (캐시도 함께 삭제)
  const clearSchedules = useCallback(() => {
    setSchedulesState([]);
    setLastSyncTime(null);
    clearCachedSchedules();
    logger.info(MODULE, 'Schedules cleared');
  }, []);

  return {
    schedules,
    processMessage,
    processSyncEvent,
    getSchedulesForDate,
    getSchedulesInRange,
    getDatesWithSchedules,
    setSchedules,
    clearSchedules,
    lastSyncTime,
  };
}
