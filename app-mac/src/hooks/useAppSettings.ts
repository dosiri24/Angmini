/**
 * 앱 설정 관리 훅
 * Why: 애니메이션 캐릭터 사용 여부 등 사용자 설정을 localStorage에 저장/관리
 */
import { useState, useCallback, useEffect } from 'react';

// 설정 키 (localStorage)
const STORAGE_KEY = 'angmini_app_settings';

// 기본 설정값
interface AppSettings {
  useAnimatedCharacter: boolean;
}

const DEFAULT_SETTINGS: AppSettings = {
  useAnimatedCharacter: true, // 기본값: 애니메이션 캐릭터 사용
};

export function useAppSettings() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);

  // 초기 로드 (localStorage에서 설정 복원)
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as Partial<AppSettings>;
        setSettings({ ...DEFAULT_SETTINGS, ...parsed });
      } catch {
        // 파싱 실패 시 기본값 유지
      }
    }
  }, []);

  // 설정 저장
  const saveSettings = useCallback((newSettings: AppSettings) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newSettings));
    setSettings(newSettings);
  }, []);

  // 애니메이션 캐릭터 토글
  const toggleAnimatedCharacter = useCallback(() => {
    const newSettings = { ...settings, useAnimatedCharacter: !settings.useAnimatedCharacter };
    saveSettings(newSettings);
  }, [settings, saveSettings]);

  return {
    useAnimatedCharacter: settings.useAnimatedCharacter,
    toggleAnimatedCharacter,
  };
}
