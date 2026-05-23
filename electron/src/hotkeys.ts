/**
 * 全局热键模块
 *
 * 默认: Alt+Q — 呼出/隐藏语音输入浮窗
 * 支持用户自定义快捷键
 */
import { globalShortcut, BrowserWindow } from 'electron';

interface HotkeyActions {
  onToggleOverlay: () => void;
}

const DEFAULT_HOTKEY = 'Alt+Q';

export class HotkeyManager {
  private _currentHotkey: string = DEFAULT_HOTKEY;
  private _registered = false;
  private actions: HotkeyActions;

  constructor(actions: HotkeyActions) {
    this.actions = actions;
  }

  get currentHotkey(): string {
    return this._currentHotkey;
  }

  /**
   * 注册全局热键
   */
  register(hotkey?: string): boolean {
    this.unregister();

    const key = hotkey || DEFAULT_HOTKEY;
    const success = globalShortcut.register(key, () => {
      this.actions.onToggleOverlay();
    });

    if (success) {
      this._currentHotkey = key;
      this._registered = true;
      console.log(`[Hotkeys] 已注册: ${key}`);
    } else {
      console.warn(`[Hotkeys] 注册失败: ${key}（可能被其他应用占用）`);
    }

    return success;
  }

  /**
   * 注销热键
   */
  unregister(): void {
    if (this._registered) {
      globalShortcut.unregister(this._currentHotkey);
      this._registered = false;
    }
  }

  /**
   * 检测热键是否可用
   */
  static isAvailable(hotkey: string): boolean {
    return globalShortcut.isRegistered(hotkey);
  }

  /**
   * 清理所有热键
   */
  static unregisterAll(): void {
    globalShortcut.unregisterAll();
  }
}
