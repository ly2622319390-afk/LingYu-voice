/**
 * Electron IPC 封装 Hook
 *
 * 在 Electron 环境中通过 window.electronAPI 与主进程通信。
 * 在浏览器环境中安全降级（不报错）。
 */
import { useCallback } from 'react';

const isElectron = typeof window !== 'undefined' && !!window.electronAPI;

export function useElectronIPC() {
  /**
   * 注入文本到当前聚焦的应用
   */
  const injectText = useCallback(async (text: string): Promise<boolean> => {
    if (!isElectron) {
      // 浏览器环境：复制到剪贴板
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch {
        return false;
      }
    }
    try {
      await window.electronAPI!.injectText(text);
      return true;
    } catch {
      return false;
    }
  }, []);

  /**
   * 隐藏浮窗
   */
  const hideOverlay = useCallback(() => {
    if (isElectron) {
      window.electronAPI!.hideOverlay();
    }
  }, []);

  /**
   * 打开完整窗口
   */
  const openFullWindow = useCallback(() => {
    if (isElectron) {
      window.electronAPI!.openFullWindow();
    }
  }, []);

  /**
   * 发送音频块（通过主进程转发）
   */
  const sendAudioChunk = useCallback((chunk: ArrayBuffer) => {
    if (isElectron) {
      window.electronAPI!.sendAudioChunk(chunk);
    }
  }, []);

  /**
   * 获取后端状态
   */
  const getBackendStatus = useCallback(async () => {
    if (!isElectron) return { running: true, port: 8000 };
    try {
      return await window.electronAPI!.getBackendStatus();
    } catch {
      return { running: false, port: 8000 };
    }
  }, []);

  return {
    isElectron,
    injectText,
    hideOverlay,
    openFullWindow,
    sendAudioChunk,
    getBackendStatus,
  };
}
