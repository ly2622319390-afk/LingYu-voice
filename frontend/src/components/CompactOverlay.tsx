import { useState, useEffect, useCallback, useRef } from 'react';

type SceneType = '办公' | '聊天' | '创作';
type OverlayState = 'idle' | 'recording' | 'result';

interface CardItem {
  id: string;
  label: string;
  text: string;
  description?: string;
}

interface CompactOverlayProps {
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  error: string | null;
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  isElectron: boolean;
}

const SCENE_LIST: SceneType[] = ['办公', '聊天', '创作'];

/** 调用后端优化接口，返回当前场景的卡片列表 */
async function fetchOptimized(text: string, scene: SceneType): Promise<CardItem[]> {
  if (!text.trim()) return [];
  let res: Response;
  try {
    res = await fetch('http://127.0.0.1:8000/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, scene_type: scene }),
    });
  } catch {
    return [];
  }
  if (!res.ok) return [];
  const data = await res.json();

  const cards: CardItem[] = [];

  if (data.versions && Array.isArray(data.versions)) {
    for (const v of data.versions) {
      cards.push({ id: v.style, label: v.style, text: v.text, description: v.description });
    }
  } else if (data.organized) {
    cards.push({ id: 'organized', label: data.organized.style, text: data.organized.text, description: data.organized.description });
    if (data.outline) cards.push({ id: 'outline', label: data.outline.style, text: data.outline.text, description: data.outline.description });
    if (data.expanded) cards.push({ id: 'expanded', label: data.expanded.style, text: data.expanded.text, description: data.expanded.description });
  }

  return cards;
}

function ensureAtLeastOriginal(cards: CardItem[], text: string): CardItem[] {
  if (cards.length === 0 && text.trim()) {
    return [{ id: 'original', label: '原文', text, description: '直接发送原文到目标应用' }];
  }
  return cards;
}

/** 创作 API 调用 */
const CREATION_BASE = 'http://127.0.0.1:8000/api/creation';

