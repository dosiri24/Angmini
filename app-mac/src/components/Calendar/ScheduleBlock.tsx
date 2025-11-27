/**
 * 일정 블록 컴포넌트
 * Why: 일간 시간표에서 개별 일정을 시각적으로 표시
 */
import type { Schedule } from '../../types';
import { CATEGORY_COLORS } from './types';
import './ScheduleBlock.css';

interface ScheduleBlockProps {
  schedule: Schedule;
  onClick?: (schedule: Schedule) => void;
}

/** 시간 문자열을 분 단위로 변환 (HH:MM -> 분) */
function timeToMinutes(time: string): number {
  const [hours, minutes] = time.split(':').map(Number);
  return hours * 60 + minutes;
}

/** 시간표 시작 시간 (06:00) */
const START_HOUR = 6;
const START_MINUTES = START_HOUR * 60;

/** 시간당 픽셀 높이 */
const HOUR_HEIGHT = 50;

export function ScheduleBlock({ schedule, onClick }: ScheduleBlockProps) {
  // 시간이 없는 일정은 표시하지 않음 (종일 일정 등)
  if (!schedule.startTime) {
    return null;
  }

  const startMinutes = timeToMinutes(schedule.startTime);
  const endMinutes = schedule.endTime
    ? timeToMinutes(schedule.endTime)
    : startMinutes + 60; // 종료 시간 없으면 1시간 기본

  // 시작 위치 (06:00 기준 offset)
  const topOffset = ((startMinutes - START_MINUTES) / 60) * HOUR_HEIGHT;

  // 블록 높이 (최소 20px)
  const height = Math.max(20, ((endMinutes - startMinutes) / 60) * HOUR_HEIGHT);

  const backgroundColor = CATEGORY_COLORS[schedule.category] || CATEGORY_COLORS['기타'];

  const timeText = schedule.endTime
    ? `${schedule.startTime} - ${schedule.endTime}`
    : schedule.startTime;

  return (
    <div
      className="schedule-block"
      style={{
        top: `${topOffset}px`,
        height: `${height}px`,
        backgroundColor,
      }}
      onClick={() => onClick?.(schedule)}
    >
      <span className="block-title">{schedule.title}</span>
      <span className="block-time">{timeText}</span>
    </div>
  );
}
