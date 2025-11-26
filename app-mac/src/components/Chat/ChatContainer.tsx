/**
 * 채팅 컨테이너 컴포넌트
 * Why: 메시지 목록과 입력 영역을 통합 관리
 */
import type { Message } from '../../types';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import './ChatContainer.css';

interface ChatContainerProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  isLoading?: boolean;
}

export function ChatContainer({
  messages,
  onSendMessage,
  isLoading = false,
}: ChatContainerProps) {
  return (
    <div className="chat-container">
      <MessageList messages={messages} />
      <MessageInput onSend={onSendMessage} disabled={isLoading} />
    </div>
  );
}
