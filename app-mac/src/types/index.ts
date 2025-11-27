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
  id: number;
  title: string;
  date: string; // YYYY-MM-DD
  startTime: string | null; // HH:MM
  endTime: string | null; // HH:MM
  location: string | null;
  category: ScheduleCategory;
  status: '대기' | '완료';
}

// 백엔드 응답 형식 (snake_case)
export interface ScheduleFromServer {
  id: number;
  title: string;
  date: string;
  start_time: string | null;
  end_time: string | null;
  location: string | null;
  category: string;
  status: string;
}

// ============================================================
// 동기화 관련 타입
// ============================================================

// 동기화 액션 타입
export type SyncAction = 'add' | 'update' | 'delete' | 'full_sync';

// 단일 일정 변경 이벤트
export interface ScheduleSyncEvent {
  action: 'add' | 'update' | 'delete';
  schedule: ScheduleFromServer;
  sync_timestamp: string;
}

// 전체 동기화 이벤트
export interface ScheduleFullSyncEvent {
  action: 'full_sync';
  schedules: ScheduleFromServer[];
  sync_timestamp: string;
}

// 동기화 이벤트 (union type)
export type SyncEvent = ScheduleSyncEvent | ScheduleFullSyncEvent;
