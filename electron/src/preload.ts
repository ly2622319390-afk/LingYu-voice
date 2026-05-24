/**
 * 预加载脚本 — 通过 contextBridge 暴露安全的 IPC 接口给渲染进程
 *
 * 渲染进程通过 window.electronAPI.* 调用
 */
import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  // 浮窗
  showOverlay: () => ipcRenderer.send('overlay:show'),
  hideOverlay: () => ipcRenderer.send('overlay:hide'),
  onToggleOverlay: (callback: () => void) =>
    ipcRenderer.on('overlay:toggle', callback),

  // 录音
  startRecording: () => ipcRenderer.send('record:start'),
  stopRecording: () => ipcRenderer.send('record:stop'),

  // 文本注入
  injectText: (text: string) => ipcRenderer.invoke('text:inject', text),
  prepareText: (text: string) => ipcRenderer.send('text:prepare', text),

  // 窗口
  openFullWindow: () => ipcRenderer.send('window:open-full'),
  closeFullWindow: () => ipcRenderer.send('window:close-full'),

  // 后端
  getBackendStatus: () => ipcRenderer.invoke('backend:status'),
  restartBackend: () => ipcRenderer.send('backend:restart'),

  // 设置
  getSettings: () => ipcRenderer.invoke('settings:get'),
  setSettings: (settings: Record<string, any>) =>
    ipcRenderer.invoke('settings:set', settings),

  // ASR 音频发送
  sendAudioChunk: (chunk: ArrayBuffer) =>
    ipcRenderer.send('audio:data', chunk),
  onASRResult: (callback: (text: string, isFinal: boolean) => void) =>
    ipcRenderer.on('asr:result', (_event, text, isFinal) => callback(text, isFinal)),

  // 录音状态变更
  onRecordStatus: (callback: (status: string) => void) =>
    ipcRenderer.on('record:status', (_event, status) => callback(status)),

  // 悬浮球
  ballClicked: () => ipcRenderer.send('ball:clicked'),
  ballRightClicked: () => ipcRenderer.send('ball:right-clicked'),
  dragBall: (dx: number, dy: number) => ipcRenderer.send('ball:drag', dx, dy),
});
