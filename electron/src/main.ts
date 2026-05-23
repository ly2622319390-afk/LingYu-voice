/**
 * 智能语音输入法 — Electron 主进程入口
 *
 * 启动顺序:
 *   1. 单实例锁检查
 *   2. 启动 Python 后端子进程
 *   3. 创建系统托盘
 *   4. 注册全局热键
 *   5. 等待用户触发 (Ctrl+Space → 浮窗)
 *
 * 生命周期:
 *   所有窗口关闭 → 隐藏到托盘
 *   退出 → 停止后端 → 清理热键 → 退出
 */
import { app, ipcMain } from 'electron';
import { BackendManager } from './backend';
import { createTray, destroyTray, updateTrayIcon } from './tray';
import { HotkeyManager } from './hotkeys';
import { OverlayManager } from './overlay';
import { FloatingBall } from './floatingBall';
import { TextInjector } from './textInjector';
import { IPC_CHANNELS } from './ipc';

// 工具函数
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

// 全局实例
const backend = new BackendManager();
const overlay = new OverlayManager();
const textInjector = new TextInjector();
let hotkeyManager: HotkeyManager;
let floatingBall: FloatingBall;

// ─── 应用生命周期 ───

app.whenReady().then(async () => {
  console.log('[App] 启动...');

  // 1. 单实例锁
  const gotLock = app.requestSingleInstanceLock();
  if (!gotLock) {
    console.log('[App] 已有实例运行，退出');
    app.quit();
    return;
  }

  // 2. 启动后端（非阻塞，继续启动）
  backend.start().catch((err) =>
    console.warn('[App] 后端启动失败（可手动启动）:', err.message)
  );

  // 3. 创建系统托盘
  createTray(handleTrayAction);

  // 4. 注册全局热键
  hotkeyManager = new HotkeyManager({
    onToggleOverlay: () => overlay.toggle(),
  });
  hotkeyManager.register();

  // 5. 创建桌面悬浮球
  floatingBall = new FloatingBall(
    () => overlay.toggle(),   // 单击 → 切换浮窗
    () => handleTrayAction('toggle-overlay'), // 右键 → 切换浮窗
  );
  floatingBall.show();

  // 6. 注册 IPC 处理
  registerIPC();

  // 7. 单实例锁 — 第二个实例启动时激活第一个实例
  app.on('second-instance', () => {
    overlay.show();
  });

  console.log('[App] 就绪 — 按 Alt+Q 或点击悬浮球呼出语音输入浮窗');
});

app.on('window-all-closed', () => {
  // 不退出（隐藏到托盘）
});

app.on('before-quit', () => {
  console.log('[App] 退出中...');
  HotkeyManager.unregisterAll();
  backend.stop();
  overlay.destroy();
  floatingBall?.destroy();
  destroyTray();
});

// ─── 托盘菜单事件 ───

function handleTrayAction(action: string) {
  switch (action) {
    case 'toggle-overlay':
      overlay.toggle();
      break;
    case 'open-full-window':
      overlay.createFullWindow();
      break;
    case 'open-settings':
      // TODO: 设置窗口
      break;
    case 'quit':
      app.quit();
      break;
  }
}

// ─── IPC 处理 ───

function registerIPC() {
  // 浮窗控制
  ipcMain.on(IPC_CHANNELS.OVERLAY_SHOW, () => overlay.show());
  ipcMain.on(IPC_CHANNELS.OVERLAY_HIDE, () => overlay.hide());

  // 窗口切换
  ipcMain.on(IPC_CHANNELS.WINDOW_OPEN_FULL, () => overlay.createFullWindow());
  ipcMain.on(IPC_CHANNELS.WINDOW_CLOSE_FULL, () => {
    // 完整窗口由用户关闭
  });

  // 文本注入（两阶段：先准备剪贴板 → 隐藏浮窗 → 再 OS 级粘贴）
  ipcMain.handle(IPC_CHANNELS.TEXT_INJECT, async (_event, text: string) => {
    if (!text) return false;
    try {
      textInjector.prepare(text);
      overlay.hide();
      // 等待浮窗隐藏完成，焦点回到外部应用
      await delay(150);
      return await textInjector.paste();
    } catch (err) {
      console.error('[App] 文本注入失败:', err);
      return false;
    }
  });

  // 后端状态
  ipcMain.handle(IPC_CHANNELS.BACKEND_STATUS, () => ({
    running: backend.ready,
    port: backend.port,
  }));

  // 录音状态通知（渲染进程 → 托盘图标更新）
  ipcMain.on(IPC_CHANNELS.RECORD_STATUS, (_event, status: string) => {
    updateTrayIcon(status === 'recording');
  });

  // 音频数据转发（渲染进程 → 主进程 → WebSocket → Python ASR）
  // 实际 ASR WebSocket 连接在渲染进程中直接建立，减少延迟
  // 音频数据通过此通道转发仅在需要时使用
  ipcMain.on(IPC_CHANNELS.AUDIO_DATA, (_event, chunk: ArrayBuffer) => {
    // 可选: 在主进程维护 WebSocket 连接
    // 当前直接在渲染进程建立 WebSocket 连接
  });
}
