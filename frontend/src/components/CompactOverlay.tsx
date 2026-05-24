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
    return []; // 网络错误由调用方处理（ensureAtLeastOriginal 兜底）
  }
  if (!res.ok) return [];
  const data = await res.json();

  const cards: CardItem[] = [];

  if (data.versions && Array.isArray(data.versions)) {
    // 办公场景
    for (const v of data.versions) {
      cards.push({ id: v.style, label: v.style, text: v.text, description: v.description });
    }
  } else if (data.organized) {
    // 创作场景
    cards.push({ id: 'organized', label: data.organized.style, text: data.organized.text, description: data.organized.description });
    if (data.outline) cards.push({ id: 'outline', label: data.outline.style, text: data.outline.text, description: data.outline.description });
    if (data.expanded) cards.push({ id: 'expanded', label: data.expanded.style, text: data.expanded.text, description: data.expanded.description });
  } else if (data.emoji_suggestions) {
    // 聊天场景
    if (data.emoji_suggestions.length > 0) {
      const first = data.emoji_suggestions[0];
      cards.push({ id: 'emoji', label: first.label, text: first.emojis + ' ' + text, description: '推荐表情' });
    }
    if (data.emoji_suggestions.length > 1) {
      cards.push({ id: 'kaomoji', label: data.emoji_suggestions[1].label, text: data.emoji_suggestions[1].emojis + ' ' + text, description: '颜文字风格' });
    }
    if (data.all_emojis) {
      const emojiText = data.all_emojis.slice(0, 3).map((e: any) => e.emoji).join(' ');
      cards.push({ id: 'all-emoji', label: '表情版', text: emojiText + ' ' + text, description: '带表情' });
    }
  }

  return cards;
}

/**
 * 兜底：当 API 返回空时，始终提供"发送原文"选项
 * 确保用户停止录音后永远不会看到空白界面
 */
