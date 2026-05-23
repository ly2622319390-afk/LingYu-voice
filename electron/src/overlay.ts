/**
 * 紧凑浮窗管理器
 *
 * 一个置顶窗口，用于语音输入交互。
 * 加载前端 React 组件 (mode=overlay)。
 */
import { BrowserWindow, screen, ipcMain, session } from 'electron';
import * as path from 'path';

const OVERLAY_WIDTH = 900;
const OVERLAY_HEIGHT = 300;

export class OverlayManager {
  private window: BrowserWindow | null = null;
  private isVisible = false;
  private fullAppWindow: BrowserWindow | null = null;

  get ready(): boolean {
    return this.window !== null;
  }

  private ensureWindow(): BrowserWindow {
    if (this.window) {
      console.log('[Overlay] ' + '复用已有窗口');
      return this.window;
    }
    console.log('[Overlay] ' + '创建新窗口...');

    const { width: sw, height: sh } = screen.getPrimaryDisplay().workArea;

    this.window = new BrowserWindow({
      width: OVERLAY_WIDTH,
      height: OVERLAY_HEIGHT,
      x: Math.round((sw - OVERLAY_WIDTH) / 2),
      y: Math.round((sh - OVERLAY_HEIGHT) / 3),
      show: false,
      frame: true,
      alwaysOnTop: true,
      skipTaskbar: false,
      resizable: false,
      title: '智能语音输入法',
      backgroundColor: '#2c2c3a',
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        nodeIntegration: false,
        contextIsolation: true,
      },
    });

    // 允许麦克风权限
    this.window.webContents.session.setPermissionRequestHandler(
      (webContents, permission, callback) => {
        if (permission === 'media' || permission === 'mediaKeySystem') {
          callback(true);
        } else {
          callback(false);
        }
      }
    );

    this.window.setAlwaysOnTop(true, 'screen-saver', 1);
    console.log('[Overlay] ' + '窗口创建完毕, 尺寸=' + OVERLAY_WIDTH + 'x' + OVERLAY_HEIGHT);

    // 加载页面
    const url = 'http://localhost:3000?mode=overlay';
    console.log('[Overlay] ' + '加载URL: ' + url);
    this.window.loadURL(url);

    this.window.webContents.on('did-finish-load', () => {
      console.log('[Overlay] ' + '页面加载完成');
    });

    this.window.webContents.on('did-fail-load', (_event, code, desc, url2) => {
      console.log('[Overlay] ' + '加载失败! code=' + code + ' desc=' + desc + ' url=' + url2);
    });

    this.window.on('closed', () => {
      console.log('[Overlay] ' + '窗口关闭');
      this.window = null;
      this.isVisible = false;
    });

    return this.window;
  }

  show(): void {
    console.log('[Overlay] ' + 'show() 被调用, 当前可见=' + this.isVisible);
    const win = this.ensureWindow();

    // 固定位置：屏幕中央偏上
    const { width: sw, height: sh } = screen.getPrimaryDisplay().workArea;
    win.setPosition(
      Math.round((sw - OVERLAY_WIDTH) / 2),
      Math.round((sh - OVERLAY_HEIGHT) / 3)
    );

    win.show();
    win.focus();
    this.isVisible = true;
    console.log('[Overlay] ' + '窗口已显示');
  }

  hide(): void {
    if (this.window && this.isVisible) {
      this.window.hide();
      this.isVisible = false;
      console.log('[Overlay] ' + '窗口已隐藏');
    }
  }

  toggle(): void {
    console.log('[Overlay] ' + 'toggle()');
    if (this.isVisible) {
      this.hide();
    } else {
      this.show();
    }
  }

  createFullWindow(): BrowserWindow {
    if (this.fullAppWindow) {
      this.fullAppWindow.focus();
      return this.fullAppWindow;
    }

    this.fullAppWindow = new BrowserWindow({
      width: 1200, height: 800, minWidth: 800, minHeight: 600,
      title: '智能语音输入法',
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        nodeIntegration: false, contextIsolation: true,
      },
    });

    this.fullAppWindow.loadURL('http://localhost:3000?mode=full');
    this.fullAppWindow.on('closed', () => { this.fullAppWindow = null; });
    return this.fullAppWindow;
  }

  sendTextToOverlay(text: string, isFinal: boolean): void {
    this.window?.webContents.send('asr:result', text, isFinal);
  }

  sendRecordingStatus(status: string): void {
    this.window?.webContents.send('record:status', status);
  }

  destroy(): void {
    console.log('[Overlay] ' + 'destroy()');
    if (this.window) { this.window.close(); this.window = null; }
    if (this.fullAppWindow) { this.fullAppWindow.close(); this.fullAppWindow = null; }
  }
}
