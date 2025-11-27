/**
 * 메시지 상태 관리 훅
 * Why: 채팅 메시지 목록을 중앙에서 관리, 추가/삭제 로직 캡슐화
 *      로컬 캐시 지원으로 앱 재시작 시 대화 내역 복원
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import type { Message, MessageType } from '../types';
import { loadMessages, saveMessages, clearMessages as clearCachedMessages } from '../utils/localCache';

// 유니크 ID 생성
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function useMessages() {
  // 초기값을 캐시에서 로드
  const [messages, setMessages] = useState<Message[]>(() => loadMessages());
  const isInitialMount = useRef(true);

  // 메시지 변경 시 자동 저장 (초기 로드 제외)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    saveMessages(messages);
  }, [messages]);

  // 메시지 추가
  const addMessage = useCallback(
    (content: string, type: MessageType): Message => {
      const newMessage: Message = {
        id: generateId(),
        type,
        content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, newMessage]);
      return newMessage;
    },
    []
  );

  // 사용자 메시지 추가 (편의 함수)
  const addUserMessage = useCallback(
    (content: string) => addMessage(content, 'user'),
    [addMessage]
  );

  // 봇 메시지 추가 (편의 함수)
  const addBotMessage = useCallback(
    (content: string) => addMessage(content, 'bot'),
    [addMessage]
  );

  // 시스템 메시지 추가 (편의 함수)
  const addSystemMessage = useCallback(
    (content: string) => addMessage(content, 'system'),
    [addMessage]
  );

  // 메시지 전체 초기화 (캐시도 함께 삭제)
  const clearMessages = useCallback(() => {
    setMessages([]);
    clearCachedMessages();
  }, []);

  return {
    messages,
    addMessage,
    addUserMessage,
    addBotMessage,
    addSystemMessage,
    clearMessages,
  };
}
