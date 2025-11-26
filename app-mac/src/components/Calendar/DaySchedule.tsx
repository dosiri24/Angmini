/**
 * 일간 시간표 컴포넌트 (3일 뷰)
 * Why: 어제/오늘/내일 일정을 세로 시간축으로 표시
 */
import { useMemo } from 'react';
import type { Schedule } from '../../types';
import { ScheduleBlock } from './ScheduleBlock';
import './DaySchedule.css';

interface DayScheduleProps {
  selectedDate: Date;
  onBack: () => void;
  onScheduleClick?: (schedule: Schedule) => void;
  getSchedulesForDate: (date: string) => Schedule[];
}

/** 시간표 시작/끝 시간 */
const START_HOUR = 6;
const END_HOUR = 24;
const HOURS = Array.from({ length: END_HOUR - START_HOUR }, (_, i) => START_HOUR + i);

/** Date를 YYYY-MM-DD 문자열로 */
function formatDateString(date: Date): string {
  return date.toISOString().split('T')[0];
}

/** 요일 이름 */
const WEEKDAY_NAMES = ['일', '월', '화', '수', '목', '금', '토'];

export function DaySchedule({
  selectedDate,
  onBack,
  onScheduleClick,
  getSchedulesForDate,
}: DayScheduleProps) {
  /** 어제/오늘/내일 날짜 계산 */
  const threeDays = useMemo(() => {
    const days: Date[] = [];
    for (let offset = -1; offset <= 1; offset++) {
      const d = new Date(selectedDate);
      d.setDate(d.getDate() + offset);
      days.push(d);
    }
    return days;
  }, [selectedDate]);

  /** 각 날짜의 일정 */
  const schedulesPerDay = useMemo(() => {
    return threeDays.map((date) => ({
      date,
      dateString: formatDateString(date),
      schedules: getSchedulesForDate(formatDateString(date)),
    }));
  }, [threeDays]);

  /** 오늘 여부 확인 */
  const today = new Date();
  const isToday = (date: Date) =>
    today.getFullYear() === date.getFullYear() &&
    today.getMonth() === date.getMonth() &&
    today.getDate() === date.getDate();

  return (
    <div className="day-schedule">
      {/* 헤더 */}
      <div className="schedule-header">
        <button className="back-btn" onClick={onBack}>
          ← 월간
        </button>
        <span className="header-date">
          {selectedDate.getMonth() + 1}월 {selectedDate.getDate()}일
        </span>
      </div>

      {/* 3일 뷰 컨테이너 */}
      <div className="three-day-view">
        {/* 시간 레이블 (좌측) */}
        <div className="time-labels">
          {HOURS.map((hour) => (
            <div key={hour} className="time-label">
              {String(hour).padStart(2, '0')}:00
            </div>
          ))}
        </div>

        {/* 3일 칼럼 */}
        <div className="day-columns">
          {schedulesPerDay.map(({ date, schedules }) => (
            <div
              key={date.toISOString()}
              className={`day-column ${isToday(date) ? 'today' : ''}`}
            >
              {/* 날짜 헤더 */}
              <div className="day-header">
                <span className="day-name">{WEEKDAY_NAMES[date.getDay()]}</span>
                <span className="day-date">{date.getDate()}</span>
              </div>

              {/* 시간 그리드 + 일정 */}
              <div className="time-grid">
                {/* 시간 줄 */}
                {HOURS.map((hour) => (
                  <div key={hour} className="hour-line" />
                ))}

                {/* 일정 블록 */}
                {schedules.map((schedule) => (
                  <ScheduleBlock
                    key={schedule.id}
                    schedule={schedule}
                    onClick={onScheduleClick}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
