/**
 * 달력 컴포넌트 내부 타입 정의
 * Why: 달력 뷰 상태 및 네비게이션 관련 타입 중앙 관리
 */

export type CalendarView = 'month' | 'day' | 'detail';

export interface CalendarState {
  view: CalendarView;
  selectedDate: Date;
  currentMonth: Date;
}

/** 카테고리별 색상 매핑 */
export const CATEGORY_COLORS: Record<string, string> = {
  '학업': '#3B82F6',   // 파랑
  '약속': '#22C55E',   // 초록
  '개인': '#A855F7',   // 보라
  '업무': '#F97316',   // 주황
  '루틴': '#06B6D4',   // 하늘색
  '기타': '#6B7280',   // 회색
};
