import { useState } from 'react';
import { creationApi } from '../services/api';

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
  onClearTranscript: () => void;
}

export default function CreationWorkspace({ transcript, onClearTranscript }: CreationWorkspaceProps) {
  const [mode, setMode] = useState<CreationMode | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [rounds, setRounds] = useState<CreationRoundData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [finished, setFinished] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // ─── Handlers ───

  const handleSelectMode = async (m: CreationMode) => {
    setMode(m);
    setLoading(true);
    setError(null);
    setFinished(false);
    try {
      const res = await creationApi.createSession(m);
      setSessionId(res.session_id);
      if (transcript.trim()) {
        await handleSubmit(res.session_id, transcript);
      }
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
    } catch {
      setError('提交失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleContinue = () => {
    onClearTranscript();
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
          选择创作方向后，录制语音或输入文字，AI 将帮助您结构化整理
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
            <div className="cw-submit-text" title={transcript}>{transcript}</div>
            <button className="cw-btn cw-btn-primary" onClick={() => sessionId && handleSubmit(sessionId, transcript)}>
              🚀 提交创作灵感
            </button>
          </div>
        ) : (
          <div className="cw-empty">
            <div className="cw-empty-icon">🎤</div>
            <div className="cw-empty-text">录制语音后提交创作灵感</div>
            <div className="cw-empty-hint">或使用左侧文本编辑区输入内容</div>
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
                <div className="cw-text cw-text-hover" title={round.organized_output}>
                  {round.organized_output}
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

      {/* Actions */}
      <div className="cw-actions">
        <button className="cw-btn cw-btn-continue" onClick={handleContinue}>
          🎤 继续补充
        </button>
        <button className="cw-btn cw-btn-finish" onClick={handleFinish}>
          ✓ 结束创作
        </button>
      </div>
    </div>
  );
}
