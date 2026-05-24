import { useState, useEffect, useCallback } from 'react'
import { LexiconWord, IndustryWord } from '../types'
import { lexiconApi, industryApi, documentsApi } from '../services/api'

const INDUSTRIES = [
  { id: '互联网/AI', icon: '🤖', desc: '编程、算法、大模型' },
  { id: '金融', icon: '💰', desc: '证券、银行、投资' },
  { id: '医疗', icon: '🏥', desc: '临床、药学、器械' },
  { id: '法律', icon: '⚖️', desc: '法规、合同、诉讼' },
  { id: '教育', icon: '📚', desc: '课程、教学、教研' },
  { id: '游戏/二次元', icon: '🎮', desc: '策划、美术、运营' },
  { id: '电商/运营', icon: '🛒', desc: '选品、推广、数据' },
  { id: '视频/自媒体', icon: '📹', desc: '剪辑、脚本、流量' },
  { id: '学术/科研', icon: '🔬', desc: '论文、实验、数据' },
]

const WORD_TYPE_LABELS: Record<string, string> = {
  framework: '框架', tool: '工具', concept: '概念', brand: '品牌',
  product: '产品', library: '库', model: '模型', protocol: '协议',
  platform: '平台', standard: '标准',
}

type Tab = 'list' | 'add' | 'industry' | 'import'

export default function LexiconIndustryManager() {
  const [tab, setTab] = useState<Tab>('list')

  return (
    <div className="lexicon-grid">
      <div className="card" style={{ gridColumn: '1/-1' }}>
        <div className="card-title">📖 词库管理</div>
        <div className="sub-nav">
          <button className={`sub-nav-btn ${tab === 'list' ? 'active' : ''}`} onClick={() => setTab('list')}>词库列表</button>
          <button className={`sub-nav-btn ${tab === 'add' ? 'active' : ''}`} onClick={() => setTab('add')}>添加词条</button>
          <button className={`sub-nav-btn ${tab === 'industry' ? 'active' : ''}`} onClick={() => setTab('industry')}>行业词库</button>
          <button className={`sub-nav-btn ${tab === 'import' ? 'active' : ''}`} onClick={() => setTab('import')}>导入文档</button>
        </div>
      </div>

      {tab === 'list' && <LexiconList />}
      {tab === 'add' && <LexiconAdd />}
      {tab === 'industry' && <IndustryPanel />}
      {tab === 'import' && <ImportPanel />}
    </div>
  )
}

/* ════════════════════════════════════════
   Tab: 词库列表
   ════════════════════════════════════════ */
function LexiconList() {
  const [words, setWords] = useState<LexiconWord[]>([])
  const [search, setSearch] = useState('')

  const loadWords = useCallback(async () => {
    try {
      const data = await lexiconApi.list(search)
      setWords(data)
    } catch (err) {
      console.error('Failed to load lexicon:', err)
    }
  }, [search])

  useEffect(() => { loadWords() }, [loadWords])

  const handleDelete = async (id: number) => {
    try {
      await lexiconApi.delete(id)
      loadWords()
    } catch (err) {
      console.error('Failed to delete word:', err)
    }
  }

  return (
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
  )
}

/* ════════════════════════════════════════
   Tab: 添加词条
   ════════════════════════════════════════ */
function LexiconAdd() {
  const [newWord, setNewWord] = useState('')
  const [wordType, setWordType] = useState('自定义')
  const [industry, setIndustry] = useState('')
  const [msg, setMsg] = useState('')
  const wordTypes = ['自定义', '专业词', '人名', '品牌名', '英文名', '缩写']
  const industries = ['互联网', '金融', '法律', '医疗', '教育', '游戏', '制造', '传媒']

  const handleAdd = async () => {
    if (!newWord.trim()) return
    try {
      await lexiconApi.add(newWord.trim(), wordType, industry)
      setNewWord('')
      setMsg('已添加')
      setTimeout(() => setMsg(''), 2000)
    } catch (err) {
      setMsg('添加失败')
    }
  }

  return (
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
      {msg && <div style={{ marginTop: 8, fontSize: 13, color: msg === '已添加' ? '#2e7d32' : '#c62828' }}>{msg}</div>}
      <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
        💡 提示：您也可以在语音转写时点击红色波浪线的词进行快速修正，修正后的词会自动加入词库。
      </div>
    </div>
  )
}

