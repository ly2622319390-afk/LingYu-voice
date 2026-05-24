/**
 * IPC 通道定义 — Electron 主进程 ↔ 渲染进程 通信契约
 *
 * 命名规范: domain:action
 * - overlay:show/hide → 浮窗显示/隐藏
 * - audio:start/stop  → 录音开始/停止
 * - text:inject       → 将文本注入当前聚焦应用
 * - backend:status    → 后端进程状态
 * - settings:*        → 设置读写
 */

export const IPC_CHANNELS = {
  // 浮窗控制
  OVERLAY_SHOW: 'overlay:show',
  OVERLAY_HIDE: 'overlay:hide',
  OVERLAY_TOGGLE: 'overlay:toggle',

  // 窗口切换
  WINDOW_OPEN_FULL: 'window:open-full',
  WINDOW_CLOSE_FULL: 'window:close-full',

  // 录音控制
  RECORD_START: 'record:start',
  RECORD_STOP: 'record:stop',
  RECORD_STATUS: 'record:status',

  // 文本注入
  TEXT_INJECT: 'text:inject',
  TEXT_PREPARE: 'text:prepare',  // 仅复制到剪贴板，不粘贴
  TEXT_INJECTED: 'text:injected',

  // 后端状态
  BACKEND_STATUS: 'backend:status',
  BACKEND_RESTART: 'backend:restart',

  // 设置
  SETTINGS_GET: 'settings:get',
  SETTINGS_SET: 'settings:set',

  // 音频捕获 (渲染进程 → WebSocket → Python ASR)
  AUDIO_DATA: 'audio:data',
  ASR_RESULT: 'asr:result',

  // 托盘
  TRAY_UPDATE: 'tray:update',

  // 悬浮球
  BALL_CLICKED: 'ball:clicked',
  BALL_RIGHT_CLICKED: 'ball:right-clicked',
  BALL_DRAG: 'ball:drag',
} as const;
