import { useState, useEffect, useCallback } from 'react'
import { LexiconWord } from '../types'
import { lexiconApi, industryApi, documentsApi } from '../services/api'

// 模块级缓存：行业词条数量（跨组件挂载持久化）
let _cachedWordCounts: Record<string, number> | null = null

const INDUSTRIES = [
  { id: '互联网/AI', icon: '🤖', desc: '编程、算法、大模型、框架、云计算' },
  { id: '金融', icon: '💰', desc: '证券、银行、金融科技、投资、保险' },
  { id: '医疗', icon: '🏥', desc: '临床、药学、器械、公共卫生、生物' },
  { id: '法律', icon: '⚖️', desc: '法规、合同、诉讼、知识产权、合规' },
  { id: '教育', icon: '📚', desc: '课程、教学、教研、在线教育、留学' },
  { id: '游戏/二次元', icon: '🎮', desc: '策划、美术、运营、发行、电竞' },
  { id: '电商/运营', icon: '🛒', desc: '选品、推广、数据、供应链、直播' },
  { id: '视频/自媒体', icon: '📹', desc: '剪辑、脚本、流量、平台、MCN' },
  { id: '学术/科研', icon: '🔬', desc: '论文、实验、数据、期刊、基金' },
]

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
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [wordCounts, setWordCounts] = useState<Record<string, number>>({})

  useEffect(() => {
    industryApi.selected().then(res => {
      setSelected(res.industries ?? [])
    }).catch(() => {})
    // 一次性获取所有行业的词条数量（模块级缓存，切换tab不重复加载）
    if (_cachedWordCounts) {
      setWordCounts(_cachedWordCounts)
    } else {
      industryApi.industries().then(res => {
        if (res._debug?.counts) {
          _cachedWordCounts = res._debug.counts
          setWordCounts(res._debug.counts)
        }
      }).catch(() => {})
    }
  }, [])

  const toggleAndSave = async (ind: string) => {
    const wasSelected = selected.includes(ind)
    const next = wasSelected
      ? selected.filter(i => i !== ind)
      : [...selected, ind]
    setSelected(next)
    setSaving(true)
    setMessage(null)
    try {
      const res = await industryApi.select('default', next)
      setMessage({
        type: 'success',
        text: wasSelected
          ? `已移除「${ind}」`
          : `已添加「${ind}」— 已加载 ${res.hotwords_loaded} 条热词`,
      })
    } catch (err: any) {
      setMessage({ type: 'error', text: '操作失败，请刷新后重试' })
    } finally {
      setSaving(false)
    }
  }

  const selectedIndustries = INDUSTRIES.filter(i => selected.includes(i.id))
  const unselectedIndustries = INDUSTRIES.filter(i => !selected.includes(i.id))

  return (
    <>
      {/* ─── 已选行业词库 ─── */}
      <div className="card" style={{ gridColumn: '1/-1' }}>
        <div className="card-title">
          已选行业词库
          <span style={{ fontSize: 12, color: '#999', fontWeight: 400, marginLeft: 8 }}>
            {selectedIndustries.length > 0 ? `${selectedIndustries.length} 个行业` : '（从下方点击行业添加）'}
          </span>
        </div>

        {selectedIndustries.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24, color: '#bbb', fontSize: 13 }}>
            还没有选择行业，从下方选择需要加载的专业词库
          </div>
        ) : (
          <div className="industry-grid" style={{ marginTop: 8 }}>
            {selectedIndustries.map(({ id, icon, desc }) => {
              const wc = wordCounts[id]
              return (
                <div key={id} className="industry-card selected" style={{ cursor: 'default' }}>
                  <span className="ind-icon">{icon}</span>
                  <div style={{ flex: 1, textAlign: 'left', minWidth: 0 }}>
                    <div className="ind-name">{id}</div>
                    <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>{desc}</div>
                    <div style={{ fontSize: 11, color: '#667eea', marginTop: 4 }}>
                      {wc !== undefined ? `${wc} 个词条` : '加载中...'}
                    </div>
                  </div>
                  <button
                    className="lexicon-del-btn"
                    style={{ padding: '4px 10px', fontSize: 12, flexShrink: 0 }}
                    disabled={saving}
                    onClick={e => {
                      e.stopPropagation()
                      toggleAndSave(id)
                    }}
                  >
                    移除
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* ─── 未选行业 ─── */}
      {unselectedIndustries.length > 0 && (
        <div className="card" style={{ gridColumn: '1/-1' }}>
          <div className="card-title">
            未选行业
            <span style={{ fontSize: 12, color: '#999', fontWeight: 400, marginLeft: 8 }}>
              （点击右侧按钮添加）
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {unselectedIndustries.map(({ id, icon }) => {
              const wc = wordCounts[id]
              return (
                <button
                  key={id}
                  disabled={saving}
                  onClick={() => toggleAndSave(id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '12px 16px', border: '1px solid #e8e8f0',
                    borderRadius: 10, background: '#fafafa', cursor: saving ? 'not-allowed' : 'pointer',
                    fontSize: 14, fontFamily: 'inherit', transition: 'all 0.2s',
                    textAlign: 'left', width: '100%',
                  }}
                  onMouseEnter={e => {
                    if (!saving) { (e.currentTarget as HTMLElement).style.borderColor = '#667eea'; (e.currentTarget as HTMLElement).style.background = '#f8f9ff' }
                  }}
                  onMouseLeave={e => {
                    (e.currentTarget as HTMLElement).style.borderColor = '#e8e8f0'; (e.currentTarget as HTMLElement).style.background = '#fafafa'
                  }}
                >
                  <span style={{ fontSize: 22 }}>{icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500 }}>{id}</div>
                    <div style={{ fontSize: 12, color: '#999' }}>
                      {wc !== undefined ? `${wc} 个词条` : '加载中...'}
                    </div>
                  </div>
                  <span style={{
                    padding: '4px 14px', borderRadius: 8, fontSize: 13,
                    background: '#667eea', color: '#fff', flexShrink: 0,
                  }}>
                    + 添加
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {message && (
        <div style={{
          gridColumn: '1/-1', padding: '10px 14px', borderRadius: 8,
          background: message.type === 'error' ? '#fff0f0' : '#f0fae0',
          color: message.type === 'error' ? '#c62828' : '#2e7d32',
          fontSize: 13,
        }}>
          {message.text}
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
  const [rawText, setRawText] = useState('')
  const [importing, setImporting] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [importMsg, setImportMsg] = useState('')
  const [extractedTerms, setExtractedTerms] = useState<string[]>([])

  const [documents, setDocuments] = useState<any[]>([])

  const loadDocs = useCallback(async () => {
    try {
      const data = await documentsApi.list()
      setDocuments(data)
    } catch (_) {}
  }, [])

  useEffect(() => { loadDocs() }, [loadDocs])

  const handleExtract = async () => {
    if (!rawText.trim()) {
      setImportMsg('请粘贴文档内容')
      return
    }
    setExtracting(true)
    setImportMsg('')
    setExtractedTerms([])
    try {
      const res = await documentsApi.extractTerms(rawText, docType)
      if (res.terms.length === 0) {
        setImportMsg('未识别出专业术语，请尝试输入更多文档内容')
        return
      }
      const terms = res.terms.map(t => t.term)
      const unique = [...new Set(terms)]
      setExtractedTerms(unique)
      setImportMsg(`AI${res.mode === 'llm' ? '大模型' : '规则'}识别出 ${unique.length} 个专业术语，确认后导入词库`)
    } catch (err: any) {
      setImportMsg('提取失败: ' + (err.message || ''))
    } finally {
      setExtracting(false)
    }
  }

  const handleImport = async () => {
    if (extractedTerms.length === 0) return
    setImporting(true)
    setImportMsg('')
    try {
      const autoName = `导入文档_${new Date().toLocaleDateString('zh-CN')}`
      await documentsApi.import(autoName, docType.trim() || '其他', extractedTerms)
      setImportMsg(`成功导入 ${extractedTerms.length} 条术语到词库`)
      setRawText('')
      setExtractedTerms([])
      loadDocs()
    } catch (err: any) {
      setImportMsg('导入失败: ' + (err.message || ''))
    } finally {
      setImporting(false)
    }
  }

  const handleCancel = () => {
    setExtractedTerms([])
    setImportMsg('')
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
      <div className="card" style={{ gridColumn: '1/-1' }}>
        <div className="card-title">导入文档术语</div>
        <p style={{ fontSize: 13, color: '#888', marginBottom: 16, lineHeight: 1.5 }}>
          AI 自动提取文档中的专业名词、技术术语、公司名、人名等，一键导入用户词库
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
            <span style={{ fontSize: 12, color: '#999', alignSelf: 'center' }}>
              选择文档类型有助于 AI 更准确提取
            </span>
          </div>
          <textarea
            className="lexicon-input"
            placeholder={"粘贴文档内容，AI 将自动提取其中的专业词汇…\n例如：技术文档、项目说明、研究报告等"}
            value={rawText}
            onChange={e => setRawText(e.target.value)}
            style={{ minHeight: 120, resize: 'vertical', padding: 8, fontFamily: 'inherit' }}
          />
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <button className="lexicon-add-btn" onClick={handleExtract} disabled={extracting || !rawText.trim()}>
              {extracting ? 'AI 提取中...' : 'AI 提取术语'}
            </button>
            {rawText.trim() && !extracting && (
              <span style={{ fontSize: 12, color: '#888' }}>
                共 {rawText.length} 字
              </span>
            )}
          </div>

          {extractedTerms.length > 0 && (
            <div style={{
              border: '1px solid #e0e0e0', borderRadius: 8, padding: 12,
              background: '#fafbff', marginTop: 4,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 500, color: '#333' }}>
                  提取到 {extractedTerms.length} 个专业术语：
                </span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    onClick={handleCancel}
                    style={{
                      padding: '4px 12px', fontSize: 12, borderRadius: 6,
                      border: '1px solid #ccc', background: '#fff', cursor: 'pointer',
                      fontFamily: 'inherit',
                    }}
                  >
                    取消
                  </button>
                  <button
                    onClick={handleImport}
                    disabled={importing}
                    style={{
                      padding: '4px 12px', fontSize: 12, borderRadius: 6,
                      border: 'none', background: '#667eea', color: '#fff',
                      cursor: importing ? 'not-allowed' : 'pointer', fontFamily: 'inherit',
                    }}
                  >
                    {importing ? '导入中...' : '确认导入词库'}
                  </button>
                </div>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {extractedTerms.map((t, i) => (
                  <span key={i} className="word-chip">{t}</span>
                ))}
              </div>
            </div>
          )}

          {importMsg && (
            <div style={{
              padding: '8px 12px', borderRadius: 6,
              background: importMsg.includes('失败') || importMsg.includes('未') ? '#fff0f0' : '#f0fae0',
              color: importMsg.includes('失败') || importMsg.includes('未') ? '#c62828' : '#2e7d32', fontSize: 13,
            }}>
              {importMsg}
            </div>
          )}
        </div>
      </div>

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

