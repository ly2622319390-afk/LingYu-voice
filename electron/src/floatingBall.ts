/**
 * 桌面悬浮球 — 始终可见的入口
 *
 * 小型圆形图标浮在桌面上，可拖拽。
 * 单击 → 切换语音输入浮窗
 * 右键 → 系统托盘菜单
 */
import { BrowserWindow, screen, ipcMain } from 'electron';
import * as path from 'path';
import { IPC_CHANNELS } from './ipc';

const BALL_SIZE = 56;

export class FloatingBall {
  private window: BrowserWindow | null = null;
  private onClick: () => void;
  private onRightClick: () => void;
  private ipcRegistered = false;

  constructor(onClick: () => void, onRightClick: () => void) {
    this.onClick = onClick;
    this.onRightClick = onRightClick;
    this.registerIPC();
  }

  private registerIPC(): void {
    if (this.ipcRegistered) return;
    this.ipcRegistered = true;

    ipcMain.on(IPC_CHANNELS.BALL_CLICKED, () => {
      this.onClick();
    });
    ipcMain.on(IPC_CHANNELS.BALL_RIGHT_CLICKED, () => {
      this.onRightClick();
    });
    ipcMain.on(IPC_CHANNELS.BALL_DRAG, (_e, dx, dy) => {
      if (!this.window) return;
      const [x, y] = this.window.getPosition();
      const displays = screen.getAllDisplays();
      // 边界约束 — 至少保留一部分在屏幕内
      const margin2 = -BALL_SIZE + 10;
      let nx = Math.max(margin2, x + dx);
      let ny = Math.max(margin2, y + dy);
      // 右边界
      const maxX = Math.max(...displays.map(d => d.workArea.x + d.workArea.width)) - 10;
      const maxY = Math.max(...displays.map(d => d.workArea.y + d.workArea.height)) - 10;
      nx = Math.min(nx, maxX);
      ny = Math.min(ny, maxY);
      this.window.setPosition(Math.round(nx), Math.round(ny));
    });
  }

  hide(): void {
    this.window?.hide();
  }

  show(): void {
    if (this.window) {
      this.window.show();
      this.window.focus();
      return;
    }

    const margin = 20;
    const { width: sw, height: sh } = screen.getPrimaryDisplay().workArea;

    this.window = new BrowserWindow({
      width: BALL_SIZE,
      height: BALL_SIZE,
      x: sw - BALL_SIZE - margin,
      y: Math.round(sh / 2 - BALL_SIZE / 2),
      show: false,
      frame: false,
      alwaysOnTop: true,
      skipTaskbar: true,
      resizable: false,
      transparent: true,
      hasShadow: false,
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        sandbox: false,
        contextIsolation: true,
        nodeIntegration: false,
      },
    });

    // 确保在所有窗口之上（包括全屏应用）
    this.window.setAlwaysOnTop(true, 'screen-saver', 1);

    this.window.loadURL(this.getDataURL());

    this.window.on('closed', () => {
      this.window = null;
    });

    this.window.show();
  }

  destroy(): void {
    ipcMain.removeAllListeners(IPC_CHANNELS.BALL_CLICKED);
    ipcMain.removeAllListeners(IPC_CHANNELS.BALL_RIGHT_CLICKED);
    ipcMain.removeAllListeners(IPC_CHANNELS.BALL_DRAG);
    if (this.window) {
      this.window.close();
      this.window = null;
    }
  }

  private getDataURL(): string {
    return 'data:text/html;charset=utf-8,' + encodeURIComponent(`<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; user-select: none; }
html, body { width: 100%; height: 100%; overflow: hidden; background: transparent; }
body { display: flex; align-items: center; justify-content: center; -webkit-app-region: no-drag; }
.ball {
  width: 52px; height: 52px; border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.5), 0 0 0 1px rgba(255,255,255,0.15);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: transform 0.15s, box-shadow 0.15s;
  position: relative;
}
.ball:hover { transform: scale(1.08); box-shadow: 0 6px 24px rgba(102, 126, 234, 0.7); }
.ball:active { transform: scale(0.95); }
.ball svg { width: 26px; height: 26px; fill: white; }
.ball::after {
  content: ''; position: absolute;
  width: 100%; height: 100%; border-radius: 50%;
  border: 2px solid rgba(102, 126, 234, 0.3);
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
  0% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.2); opacity: 0; }
  100% { transform: scale(1); opacity: 0.6; }
}
.recording .ball { background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); box-shadow: 0 4px 16px rgba(231, 76, 60, 0.5); }
.recording .ball::after { border-color: rgba(231, 76, 60, 0.3); }
</style>
</head>
<body class="idle">
<div class="ball" id="ball">
  <svg viewBox="0 0 24 24">
    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
  </svg>
</div>
<script>
  const ball = document.getElementById('ball');
  let isDragging = false;
  let startX, startY;

  ball.addEventListener('mousedown', (e) => {
    isDragging = false;
    startX = e.screenX;
    startY = e.screenY;
  });

  document.addEventListener('mousemove', (e) => {
    if (e.buttons !== 1) return;
    const dx = e.screenX - startX;
    const dy = e.screenY - startY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      isDragging = true;
      if (window.electronAPI && window.electronAPI.dragBall) {
        window.electronAPI.dragBall(dx, dy);
      }
      startX = e.screenX;
      startY = e.screenY;
    }
  });

  ball.addEventListener('mouseup', () => {
    if (!isDragging) {
      if (window.electronAPI && window.electronAPI.ballClicked) {
        window.electronAPI.ballClicked();
      }
    }
  });

  ball.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    if (window.electronAPI && window.electronAPI.ballRightClicked) {
      window.electronAPI.ballRightClicked();
    }
  });
</script>
</body>
</html>`);
  }
}