/* ════════════════════════════════════════
   Tab: 行业词库
   ════════════════════════════════════════ */
function IndustryPanel() {
  const [selected, setSelected] = useState<string[]>([])
  const [pendingSet, setPendingSet] = useState<Set<string>>(new Set())
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  const [wordsMap, setWordsMap] = useState<Record<string, IndustryWord[]>>({})
  const [expanded, setExpanded] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [categoryCounts, setCategoryCounts] = useState<Record<string, Record<string, number>>>({})
  const [wordCounts, setWordCounts] = useState<Record<string, number>>({})

  const CATEGORY_ORDER = ['专业层', '基础层', '办公层', '黑话层']
  const CATEGORY_LABELS: Record<string, string> = {
    '专业层': '专业术语',
    '基础层': '基础概念',
    '办公层': '办公表达',
    '黑话层': '行业黑话',
  }

  useEffect(() => {
    industryApi.selected().then(res => {
      setSelected(res.industries)
      setPendingSet(new Set(res.industries))
    }).catch(() => {})
    // 加载所有行业的词条数量
    Promise.all(INDUSTRIES.map(ind =>
      industryApi.wordsByIndustry(ind.id).then(res => ({ id: ind.id, count: res.words.length })).catch(() => ({ id: ind.id, count: 0 }))
    )).then(results => {
      const counts: Record<string, number> = {}
      results.forEach(r => { counts[r.id] = r.count })
      setWordCounts(counts)
    })
  }, [])

  const toggle = (ind: string) => {
    setPendingSet(prev => {
      const next = new Set(prev)
      if (next.has(ind)) next.delete(ind)
      else next.add(ind)
      return next
    })
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage('')
    const list = [...pendingSet]
    try {
      const res = await industryApi.select('default', list)
      setSelected(list)
      setMessage(`已保存 — ${res.hotwords_loaded} 条行业热词已加载`)
    } catch (err: any) {
      setMessage('保存失败: ' + (err.message || ''))
    } finally {
      setSaving(false)
    }
  }

  const loadWords = async (ind: string) => {
    if (expanded === ind) { setExpanded(''); setSelectedCategory(''); return }
    setExpanded(ind)
    // 加载分类统计
    industryApi.categories(ind).then(res => {
      setCategoryCounts(prev => ({ ...prev, [ind]: res.categories }))
    }).catch(() => {})
    if (!wordsMap[ind]) {
      try {
        const res = await industryApi.wordsByIndustry(ind)
        setWordsMap(prev => ({ ...prev, [ind]: res.words }))
      } catch (_) {}
    }
  }

  const loadCategory = async (ind: string, cat: string) => {
    setSelectedCategory(cat === selectedCategory ? '' : cat)
    if (cat !== selectedCategory && (!wordsMap[ind] || !wordsMap[ind].some(w => w.category === cat))) {
      try {
        const res = await industryApi.wordsByCategory(ind, cat)
        // Merge category words into existing map
        setWordsMap(prev => {
          const existing = prev[ind] || []
          const merged = [...existing]
          for (const w of res.words) {
            if (!merged.find(m => m.word === w.word)) merged.push(w)
          }
          return { ...prev, [ind]: merged }
        })
      } catch (_) {}
    }
  }

  const selectedIndustries = INDUSTRIES.filter(i => pendingSet.has(i.id))
  const unselectedIndustries = INDUSTRIES.filter(i => !pendingSet.has(i.id))

  return (
    <>
      {/* ─── 行业选择网格 ─── */}
      <div className="card" style={{ gridColumn: '1/-1' }}>
        <div className="card-title">选择行业领域</div>
        <p style={{ fontSize: 13, color: '#888', marginBottom: 16, lineHeight: 1.5 }}>
          选择您所在的行业，系统将自动加载对应的专业词库，提升行业术语的语音识别准确率
        </p>

        <div className="industry-grid">
          {INDUSTRIES.map(({ id, icon, desc }) => {
            const isSelected = pendingSet.has(id)
            return (
              <button
                key={id}
                className={`industry-card ${isSelected ? 'selected' : ''}`}
                onClick={() => toggle(id)}
              >
                <span className="ind-icon">{icon}</span>
                <div style={{ flex: 1, textAlign: 'left' }}>
                  <div className="ind-name">{id}</div>
                  <div className="ind-count">{desc}</div>
                </div>
                <span className="ind-check">{isSelected ? '✓' : ''}</span>
              </button>
            )
          })}
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <button className="lexicon-add-btn" onClick={handleSave} disabled={saving}>
            {saving ? '保存中...' : '保存选择'}
          </button>
          <span style={{ fontSize: 13, color: '#888' }}>
            已选 {pendingSet.size} 个行业
          </span>
        </div>

        {message && (
          <div style={{
            marginTop: 12, padding: '8px 12px', borderRadius: 6,
            background: message.includes('失败') ? '#fff0f0' : '#f0fae0',
            color: message.includes('失败') ? '#c62828' : '#2e7d32', fontSize: 13,
          }}>
            {message}
          </div>
        )}
      </div>

      {/* ─── 已选行业词库 ─── */}
      {selectedIndustries.length > 0 && (
        <div className="card" style={{ gridColumn: '1/-1' }}>
          <div className="card-title">
            已选行业词库
            <span style={{ fontSize: 12, color: '#999', fontWeight: 400, marginLeft: 8 }}>
              （点击行业展开查看词条）
            </span>
          </div>
          {selectedIndustries.map(({ id, icon }) => (
            <div key={id} style={{ borderBottom: '1px solid #f0f0f0' }}>
              <div
                style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '12px 8px', cursor: 'pointer', borderRadius: 6, userSelect: 'none',
                }}
                onClick={() => loadWords(id)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 20 }}>{icon}</span>
                  <div>
                    <span style={{ fontWeight: 500 }}>{id}</span>
                    {wordsMap[id] && (
                      <span style={{ marginLeft: 8, fontSize: 12, color: '#999' }}>
                        {wordsMap[id].length} 条
                      </span>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <button
                    className="lexicon-del-btn"
                    style={{ padding: '2px 10px', fontSize: 12, position: 'relative', zIndex: 1 }}
                    onClick={e => {
                      e.stopPropagation()
                      const next = selected.filter(i => i !== id)
                      setSelected(next)
                      setPendingSet(new Set(next))
                      industryApi.select('default', next).catch(() => {})
                    }}
                  >
                    移除
                  </button>
                  <span style={{
                    color: '#999', fontSize: 12, transition: 'transform 0.2s',
                    display: 'inline-block', transform: expanded === id ? 'rotate(180deg)' : '',
                  }}>
                    ▼
                  </span>
                </div>
              </div>
              {expanded === id && (
                <div style={{ padding: '0 8px 12px' }}>
                  {categoryCounts[id] && (
                    <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
                      {CATEGORY_ORDER.map(cat => {
                        const count = categoryCounts[id]?.[cat] || 0
                        if (count === 0) return null
                        return (
                          <button
                            key={cat}
                            onClick={() => loadCategory(id, cat)}
                            style={{
                              padding: '4px 12px', borderRadius: 14, border: 'none',
                              fontSize: 12, cursor: 'pointer', fontFamily: 'inherit',
                              background: selectedCategory === cat ? '#667eea' : '#f0f0f8',
                              color: selectedCategory === cat ? '#fff' : '#555',
                            }}
                          >
                            {CATEGORY_LABELS[cat] || cat} ({count})
                          </button>
                        )
                      })}
                    </div>
                  )}
                  <WordList
                    words={(wordsMap[id] || []).filter(w => !selectedCategory || w.category === selectedCategory)}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ─── 未选行业预览 ─── */}
      {unselectedIndustries.length > 0 && (
        <div className="card" style={{ gridColumn: '1/-1' }}>
          <div className="card-title">
            未选行业
            <span style={{ fontSize: 12, color: '#999', fontWeight: 400, marginLeft: 8 }}>
              （共 {unselectedIndustries.length} 个行业可添加）
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {unselectedIndustries.map(({ id, icon, desc }) => (
              <button
                key={id}
                onClick={() => toggle(id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '10px 14px', border: '1px solid #e8e8f0',
                  borderRadius: 10, background: '#fafafa', cursor: 'pointer',
                  fontSize: 13, fontFamily: 'inherit', transition: 'all 0.2s',
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = '#667eea'; (e.currentTarget as HTMLElement).style.background = '#f8f9ff' }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = '#e8e8f0'; (e.currentTarget as HTMLElement).style.background = '#fafafa' }}
              >
                <span style={{ fontSize: 18 }}>{icon}</span>
                <div style={{ textAlign: 'left' }}>
                  <div style={{ fontWeight: 500 }}>{id}</div>
                  <div style={{ fontSize: 11, color: '#999' }}>
                    {wordCounts[id] ? `${wordCounts[id]} 条词条` : desc}
                  </div>
                </div>
                <span style={{ color: '#667eea', fontSize: 11, marginLeft: 4 }}>+添加</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

/* ════════════════════════════════════════
   Tab: 导入文档
   ════════════════════════════════════════ */
function ImportPanel() {
  const [docType, setDocType] = useState('')
  const [termsText, setTermsText] = useState('')
  const [importing, setImporting] = useState(false)
  const [importMsg, setImportMsg] = useState('')

  const [documents, setDocuments] = useState<any[]>([])

  const loadDocs = useCallback(async () => {
    try {
      const data = await documentsApi.list()
      setDocuments(data)
    } catch (_) {}
  }, [])

  useEffect(() => { loadDocs() }, [loadDocs])

  const handleImport = async () => {
    if (!termsText.trim()) {
      setImportMsg('请粘贴术语列表')
      return
    }
    setImporting(true)
    setImportMsg('')
    try {
      const terms = termsText.split('\n').map(s => s.trim()).filter(Boolean)
      const autoName = `导入文档_${new Date().toLocaleDateString('zh-CN')}`
      await documentsApi.import(autoName, docType.trim() || '其他', terms)
      setImportMsg(`成功导入 ${terms.length} 条术语`)
      setDocType(''); setTermsText('')
      loadDocs()
    } catch (err: any) {
      setImportMsg('导入失败: ' + (err.message || ''))
    } finally {
      setImporting(false)
    }
  }

  const handleDeleteDoc = async (id: number) => {
    try {
      await documentsApi.delete(id)
      loadDocs()
    } catch (_) {}
  }

  const totalTerms = documents.reduce((sum, d) => sum + (d.extracted_terms?.length || 0), 0)

  return (
    <>
      {/* ─── 导入表单 ─── */}
      <div className="card" style={{ gridColumn: '1/-1' }}>
        <div className="card-title">导入文档术语</div>
        <p style={{ fontSize: 13, color: '#888', marginBottom: 16, lineHeight: 1.5 }}>
          从专业文档中提取术语，粘贴到下方即可导入用户词库
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <select
              className="lexicon-select"
              value={docType}
              onChange={e => setDocType(e.target.value)}
              style={{ width: 150 }}
            >
              <option value="">选择类型</option>
              <option value="技术文档">技术文档</option>
              <option value="产品文档">产品文档</option>
              <option value="项目文档">项目文档</option>
              <option value="研究报告">研究报告</option>
              <option value="其他">其他</option>
            </select>
          </div>
          <textarea
            className="lexicon-input"
            placeholder="每行一个专业术语，例如：&#10;Transformer&#10;RAG&#10;LoRA&#10;向量数据库"
            value={termsText}
            onChange={e => setTermsText(e.target.value)}
            style={{ minHeight: 100, resize: 'vertical', padding: 8 }}
          />
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <button className="lexicon-add-btn" onClick={handleImport} disabled={importing}>
              {importing ? '导入中...' : '导入词条'}
            </button>
            {termsText.trim() && (
              <span style={{ fontSize: 12, color: '#888' }}>
                共 {termsText.split('\n').filter(s => s.trim()).length} 个术语
              </span>
            )}
          </div>
          {importMsg && (
            <div style={{
              padding: '8px 12px', borderRadius: 6,
              background: importMsg.includes('失败') ? '#fff0f0' : '#f0fae0',
              color: importMsg.includes('失败') ? '#c62828' : '#2e7d32', fontSize: 13,
            }}>
              {importMsg}
            </div>
          )}
        </div>
      </div>

      {/* ─── 已导入文档列表 ─── */}
      <div className="card" style={{ gridColumn: '1/-1' }}>
        <div className="card-title">
          已导入文档
          <span style={{ fontSize: 12, color: '#999', fontWeight: 400, marginLeft: 8 }}>
            {documents.length > 0 ? `共 ${documents.length} 个文档，${totalTerms} 条术语` : ''}
          </span>
        </div>
        {documents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24, color: '#bbb', fontSize: 13 }}>
            还没有导入过文档
          </div>
        ) : (
          documents.map(doc => (
            <div key={doc.id} className="lexicon-item">
              <div>
                <div className="word-text">{doc.file_name}</div>
                <div className="word-meta">
                  <span className="word-tag">{doc.file_type}</span>
                  <span>{doc.extracted_terms?.length || 0} 条术语</span>
                  <span>{doc.imported_at}</span>
                </div>
                {doc.extracted_terms && doc.extracted_terms.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                    {doc.extracted_terms.slice(0, 10).map((t: string, i: number) => (
                      <span key={i} className="word-chip" style={{ fontSize: 12 }}>{t}</span>
                    ))}
                    {doc.extracted_terms.length > 10 && (
                      <span style={{ fontSize: 11, color: '#999' }}>+{doc.extracted_terms.length - 10} 更多</span>
                    )}
                  </div>
                )}
              </div>
              <button className="lexicon-del-btn" onClick={() => handleDeleteDoc(doc.id)}>删除</button>
            </div>
          ))
        )}
      </div>
    </>
  )
}

/* ════════════════════════════════════════
   词条展示（按类型分组）
   ════════════════════════════════════════ */
function WordList({ words }: { words: IndustryWord[] }) {
  const groups: Record<string, IndustryWord[]> = {}
  for (const w of words) {
    const t = w.type || 'other'
    if (!groups[t]) groups[t] = []
    groups[t].push(w)
  }
  const keys = Object.keys(groups).sort((a, b) => (b === 'other' ? -1 : 1))

  if (words.length === 0) {
    return <div style={{ color: '#bbb', fontSize: 13, padding: 8 }}>暂无词条数据</div>
  }

  return (
    <div>
      {keys.map(key => (
        <div key={key} className="word-type-group">
          <div className="word-type-title">
            {WORD_TYPE_LABELS[key] || key}
            <span style={{ color: '#bbb', marginLeft: 4 }}>({groups[key].length})</span>
          </div>
          <div className="word-type-tags">
            {groups[key].map(w => (
              <span key={w.id || w.word} className="word-chip">{w.word}</span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
