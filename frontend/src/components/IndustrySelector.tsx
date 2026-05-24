import { useState, useEffect } from 'react'
import { IndustryWord } from '../types'
import { industryApi, documentsApi } from '../services/api'

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
  framework: '框架',
  tool: '工具',
  concept: '概念',
  brand: '品牌',
  product: '产品',
  library: '库',
  model: '模型',
  protocol: '协议',
  platform: '平台',
  standard: '标准',
}

export default function IndustrySelector() {
  const [selected, setSelected] = useState<string[]>([])
  const [pendingSet, setPendingSet] = useState<Set<string>>(new Set())
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  const [wordsMap, setWordsMap] = useState<Record<string, IndustryWord[]>>({})
  const [expanded, setExpanded] = useState('')

  // 文档导入
  const [docName, setDocName] = useState('')
  const [docType, setDocType] = useState('')
  const [termsText, setTermsText] = useState('')
  const [importing, setImporting] = useState(false)
  const [importMsg, setImportMsg] = useState('')

  useEffect(() => {
    industryApi.selected().then(res => {
      setSelected(res.industries)
      setPendingSet(new Set(res.industries))
    }).catch(() => {})
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
    if (expanded === ind) { setExpanded(''); return }
    setExpanded(ind)
    if (!wordsMap[ind]) {
      try {
        const res = await industryApi.wordsByIndustry(ind)
        setWordsMap(prev => ({ ...prev, [ind]: res.words }))
      } catch (_) {}
    }
  }

  const handleImport = async () => {
    if (!docName.trim() || !termsText.trim()) {
      setImportMsg('请填写文档名称和术语列表')
      return
    }
    setImporting(true)
    setImportMsg('')
    try {
      const terms = termsText.split('\n').map(s => s.trim()).filter(Boolean)
      await documentsApi.import(docName.trim(), docType.trim() || '其他', terms)
      setImportMsg(`成功导入 ${terms.length} 条术语`)
      setDocName(''); setDocType(''); setTermsText('')
    } catch (err: any) {
      setImportMsg('导入失败: ' + (err.message || ''))
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="lexicon-grid">
      {/* ─── 行业选择 ─── */}
      <div className="card" style={{ gridColumn: '1/-1' }}>
        <div className="card-title">选择行业领域</div>
        <p style={{ fontSize: 13, color: '#888', marginBottom: 16, lineHeight: 1.5 }}>
          选择您所在的行业，系统将自动加载对应的专业词库，<br />
          提升行业术语的语音识别准确率
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
          <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 6, background: message.includes('失败') ? '#fff0f0' : '#f0fae0', color: message.includes('失败') ? '#c62828' : '#2e7d32', fontSize: 13 }}>
            {message}
          </div>
        )}
      </div>

      {/* ─── 已选行业词库 ─── */}
      {selected.length > 0 && (
        <div className="card" style={{ gridColumn: '1/-1' }}>
          <div className="card-title">
            已选行业词库
            <span style={{ fontSize: 12, color: '#999', fontWeight: 400 }}>
              （点击行业展开查看词条）
            </span>
          </div>
          {selected.map(ind => {
            const info = INDUSTRIES.find(i => i.id === ind)
            return (
              <div key={ind} style={{ borderBottom: '1px solid #f0f0f0' }}>
                <div
                  style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '12px 8px', cursor: 'pointer', borderRadius: 6,
                    userSelect: 'none',
                  }}
                  onClick={() => loadWords(ind)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 20 }}>{info?.icon || '📁'}</span>
                    <div>
                      <span style={{ fontWeight: 500 }}>{ind}</span>
                      {wordsMap[ind] && (
                        <span style={{ marginLeft: 8, fontSize: 12, color: '#999' }}>
                          {wordsMap[ind].length} 条
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
                        const next = selected.filter(i => i !== ind)
                        setSelected(next)
                        setPendingSet(new Set(next))
                        industryApi.select('default', next).catch(() => {})
                      }}
                    >
                      移除
                    </button>
                    <span style={{ color: '#999', fontSize: 12, transition: 'transform 0.2s', display: 'inline-block', transform: expanded === ind ? 'rotate(180deg)' : '' }}>
                      ▼
                    </span>
                  </div>
                </div>
                {expanded === ind && (
                  <div style={{ padding: '0 8px 12px' }}>
                    <WordList words={wordsMap[ind] || []} />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* ─── 导入文档 ─── */}
      <div className="card" style={{ gridColumn: '1/-1' }}>
        <div className="card-title">导入文档术语</div>
        <p style={{ fontSize: 13, color: '#888', marginBottom: 16, lineHeight: 1.5 }}>
          从专业文档中提取术语，粘贴到下方即可导入用户词库
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <input
              className="lexicon-input"
              placeholder="文档名称"
              value={docName}
              onChange={e => setDocName(e.target.value)}
              style={{ flex: 1 }}
            />
            <select
              className="lexicon-select"
              value={docType}
              onChange={e => setDocType(e.target.value)}
              style={{ width: 130 }}
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
              color: importMsg.includes('失败') ? '#c62828' : '#2e7d32',
              fontSize: 13,
            }}>
              {importMsg}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ─── 按类型分组的词条展示 ─── */
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
