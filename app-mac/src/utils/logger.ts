/**
 * 디버그 로거 유틸리티
 * Why: 앱 크래시 전 상태를 추적하기 위한 타임스탬프 기반 로깅
 * localStorage에 로그를 저장하여 크래시 후에도 확인 가능
 */

const LOG_STORAGE_KEY = 'angmini_debug_logs';
const MAX_LOGS = 500; // 최대 로그 수

export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  module: string;
  message: string;
  data?: unknown;
}

function getTimestamp(): string {
  return new Date().toISOString();
}

function getStoredLogs(): LogEntry[] {
  try {
    const stored = localStorage.getItem(LOG_STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function storeLogs(logs: LogEntry[]): void {
  try {
    // 최대 로그 수 제한
    const trimmedLogs = logs.slice(-MAX_LOGS);
    localStorage.setItem(LOG_STORAGE_KEY, JSON.stringify(trimmedLogs));
  } catch {
    // 저장 실패 무시
  }
}

function log(level: LogLevel, module: string, message: string, data?: unknown): void {
  const entry: LogEntry = {
    timestamp: getTimestamp(),
    level,
    module,
    message,
    data,
  };

  // 콘솔 출력
  const consoleMsg = `[${entry.timestamp}] [${level}] [${module}] ${message}`;
  const consoleMethod = level === 'ERROR' ? console.error
    : level === 'WARN' ? console.warn
    : level === 'DEBUG' ? console.debug
    : console.log;

  if (data !== undefined) {
    consoleMethod(consoleMsg, data);
  } else {
    consoleMethod(consoleMsg);
  }

  // localStorage에 저장
  const logs = getStoredLogs();
  logs.push(entry);
  storeLogs(logs);
}

export const logger = {
  debug: (module: string, message: string, data?: unknown) => log('DEBUG', module, message, data),
  info: (module: string, message: string, data?: unknown) => log('INFO', module, message, data),
  warn: (module: string, message: string, data?: unknown) => log('WARN', module, message, data),
  error: (module: string, message: string, data?: unknown) => log('ERROR', module, message, data),

  // 저장된 로그 가져오기
  getLogs: (): LogEntry[] => getStoredLogs(),

  // 로그 클리어
  clearLogs: (): void => {
    localStorage.removeItem(LOG_STORAGE_KEY);
    console.log('[Logger] Logs cleared');
  },

  // 로그 덤프 (디버깅용)
  dumpLogs: (): string => {
    const logs = getStoredLogs();
    return logs.map(l =>
      `[${l.timestamp}] [${l.level}] [${l.module}] ${l.message}${l.data ? ' ' + JSON.stringify(l.data) : ''}`
    ).join('\n');
  },
};

// 전역에서 접근 가능하도록 window에 추가 (디버깅용)
if (typeof window !== 'undefined') {
  (window as unknown as { angminiLogger: typeof logger }).angminiLogger = logger;
}

export default logger;
