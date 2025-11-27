/**
 * 창 속성 관리 훅
 * Why: Tauri 창 API를 React에서 편리하게 사용
 */
import { useState, useCallback, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import logger from '../utils/logger';

const MODULE = 'useWindow';
const STORAGE_KEY = 'angmini_always_on_top';

interface UseWindowReturn {
  alwaysOnTop: boolean;
  setAlwaysOnTop: (enabled: boolean) => Promise<void>;
  toggleAlwaysOnTop: () => Promise<void>;
}

export function useWindow(): UseWindowReturn {
  // localStorage에서 초기값 로드
  const [alwaysOnTop, setAlwaysOnTopState] = useState<boolean>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === 'true';
  });

  // 컴포넌트 마운트 시 저장된 설정 적용
  useEffect(() => {
    const initAlwaysOnTop = async () => {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'true') {
        try {
          await invoke('set_always_on_top', { enabled: true });
          logger.info(MODULE, 'Applied stored always-on-top setting');
        } catch (error) {
          logger.error(MODULE, 'Failed to apply always-on-top', { error });
        }
      }
    };
    initAlwaysOnTop();
  }, []);

  // "항상 위에" 설정
  const setAlwaysOnTop = useCallback(async (enabled: boolean): Promise<void> => {
    try {
      await invoke('set_always_on_top', { enabled });
      setAlwaysOnTopState(enabled);
      localStorage.setItem(STORAGE_KEY, String(enabled));
      logger.info(MODULE, 'Always on top changed', { enabled });
    } catch (error) {
      logger.error(MODULE, 'Failed to set always on top', { error });
      throw error;
    }
  }, []);

  // "항상 위에" 토글
  const toggleAlwaysOnTop = useCallback(async (): Promise<void> => {
    await setAlwaysOnTop(!alwaysOnTop);
  }, [alwaysOnTop, setAlwaysOnTop]);

  return {
    alwaysOnTop,
    setAlwaysOnTop,
    toggleAlwaysOnTop,
  };
}
