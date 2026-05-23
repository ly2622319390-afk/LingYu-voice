/** 渲染进程使用的 Electron API 类型声明 */

interface ElectronAPI {
  // 浮窗
  showOverlay: () => void;
  hideOverlay: () => void;
  onToggleOverlay: (callback: () => void) => void;

  // 录音
  startRecording: () => void;
  stopRecording: () => void;

  // 文本注入
  injectText: (text: string) => Promise<void>;

  // 窗口
  openFullWindow: () => void;
  closeFullWindow: () => void;

  // 后端
  getBackendStatus: () => Promise<{ running: boolean; port: number }>;
  restartBackend: () => void;

  // 设置
  getSettings: () => Promise<Record<string, any>>;
  setSettings: (settings: Record<string, any>) => Promise<void>;

  // ASR
  sendAudioChunk: (chunk: ArrayBuffer) => void;
  onASRResult: (callback: (text: string, isFinal: boolean) => void) => void;

  // 录音状态
  onRecordStatus: (callback: (status: string) => void) => void;

  // 悬浮球
  ballClicked: () => void;
  ballRightClicked: () => void;
  dragBall: (dx: number, dy: number) => void;
}

interface Window {
  electronAPI?: ElectronAPI;
}
