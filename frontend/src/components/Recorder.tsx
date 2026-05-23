interface RecorderProps {
  isListening: boolean;
  onStart: () => void;
  onStop: () => void;
  onNewTranscript: (text: string) => void;
  error: string | null;
}

export default function Recorder({ isListening, onStart, onStop, onNewTranscript, error }: RecorderProps) {
  return (
    <div className="card">
      <div className="card-title">🎙️ 语音输入</div>
      <div className="recorder-area">
        <button
          className={`record-btn ${isListening ? 'listening' : 'idle'}`}
          onClick={isListening ? onStop : onStart}
          title={isListening ? '点击停止录音' : '点击开始录音'}
        >
          {isListening ? '⏹' : '🎤'}
        </button>
        <div className="record-status">
          <div className={`status-text ${isListening ? 'active' : ''}`}>
            {isListening ? '🔴 录音中... 请说话' : '点击按钮开始语音输入'}
          </div>
          {error && <div style={{ color: '#e74c3c', fontSize: 13, marginTop: 4 }}>{error}</div>}
          {isListening && (
            <div style={{ marginTop: 8, display: 'flex', gap: 4, alignItems: 'center' }}>
              <div className="waveform">
                {[...Array(5)].map((_, i) => (
                  <span key={i} className="wave-bar" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      <style>{`
        .waveform { display: flex; align-items: center; gap: 3px; height: 24px; }
        .wave-bar {
          width: 4px; height: 8px; background: #e74c3c; border-radius: 2px;
          animation: wave 0.8s ease-in-out infinite;
        }
        @keyframes wave {
          0%, 100% { height: 8px; }
          50% { height: 20px; }
        }
      `}</style>
    </div>
  )
}
