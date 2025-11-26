/**
 * 달력 컨테이너 컴포넌트
 * Why: 월간/일간 뷰 전환 및 상태 관리
 */
import { useState } from 'react';
import type { Schedule } from '../../types';
import type { CalendarView } from './types';
import { MonthCalendar } from './MonthCalendar';
import { DaySchedule } from './DaySchedule';
import './CalendarContainer.css';

interface CalendarContainerProps {
  onScheduleClick?: (schedule: Schedule) => void;
}

export function CalendarContainer({ onScheduleClick }: CalendarContainerProps) {
  const [view, setView] = useState<CalendarView>('month');
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(new Date());

  /** 월간 달력에서 날짜 클릭 → 일간 뷰로 전환 */
  const handleDateSelect = (date: Date) => {
    setSelectedDate(date);
    setView('day');
  };

  /** 일간 뷰에서 뒤로가기 → 월간 뷰로 복귀 */
  const handleBackToMonth = () => {
    setView('month');
  };

  /** 월 변경 (이전/다음) */
  const handleMonthChange = (date: Date) => {
    setCurrentMonth(date);
  };

  /** 일정 클릭 처리 */
  const handleScheduleClick = (schedule: Schedule) => {
    // TODO: 상세 정보 모달 또는 툴팁 표시
    console.log('Schedule clicked:', schedule);
    onScheduleClick?.(schedule);
  };

  return (
    <div className="calendar-container">
      {view === 'month' ? (
        <MonthCalendar
          currentMonth={currentMonth}
          onMonthChange={handleMonthChange}
          onDateSelect={handleDateSelect}
        />
      ) : (
        <DaySchedule
          selectedDate={selectedDate}
          onBack={handleBackToMonth}
          onScheduleClick={handleScheduleClick}
        />
      )}
    </div>
  );
}
