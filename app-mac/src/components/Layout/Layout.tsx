/**
 * 3단 레이아웃 컴포넌트
 * Why: 캐릭터(상단) / 컨텐츠(중앙) / 토글(하단) 구조
 */
import { useState, useEffect } from 'react';
import type { ContentMode } from '../../types';
import { useCharacter } from '../../hooks/useCharacter';
import { useMessages } from '../../hooks/useMessages';
import { useDiscord } from '../../hooks/useDiscord';
import { useSchedules } from '../../hooks/useSchedules';
import { stripScheduleDataMarker } from '../../utils/scheduleParser';
import { Character } from '../Character/Character';
import { ChatContainer } from '../Chat';
import { CalendarContainer } from '../Calendar';
import { Toggle } from '../Toggle/Toggle';
import { Settings } from '../Settings';
import logger from '../../utils/logger';
import './Layout.css';

const MODULE = 'Layout';

export function Layout() {
  logger.info(MODULE, 'Layout component rendering');

  const [mode, setMode] = useState<ContentMode>('chat');
  const [showSettings, setShowSettings] = useState(false);
  const character = useCharacter();
  const { messages, addUserMessage, addBotMessage, addSystemMessage } = useMessages();
  const discord = useDiscord();
  const schedules = useSchedules();

  logger.debug(MODULE, 'Discord state', {
    isConfigured: discord.isConfigured,
    isLoading: discord.isLoading,
    error: discord.error
  });

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

      // 일정 데이터 추출 시도
      const hasScheduleData = schedules.processMessage(content);
      logger.debug(MODULE, 'Schedule data extraction', { hasScheduleData });

      // 채팅에는 마커 제거한 텍스트만 표시
      const displayContent = stripScheduleDataMarker(content);
      addBotMessage(displayContent);
      character.onMessageReceive();
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
      <Character state={character.state} />

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
        />
      )}
    </div>
  );
}
