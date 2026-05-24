import { useState } from 'react'
import { SceneType, OfficeResult, ChatResult, CreationResult } from '../types'
import { optimizeApi, historyApi, correctionsApi } from '../services/api'

interface OptimizedViewProps {
  scene: SceneType
  text: string
  result: any
  onOptimize: (result: any) => void
}

export default function OptimizedView({ scene, text, result, onOptimize }: OptimizedViewProps) {
  const [loading, setLoading] = useState(false)
  const [activeVersion, setActiveVersion] = useState(0)

  const handleOptimize = async () => {
    if (!text.trim()) return
    setLoading(true)
    try {
      const res = await optimizeApi.process(text, scene)
      onOptimize(res)
      setActiveVersion(0)
      // Save to history
      let optimizedText = ''
      if (res.versions) optimizedText = res.versions[0]?.text || ''
      else if (res.organized) optimizedText = res.organized.text
      else if (res.emoji_suggestions) optimizedText = res.emoji_suggestions[0]?.emojis || ''
      await historyApi.save(text, optimizedText, scene)
    } catch (err) {
      console.error('Optimize error:', err)
    }
    setLoading(false)
  }

  const handleAcceptVersion = async (versionText: string) => {
    await correctionsApi.log(text, versionText, scene, text, versionText)
    // Copy to clipboard
    try {
      await navigator.clipboard.writeText(versionText)
      alert('已复制到剪贴板')
    } catch {
      alert('已采纳该版本')
    }
  }

  const renderOffice = () => {
    if (!result?.versions) return null
    const versions: OfficeResult[] = result.versions
    const current = versions[activeVersion]
    if (!current) return null

    return (
      <>
        <div className="optimize-tabs">
          {versions.map((v, i) => (
            <button
              key={i}
              className={`optimize-tab ${i === activeVersion ? 'active' : ''}`}
              onClick={() => setActiveVersion(i)}
            >
              {v.style}
            </button>
          ))}
        </div>
        <div className="optimize-content">
          <div className="optimize-desc">{current.description}</div>
          <div className="optimize-text">{current.text}</div>
        </div>
        <div className="optimize-actions">
          <button className="action-btn primary" onClick={() => handleAcceptVersion(current.text)}>
            📋 采用此版本
          </button>
        </div>
      </>
    )
  }

  const renderChat = () => {
    if (!result?.emoji_suggestions) return null
    const chat: ChatResult = result

    return (
      <>
        <div className="optimize-desc">检测到情绪：{chat.emotion}</div>
        <div style={{ marginBottom: 12 }}>
          {chat.emoji_suggestions.map((s, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>{s.label}</div>
              <div style={{ fontSize: 24, letterSpacing: 4 }}>{s.emojis}</div>
            </div>
          ))}
        </div>
        <div className="optimize-tabs">
          {chat.all_emojis.map((e, i) => (
            <button
              key={i}
              className="optimize-tab"
              onClick={async () => {
                await navigator.clipboard.writeText(e.emoji)
                alert(`已复制: ${e.emoji}`)
              }}
              title={e.desc}
            >
              {e.emoji}
            </button>
          ))}
        </div>
      </>
    )
  }

  const renderCreation = () => {
    if (!result?.organized) return null
    const modes = [
      { key: 'organized', label: '整理版' },
      { key: 'outline', label: '提纲版' },
      { key: 'expanded', label: '扩写版' },
    ]
    const currentKey = modes[activeVersion]?.key
    const current = result[currentKey]
    if (!current) return null

    return (
      <>
        <div className="optimize-tabs">
          {modes.map((m, i) => (
            <button
              key={i}
              className={`optimize-tab ${i === activeVersion ? 'active' : ''}`}
              onClick={() => setActiveVersion(i)}
            >
              {m.label}
            </button>
          ))}
        </div>
        <div className="optimize-content">
          <div className="optimize-desc">{current.description}</div>
          <div className="optimize-text">{current.text}</div>
        </div>
        <div className="optimize-actions">
          <button className="action-btn primary" onClick={() => handleAcceptVersion(current.text)}>
            📋 采用此版本
          </button>
        </div>
      </>
    )
  }

  const renderSceneContent = () => {
    if (!text.trim()) {
      return <div className="scene-empty">请先录制语音内容</div>
    }
    if (!result) {
      return (
        <div className="scene-empty">
          点击下方按钮生成{scene === '办公' ? '润色建议' : scene === '聊天' ? '表情推荐' : '内容整理'}
        </div>
      )
    }
    switch (scene) {
      case '办公': return renderOffice()
      case '聊天': return renderChat()
      case '创作': return renderCreation()
      default: return null
    }
  }

  return (
    <div className="card">
      <div className="card-title">
        {scene === '办公' && '✨ 润色建议'}
        {scene === '聊天' && '😊 表情推荐'}
        {scene === '创作' && '📝 内容整理'}
      </div>
      {renderSceneContent()}
      <div style={{ marginTop: 12 }}>
        <button
          className="action-btn primary"
          onClick={handleOptimize}
          disabled={loading || !text.trim()}
          style={{ width: '100%', padding: '10px', fontSize: 14 }}
        >
          {loading ? '处理中...' : `🚀 生成${scene === '办公' ? '润色' : scene === '聊天' ? '表情' : '整理'}建议`}
        </button>
      </div>
    </div>
  )
}
