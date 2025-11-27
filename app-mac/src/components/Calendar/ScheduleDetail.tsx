/**
 * 일정 상세 정보 컴포넌트
 * Why: 일정 클릭 시 상세 정보(제목, 시간, 장소, 메모 등)를 표시
 */
import type { Schedule } from '../../types';
import { CATEGORY_COLORS } from './types';
import './ScheduleDetail.css';

interface ScheduleDetailProps {
  schedule: Schedule;
  onBack: () => void;
}

export function ScheduleDetail({ schedule, onBack }: ScheduleDetailProps) {
  const backgroundColor = CATEGORY_COLORS[schedule.category] || CATEGORY_COLORS['기타'];

  /** 시간 포맷팅 */
  const formatTime = () => {
    if (!schedule.startTime) return '시간 미정';
    if (schedule.endTime) {
      return `${schedule.startTime} - ${schedule.endTime}`;
    }
    return schedule.startTime;
  };

  /** 날짜 포맷팅 */
  const formatDate = () => {
    const [year, month, day] = schedule.date.split('-');
    return `${year}년 ${parseInt(month)}월 ${parseInt(day)}일`;
  };

  return (
    <div className="schedule-detail">
      {/* 헤더 */}
      <div className="detail-header">
        <button className="back-btn" onClick={onBack}>
          ← 시간표
        </button>
      </div>

      {/* 일정 정보 */}
      <div className="detail-content">
        {/* 카테고리 태그 */}
        <div className="category-tag" style={{ backgroundColor }}>
          {schedule.category}
        </div>

        {/* 제목 */}
        <h2 className="detail-title">{schedule.title}</h2>

        {/* 정보 섹션 */}
        <div className="info-section">
          {/* 날짜 */}
          <div className="info-row">
            <span className="info-icon">📅</span>
            <span className="info-text">{formatDate()}</span>
          </div>

          {/* 시간 */}
          <div className="info-row">
            <span className="info-icon">🕐</span>
            <span className="info-text">{formatTime()}</span>
          </div>

          {/* 장소 */}
          {schedule.location && (
            <div className="info-row">
              <span className="info-icon">📍</span>
              <span className="info-text">{schedule.location}</span>
            </div>
          )}

          {/* 상태 */}
          <div className="info-row">
            <span className="info-icon">📌</span>
            <span className={`status-badge ${schedule.status === '완료' ? 'completed' : 'pending'}`}>
              {schedule.status}
            </span>
          </div>
        </div>

        {/* 메모 섹션 */}
        <div className="memo-section">
          <h3 className="section-title">메모</h3>
          <div className="memo-content">
            {schedule.memo ? (
              <p>{schedule.memo}</p>
            ) : (
              <p className="empty-memo">메모가 없습니다</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
