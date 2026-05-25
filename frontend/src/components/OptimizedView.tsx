import { useState } from 'react'
import { SceneType, OfficeResult, CreationResult } from '../types'
import { optimizeApi, historyApi } from '../services/api'

interface OptimizedViewProps {
  scene: SceneType
  text: string
  originalText?: string
  result: any
  onOptimize: (result: any) => void
  onAcceptVersion?: (versionText: string) => void
  isAnalyzing?: boolean
}

export default function OptimizedView({ scene, text, originalText, result, onOptimize, onAcceptVersion, isAnalyzing }: OptimizedViewProps) {
  const [loading, setLoading] = useState(false)

  // 文本清理：去除换行、符号和生成描述
  const cleanText = (s: string): string => {
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
  }
  const [activeVersion, setActiveVersion] = useState(0)
  const [accepted, setAccepted] = useState(false)
  const hasEdits = originalText !== undefined && text !== originalText

  const handleOptimize = async () => {
    if (!text.trim()) return
    setLoading(true)
    setAccepted(false)
    try {
      const res = await optimizeApi.process(text, scene)
      onOptimize(res)
      setActiveVersion(0)
      // Save to history
      let optimizedText = ''
      if (res.versions) optimizedText = res.versions[0]?.text || ''
      else if (res.organized) optimizedText = res.organized.text
      await historyApi.save(text, optimizedText, scene)
    } catch (err) {
      console.error('Optimize error:', err)
    }
    setLoading(false)
  }

  const handleAcceptVersion = async (versionText: string) => {
    setAccepted(true)
    onAcceptVersion?.(versionText)
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
          <div className="optimize-text">{cleanText(current.text)}</div>
        </div>
        <div className="optimize-actions">
          <button className="action-btn primary" onClick={() => handleAcceptVersion(current.text)} disabled={accepted}>
            {accepted ? '✓ 已采纳' : '📋 采用此版本'}
          </button>
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
          <div className="optimize-text">{cleanText(current.text)}</div>
        </div>
        <div className="optimize-actions">
          <button className="action-btn primary" onClick={() => handleAcceptVersion(current.text)} disabled={accepted}>
            {accepted ? '✓ 已采纳' : '📋 采用此版本'}
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
          点击下方按钮生成{scene === '办公' ? '润色建议' : scene === '聊天' ? '颜文字推荐' : '内容整理'}
        </div>
      )
    }
    switch (scene) {
      case '办公':
      case '聊天': return renderOffice()
      case '创作': return renderCreation()
      default: return null
    }
  }

  return (
    <div className="card">
      <div className="card-title">
        {scene === '办公' && '✨ 润色建议'}
        {scene === '聊天' && '😊 颜文字推荐'}
        {scene === '创作' && '📝 内容整理'}
        {hasEdits && (
          <span style={{ fontSize: 11, color: '#e67e22', fontWeight: 400, marginLeft: 8 }}>
            （基于编辑后的文本）
          </span>
        )}
      </div>
      {renderSceneContent()}
      <div style={{ marginTop: 12 }}>
        {isAnalyzing && (
          <div style={{ fontSize: 12, color: '#999', textAlign: 'center', marginBottom: 8 }}>
            正在分析编辑内容...
          </div>
        )}
        <button
          className="action-btn primary"
          onClick={handleOptimize}
          disabled={loading || !text.trim()}
          style={{ width: '100%', padding: '10px', fontSize: 14 }}
        >
          {loading ? '处理中...' : `🚀 生成${scene === '办公' ? '润色' : scene === '聊天' ? '颜文字' : '整理'}建议`}
        </button>
      </div>
    </div>
  )
}
