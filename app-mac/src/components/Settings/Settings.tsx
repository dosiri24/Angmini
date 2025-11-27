/**
 * 설정 화면 컴포넌트
 * Why: Discord API 설정값과 창 옵션을 사용자가 설정할 수 있는 UI 제공
 */
import { useState, useCallback, useEffect } from 'react';
import { useWindow } from '../../hooks/useWindow';
import './Settings.css';

interface SettingsProps {
  isConfigured: boolean;
  onSave: (config: { botToken: string; channelId: string; botUserId: string }) => void;
  onClear: () => void;
  onClose: () => void;
  // 앱 설정 props
  useAnimatedCharacter: boolean;
  onToggleAnimatedCharacter: () => void;
  // 채팅 초기화
  onClearChat: () => void;
}

export function Settings({
  isConfigured,
  onSave,
  onClear,
  onClose,
  useAnimatedCharacter,
  onToggleAnimatedCharacter,
  onClearChat,
}: SettingsProps) {
  const [botToken, setBotToken] = useState('');
  const [channelId, setChannelId] = useState('');
  const [botUserId, setBotUserId] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [saved, setSaved] = useState(false);
  const windowSettings = useWindow();

  // 설정된 상태면 placeholder 표시
  useEffect(() => {
    if (isConfigured) {
      // localStorage에서 현재 값 로드 (표시용)
      const stored = localStorage.getItem('angmini_discord_config');
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          setBotToken(parsed.botToken || '');
          setChannelId(parsed.channelId || '');
          setBotUserId(parsed.botUserId || '');
        } catch {
          // 파싱 실패 시 빈 값 유지
        }
      }
    }
  }, [isConfigured]);

  // 저장 처리
  const handleSave = useCallback(() => {
    if (!botToken.trim() || !channelId.trim() || !botUserId.trim()) {
      return;
    }
    onSave({
      botToken: botToken.trim(),
      channelId: channelId.trim(),
      botUserId: botUserId.trim(),
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }, [botToken, channelId, botUserId, onSave]);

  // 초기화 처리
  const handleClear = useCallback(() => {
    if (window.confirm('정말 설정을 초기화하시겠습니까?')) {
      onClear();
      setBotToken('');
      setChannelId('');
      setBotUserId('');
    }
  }, [onClear]);

  // 채팅 초기화 처리
  const handleClearChat = useCallback(() => {
    onClearChat();
    onClose(); // 초기화 후 설정 모달 닫기
  }, [onClearChat, onClose]);

  // 유효성 검사
  const isValid = botToken.trim() && channelId.trim() && botUserId.trim();

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        {/* 헤더 */}
        <div className="settings-header">
          <h2>Discord 설정</h2>
          <button className="close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* 설정 폼 */}
        <div className="settings-content">
          {/* 상태 표시 */}
          <div className={`status-badge ${isConfigured ? 'configured' : 'not-configured'}`}>
            {isConfigured ? '✓ 연결됨' : '미설정'}
          </div>

          {/* Bot Token 입력 */}
          <div className="input-group">
            <label htmlFor="botToken">Bot Token</label>
            <div className="input-with-toggle">
              <input
                id="botToken"
                type={showToken ? 'text' : 'password'}
                value={botToken}
                onChange={(e) => setBotToken(e.target.value)}
                placeholder="Discord Bot Token"
              />
              <button
                type="button"
                className="toggle-visibility"
                onClick={() => setShowToken(!showToken)}
              >
                {showToken ? '숨김' : '표시'}
              </button>
            </div>
            <span className="input-hint">Discord Developer Portal에서 발급받은 토큰</span>
          </div>

          {/* Channel ID 입력 */}
          <div className="input-group">
            <label htmlFor="channelId">Channel ID</label>
            <input
              id="channelId"
              type="text"
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              placeholder="예: 1234567890123456789"
            />
            <span className="input-hint">봇과 대화할 채널의 ID (개발자 모드에서 복사)</span>
          </div>

          {/* Bot User ID 입력 */}
          <div className="input-group">
            <label htmlFor="botUserId">Bot User ID</label>
            <input
              id="botUserId"
              type="text"
              value={botUserId}
              onChange={(e) => setBotUserId(e.target.value)}
              placeholder="예: 1234567890123456789"
            />
            <span className="input-hint">봇의 사용자 ID (봇 응답 필터링용)</span>
          </div>

          {/* 창 설정 섹션 */}
          <div className="settings-section">
            <h3>창 설정</h3>
            <div className="settings-toggle-option">
              <label htmlFor="alwaysOnTop">
                <span className="settings-toggle-text">항상 위에 표시</span>
                <span className="settings-toggle-hint">다른 창 위에 항상 표시됩니다</span>
              </label>
              <button
                id="alwaysOnTop"
                className={`settings-toggle-switch ${windowSettings.alwaysOnTop ? 'on' : ''}`}
                onClick={() => windowSettings.toggleAlwaysOnTop()}
                aria-pressed={windowSettings.alwaysOnTop}
              >
                <span className="settings-toggle-knob" />
              </button>
            </div>
          </div>

          {/* 표시 설정 섹션 */}
          <div className="settings-section">
            <h3>표시 설정</h3>
            <div className="settings-toggle-option">
              <label htmlFor="animatedCharacter">
                <span className="settings-toggle-text">애니메이션 캐릭터</span>
                <span className="settings-toggle-hint">
                  {useAnimatedCharacter ? '캐릭터 이미지가 표시됩니다' : '이모지와 텍스트로 표시됩니다'}
                </span>
              </label>
              <button
                id="animatedCharacter"
                className={`settings-toggle-switch ${useAnimatedCharacter ? 'on' : ''}`}
                onClick={onToggleAnimatedCharacter}
                aria-pressed={useAnimatedCharacter}
              >
                <span className="settings-toggle-knob" />
              </button>
            </div>
          </div>

          {/* 데이터 관리 섹션 */}
          <div className="settings-section">
            <h3>데이터 관리</h3>
            <div className="settings-action-row">
              <div className="settings-action-info">
                <span className="settings-action-text">채팅 내역 초기화</span>
                <span className="settings-action-hint">모든 대화 기록을 삭제합니다</span>
              </div>
              <button type="button" className="btn-danger-small" onClick={handleClearChat}>
                초기화
              </button>
            </div>
          </div>
        </div>

        {/* 액션 버튼 */}
        <div className="settings-actions">
          {isConfigured && (
            <button className="btn-clear" onClick={handleClear}>
              초기화
            </button>
          )}
          <button className="btn-save" onClick={handleSave} disabled={!isValid}>
            {saved ? '✓ 저장됨' : '저장'}
          </button>
        </div>

        {/* 도움말 */}
        <div className="settings-help">
          <details>
            <summary>설정 방법</summary>
            <ol>
              <li>
                <a href="https://discord.com/developers/applications" target="_blank" rel="noreferrer">
                  Discord Developer Portal
                </a>
                에서 봇을 생성합니다.
              </li>
              <li>Bot 탭에서 Token을 복사합니다.</li>
              <li>Discord 설정에서 개발자 모드를 활성화합니다.</li>
              <li>채널 우클릭 → "채널 ID 복사"로 Channel ID를 가져옵니다.</li>
              <li>봇 프로필 우클릭 → "ID 복사"로 Bot User ID를 가져옵니다.</li>
            </ol>
          </details>
        </div>
      </div>
    </div>
  );
}