function ensureAtLeastOriginal(cards: CardItem[], text: string): CardItem[] {
  if (cards.length === 0 && text.trim()) {
    return [{ id: 'original', label: '原文', text, description: '直接发送原文到目标应用' }];
  }
  return cards;
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
  const prevScene = useRef(scene);

  // 当前状态
  const state: OverlayState = isListening ? 'recording' : (transcript ? 'result' : 'idle');

  // 调用优化 API
  const doOptimize = useCallback(async (text: string, sceneType: SceneType) => {
    if (!text.trim()) { setCards([]); return; }
    setLoadingCards(true);
    try {
      const result = await fetchOptimized(text, sceneType);
      // 确保即使 API 返回空，也至少有一张"发送原文"卡片
      setCards(ensureAtLeastOriginal(result, text));
    } catch {
      // 网络异常时保证用户仍可发送原文
      setCards(ensureAtLeastOriginal([], text));
    } finally {
      setLoadingCards(false);
    }
  }, []);

  // 录音停止或 transcript 更新后触发优化
  useEffect(() => {
    const wasListening = prevListening.current;
    prevListening.current = isListening;

    // 场景1：录音刚停止（isListening false）且有原文
    if (wasListening && !isListening && transcript) {
      doOptimize(transcript, scene);
      return;
    }
    // 场景2：不是由录音停止触发的，但 transcript 更新了且不在录音中（final 结果到达）
    if (!wasListening && !isListening && transcript) {
      doOptimize(transcript, scene);
    }
  }, [isListening, transcript, scene, doOptimize]);

  // 切换场景 → 如果有原文则重新优化
  const handleSceneChange = (s: SceneType) => {
    if (s === scene) return;
    prevScene.current = s;
    setScene(s);
    if (transcript) doOptimize(transcript, s);
  };

  // 复制文字到剪贴板（两步粘贴：仅复制，不隐藏浮窗）
  const copyText = useCallback(async (text: string, cardId: string) => {
    if (!text.trim()) return;
    if (isElectron && (window as any).electronAPI?.prepareText) {
      (window as any).electronAPI.prepareText(text);
    } else {
      await navigator.clipboard.writeText(text).catch(() => {});
    }
    // 视觉反馈
    setCopiedId(cardId);
    setTimeout(() => setCopiedId(null), 1500);
  }, [isElectron]);

  // 注入文字到目标应用（保留旧功能用于非 Electron 或特殊场景）
  const injectText = useCallback(async (text: string) => {
    if (!text.trim()) return;
    if (isElectron && (window as any).electronAPI?.injectText) {
      const ok = await (window as any).electronAPI.injectText(text);
      if (ok) (window as any).electronAPI?.hideOverlay?.();
    } else {
      await navigator.clipboard.writeText(text);
    }
  }, [isElectron]);

  // 主文字区内容
  const mainText = isListening
    ? (transcript + interimTranscript)
    : transcript;

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

      {/* ─── 主文字区 ─── */}
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
            onClick={() => copyText(card.text, card.id)}
            title={card.text + (card.description ? `\n\n${card.description}\n\n点击复制到剪贴板，点击目标窗口自动粘贴` : '')}
          >
            <div style={styles.cardLabel}>
              {copiedId === card.id ? '✓ 已复制' : card.label}
            </div>
            <div style={styles.cardText} title={card.text}>{card.text}</div>
          </div>
        ))}
      </div>

      {/* ─── 底部操作栏 ─── */}
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
              onClick={() => copyText(transcript, 'send-original')}
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

  /* 标题栏 */
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexShrink: 0,
    height: 32,
  },
  headerLeft: { display: 'flex', alignItems: 'center', gap: 6 },
  micIcon: { fontSize: 14 },
  title: { fontSize: 14, fontWeight: 600, color: '#eee' },

  sceneGroup: { display: 'flex', gap: 4 },
  sceneBtn: {
    padding: '3px 12px',
    borderRadius: 4,
    border: '1px solid rgba(255,255,255,0.15)',
    background: 'transparent',
    color: '#aaa',
    fontSize: 12,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  sceneBtnActive: {
    background: 'rgba(102,126,234,0.3)',
    borderColor: 'rgba(102,126,234,0.6)',
    color: '#fff',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#888',
    fontSize: 16,
    cursor: 'pointer',
    padding: '2px 6px',
    borderRadius: 4,
  },

  /* 错误条 */
  errorBar: {
    background: 'rgba(231,76,60,0.2)',
    color: '#e74c3c',
    padding: '4px 10px',
    borderRadius: 6,
    fontSize: 12,
    flexShrink: 0,
  },

  /* 主文字区 */
  textArea: {
    flex: 1,
    minHeight: 0,
    padding: '10px 12px',
    background: 'rgba(0,0,0,0.2)',
    borderRadius: 8,
    fontSize: 15,
    lineHeight: 1.6,
    color: '#f0f0f0',
    overflow: 'hidden',
    display: 'flex',
    alignItems: 'flex-start',
    border: '1px solid rgba(255,255,255,0.06)',
  },
  textAreaWithCards: {
    maxHeight: 110,
  },
  placeholder: { color: '#666', fontSize: 13 },
  mainTextContent: {
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-all',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    display: '-webkit-box',
    WebkitLineClamp: 4,
    WebkitBoxOrient: 'vertical' as any,
  },
  cursor: {
    color: '#667eea',
    animation: 'blink 1s step-end infinite',
    marginLeft: 1,
  },

  /* 卡片行 */
  cardsRow: {
    display: 'flex',
    gap: 8,
    flexShrink: 0,
    minHeight: 70,
    alignItems: 'stretch',
  },
  hint: {
    color: '#666',
    fontSize: 12,
    padding: '8px 0',
    fontStyle: 'italic',
  },
  cardCopied: {
    background: 'rgba(46, 204, 113, 0.15) !important',
    borderColor: 'rgba(46, 204, 113, 0.4) !important',
  },
  hintAutoPaste: {
    fontSize: 11,
    color: '#888',
    marginRight: 8,
    alignSelf: 'center',
  },
  card: {
    flex: 1,
    background: 'rgba(255,255,255,0.06)',
    borderRadius: 8,
    padding: '8px 10px',
    cursor: 'pointer',
    border: '1px solid rgba(255,255,255,0.08)',
    transition: 'all 0.15s',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    minWidth: 0,
    overflow: 'hidden',
  },
  cardLabel: {
    fontSize: 12,
    fontWeight: 600,
    color: '#aaa',
    flexShrink: 0,
  },
  cardText: {
    fontSize: 13,
    lineHeight: 1.4,
    color: '#ddd',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical' as any,
    wordBreak: 'break-all',
    whiteSpace: 'pre-wrap',
  },

  /* 底部栏 */
  footer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexShrink: 0,
    height: 36,
  },
  footerLeft: { display: 'flex', gap: 6 },
  footerRight: { display: 'flex', gap: 6 },

  btnPrimary: {
    padding: '5px 14px',
    borderRadius: 6,
    border: 'none',
    background: '#667eea',
    color: '#fff',
    fontSize: 12,
    fontWeight: 500,
    cursor: 'pointer',
  },
  btnDanger: {
    padding: '5px 14px',
    borderRadius: 6,
    border: 'none',
    background: '#c0392b',
    color: '#fff',
    fontSize: 12,
    fontWeight: 500,
    cursor: 'pointer',
  },
  btnOutline: {
    padding: '5px 14px',
    borderRadius: 6,
    border: '1px solid rgba(255,255,255,0.2)',
    background: 'transparent',
    color: '#ccc',
    fontSize: 12,
    cursor: 'pointer',
  },
  btnGhost: {
    padding: '5px 14px',
    borderRadius: 6,
    border: 'none',
    background: 'transparent',
    color: '#888',
    fontSize: 12,
    cursor: 'pointer',
  },
};