async function createSession(mode: string): Promise<string> {
  const res = await fetch(`${CREATION_BASE}/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  });
  const data = await res.json();
  return data.session_id;
}

async function submitInput(sessionId: string, text: string): Promise<any> {
  const res = await fetch(`${CREATION_BASE}/session/${sessionId}/input`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  return res.json();
}

async function finishSession(sessionId: string): Promise<any> {
  const res = await fetch(`${CREATION_BASE}/session/${sessionId}/finish`, {
    method: 'POST',
  });
  return res.json();
}

async function trackCopy(sessionId: string, roundNum: number, target: string): Promise<void> {
  await fetch(`${CREATION_BASE}/session/${sessionId}/round/${roundNum}/copy-${target}`, {
    method: 'POST',
  });
}

export default function CompactOverlay({
  isListening, transcript, interimTranscript, error,
  onStart, onStop, onReset, isElectron,
}: CompactOverlayProps) {
  const [scene, setScene] = useState<SceneType>('办公');
  const [cards, setCards] = useState<CardItem[]>([]);
  const [loadingCards, setLoadingCards] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const prevListening = useRef(isListening);

  // ─── 创作模式状态 ───
  const [creationSessionId, setCreationSessionId] = useState<string | null>(null);
  const [creationMode, setCreationMode] = useState<'novel' | 'project' | null>(null);
  const [creationRounds, setCreationRounds] = useState<any[]>([]);
  const [creationLoading, setCreationLoading] = useState(false);
  const [creationFinished, setCreationFinished] = useState(false);
  const [creationError, setCreationError] = useState<string | null>(null);
  const prevCreationTranscript = useRef('');

  // 当前状态
  const state: OverlayState = isListening ? 'recording' : (transcript ? 'result' : 'idle');

  // ─── 办公/聊天模式的自动优化 ───
  const doOptimize = useCallback(async (text: string, sceneType: SceneType) => {
    if (!text.trim()) { setCards([]); return; }
    setLoadingCards(true);
    try {
      const result = await fetchOptimized(text, sceneType);
      setCards(ensureAtLeastOriginal(result, text));
    } catch {
      setCards(ensureAtLeastOriginal([], text));
    } finally {
      setLoadingCards(false);
    }
  }, []);

  // 非创作模式：录音停止后自动优化
  useEffect(() => {
    if (scene === '创作') return;
    const wasListening = prevListening.current;
    prevListening.current = isListening;
    if ((wasListening && !isListening && transcript) || (!wasListening && !isListening && transcript)) {
      doOptimize(transcript, scene);
    }
  }, [isListening, transcript, scene, doOptimize]);

  // ─── 创作模式逻辑 ───
  const isCreationMode = scene === '创作';

  // 进入创作模式时如果已有文本，提示可提交
  useEffect(() => {
    if (!isCreationMode) return;
    if (transcript && transcript !== prevCreationTranscript.current && !creationLoading && creationSessionId) {
      prevCreationTranscript.current = transcript;
    }
  }, [isCreationMode, transcript, creationLoading, creationSessionId]);

  const handleSelectCreationMode = async (mode: 'novel' | 'project') => {
    setCreationMode(mode);
    setCreationLoading(true);
    setCreationError(null);
    setCreationFinished(false);
    try {
      const sid = await createSession(mode);
      setCreationSessionId(sid);
      // 如果已有转录文本则自动提交
      if (transcript.trim()) {
        await handleSubmitCreation(sid, transcript);
      }
    } catch (e: any) {
      setCreationError('创建会话失败，请重试');
    } finally {
      setCreationLoading(false);
    }
  };

  const handleSubmitCreation = async (sid: string, text: string) => {
    setCreationLoading(true);
    setCreationError(null);
    try {
      const result = await submitInput(sid, text);
      setCreationRounds(prev => [...prev, result]);
    } catch (e: any) {
      setCreationError('提交失败，请重试');
    } finally {
      setCreationLoading(false);
    }
  };

  const handleContinue = () => {
    // 清除本轮转录状态，让用户继续录音
    onReset();
  };

  const handleFinish = async () => {
    if (!creationSessionId) return;
    setCreationLoading(true);
    try {
      await finishSession(creationSessionId);
      setCreationFinished(true);
    } catch (e: any) {
      setCreationError('结束会话失败');
    } finally {
      setCreationLoading(false);
    }
  };

  const handleCopyOrganized = async (text: string, roundNum: number) => {
    if (!creationSessionId) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(`org-${roundNum}`);
      setTimeout(() => setCopiedId(null), 1500);
      trackCopy(creationSessionId, roundNum, 'organized');
    } catch {}
  };

  const handleCopyRaw = async (text: string, roundNum: number) => {
    if (!creationSessionId) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(`raw-${roundNum}`);
      setTimeout(() => setCopiedId(null), 1500);
      trackCopy(creationSessionId, roundNum, 'raw');
    } catch {}
  };

  // 在场景切换到非创作时重置
  const handleSceneChange = (s: SceneType) => {
    if (s === scene) return;
    setScene(s);
    if (s !== '创作') {
      // 保留创作状态不变（切换回来可恢复）
    }
    // 非创作模式且有原文时重新优化
    if (s !== '创作' && transcript) doOptimize(transcript, s);
  };

  // 开始新创作
  const handleNewCreation = () => {
    setCreationSessionId(null);
    setCreationMode(null);
    setCreationRounds([]);
    setCreationFinished(false);
    setCreationError(null);
  };

  // ─── 主文字区内容 ───
  const mainText = isListening
    ? (transcript + interimTranscript)
    : transcript;

  // ─── 渲染创作模式 ───
  const renderCreationView = () => {
    // 状态: 已结束
    if (creationFinished) {
      return (
        <div style={styles.creationFinished}>
          <div style={{ fontSize: 16, marginBottom: 6 }}>✓ 创作已完成</div>
          <div style={{ fontSize: 12, color: '#999' }}>已保存到历史记录，可在完整界面查看</div>
          <button className="ov-btn-primary" style={{ ...styles.btnPrimary, marginTop: 12 }} onClick={handleNewCreation}>
            开始新创作
          </button>
        </div>
      );
    }

    // 状态: 模式选择（无会话）
    if (!creationSessionId) {
      return (
        <div style={styles.creationModeSelector}>
          <div style={styles.creationModeCard} onClick={() => handleSelectCreationMode('novel')}>
            <span style={{ fontSize: 28 }}>📖</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>写小说</div>
              <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>整理小说灵感、人物设定、情节脉络</div>
            </div>
          </div>
          <div style={styles.creationModeCard} onClick={() => handleSelectCreationMode('project')}>
            <span style={{ fontSize: 28 }}>💻</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>代码项目策划</div>
              <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>整理项目需求、技术方案、功能规划</div>
            </div>
          </div>
        </div>
      );
    }

    // 状态: 加载中
    if (creationLoading) {
      return (
        <div style={{ textAlign: 'center', padding: 20, color: '#667eea', fontSize: 12 }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>🔄</div>
          AI 正在分析您的创作灵感...
        </div>
      );
    }

    // 状态: 错误
    if (creationError) {
      return (
        <div style={{ ...styles.creationError, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>⚠️ {creationError}</span>
          <button className="ov-btn-primary" style={{ ...styles.btnPrimary, marginLeft: 'auto' }} onClick={() => {
            if (creationSessionId && transcript) handleSubmitCreation(creationSessionId, transcript);
            else handleSelectCreationMode(creationMode || 'novel');
          }}>
            重试
          </button>
        </div>
      );
    }

    // 状态: 已有轮次结果
    if (creationRounds.length > 0) {
      const lastRound = creationRounds[creationRounds.length - 1];
      const modeLabel = creationMode === 'novel' ? '写小说' : '项目策划';

      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, overflow: 'hidden' }}>
          {/* 轮次信息 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, flexShrink: 0 }}>
            <span style={{ padding: '2px 8px', borderRadius: 4, background: 'rgba(102,126,234,0.3)', color: '#667eea', fontWeight: 600, fontSize: 11 }}>{modeLabel}</span>
            <span style={{ color: '#999' }}>第{creationRounds.length}轮</span>
          </div>

          {/* 当前轮次卡片 */}
          <div style={{
            background: 'rgba(255,255,255,0.06)', borderRadius: 8, padding: 10,
            border: '1px solid rgba(255,255,255,0.08)', flex: 1, overflow: 'hidden',
            display: 'flex', flexDirection: 'column', minHeight: 0,
          }}>
            {/* 轮次头部 - 复制按钮 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: 11, color: '#888' }}>✓ 已整理</span>
              <div style={{ display: 'flex', gap: 4 }}>
                <button className="ov-btn-primary" style={{ ...styles.miniBtn, background: copiedId === `org-${lastRound.round_number}` ? '#2ecc71' : '#667eea', color: '#fff' }}
                  onClick={() => handleCopyOrganized(lastRound.organized_output, lastRound.round_number)}
                  title="复制推荐文本">
                  {copiedId === `org-${lastRound.round_number}` ? '✓' : '📋'} 推荐
                </button>
                <button style={{ ...styles.miniBtn, background: 'rgba(255,255,255,0.1)', color: '#ccc' }}
                  onClick={() => handleCopyRaw(lastRound.raw_input, lastRound.round_number)}
                  title="复制原始语音">
                  {copiedId === `raw-${lastRound.round_number}` ? '✓' : '🗣'} 原文
                </button>
              </div>
            </div>

            {/* 整理内容 - 可悬浮展开 */}
            <div style={{ position: 'relative', flex: 1, overflow: 'hidden', marginBottom: 6 }}>
              <div style={styles.hoverExpandText} title={lastRound.organized_output}>
                {lastRound.organized_output}
              </div>
            </div>

            {/* 建议标签页 */}
            {lastRound.tips && lastRound.tips.length > 0 && (
              <div style={{ flexShrink: 0 }}>
                <details style={{ fontSize: 12 }}>
                  <summary style={{ cursor: 'pointer', color: '#667eea', fontSize: 11, marginBottom: 4 }}>
                    💡 创作建议（{lastRound.tips.length + (lastRound.innovations?.length || 0) + (lastRound.improvements?.length || 0)} 条）
                  </summary>
                  <div style={{ maxHeight: 100, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {lastRound.tips?.map((t: string, i: number) => (
                      <div key={`tip-${i}`} style={{ padding: '3px 6px', background: 'rgba(52,152,219,0.1)', borderRadius: 4, borderLeft: '2px solid #3498db', fontSize: 11, lineHeight: 1.4, ...styles.hoverExpandText }} title={t}>💡 {t}</div>
                    ))}
                    {lastRound.innovations?.map((t: string, i: number) => (
                      <div key={`inv-${i}`} style={{ padding: '3px 6px', background: 'rgba(46,204,113,0.1)', borderRadius: 4, borderLeft: '2px solid #2ecc71', fontSize: 11, lineHeight: 1.4, ...styles.hoverExpandText }} title={t}>✨ {t}</div>
                    ))}
                    {lastRound.improvements?.map((t: string, i: number) => (
                      <div key={`imp-${i}`} style={{ padding: '3px 6px', background: 'rgba(230,126,34,0.1)', borderRadius: 4, borderLeft: '2px solid #e67e22', fontSize: 11, lineHeight: 1.4, ...styles.hoverExpandText }} title={t}>🔧 {t}</div>
                    ))}
                  </div>
                </details>
              </div>
            )}
          </div>

          {/* 操作按钮 */}
          <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
            <button className="ov-btn-primary" style={{ ...styles.btnPrimary, flex: 1, background: 'rgba(102,126,234,0.2)', color: '#667eea', border: '1px solid rgba(102,126,234,0.3)' }}
              onClick={handleContinue}>
              🎤 继续补充
            </button>
            <button className="ov-btn-danger" style={{ ...styles.btnDanger, flex: 1, background: 'rgba(231,76,60,0.15)', color: '#e74c3c', border: '1px solid rgba(231,76,60,0.2)' }}
              onClick={handleFinish}>
              ✓ 结束创作
            </button>
          </div>
        </div>
      );
    }

    // 状态: 有会话、有转录文本但尚未提交
    if (transcript.trim()) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
          <div style={{ fontSize: 12, color: '#999' }}>
            检测到语音输入，点击提交开始创作：
          </div>
          <div style={{ ...styles.hoverExpandText, padding: '8px 10px', background: 'rgba(0,0,0,0.2)', borderRadius: 6, fontSize: 13, lineHeight: 1.5 }} title={transcript}>
            {transcript}
          </div>
          <button className="ov-btn-primary" style={{ ...styles.btnPrimary, width: '100%', padding: '10px' }}
            onClick={() => creationSessionId && handleSubmitCreation(creationSessionId, transcript)}>
            🚀 提交创作灵感
          </button>
        </div>
      );
    }

    // 状态: 会话已创建，等待录音
    return (
      <div style={{ textAlign: 'center', padding: 20, color: '#888', fontSize: 12 }}>
        <div style={{ fontSize: 24, marginBottom: 6 }}>🎤</div>
        <div>请录制语音后提交创作灵感</div>
      </div>
    );
  };

  return (
    <>
      <style>{`
        .ov-card:hover { background: rgba(102,126,234,0.15) !important; border-color: rgba(102,126,234,0.4) !important; }
        .ov-card:hover .ov-card-label { color: #667eea !important; }
        .ov-scene-btn:hover { color: #ddd !important; border-color: rgba(255,255,255,0.3) !important; }
        .ov-close-btn:hover { background: rgba(255,255,255,0.1) !important; color: #fff !important; }
        .ov-btn-primary:hover { background: #5a6fd6 !important; }
        .ov-btn-danger:hover { background: #e74c3c !important; }
        .ov-btn-outline:hover { background: rgba(255,255,255,0.08) !important; color: #fff !important; }
        .ov-btn-ghost:hover { color: #aaa !important; }
        .ov-cursor { animation: ov-blink 1s step-end infinite; }
        @keyframes ov-blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }
        /* 创作模式按钮特有 hover */
        .ov-creation-btn:hover { background: rgba(46,204,113,0.2) !important; border-color: rgba(46,204,113,0.5) !important; }
        .ov-creation-btn:hover .ov-btn-label { color: #2ecc71 !important; }
      `}</style>
    <div style={styles.wrapper}>
      {/* ─── 标题栏 ─── */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.micIcon}>{isListening ? '🔴' : '🎤'}</span>
          <span style={styles.title}>语音输入</span>
        </div>

        <div style={styles.sceneGroup}>
          {SCENE_LIST.map(s => (
            <button
              key={s}
              onClick={() => handleSceneChange(s)}
              className="ov-scene-btn"
              style={{
                ...styles.sceneBtn,
                ...(scene === s ? styles.sceneBtnActive : {}),
                ...(scene === s && s === '创作' ? { background: 'rgba(46,204,113,0.25)', borderColor: 'rgba(46,204,113,0.5)', color: '#2ecc71' } : {}),
              }}
            >
              {s}
            </button>
          ))}
        </div>

        <button
          className="ov-close-btn"
          style={styles.closeBtn}
          onClick={() => (window as any).electronAPI?.hideOverlay?.()}
          title="关闭"
        >
          ✕
        </button>
      </div>

      {/* ─── 错误提示 ─── */}
      {error && <div style={styles.errorBar}>{error}</div>}

      {/* ─── 创作模式内容 ─── */}
      {isCreationMode ? (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, gap: 6 }}>
          {renderCreationView()}

          {/* 完整界面提示 */}
          <div style={{ fontSize: 11, color: '#888', textAlign: 'center', flexShrink: 0, padding: '4px 0' }}>
            ℹ️ 建议在完整界面进行深度创作
            {isElectron && (
              <span
                style={{ color: '#667eea', cursor: 'pointer', marginLeft: 4, textDecoration: 'underline' }}
                onClick={() => (window as any).electronAPI?.openFullWindow?.()}
              >⛶ 打开</span>
            )}
          </div>
        </div>
      ) : (
        <>
          {/* ─── 主文字区 (非创作) ─── */}
          <div
            style={{
              ...styles.textArea,
              ...(state === 'result' && cards.length > 0 ? styles.textAreaWithCards : {}),
            }}
            title={mainText || undefined}
          >
            {state === 'idle' && !mainText && (
              <span style={styles.placeholder}>
                {isElectron ? '按 Alt+Q 或点击悬浮球开始语音输入' : '点击开始录音'}
              </span>
            )}
            {mainText && (
              <span style={styles.mainTextContent}>{mainText}</span>
            )}
            {isListening && (
              <span style={styles.cursor} className="ov-cursor">|</span>
            )}
          </div>

          {/* ─── 卡片行 ─── */}
          <div style={styles.cardsRow}>
            {loadingCards && (
              <span style={styles.hint}>生成优化方案中...</span>
            )}
            {!loadingCards && state === 'result' && cards.length === 0 && transcript.trim() && (
              <span style={{...styles.hint, color: '#999', fontStyle: 'normal'}}>
                已识别：{transcript.length > 40 ? transcript.slice(0, 40) + '…' : transcript}
                <br/>
                <span style={{fontSize: 12, color: '#888'}}>点击下方「发送原文」直接使用</span>
              </span>
            )}
            {!loadingCards && state === 'result' && cards.length > 0 && cards.map(card => (
              <div
                key={card.id}
                className="ov-card"
                style={{
                  ...styles.card,
                  ...(copiedId === card.id ? styles.cardCopied : {}),
                }}
                onClick={() => {
                  if (!card.text.trim()) return;
                  if (isElectron && (window as any).electronAPI?.prepareText) {
                    (window as any).electronAPI.prepareText(card.text);
                  } else {
                    navigator.clipboard.writeText(card.text).catch(() => {});
                  }
                  setCopiedId(card.id);
                  setTimeout(() => setCopiedId(null), 1500);
                }}
                title={card.text + (card.description ? `\n\n${card.description}\n\n点击复制到剪贴板，点击目标窗口自动粘贴` : '')}
              >
                <div style={styles.cardLabel} className="ov-card-label">
                  {copiedId === card.id ? '✓ 已复制' : card.label}
                </div>
                <div style={styles.cardText} title={card.text}>{card.text}</div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ─── 底部操作栏 (仅非创作模式) ─── */}
      {!isCreationMode && (
        <div style={styles.footer}>
          <div style={styles.footerLeft}>
            {state === 'recording' ? (
              <button className="ov-btn-danger" style={styles.btnDanger} onClick={onStop}>
                ⏹ 停止录音
              </button>
            ) : state === 'result' ? (
              <button className="ov-btn-outline" style={styles.btnOutline} onClick={onReset}>
                🔄 重新录音
              </button>
            ) : (
              <button className="ov-btn-primary" style={styles.btnPrimary} onClick={onStart}>
                🎤 开始录音
              </button>
            )}
          </div>

          <div style={styles.footerRight}>
            {state === 'result' && isElectron && (
              <span style={styles.hintAutoPaste}>点击目标窗口自动粘贴</span>
            )}
            {state === 'result' && (
              <button
                className="ov-btn-primary"
                style={styles.btnPrimary}
                onClick={() => {
                  if (isElectron && (window as any).electronAPI?.prepareText) {
                    (window as any).electronAPI.prepareText(transcript);
                  } else {
                    navigator.clipboard.writeText(transcript).catch(() => {});
                  }
                  setCopiedId('send-original');
                  setTimeout(() => setCopiedId(null), 1500);
                }}
              >
                {copiedId === 'send-original' ? '✓ 已复制' : '📋 复制原文'}
              </button>
            )}
            {state === 'idle' && isElectron && (
              <button
                className="ov-btn-ghost"
                style={styles.btnGhost}
                onClick={() => (window as any).electronAPI?.openFullWindow?.()}
              >
                ⛶ 完整窗口
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  </>);
}

// ─── 内联样式 ───
const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    width: '100%',
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    background: 'rgba(28, 28, 36, 0.96)',
    borderRadius: 12,
    padding: '8px 14px 10px',
    color: '#eee',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
    fontSize: 13,
    boxSizing: 'border-box',
    overflow: 'hidden',
    gap: 6,
  },

  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    flexShrink: 0, height: 32,
  },
  headerLeft: { display: 'flex', alignItems: 'center', gap: 6 },
  micIcon: { fontSize: 14 },
  title: { fontSize: 14, fontWeight: 600, color: '#eee' },

  sceneGroup: { display: 'flex', gap: 4 },
  sceneBtn: {
    padding: '3px 12px', borderRadius: 4,
    border: '1px solid rgba(255,255,255,0.15)',
    background: 'transparent', color: '#aaa',
    fontSize: 12, cursor: 'pointer', transition: 'all 0.15s',
  },
  sceneBtnActive: {
    background: 'rgba(102,126,234,0.3)',
    borderColor: 'rgba(102,126,234,0.6)',
    color: '#fff',
  },
  closeBtn: {
    background: 'none', border: 'none', color: '#888',
    fontSize: 16, cursor: 'pointer', padding: '2px 6px', borderRadius: 4,
  },

  errorBar: {
    background: 'rgba(231,76,60,0.2)', color: '#e74c3c',
    padding: '4px 10px', borderRadius: 6, fontSize: 12, flexShrink: 0,
  },

  // ─── 非创作模式文字区 ───
  textArea: {
    flex: 1, minHeight: 0, padding: '10px 12px',
    background: 'rgba(0,0,0,0.2)', borderRadius: 8,
    fontSize: 15, lineHeight: 1.6, color: '#f0f0f0',
    overflow: 'hidden', display: 'flex', alignItems: 'flex-start',
    border: '1px solid rgba(255,255,255,0.06)',
  },
  textAreaWithCards: { maxHeight: 110 },
  placeholder: { color: '#666', fontSize: 13 },
  mainTextContent: {
    whiteSpace: 'pre-wrap', wordBreak: 'break-all',
    overflow: 'hidden', textOverflow: 'ellipsis',
    display: '-webkit-box', WebkitLineClamp: 4,
    WebkitBoxOrient: 'vertical' as any,
  },
  cursor: { color: '#667eea', animation: 'blink 1s step-end infinite', marginLeft: 1 },

  // ─── 卡片行 ───
  cardsRow: {
    display: 'flex', gap: 8, flexShrink: 0,
    minHeight: 70, alignItems: 'stretch',
  },
  hint: { color: '#666', fontSize: 12, padding: '8px 0', fontStyle: 'italic' },
  cardCopied: {
    background: 'rgba(46, 204, 113, 0.15) !important',
    borderColor: 'rgba(46, 204, 113, 0.4) !important',
  },
  hintAutoPaste: { fontSize: 11, color: '#888', marginRight: 8, alignSelf: 'center' },
  card: {
    flex: 1, background: 'rgba(255,255,255,0.06)', borderRadius: 8,
    padding: '8px 10px', cursor: 'pointer',
    border: '1px solid rgba(255,255,255,0.08)',
    transition: 'all 0.15s', display: 'flex',
    flexDirection: 'column', gap: 4, minWidth: 0, overflow: 'hidden',
  },
  cardLabel: { fontSize: 12, fontWeight: 600, color: '#aaa', flexShrink: 0 },
  cardText: {
    fontSize: 13, lineHeight: 1.4, color: '#ddd',
    overflow: 'hidden', textOverflow: 'ellipsis',
    display: '-webkit-box', WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical' as any,
    wordBreak: 'break-all', whiteSpace: 'pre-wrap',
  },

  // ─── 底部栏 ───
  footer: {
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between', flexShrink: 0, height: 36,
  },
  footerLeft: { display: 'flex', gap: 6 },
  footerRight: { display: 'flex', gap: 6 },

  btnPrimary: {
    padding: '5px 14px', borderRadius: 6, border: 'none',
    background: '#667eea', color: '#fff',
    fontSize: 12, fontWeight: 500, cursor: 'pointer',
  },
  btnDanger: {
    padding: '5px 14px', borderRadius: 6, border: 'none',
    background: '#c0392b', color: '#fff',
    fontSize: 12, fontWeight: 500, cursor: 'pointer',
  },
  btnOutline: {
    padding: '5px 14px', borderRadius: 6,
    border: '1px solid rgba(255,255,255,0.2)',
    background: 'transparent', color: '#ccc', fontSize: 12, cursor: 'pointer',
  },
  btnGhost: {
    padding: '5px 14px', borderRadius: 6, border: 'none',
    background: 'transparent', color: '#888', fontSize: 12, cursor: 'pointer',
  },

  // ─── 创作模式 ───
  creationModeSelector: {
    display: 'flex', flexDirection: 'column', gap: 8, flex: 1,
    justifyContent: 'center', padding: '0 8px',
  },
  creationModeCard: {
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '14px 16px', border: '1px solid rgba(255,255,255,0.15)',
    borderRadius: 10, cursor: 'pointer', transition: 'all 0.2s',
    background: 'rgba(255,255,255,0.04)',
  },
  creationFinished: {
    textAlign: 'center', padding: 20, flex: 1,
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
  },

  // ─── 悬浮展开文字 ───
  hoverExpandText: {
    overflow: 'hidden',
    display: '-webkit-box',
    WebkitLineClamp: 3,
    WebkitBoxOrient: 'vertical' as any,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-all',
    position: 'relative' as any,
    transition: 'all 0.15s',
  },
  creationError: {
    padding: 12, background: 'rgba(231,76,60,0.1)',
    border: '1px solid rgba(231,76,60,0.2)', borderRadius: 8,
    color: '#e74c3c', fontSize: 12,
  },

  // 迷你操作按钮
  miniBtn: {
    padding: '3px 8px', borderRadius: 4, border: 'none',
    fontSize: 11, cursor: 'pointer', fontWeight: 500,
  },
};
