/**
 * 系统托盘模块
 *
 * 图标:
 *   - tray-icon.png    默认状态
 *   - tray-icon-active.png  录音中
 * 右键菜单:
 *   - 打开浮窗 (Ctrl+Space)
 *   - 打开完整窗口
 *   - 分隔线
 *   - 设置
 *   - 退出
 */
import { Tray, Menu, nativeImage, app } from 'electron';
import * as path from 'path';

let tray: Tray | null = null;
let statusListeners: Array<(action: string) => void> = [];

export function createTray(onAction: (action: string) => void): Tray {
  statusListeners.push(onAction);

  const iconPath = path.join(__dirname, '..', 'assets', 'tray-icon.png');
  const icon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });

  tray = new Tray(icon);
  tray.setToolTip('智能语音输入法 — 就绪');

  updateMenu();

  tray.on('double-click', () => {
    notifyListeners('toggle-overlay');
  });

  return tray;
}

function notifyListeners(action: string) {
  statusListeners.forEach((fn) => fn(action));
}

export function updateTrayIcon(isRecording: boolean) {
  if (!tray) return;

  const iconName = isRecording ? 'tray-icon-active.png' : 'tray-icon.png';
  const iconPath = path.join(__dirname, '..', 'assets', iconName);
  const icon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });

  tray.setImage(icon);
  tray.setToolTip(isRecording ? '智能语音输入法 — 录音中...' : '智能语音输入法 — 就绪');
}

export function updateMenu() {
  if (!tray) return;

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '🎤 语音输入 (Alt+Q)',
      click: () => notifyListeners('toggle-overlay'),
    },
    {
      label: '📖 打开完整窗口',
      click: () => notifyListeners('open-full-window'),
    },
    { type: 'separator' },
    {
      label: '⚙️ 设置',
      click: () => notifyListeners('open-settings'),
    },
    { type: 'separator' },
    {
      label: '❌ 退出',
      click: () => notifyListeners('quit'),
    },
  ]);

  tray.setContextMenu(contextMenu);
}

export function destroyTray() {
  if (tray) {
    tray.destroy();
    tray = null;
  }
  statusListeners = [];
}
