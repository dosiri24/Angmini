/**
 * 메시지 목록 컴포넌트
 * Why: 메시지들을 스크롤 가능한 영역에 표시, 새 메시지 시 자동 스크롤
 */
import { useEffect, useRef } from 'react';
import type { Message } from '../../types';
import { MessageItem } from './MessageItem';
import './MessageList.css';

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // 새 메시지 추가 시 하단으로 자동 스크롤
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="message-list message-list-empty">
        <p>💬 대화를 시작해보세요!</p>
        <p className="hint">일정을 추가하거나 질문해보세요</p>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
