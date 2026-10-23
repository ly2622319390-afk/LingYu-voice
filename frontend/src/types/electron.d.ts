interface ElectronAPI {
  showOverlay: () => void;
  hideOverlay: () => void;
  onToggleOverlay: (callback: () => void) => void;
  startRecording: () => void;
  stopRecording: () => void;
  injectText: (text: string) => Promise<void>;
  prepareText: (text: string) => void;
  openFullWindow: () => void;
  closeFullWindow: () => void;
  getBackendStatus: () => Promise<{ running: boolean; port: number }>;
  restartBackend: () => void;
  getSettings: () => Promise<Record<string, unknown>>;
  setSettings: (settings: Record<string, unknown>) => Promise<void>;
  sendAudioChunk: (chunk: ArrayBuffer) => void;
  onASRResult: (callback: (text: string, isFinal: boolean) => void) => void;
  onRecordStatus: (callback: (status: string) => void) => void;
  ballClicked: () => void;
  ballRightClicked: () => void;
  dragBall: (dx: number, dy: number) => void;
}

interface Window {
  electronAPI?: ElectronAPI;
}
