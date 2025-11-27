/**
 * 개별 메시지 컴포넌트
 * Why: 사용자/봇/시스템 메시지를 구분하여 표시
 */
import type { Message } from '../../types';
import './MessageItem.css';

interface MessageItemProps {
  message: Message;
}

export function MessageItem({ message }: MessageItemProps) {
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className={`message-wrapper ${message.type}`}>
      <div className={`message-item message-${message.type}`}>
        <div className="message-content">{message.content}</div>
      </div>
      {message.type !== 'system' && (
        <div className="message-time">{formatTime(message.timestamp)}</div>
      )}
    </div>
  );
}
