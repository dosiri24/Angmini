/**
 * 월간 달력 컴포넌트
 * Why: 달력 그리드(7열 x 6행)로 월간 일정 개요 표시
 */
import { useMemo } from 'react';
import { getDatesWithSchedules } from './dummyData';
import './MonthCalendar.css';

interface MonthCalendarProps {
  currentMonth: Date;
  onMonthChange: (date: Date) => void;
  onDateSelect: (date: Date) => void;
}

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];

export function MonthCalendar({
  currentMonth,
  onMonthChange,
  onDateSelect,
}: MonthCalendarProps) {
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();

  /** 달력 그리드 데이터 생성 */
  const calendarDays = useMemo(() => {
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDayOfWeek = firstDay.getDay();
    const daysInMonth = lastDay.getDate();

    const days: (number | null)[] = [];

    // 이전 달 빈 칸
    for (let i = 0; i < startDayOfWeek; i++) {
      days.push(null);
    }

    // 현재 달 날짜
    for (let d = 1; d <= daysInMonth; d++) {
      days.push(d);
    }

    // 6행 채우기 (42칸)
    while (days.length < 42) {
      days.push(null);
    }

    return days;
  }, [year, month]);

  /** 일정 있는 날짜 */
  const datesWithSchedules = useMemo(
    () => getDatesWithSchedules(year, month),
    [year, month]
  );

  /** 오늘 날짜 */
  const today = new Date();
  const isToday = (day: number) =>
    today.getFullYear() === year &&
    today.getMonth() === month &&
    today.getDate() === day;

  /** 이전/다음 월 이동 */
  const goToPrevMonth = () => {
    onMonthChange(new Date(year, month - 1, 1));
  };

  const goToNextMonth = () => {
    onMonthChange(new Date(year, month + 1, 1));
  };

  /** 날짜 클릭 */
  const handleDateClick = (day: number) => {
    onDateSelect(new Date(year, month, day));
  };

  return (
    <div className="month-calendar">
      {/* 헤더: 월 표시 + 네비게이션 */}
      <div className="calendar-header">
        <button className="nav-btn" onClick={goToPrevMonth}>
          ‹
        </button>
        <span className="current-month">
          {year}년 {month + 1}월
        </span>
        <button className="nav-btn" onClick={goToNextMonth}>
          ›
        </button>
      </div>

      {/* 요일 헤더 */}
      <div className="weekday-header">
        {WEEKDAYS.map((day, idx) => (
          <div
            key={day}
            className={`weekday ${idx === 0 ? 'sunday' : idx === 6 ? 'saturday' : ''}`}
          >
            {day}
          </div>
        ))}
      </div>

      {/* 달력 그리드 */}
      <div className="calendar-grid">
        {calendarDays.map((day, idx) => {
          const dayOfWeek = idx % 7;
          const isSunday = dayOfWeek === 0;
          const isSaturday = dayOfWeek === 6;
          const hasSchedule = day !== null && datesWithSchedules.has(day);

          return (
            <div
              key={idx}
              className={`calendar-cell ${day === null ? 'empty' : ''} ${
                day !== null && isToday(day) ? 'today' : ''
              } ${isSunday ? 'sunday' : ''} ${isSaturday ? 'saturday' : ''}`}
              onClick={() => day !== null && handleDateClick(day)}
            >
              {day !== null && (
                <>
                  <span className="day-number">{day}</span>
                  {hasSchedule && <span className="schedule-dot" />}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
