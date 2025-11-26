/**
 * SmartScheduler 타입 정의
 * Why: 앱 전체에서 사용하는 타입을 중앙 관리
 */

export type CharacterState = 'idle' | 'thinking' | 'action' | 'looking_down';
export type ContentMode = 'chat' | 'calendar';
export type MessageType = 'user' | 'bot' | 'system';
export type ScheduleCategory = '학업' | '약속' | '개인' | '업무' | '루틴' | '기타';

export interface Message {
  id: string;
  type: MessageType;
  content: string;
  timestamp: Date;
}

export interface Schedule {
  id: string;
  title: string;
  date: string;
  startTime: string;
  endTime: string;
  category: ScheduleCategory;
}
