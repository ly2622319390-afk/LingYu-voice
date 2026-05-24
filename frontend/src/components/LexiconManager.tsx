import { useState, useEffect, useCallback } from 'react'
import { LexiconWord } from '../types'
import { lexiconApi } from '../services/api'

export default function LexiconManager() {
  const [words, setWords] = useState<LexiconWord[]>([])
  const [newWord, setNewWord] = useState('')
  const [wordType, setWordType] = useState('自定义')
  const [industry, setIndustry] = useState('')
  const [search, setSearch] = useState('')
  const [tab, setTab] = useState<'list' | 'add' | 'industry'>('list')

  const loadWords = useCallback(async () => {
    try {
      const data = await lexiconApi.list(search)
      setWords(data)
    } catch (err) {
      console.error('Failed to load lexicon:', err)
    }
  }, [search])

  useEffect(() => { loadWords() }, [loadWords])

  const handleAdd = async () => {
    if (!newWord.trim()) return
    try {
      await lexiconApi.add(newWord.trim(), wordType, industry)
      setNewWord('')
      loadWords()
    } catch (err) {
      console.error('Failed to add word:', err)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await lexiconApi.delete(id)
      loadWords()
    } catch (err) {
      console.error('Failed to delete word:', err)
    }
  }

  const wordTypes = ['自定义', '专业词', '人名', '品牌名', '英文名', '缩写']
  const industries = ['互联网', '金融', '法律', '医疗', '教育', '游戏', '制造', '传媒']

  return (
    <div className="lexicon-grid">
      <div className="card" style={{ gridColumn: '1/-1' }}>
        <div className="card-title">📖 用户词库管理</div>
        <div className="sub-nav">
          <button className={`sub-nav-btn ${tab === 'list' ? 'active' : ''}`} onClick={() => setTab('list')}>词库列表</button>
          <button className={`sub-nav-btn ${tab === 'add' ? 'active' : ''}`} onClick={() => setTab('add')}>添加词条</button>
          <button className={`sub-nav-btn ${tab === 'industry' ? 'active' : ''}`} onClick={() => setTab('industry')}>行业词库</button>
        </div>
      </div>

      {tab === 'list' && (
        <div className="card" style={{ gridColumn: '1/-1' }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <input
              className="lexicon-input"
              placeholder="搜索词条..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="lexicon-list">
            {words.length === 0 && (
              <div style={{ textAlign: 'center', padding: 24, color: '#bbb' }}>
                {search ? '未找到匹配词条' : '词库为空，请先添加词条'}
              </div>
            )}
            {words.map(w => (
              <div key={w.id} className="lexicon-item">
                <div>
                  <div className="word-text">{w.word}</div>
                  <div className="word-meta">
                    <span className="word-tag">{w.word_type}</span>
                    {w.industry_tag && <span>{w.industry_tag}</span>}
                    <span>使用 {w.usage_count} 次</span>
                    <span>来源: {w.source}</span>
                  </div>
                </div>
                <button className="lexicon-del-btn" onClick={() => handleDelete(w.id)}>删除</button>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 12, color: '#999', marginTop: 8, textAlign: 'right' }}>
            共 {words.length} 条词条
          </div>
        </div>
      )}

      {tab === 'add' && (
        <div className="card" style={{ gridColumn: '1/-1' }}>
          <div className="card-title">✏️ 添加新词条</div>
          <div className="lexicon-form">
            <input
              className="lexicon-input"
              placeholder="输入词语..."
              value={newWord}
              onChange={e => setNewWord(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleAdd()}
            />
            <select className="lexicon-select" value={wordType} onChange={e => setWordType(e.target.value)}>
              {wordTypes.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <select className="lexicon-select" value={industry} onChange={e => setIndustry(e.target.value)}>
              <option value="">无行业标签</option>
              {industries.map(i => <option key={i} value={i}>{i}</option>)}
            </select>
            <button className="lexicon-add-btn" onClick={handleAdd}>添加</button>
          </div>
          <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
            💡 提示：您也可以在语音转写时点击红色波浪线的词进行快速修正，修正后的词会自动加入词库。
          </div>
        </div>
      )}

      {tab === 'industry' && (
        <div className="card" style={{ gridColumn: '1/-1' }}>
          <div className="card-title">🏢 行业词库</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
            {industries.map(i => (
              <button
                key={i}
                className={`sub-nav-btn ${industry === i ? 'active' : ''}`}
                onClick={() => setIndustry(industry === i ? '' : i)}
              >
                {i}
              </button>
            ))}
          </div>
          <div style={{ fontSize: 13, color: '#666', padding: 16, textAlign: 'center' }}>
            {industry
              ? `已选择「${industry}」行业。`
              : '请选择行业标签查看对应词汇。'}
            <div style={{ marginTop: 12 }}>
              <a href="#" onClick={e => { e.preventDefault(); window.location.hash = '#/industry' }}
                 style={{ color: '#4fc3f7' }}>
                前往行业专业词库系统 →
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
