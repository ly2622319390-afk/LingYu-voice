import { useState, useRef, useEffect } from 'react'
interface TranscriptProps {
  transcript: string
  interimTranscript: string
  onEditComplete?: (edited: string) => void
}

export default function Transcript({ transcript, interimTranscript, onEditComplete }: TranscriptProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState(transcript)
  const [editHistory, setEditHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // 新录音时重置编辑状态
  useEffect(() => {
    setEditText(transcript)
    setEditHistory([])
    setHistoryIndex(-1)
    setIsEditing(false)
  }, [transcript])

  const saveToHistory = (text: string) => {
    const newHistory = editHistory.slice(0, historyIndex + 1)
    newHistory.push(text)
    setEditHistory(newHistory)
    setHistoryIndex(newHistory.length - 1)
  }

  const handleTextChange = (value: string) => {
    saveToHistory(value)
    setEditText(value)
  }

  const handleUndo = () => {
    if (historyIndex <= 0) return
    const newIndex = historyIndex - 1
    setHistoryIndex(newIndex)
    setEditText(editHistory[newIndex])
  }

  const handleRedo = () => {
    if (historyIndex >= editHistory.length - 1) return
    const newIndex = historyIndex + 1
    setHistoryIndex(newIndex)
    setEditText(editHistory[newIndex])
  }

  const handleDone = () => {
    setIsEditing(false)
    onEditComplete?.(editText)
  }

  const handleCancel = () => {
    setEditText(transcript)
    setEditHistory([])
    setHistoryIndex(-1)
    setIsEditing(false)
  }

  const enterEditMode = () => {
    if (!transcript && !interimTranscript) return
    setEditText(transcript)
    setIsEditing(true)
    // 选中全部文本方便替换
    setTimeout(() => textareaRef.current?.select(), 50)
  }

  // ─── 编辑模式 ───
  if (isEditing) {
    const canUndo = historyIndex > 0
    const canRedo = historyIndex < editHistory.length - 1
    const editCount = editHistory.length > 0 ? editHistory.length - 1 : 0

    return (
      <div className="card">
        <div className="card-title">
          📝 编辑转写文本
          <span style={{ fontSize: 11, color: '#999', fontWeight: 400, marginLeft: 8 }}>
            （已编辑 {editCount} 次）
          </span>
        </div>
        <div className="transcript-box">
          <textarea
            ref={textareaRef}
            className="transcript-edit-area"
            value={editText}
            onChange={e => handleTextChange(e.target.value)}
            rows={4}
          />
        </div>
        <div className="edit-toolbar">
          <button className="edit-btn" onClick={handleUndo} disabled={!canUndo} title="撤销">
            ↩ 撤销
          </button>
          <button className="edit-btn" onClick={handleRedo} disabled={!canRedo} title="重做">
            ↪ 重做
          </button>
          <span className="edit-spacer" />
          <button className="edit-btn cancel" onClick={handleCancel}>
            取消
          </button>
          <button className="edit-btn primary" onClick={handleDone}>
            完成编辑
          </button>
        </div>
      </div>
    )
  }

  // ─── 只读模式 ───
  if (!transcript && !interimTranscript) {
    return (
      <div className="card">
        <div className="card-title">📝 实时转写</div>
        <div className="transcript-box">
          <div className="empty-hint">录音后此处将显示转写结果...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-title">
        📝 实时转写
        <span
          className="edit-trigger"
          onClick={enterEditMode}
          title="点击编辑文本"
        >
          ✏️
        </span>
      </div>
      <div className="transcript-box" onClick={enterEditMode} style={{ cursor: 'pointer' }}>
        <div className="transcript-text">{transcript}</div>
        {interimTranscript && (
          <div className="interim-text">{interimTranscript}</div>
        )}
      </div>
      <div style={{ fontSize: 11, color: '#999', textAlign: 'right', marginTop: 4 }}>
        点击文本可编辑
      </div>
    </div>
  )
}
