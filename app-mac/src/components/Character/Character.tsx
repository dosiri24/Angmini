/**
 * 캐릭터 영역 컴포넌트
 * Why: 2D 캐릭터를 표시하는 상단 영역 (현재는 플레이스홀더)
 */
import type { CharacterState } from '../../types';
import './Character.css';

interface CharacterProps {
  state: CharacterState;
}

// 상태별 텍스트 (나중에 이미지로 교체)
const stateLabels: Record<CharacterState, string> = {
  idle: '😊 대기중',
  thinking: '🤔 생각중...',
  action: '✨ 완료!',
  looking_down: '👀 달력 보는 중',
};

export function Character({ state }: CharacterProps) {
  return (
    <div className="character-container">
      <div className="character-placeholder">
        <span className="character-state">{stateLabels[state]}</span>
      </div>
    </div>
  );
}
