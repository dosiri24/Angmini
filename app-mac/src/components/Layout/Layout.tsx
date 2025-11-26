/**
 * 3단 레이아웃 컴포넌트
 * Why: 캐릭터(상단) / 컨텐츠(중앙) / 토글(하단) 구조
 */
import { useState } from 'react';
import type { ContentMode } from '../../types';
import { useCharacter } from '../../hooks/useCharacter';
import { Character } from '../Character/Character';
import { Toggle } from '../Toggle/Toggle';
import './Layout.css';

export function Layout() {
  const [mode, setMode] = useState<ContentMode>('chat');
  const character = useCharacter();

  const handleModeChange = (newMode: ContentMode) => {
    setMode(newMode);
    character.onModeChange(newMode);
  };

  return (
    <div className="layout">
      {/* 상단: 캐릭터 영역 */}
      <Character state={character.state} />

      {/* 중앙: 컨텐츠 영역 */}
      <div className="content-area">
        {mode === 'chat' ? (
          <div className="placeholder-content">
            <p>💬 채팅 영역</p>
            <p className="placeholder-hint">Phase 2에서 구현 예정</p>
          </div>
        ) : (
          <div className="placeholder-content">
            <p>📅 달력 영역</p>
            <p className="placeholder-hint">Phase 3에서 구현 예정</p>
          </div>
        )}
      </div>

      {/* 하단: 토글 영역 */}
      <Toggle mode={mode} onModeChange={handleModeChange} />
    </div>
  );
}
