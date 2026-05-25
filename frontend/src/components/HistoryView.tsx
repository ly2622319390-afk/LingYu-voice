import { useState, useEffect, useCallback } from 'react'
import { HistoryItem } from '../types'
import { historyApi, correctionsApi } from '../services/api'

export default function HistoryView() {
  const [items, setItems] = useState<HistoryItem[]>([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null)
  const [tab, setTab] = useState<'list' | 'frequent'>('list')

  // 常用修正
  const [freqCorrections, setFreqCorrections] = useState<any[]>([])

  // 只展示创作模式
  const sceneFilter = '创作'

  const loadItems = useCallback(async () => {
    try {
      const data = await historyApi.list(page, sceneFilter)
      setItems(data.items)
      setTotalPages(data.total_pages)
    } catch (err) {
      console.error('Failed to load history:', err)
    }
  }, [page, sceneFilter])

  useEffect(() => { loadItems() }, [loadItems])

  const handleViewDetail = async (id: number) => {
    try {
      const item = await historyApi.detail(id)
      setSelectedItem(item)
    } catch (err) {
      console.error('Failed to load detail:', err)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除此记录？')) return
    try {
      await historyApi.delete(id)
      if (selectedItem?.id === id) setSelectedItem(null)
      loadItems()
    } catch (err) {
      console.error('Failed to delete:', err)
    }
  }

  // 加载常用修正
  useEffect(() => {
    if (tab !== 'frequent') return
    correctionsApi.frequent().then(setFreqCorrections).catch(() => {})
  }, [tab])

  // 格式化优化文本：兼容旧数据中的 JSON
  const formatOptimized = (text: string): string[] => {
    if (!text) return []
    // 检测 JSON 格式（旧数据兼容）
    const trimmed = text.trim()
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try {
        const parsed = JSON.parse(trimmed)
        // 是创作会话 JSON
        if (parsed.rounds) {
          const lines: string[] = []
          const modeLabel = parsed.mode === 'novel' ? '写小说' : '项目策划'
          lines.push(`【${modeLabel}】共 ${parsed.rounds.length} 轮`)
          for (const r of parsed.rounds) {
            lines.push(`第 ${r.round_number} 轮：`)
            lines.push(`原始语音：${r.raw_input}`)
            lines.push(`整理内容：${r.organized_output}`)
          }
          return lines
        }
        return [JSON.stringify(parsed, null, 2)]
      } catch {
        return [text]
      }
    }
    // 新格式：按行分割返回
    return text.split('\n')
  }

  // 渲染优化文本
  const renderOptimized = (text: string) => {
    const lines = formatOptimized(text)
    if (lines.length === 0) return null

    // 检测是否是创作模式的结构化展示
    const isCreationStructured = lines.some(l => l.includes('第') && l.includes('轮'))

    if (isCreationStructured) {
      const rounds: { num: number; raw: string; organized: string }[] = []
      let currentRound: any = null
      for (const line of lines) {
        const roundMatch = line.match(/第 (\d+) 轮/)
        if (roundMatch) {
          currentRound = { num: parseInt(roundMatch[1]), raw: '', organized: '' }
          rounds.push(currentRound)
        } else if (line.startsWith('原始语音：') && currentRound) {
          currentRound.raw = line.replace('原始语音：', '')
        } else if (line.startsWith('整理内容：') && currentRound) {
          currentRound.organized = line.replace('整理内容：', '')
        }
      }

      return (
        <div className="h-creation-rounds">
          {rounds.map((r, i) => (
            <div key={i} className="h-creation-round">
              <div className="h-round-title">第 {r.num} 轮</div>
              <div className="h-round-label">原始语音</div>
              <div className="h-round-text">{r.raw}</div>
              <div className="h-round-label">整理内容</div>
              <div className="h-round-text">{r.organized}</div>
            </div>
          ))}
        </div>
      )
    }

    return <div className="h-optimized">{text}</div>
  }

  return (
    <div className="history-grid">
      <div className="card" style={{ gridColumn: '1/-1' }}>
        <div className="card-title">📚 创作记录</div>
        <div className="sub-nav">
          <button className={`sub-nav-btn ${tab === 'list' ? 'active' : ''}`} onClick={() => setTab('list')}>记录列表</button>
          <button className={`sub-nav-btn ${tab === 'frequent' ? 'active' : ''}`} onClick={() => setTab('frequent')}>常用修正</button>
        </div>
      </div>

      {tab === 'list' && (
        <>
          <div className="card">
            <div className="history-list">
              {items.length === 0 && (
                <div style={{ textAlign: 'center', padding: 32, color: '#bbb' }}>
                  暂无创作记录
                </div>
              )}
              {items.map(item => (
                <div
                  key={item.id}
                  className="history-item"
                  onClick={() => handleViewDetail(item.id)}
                >
                  <div className="h-title">
                    {item.title || `创作 - ${new Date(item.created_at).toLocaleString('zh-CN')}`}
                  </div>
                  <div className="h-preview">{item.content_raw}</div>
                  <div className="h-meta">
                    <span>{item.scene_type || '未分类'}</span>
                    <span>{new Date(item.created_at).toLocaleString('zh-CN')}</span>
                    {item.content_optimized && <span>✓ 已整理</span>}
                  </div>
                </div>
              ))}
            </div>
            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 12 }}>
                <button
                  className="sub-nav-btn"
                  disabled={page <= 1}
                  onClick={() => setPage(p => p - 1)}
                >
                  上一页
                </button>
                <span style={{ padding: '6px 12px', fontSize: 13, color: '#666' }}>
                  {page} / {totalPages}
                </span>
                <button
                  className="sub-nav-btn"
                  disabled={page >= totalPages}
                  onClick={() => setPage(p => p + 1)}
                >
                  下一页
                </button>
              </div>
            )}
          </div>

          <div className="card history-detail-card">
            {selectedItem ? (
              <>
                <div className="card-title">
                  📄 详情
                  <button
                    className="lexicon-del-btn"
                    style={{ marginLeft: 'auto' }}
                    onClick={() => handleDelete(selectedItem.id)}
                  >
                    删除
                  </button>
                </div>
                <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
                  {new Date(selectedItem.created_at).toLocaleString('zh-CN')} · {selectedItem.scene_type || '未分类'}
                  {selectedItem.tags && ` · ${selectedItem.tags}`}
                </div>
                <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>原始语音：</div>
                <div className="h-raw">{selectedItem.content_raw}</div>
                {selectedItem.content_optimized && (
                  <>
                    <div style={{ fontSize: 13, fontWeight: 500, marginTop: 12, marginBottom: 4 }}>整理内容：</div>
                    {renderOptimized(selectedItem.content_optimized)}
                  </>
                )}
              </>
            ) : (
              <div className="scene-empty">点击左侧记录查看详情</div>
            )}
          </div>
        </>
      )}

      {tab === 'frequent' && (
        <div className="card" style={{ gridColumn: '1/-1' }}>
          <div className="card-title">🔄 常用修正记录</div>
          {freqCorrections.length === 0 ? (
            <div style={{ fontSize: 13, color: '#666', textAlign: 'center', padding: 32 }}>
              暂无常用修正记录。
              <br />
              您在语音识别时编辑或替换的每个词都会被记录和学习。
            </div>
          ) : (
            <div className="freq-corrections">
              <div className="freq-header">
                <span className="freq-col-original">原文</span>
                <span className="freq-col-arrow" />
                <span className="freq-col-corrected">修正为</span>
                <span className="freq-col-count">次数</span>
              </div>
              {freqCorrections.map((c, i) => (
                <div key={i} className="freq-row">
                  <span className="freq-col-original">{c.original_word}</span>
                  <span className="freq-col-arrow">→</span>
                  <span className="freq-col-corrected">{c.corrected_word}</span>
                  <span className="freq-col-count">
                    <span className="freq-badge">{c.freq}</span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
