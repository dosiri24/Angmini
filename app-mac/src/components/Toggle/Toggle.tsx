/**
 * 토글 스위치 컴포넌트
 * Why: 채팅 ↔ 달력 모드 전환 (슬라이드 스위치 스타일)
 */
import type { ContentMode } from '../../types';
import './Toggle.css';

interface ToggleProps {
  mode: ContentMode;
  onModeChange: (mode: ContentMode) => void;
}

export function Toggle({ mode, onModeChange }: ToggleProps) {
  const handleClick = () => {
    onModeChange(mode === 'chat' ? 'calendar' : 'chat');
  };

  return (
    <div className="toggle-container">
      <div className="toggle-switch" onClick={handleClick}>
        {/* 배경 라벨 */}
        <span className="toggle-label left">💬 채팅</span>
        <span className="toggle-label right">📅 달력</span>

        {/* 슬라이더 */}
        <div className={`toggle-slider ${mode === 'calendar' ? 'right' : ''}`}>
          {mode === 'chat' ? '💬 채팅' : '📅 달력'}
        </div>
      </div>
    </div>
  );
}
