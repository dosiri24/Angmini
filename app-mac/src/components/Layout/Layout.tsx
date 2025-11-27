/**
 * 3단 레이아웃 컴포넌트
 * Why: 캐릭터(상단) / 컨텐츠(중앙) / 토글(하단) 구조
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import type { ContentMode } from '../../types';
import { useCharacter } from '../../hooks/useCharacter';
import { useMessages } from '../../hooks/useMessages';
import { useDiscord } from '../../hooks/useDiscord';
import { useSchedules } from '../../hooks/useSchedules';
import { useAppSettings } from '../../hooks/useAppSettings';
import { stripAllMarkers, hasSyncEvent } from '../../utils/scheduleParser';
import { Character } from '../Character/Character';
import { ChatContainer } from '../Chat';
import { CalendarContainer } from '../Calendar';
import { Toggle } from '../Toggle/Toggle';
import { Settings } from '../Settings';
import logger from '../../utils/logger';
import './Layout.css';

// 자동 동기화 주기 (30분)
const AUTO_SYNC_INTERVAL = 30 * 60 * 1000;

const MODULE = 'Layout';

export function Layout() {
  logger.info(MODULE, 'Layout component rendering');

  const [mode, setMode] = useState<ContentMode>('chat');
  const [showSettings, setShowSettings] = useState(false);
  const character = useCharacter();
  const { messages, addUserMessage, addBotMessage, addSystemMessage, clearMessages } = useMessages();
  const discord = useDiscord();
  const schedules = useSchedules();
  const appSettings = useAppSettings();

  // 자동 동기화 타이머 ref
  const syncTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 초기 동기화 완료 여부
  const initialSyncDoneRef = useRef(false);

  logger.debug(MODULE, 'Discord state', {
    isConfigured: discord.isConfigured,
    isLoading: discord.isLoading,
    error: discord.error
  });

  // 자동 동기화 타이머 리셋 (30분 주기)
  const resetSyncTimer = useCallback(() => {
    if (syncTimerRef.current) {
      clearTimeout(syncTimerRef.current);
    }
    syncTimerRef.current = setTimeout(() => {
      logger.info(MODULE, 'Auto sync timer triggered (30min)');
      discord.sendBackgroundSync();
      resetSyncTimer(); // 다음 주기 설정
    }, AUTO_SYNC_INTERVAL);
    logger.debug(MODULE, 'Sync timer reset');
  }, [discord]);

  // 앱 시작 시 초기 동기화 (Discord 설정 완료 후)
  useEffect(() => {
    if (discord.isConfigured && !initialSyncDoneRef.current) {
      logger.info(MODULE, 'Initial sync on app startup');
      initialSyncDoneRef.current = true;
      // 약간의 딜레이 후 동기화 (폴링 초기화 대기)
      setTimeout(() => {
        discord.sendBackgroundSync();
        resetSyncTimer();
      }, 2000);
    }

    return () => {
      if (syncTimerRef.current) {
        clearTimeout(syncTimerRef.current);
      }
    };
  }, [discord.isConfigured, discord, resetSyncTimer]);

  const handleModeChange = (newMode: ContentMode) => {
    logger.info(MODULE, 'Mode changed', { from: mode, to: newMode });
    setMode(newMode);
    character.onModeChange(newMode);
  };

  // Discord 봇 메시지 수신 시 처리 (최초 1회만 등록)
  useEffect(() => {
    logger.info(MODULE, 'Registering bot message callback');
    discord.onBotMessage((content) => {
      logger.info(MODULE, 'Bot message received in Layout', { contentLength: content.length });

      // 일정 데이터/동기화 이벤트 추출 시도
      const hasScheduleProcessed = schedules.processMessage(content);
      logger.debug(MODULE, 'Schedule data extraction', { hasScheduleProcessed });

      // 마커 제거 후 자연어 부분만 추출
      const displayContent = stripAllMarkers(content).trim();

      // 백그라운드 동기화 응답은 채팅에 표시하지 않음
      // Why: 순수 동기화 응답 ([SCHEDULE_SYNC]만 포함)은 자연어가 없으므로 채팅 불필요
      if (!displayContent && hasSyncEvent(content)) {
        logger.info(MODULE, 'Background sync response received, not displaying in chat');
        return;
      }

      // 자연어 응답이 있으면 채팅에 표시
      if (displayContent) {
        addBotMessage(displayContent);
        character.onMessageReceive();
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 콜백은 최초 1회만 등록, 내부에서 최신 함수 참조

  // Discord 설정 안내 (미설정 시)
  useEffect(() => {
    logger.debug(MODULE, 'Discord config check effect', { isConfigured: discord.isConfigured });
    if (!discord.isConfigured) {
      logger.warn(MODULE, 'Discord not configured, showing system message');
      addSystemMessage('Discord 연결이 필요합니다. 설정을 확인해주세요.');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discord.isConfigured]); // isConfigured 변경 시에만

  // 메시지 전송 처리
  const handleSendMessage = async (content: string) => {
    logger.info(MODULE, 'handleSendMessage called', { contentLength: content.length, content: content.slice(0, 50) });

    // 사용자 메시지 추가
    addUserMessage(content);
    character.onMessageSend();

    // Discord로 전송
    if (discord.isConfigured) {
      logger.info(MODULE, 'Sending via Discord');
      const success = await discord.sendMessage(content);
      logger.info(MODULE, 'Discord send result', { success, error: discord.error });

      if (!success && discord.error) {
        logger.error(MODULE, 'Message send failed', { error: discord.error });
        addSystemMessage(`전송 실패: ${discord.error}`);
        character.onMessageReceive(); // 에러 시에도 상태 복귀
      } else {
        // 메시지 전송 성공 시 백그라운드 동기화 및 타이머 리셋
        // Why: 일정 추가/수정 요청 후 자동으로 캘린더 갱신
        logger.info(MODULE, 'Triggering background sync after message send');
        // 봇 응답 처리 후 동기화 요청 (약간의 딜레이)
        setTimeout(() => {
          discord.sendBackgroundSync();
        }, 3000);
        resetSyncTimer();
      }
    } else {
      logger.info(MODULE, 'Discord not configured, using test mode');
      // 미설정 시 로컬 테스트 모드
      setTimeout(() => {
        addBotMessage('(테스트 모드) Discord 연결 후 실제 응답을 받을 수 있습니다.');
        character.onMessageReceive();
      }, 1000);
    }
  };

  return (
    <div className="layout">
      {/* 상단: 캐릭터 영역 */}
      <Character state={character.state} useAnimatedCharacter={appSettings.useAnimatedCharacter} />

      {/* 설정 버튼 (우측 상단) */}
      <button
        className={`settings-btn ${!discord.isConfigured ? 'attention' : ''}`}
        onClick={() => setShowSettings(true)}
        title="Discord 설정"
      >
        ⚙
      </button>

      {/* 중앙: 컨텐츠 영역 */}
      <div className="content-area">
        {mode === 'chat' ? (
          <ChatContainer
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={discord.isLoading}
          />
        ) : (
          <CalendarContainer
            schedules={schedules.schedules}
            getSchedulesForDate={schedules.getSchedulesForDate}
            getDatesWithSchedules={schedules.getDatesWithSchedules}
          />
        )}
      </div>

      {/* 하단: 토글 영역 */}
      <Toggle mode={mode} onModeChange={handleModeChange} />

      {/* 설정 모달 */}
      {showSettings && (
        <Settings
          isConfigured={discord.isConfigured}
          onSave={discord.configure}
          onClear={discord.clearConfig}
          onClose={() => setShowSettings(false)}
          useAnimatedCharacter={appSettings.useAnimatedCharacter}
          onToggleAnimatedCharacter={appSettings.toggleAnimatedCharacter}
          onClearChat={clearMessages}
        />
      )}
    </div>
  );
}
