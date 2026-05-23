import { useState, useEffect, useCallback } from 'react'
import { HistoryItem, SceneType } from '../types'
import { historyApi } from '../services/api'

export default function HistoryView() {
  const [items, setItems] = useState<HistoryItem[]>([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [sceneFilter, setSceneFilter] = useState('')
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null)
  const [tab, setTab] = useState<'list' | 'frequent'>('list')

  const scenes: { type: string; label: string }[] = [
    { type: '', label: '全部' },
    { type: '办公', label: '办公' },
    { type: '聊天', label: '聊天' },
    { type: '创作', label: '创作' },
  ]

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

  return (
    <div className="history-grid">
      <div className="card" style={{ gridColumn: '1/-1' }}>
        <div className="card-title">📚 历史记录</div>
        <div className="sub-nav">
          <button className={`sub-nav-btn ${tab === 'list' ? 'active' : ''}`} onClick={() => setTab('list')}>记录列表</button>
          <button className={`sub-nav-btn ${tab === 'frequent' ? 'active' : ''}`} onClick={() => setTab('frequent')}>常用修正</button>
        </div>
      </div>

      {tab === 'list' && (
        <>
          <div className="card">
            <div className="history-filter">
              {scenes.map(s => (
                <button
                  key={s.type}
                  className={`sub-nav-btn ${sceneFilter === s.type ? 'active' : ''}`}
                  onClick={() => { setSceneFilter(s.type); setPage(1) }}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <div className="history-list">
              {items.length === 0 && (
                <div style={{ textAlign: 'center', padding: 32, color: '#bbb' }}>
                  暂无历史记录
                </div>
              )}
              {items.map(item => (
                <div
                  key={item.id}
                  className="history-item"
                  onClick={() => handleViewDetail(item.id)}
                >
                  <div className="h-title">
                    {item.title || `语音输入 - ${new Date(item.created_at).toLocaleString('zh-CN')}`}
                  </div>
                  <div className="h-preview">{item.content_raw}</div>
                  <div className="h-meta">
                    <span>{item.scene_type || '未分类'}</span>
                    <span>{new Date(item.created_at).toLocaleString('zh-CN')}</span>
                    {item.content_optimized && <span>✓ 已优化</span>}
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
                <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>原文：</div>
                <div className="h-raw">{selectedItem.content_raw}</div>
                {selectedItem.content_optimized && (
                  <>
                    <div style={{ fontSize: 13, fontWeight: 500, marginTop: 12, marginBottom: 4 }}>优化版：</div>
                    <div className="h-optimized">{selectedItem.content_optimized}</div>
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
          <div style={{ fontSize: 13, color: '#666', textAlign: 'center', padding: 32 }}>
            修正词频统计功能将在多次修正后自动展示。
            <br />
            您在语音识别时点击替换的每个词都会被记录和学习。
          </div>
        </div>
      )}
    </div>
  )
}
