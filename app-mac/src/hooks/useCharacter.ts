/**
 * 캐릭터 상태 관리 훅
 * Why: 캐릭터의 표정/동작 상태를 중앙에서 관리
 */
import { useState, useCallback } from 'react';
import type { CharacterState, ContentMode } from '../types';

export function useCharacter() {
  const [state, setState] = useState<CharacterState>('idle');

  // 상태 변경 (일정 시간 후 idle로 복귀)
  const setTemporaryState = useCallback((newState: CharacterState, duration = 2000) => {
    setState(newState);
    setTimeout(() => setState('idle'), duration);
  }, []);

  // 모드 전환 시 캐릭터 상태 변경
  const onModeChange = useCallback((mode: ContentMode) => {
    setState(mode === 'calendar' ? 'looking_down' : 'idle');
  }, []);

  // 메시지 전송 시 thinking 상태
  const onMessageSend = useCallback(() => {
    setState('thinking');
  }, []);

  // 응답 수신 시 action 상태
  const onMessageReceive = useCallback(() => {
    setTemporaryState('action', 2000);
  }, [setTemporaryState]);

  return {
    state,
    setState,
    onModeChange,
    onMessageSend,
    onMessageReceive,
  };
}
