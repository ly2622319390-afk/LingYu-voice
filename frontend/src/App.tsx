import { useState, useEffect, useMemo, useRef } from 'react'
import './App.css'
import { SceneType, EditAnalysis } from './types'
import { useSpeechRecognition } from './hooks/useSpeechRecognition'
import { useAudioCapture } from './hooks/useAudioCapture'
import { useElectronIPC } from './hooks/useElectronIPC'
import Recorder from './components/Recorder'
import Transcript from './components/Transcript'
import SceneSwitcher from './components/SceneSwitcher'
import OptimizedView from './components/OptimizedView'
import LexiconIndustryManager from './components/LexiconIndustryManager'
import HistoryView from './components/HistoryView'
import CompactOverlay from './components/CompactOverlay'
import CreationWorkspace from './components/CreationWorkspace'
import { industryApi, editsApi, optimizeApi, correctionsApi } from './services/api'

type PageView = 'main' | 'lexicon' | 'history'
type AppMode = 'web' | 'overlay' | 'full'

export default function App() {
  // 检测运行模式: URL query 参数 ?mode=overlay / ?mode=full
  const appMode = useMemo<AppMode>(() => {
    const params = new URLSearchParams(window.location.search)
    const mode = params.get('mode')
    if (mode === 'overlay') return 'overlay'
    if (mode === 'full') return 'full'
    return 'web'
  }, [])

  const isDesktop = appMode === 'overlay' || appMode === 'full'
  const { isElectron } = useElectronIPC()

  // 桌面模式使用音频捕获 (WebSocket ASR)，Web 模式使用 Web Speech API
  const webSpeech = useSpeechRecognition()
  const audioCapture = useAudioCapture()

  // 根据模式选择正确的 hook
  const speech = appMode === 'overlay' || (appMode === 'full' && isElectron)
    ? audioCapture
    : webSpeech

  const { isListening, transcript, interimTranscript, isSupported, error, startListening, stopListening, resetTranscript } = speech

  const [scene, setScene] = useState<SceneType>('办公')
  const [view, setView] = useState<PageView>('main')
  const [optimizedResult, setOptimizedResult] = useState<any>(null)
  const [uncertainWords, setUncertainWords] = useState<{ word: string; suggestions: string[]; position: number }[]>([])
  const [industrySelected, setIndustrySelected] = useState<string[]>([])
  const [industryHotwords, setIndustryHotwords] = useState(0)

  // ─── 编辑追踪状态 ───
  const [editedTranscript, setEditedTranscript] = useState('')
  const [editAnalysis, setEditAnalysis] = useState<EditAnalysis | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  // 新录音时重置编辑状态
  useEffect(() => {
    setEditedTranscript(transcript)
    setEditAnalysis(null)
  }, [transcript])

  // 从办公/聊天切换到创作时，清空转录文本让用户重新录音
  const prevSceneRef = useRef(scene)
  useEffect(() => {
    if (prevSceneRef.current !== '创作' && scene === '创作') {
      resetTranscript()
      setOptimizedResult(null)
      setEditAnalysis(null)
      setUncertainWords([])
      autoTriggeredRef.current = false
    }
    prevSceneRef.current = scene
  }, [scene])

  // 录音结束后自动触发优化（修复时序：等 SenseVoice 返回 final 文本后再触发）
  const autoTriggeredRef = useRef(false)
  useEffect(() => {
    if (isListening) {
      autoTriggeredRef.current = false // 新录音开始时重置
      return
    }
    // 录音已停止，且文本非空，且尚未触发过自动优化
    if (transcript.trim() && !autoTriggeredRef.current) {
      autoTriggeredRef.current = true
      if (scene === '创作') return // 创作模式走创作工作室，不自动优化
      optimizeApi.process(transcript, scene).then(res => {
        setOptimizedResult(res)
      }).catch(() => {})
    }
  }, [isListening, transcript, scene])

  const handleTranscriptChange = (newTranscript: string) => {
    resetTranscript()
    const words = newTranscript.split(/[\s，。、；：]+/).filter(w => w.length > 1)
    const uncertain = words
      .filter(w => w.length >= 2 && Math.random() > 0.85)
      .slice(0, 3)
      .map((w, i) => ({
        word: w,
        suggestions: [w, w + '（候选）', '候选词' + (i + 1)],
        position: newTranscript.indexOf(w),
      }))
    setUncertainWords(uncertain)
    setOptimizedResult(null)
  }

  const handleEditComplete = (edited: string) => {
    setEditedTranscript(edited)
  }

  const handleAcceptVersion = async (versionText: string) => {
    // 编辑分析：对比原文和编辑后的文本
    if (editedTranscript !== transcript) {
      setIsAnalyzing(true)
      try {
        const analysis = await editsApi.analyze(transcript, editedTranscript, scene)
        setEditAnalysis(analysis)
        console.log('编辑分析结果:', analysis)
      } catch (err) {
        console.error('编辑分析失败:', err)
      }
      setIsAnalyzing(false)
    }
    // 复制到剪贴板
    try {
      await navigator.clipboard.writeText(versionText)
    } catch {
      // ignore
    }
  }

  // 完整窗口加载行业词库状态
  useEffect(() => {
    if (appMode !== 'full') return
    industryApi.selected().then(res => setIndustrySelected(res.industries ?? [])).catch(() => setIndustrySelected([]))
    industryApi.hotwords().then(res => setIndustryHotwords(res.count)).catch(() => {})
  }, [view])

  // ─── 紧凑浮窗模式 ───
  if (appMode === 'overlay') {
    return (
      <CompactOverlay
        isListening={isListening}
        transcript={transcript}
        interimTranscript={interimTranscript}
        error={error}
        onStart={startListening}
        onStop={stopListening}
        onReset={() => {
          resetTranscript()
          setOptimizedResult(null)
          setUncertainWords([])
        }}
        isElectron={isElectron}
      />
    )
  }

  // ─── 完整窗口 / Web 模式 ───
  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">🎤 智能语音输入法</h1>
        <div className="header-nav">
          <button className={`nav-btn ${view === 'main' ? 'active' : ''}`} onClick={() => setView('main')}>首页</button>
          <button className={`nav-btn ${view === 'lexicon' ? 'active' : ''}`} onClick={() => setView('lexicon')}>词库管理</button>
          <button className={`nav-btn ${view === 'history' ? 'active' : ''}`} onClick={() => setView('history')}>历史记录</button>
        </div>
      </header>

      {!isSupported && (
        <div className="browser-warning">
          ⚠️ 您的浏览器不支持语音识别。请使用 Chrome 或 Edge 浏览器。
        </div>
      )}

      {view === 'main' && (
        <main className="main-content">
          <div className="left-panel">
            <SceneSwitcher scene={scene} onChange={setScene} />
            <Recorder
              isListening={isListening}
              onStart={startListening}
              onStop={stopListening}
              onNewTranscript={handleTranscriptChange}
              error={error}
              isSupported={isSupported}
            />
            <Transcript
              transcript={transcript}
              interimTranscript={interimTranscript}
              uncertainWords={uncertainWords}
              onReplaceWord={(oldWord, newWord) => {
                const newText = editedTranscript.replace(oldWord, newWord)
                setEditedTranscript(newText)
                setUncertainWords(prev => prev.filter(w => w.word !== oldWord))
                // 记录修正到历史
                correctionsApi.log(oldWord, newWord, scene, transcript, newText).catch(() => {})
                // 触发编辑分析
                editsApi.analyze(transcript, newText, scene).catch(() => {})
              }}
              onEditComplete={handleEditComplete}
            />
            {editAnalysis && editAnalysis.has_changes && (
              <div className="card">
                <div className="card-title">📊 编辑分析</div>
                <div style={{ fontSize: 12, padding: '4px 0' }}>
                  <div>类型: {editAnalysis.edit_type}</div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 4, flexWrap: 'wrap' }}>
                    {Object.entries(editAnalysis.classifications).map(([type, count]) => (
                      <span key={type} className="edit-badge">{type}: {count}</span>
                    ))}
                  </div>
                  <div style={{ marginTop: 4, color: '#999' }}>
                    已自动学习 {editAnalysis.learn_actions.filter(a => a.learned).length} 项改进
                  </div>
                </div>
              </div>
            )}
          </div>
          <div className="right-panel">
            {appMode === 'full' && scene !== '创作' && (
              <div className="industry-status-card">
                <div className="status-header">
                  <span className="status-title">行业词库</span>
                  {(industrySelected?.length ?? 0) > 0 && (
                    <span className="status-badge">{industryHotwords} 热词</span>
                  )}
                </div>
                {(industrySelected?.length ?? 0) > 0 ? (
                  <>
                    <div className="status-tags">
                      {(industrySelected ?? []).map(ind => (
                        <span key={ind} className="status-tag">{ind}</span>
                      ))}
                    </div>
                    <button className="status-action" onClick={() => setView('lexicon')}>
                      管理行业词库
                    </button>
                  </>
                ) : (
                  <>
                    <div className="status-hint">选择行业可提升专业术语识别准确率</div>
                    <button className="status-action" onClick={() => setView('lexicon')}>
                      去选择行业
                    </button>
                  </>
                )}
              </div>
            )}
            {scene === '创作' ? (
              <CreationWorkspace
                transcript={editedTranscript}
                isListening={isListening}
                onStartRecording={startListening}
                onStopRecording={stopListening}
                onClearTranscript={() => {
                  resetTranscript()
                  setOptimizedResult(null)
                  setUncertainWords([])
                }}
              />
            ) : (
              <OptimizedView
                scene={scene}
                text={editedTranscript}
                originalText={transcript}
                result={optimizedResult}
                onOptimize={setOptimizedResult}
                onAcceptVersion={handleAcceptVersion}
                isAnalyzing={isAnalyzing}
              />
            )}
          </div>
        </main>
      )}

      {view === 'lexicon' && <LexiconIndustryManager />}
      {view === 'history' && <HistoryView />}
    </div>
  )
}
