import { useState, useEffect } from 'react';
import { creationApi, correctionsApi } from '../services/api';

type CreationMode = 'novel' | 'project';

interface CreationRoundData {
  round_number: number;
  raw_input: string;
  organized_output: string;
  extraction: Record<string, any>;
  tips: string[];
  innovations: string[];
  improvements: string[];
  created_at: string;
}

interface CreationWorkspaceProps {
  transcript: string;
  isListening: boolean;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onClearTranscript: () => void;
}

export default function CreationWorkspace({ transcript, isListening, onStartRecording, onStopRecording, onClearTranscript }: CreationWorkspaceProps) {
  // 文本清理工具
  const cleanDisplayText = (s: string): string => {
    if (!s) return s;
    return s
      .replace(/\n+/g, ' ')
      .replace(/[•└]/g, '')
      .replace(/^\d+\.\s*/gm, '')
      .replace(/[，,]\s*具体来说[^，。]*[，。]?/g, '')
      .replace(/[，,]\s*这一点的关键在于[^，。]*[，。]?/g, '')
      .replace(/[。.]\s*在此基础上[^，。]*[，。]?/g, '')
      .replace(/[，,]\s*我们需要[^，。]*[，。]?/g, '')
      .replace(/\s{2,}/g, ' ')
      .trim();
  };

  const [mode, setMode] = useState<CreationMode | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [rounds, setRounds] = useState<CreationRoundData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [finished, setFinished] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showOriginalText, setShowOriginalText] = useState(false);
  const [editingText, setEditingText] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  // 同步编辑文本与转录文本
  useEffect(() => {
    if (!isEditing) setEditingText(transcript);
  }, [transcript, isEditing]);

  const handleStartEdit = () => {
    setEditingText(transcript);
    setIsEditing(true);
  };

  const handleConfirmEdit = () => {
    setIsEditing(false);
  };

  // ─── Handlers ───

  const handleSelectMode = async (m: CreationMode) => {
    setMode(m);
    setLoading(true);
    setError(null);
    setFinished(false);
    try {
      const res = await creationApi.createSession(m);
      setSessionId(res.session_id);
      // 不自动提交文本 — 让用户手动点击"提交创作灵感"
    } catch {
      setError('创建会话失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (sid: string, text: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await creationApi.submitInput(sid, text);
      setRounds(prev => [...prev, result]);
      // 追踪编辑行为
      if (text !== transcript) {
        correctionsApi.log(transcript, text, '创作', transcript, text).catch(() => {});
      }
      onClearTranscript();
    } catch {
      setError('提交失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleContinue = () => {
    onClearTranscript();
    onStartRecording();
  };

  const handleFinish = async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      await creationApi.finishSession(sessionId);
      setFinished(true);
    } catch {
      setError('结束会话失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async (text: string, target: string, roundNum: number) => {
    if (!sessionId) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(`${target}-${roundNum}`);
      setTimeout(() => setCopiedId(null), 1500);
      creationApi.trackCopy(sessionId, roundNum, target as 'organized' | 'raw');
    } catch {}
  };

  const handleNewCreation = () => {
    setMode(null);
    setSessionId(null);
    setRounds([]);
    setFinished(false);
    setError(null);
  };

  // ─── Render: Finished ───
  if (finished) {
    return (
      <div className="cw-finished">
        <div className="cw-finished-icon">✓</div>
        <div className="cw-finished-title">创作已完成</div>
        <div className="cw-finished-desc">已保存到历史记录，可在"历史记录"中回溯查看</div>
        <button className="cw-btn cw-btn-primary" onClick={handleNewCreation}>
          开始新创作
        </button>
      </div>
    );
  }

  // ─── Render: Mode Selector ───
  if (!sessionId) {
    return (
      <div className="cw-container">
        <div className="cw-mode-selector">
          <div className="cw-mode-card" onClick={() => handleSelectMode('novel')}>
            <span className="cw-mode-icon">📖</span>
            <div className="cw-mode-info">
              <div className="cw-mode-name">写小说</div>
              <div className="cw-mode-desc">整理小说灵感、人物设定、情节脉络</div>
            </div>
          </div>
          <div className="cw-mode-card" onClick={() => handleSelectMode('project')}>
            <span className="cw-mode-icon">💻</span>
            <div className="cw-mode-info">
              <div className="cw-mode-name">代码项目策划</div>
              <div className="cw-mode-desc">整理项目需求、技术方案、功能规划</div>
            </div>
          </div>
        </div>
        <div className="cw-hint">
          选择创作方向后，点击"开始录音"说出您的灵感
        </div>
      </div>
    );
  }

  // ─── Render: Loading ───
  if (loading) {
    return (
      <div className="cw-container">
        <div className="cw-loading">
          <div className="cw-loading-spinner" />
          <div>AI 正在分析您的创作灵感...</div>
        </div>
      </div>
    );
  }

  // ─── Render: Error ───
  if (error) {
    return (
      <div className="cw-container">
        <div className="cw-error">
          <span>⚠️ {error}</span>
          <button className="cw-btn cw-btn-primary" onClick={() => {
            if (sessionId && transcript) handleSubmit(sessionId, transcript);
            else handleSelectMode(mode || 'novel');
          }}>
            重试
          </button>
        </div>
      </div>
    );
  }

  // ─── Render: Session active, no rounds yet ───
  if (rounds.length === 0) {
    return (
      <div className="cw-container">
        {transcript.trim() ? (
          <div className="cw-submit-prompt">
            <div className="cw-submit-label">检测到语音输入，点击提交开始创作：</div>
            {isEditing ? (
              <>
                <textarea
                  className="cw-edit-area"
                  value={editingText}
                  onChange={e => setEditingText(e.target.value)}
                  rows={4}
                />
                <div className="cw-edit-actions">
                  <button className="cw-btn cw-btn-copy-outline" onClick={() => { setEditingText(transcript); setIsEditing(false) }}>取消</button>
                  <button className="cw-btn cw-btn-primary" onClick={() => { setIsEditing(false); sessionId && handleSubmit(sessionId, editingText) }}>
                    🚀 提交创作灵感
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="cw-submit-text" title={transcript}>{transcript}</div>
                <div className="cw-edit-actions">
                  <button className="cw-btn cw-btn-copy-outline" onClick={handleStartEdit}>✏️ 编辑文本</button>
                </div>
                <button className="cw-btn cw-btn-primary" onClick={() => sessionId && handleSubmit(sessionId, transcript)}>
                  🚀 提交创作灵感
                </button>
              </>
            )}
          </div>
        ) : (
          <div className="cw-empty">
            <div className="cw-empty-icon">🎤</div>
            <div className="cw-empty-text">点击下方按钮开始录音</div>
            <button
              className="cw-btn cw-btn-record"
              onClick={isListening ? onStopRecording : onStartRecording}
            >
              {isListening ? '⏹ 结束录音' : '🎤 开始录音'}
            </button>
            <div className="cw-empty-hint">录音完成后会自动识别，点击"提交创作灵感"开始分析</div>
          </div>
        )}
      </div>
    );
  }

  // ─── Render: Rounds ───
  const modeLabel = mode === 'novel' ? '写小说' : '项目策划';

  return (
    <div className="cw-container">
      {/* Header */}
      <div className="cw-header">
        <span className="cw-mode-tag">{modeLabel}</span>
        <span className="cw-round-count">共 {rounds.length} 轮</span>
        <span className="cw-session-id">会话: {sessionId}</span>
      </div>

      {/* Round List */}
      <div className="cw-round-list">
        {rounds.map((round, idx) => (
          <details key={idx} className="cw-round-card" open={idx === rounds.length - 1}>
            <summary className="cw-round-summary">
              <span className="cw-round-number">第 {round.round_number} 轮</span>
              <span className="cw-round-time">
                {new Date(round.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
              </span>
            </summary>
            <div className="cw-round-body">
              {/* Raw input */}
              <div className="cw-section">
                <div className="cw-section-title">原始语音</div>
                <div className="cw-text cw-text-hover" title={round.raw_input}>
                  {round.raw_input}
                </div>
              </div>

              {/* Organized output */}
              <div className="cw-section">
                <div className="cw-section-title">整理内容</div>
                <div className="cw-text cw-text-hover" title={cleanDisplayText(round.organized_output)}>
                  {cleanDisplayText(round.organized_output)}
                </div>
              </div>

              {/* Extraction */}
              {round.extraction && Object.keys(round.extraction).length > 0 && (
                <div className="cw-section">
                  <div className="cw-section-title">提取要素</div>
                  <div className="cw-extraction-grid">
                    {Object.entries(round.extraction).map(([key, val]) => (
                      <div key={key} className="cw-extraction-item">
                        <span className="cw-extraction-key">{key}</span>
                        <span className="cw-extraction-val" title={Array.isArray(val) ? val.join(', ') : String(val)}>
                          {Array.isArray(val) ? val.join(', ') : String(val)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Suggestions */}
              {(round.tips?.length > 0 || round.innovations?.length > 0 || round.improvements?.length > 0) && (
                <div className="cw-section">
                  <div className="cw-section-title">创作建议</div>
                  <div className="cw-suggestions">
                    {round.tips?.map((t, i) => (
                      <div key={`tip-${i}`} className="cw-suggestion cw-suggestion-tip" title={t}>
                        <span className="cw-sug-icon">💡</span> {t}
                      </div>
                    ))}
                    {round.innovations?.map((t, i) => (
                      <div key={`inv-${i}`} className="cw-suggestion cw-suggestion-innovation" title={t}>
                        <span className="cw-sug-icon">✨</span> {t}
                      </div>
                    ))}
                    {round.improvements?.map((t, i) => (
                      <div key={`imp-${i}`} className="cw-suggestion cw-suggestion-improve" title={t}>
                        <span className="cw-sug-icon">🔧</span> {t}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Copy actions */}
              <div className="cw-copy-actions">
                <button
                  className="cw-btn cw-btn-copy"
                  onClick={() => handleCopy(round.organized_output, 'organized', round.round_number)}
                >
                  {copiedId === `organized-${round.round_number}` ? '✓ 已复制' : '📋 复制推荐文本'}
                </button>
                <button
                  className="cw-btn cw-btn-copy-outline"
                  onClick={() => handleCopy(round.raw_input, 'raw', round.round_number)}
                >
                  {copiedId === `raw-${round.round_number}` ? '✓ 已复制' : '🗣 复制原文'}
                </button>
              </div>
            </div>
          </details>
        ))}
      </div>

      {/* 新一轮录音补充 — 检测到新文本时显示提交入口 */}
      {transcript.trim() && (
        <div className="cw-submit-round">
          <div className="cw-submit-label">检测到补充内容：</div>
          {isEditing ? (
            <>
              <textarea
                className="cw-edit-area"
                value={editingText}
                onChange={e => setEditingText(e.target.value)}
                rows={3}
              />
              <div className="cw-edit-actions" style={{ marginTop: 6 }}>
                <button className="cw-btn cw-btn-copy-outline" onClick={() => { setEditingText(transcript); setIsEditing(false) }}>取消</button>
                <button className="cw-btn cw-btn-primary" onClick={() => { setIsEditing(false); sessionId && handleSubmit(sessionId, editingText) }}>
                  🚀 提交补充内容
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="cw-submit-text" title={transcript}>{transcript}</div>
              <div className="cw-edit-actions" style={{ marginTop: 6 }}>
                <button className="cw-btn cw-btn-copy-outline" onClick={handleStartEdit}>✏️ 编辑文本</button>
              </div>
              <button className="cw-btn cw-btn-primary" onClick={() => sessionId && handleSubmit(sessionId, transcript)}>
                🚀 提交补充内容
              </button>
            </>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="cw-actions">
        <button className="cw-btn cw-btn-continue" onClick={isListening ? onStopRecording : handleContinue}>
          {isListening ? '⏹ 结束录音' : '🎤 继续补充'}
        </button>
        <button className="cw-btn cw-btn-copy-outline" onClick={() => setShowOriginalText(true)}>
          📋 原文
        </button>
        <button className="cw-btn cw-btn-finish" onClick={handleFinish}>
          ✓ 结束创作
        </button>
      </div>
      {isListening && (
        <div className="cw-recording-hint">🔴 录音中，请对着麦克风说话...</div>
      )}

      {/* 原文弹窗 */}
      {showOriginalText && (
        <div className="cw-modal-overlay" onClick={() => setShowOriginalText(false)}>
          <div className="cw-modal" onClick={e => e.stopPropagation()}>
            <div className="cw-modal-header">
              <span>📋 原文查看</span>
              <button className="cw-btn cw-btn-copy-outline" onClick={() => setShowOriginalText(false)} style={{ border: 'none', fontSize: 16, padding: '2px 8px' }}>✕</button>
            </div>
            <div className="cw-modal-body">
              <div className="cw-section">
                <div className="cw-section-title">全部累积文本</div>
                <div className="cw-text">{rounds.map(r => r.raw_input).join('\n')}</div>
              </div>
              {rounds.map(r => (
                <div key={r.round_number} className="cw-section">
                  <div className="cw-section-title">第 {r.round_number} 轮原文</div>
                  <div className="cw-text">{r.raw_input}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
