/**
 * 캐릭터 영역 컴포넌트
 * Why: 2D 캐릭터를 표시하는 상단 영역
 * Note: public/character/ 폴더의 이미지 사용
 */
import { useState } from 'react';
import type { CharacterState } from '../../types';
import './Character.css';

interface CharacterProps {
  state: CharacterState;
}

// 상태별 이미지 경로 (public 폴더 기준)
const stateImages: Record<CharacterState, string> = {
  idle: '/character/idle.png',
  thinking: '/character/thinking.png',
  action: '/character/action.png',
  looking_down: '/character/idle.png', // looking_down은 idle 이미지 재사용
};

// 이미지 로드 실패 시 대체 텍스트
const stateLabels: Record<CharacterState, string> = {
  idle: '😊 대기중',
  thinking: '🤔 생각중...',
  action: '✨ 완료!',
  looking_down: '👀 달력 보는 중',
};

export function Character({ state }: CharacterProps) {
  const [imageError, setImageError] = useState(false);

  const handleImageError = () => {
    setImageError(true);
  };

  return (
    <div className="character-container">
      <div className="character-image-wrapper">
        {!imageError ? (
          <img
            src={stateImages[state]}
            alt={stateLabels[state]}
            className="character-image"
            onError={handleImageError}
          />
        ) : (
          <div className="character-placeholder">
            <span className="character-state">{stateLabels[state]}</span>
          </div>
        )}
      </div>
    </div>
  );
}
