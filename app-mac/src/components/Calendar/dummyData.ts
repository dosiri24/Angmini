/**
 * 더미 일정 데이터
 * Why: Phase 3 UI 테스트용 임시 데이터
 */
import type { Schedule, ScheduleCategory } from '../../types';

/** 오늘 날짜 기준 YYYY-MM-DD 문자열 생성 */
function getDateString(daysOffset: number = 0): string {
  const date = new Date();
  date.setDate(date.getDate() + daysOffset);
  return date.toISOString().split('T')[0];
}

/** 더미 일정 데이터 생성 */
export const DUMMY_SCHEDULES: Schedule[] = [
  // 어제
  {
    id: '1',
    title: '영어 스터디',
    date: getDateString(-1),
    startTime: '10:00',
    endTime: '12:00',
    category: '학업',
  },
  // 오늘
  {
    id: '2',
    title: '팀 미팅',
    date: getDateString(0),
    startTime: '09:00',
    endTime: '10:30',
    category: '업무',
  },
  {
    id: '3',
    title: '점심 약속',
    date: getDateString(0),
    startTime: '12:00',
    endTime: '13:30',
    category: '약속',
  },
  {
    id: '4',
    title: '운동',
    date: getDateString(0),
    startTime: '18:00',
    endTime: '19:30',
    category: '루틴',
  },
  // 내일
  {
    id: '5',
    title: '프로젝트 발표',
    date: getDateString(1),
    startTime: '14:00',
    endTime: '16:00',
    category: '학업',
  },
  {
    id: '6',
    title: '저녁 약속',
    date: getDateString(1),
    startTime: '19:00',
    endTime: '21:00',
    category: '약속',
  },
  // 이번 주
  {
    id: '7',
    title: '온라인 강의',
    date: getDateString(2),
    startTime: '10:00',
    endTime: '11:30',
    category: '학업',
  },
  {
    id: '8',
    title: '독서',
    date: getDateString(3),
    startTime: '20:00',
    endTime: '21:30',
    category: '개인',
  },
];

/** 특정 날짜의 일정 필터링 */
export function getSchedulesForDate(date: string): Schedule[] {
  return DUMMY_SCHEDULES.filter((s) => s.date === date);
}

/** 특정 월의 일정이 있는 날짜 목록 */
export function getDatesWithSchedules(year: number, month: number): Set<number> {
  const dates = new Set<number>();
  DUMMY_SCHEDULES.forEach((s) => {
    const [y, m, d] = s.date.split('-').map(Number);
    if (y === year && m === month + 1) {
      dates.add(d);
    }
  });
  return dates;
}
