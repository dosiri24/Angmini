/**
 * 일정 상태 관리 훅
 * Why: 봇 응답에서 추출한 일정 데이터를 중앙 관리하고 달력에 제공
 *      로컬 캐시 지원으로 오프라인 조회 및 앱 재시작 시 복원 가능
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import type { Schedule } from '../types';
import { parseScheduleData, hasScheduleData } from '../utils/scheduleParser';
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
  // 봇 메시지를 처리하여 일정 데이터 추출 및 저장
  processMessage: (content: string) => boolean;
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

  // 봇 메시지 처리 - 일정 데이터 추출 및 저장
  const processMessage = useCallback((content: string): boolean => {
    if (!hasScheduleData(content)) {
      logger.debug(MODULE, 'Message has no schedule data');
      return false;
    }

    const parsedSchedules = parseScheduleData(content);
    if (parsedSchedules.length === 0) {
      logger.warn(MODULE, 'Failed to parse schedule data from message');
      return false;
    }

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
      logger.info(MODULE, 'Schedules updated', {
        prevCount: prev.length,
        newCount: merged.length,
        added: newSchedules.length,
      });
      return merged;
    });

    setLastSyncTime(new Date());
    return true;
  }, []);

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
    getSchedulesForDate,
    getSchedulesInRange,
    getDatesWithSchedules,
    setSchedules,
    clearSchedules,
    lastSyncTime,
  };
}
