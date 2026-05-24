import { useState } from 'react'
import { UncertainWord } from '../types'

interface TranscriptProps {
  transcript: string
  interimTranscript: string
  uncertainWords: UncertainWord[]
  onReplaceWord: (oldWord: string, newWord: string) => void
}

export default function Transcript({ transcript, interimTranscript, uncertainWords, onReplaceWord }: TranscriptProps) {
  const [popupWord, setPopupWord] = useState<string | null>(null)

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

  // Build a display with highlighted uncertain words
  const renderText = () => {
    let result: JSX.Element[] = []
    let remaining = transcript

    const sortedWords = [...uncertainWords].sort((a, b) => a.position - b.position)

    sortedWords.forEach((uw, idx) => {
      const pos = remaining.indexOf(uw.word)
      if (pos === -1) {
        // word already replaced
        return
      }
      // Text before this word
      if (pos > 0) {
        result.push(<span key={`t${idx}`}>{remaining.slice(0, pos)}</span>)
      }
      // The uncertain word
      const isOpen = popupWord === uw.word
      result.push(
        <span key={`uw${idx}`} className="uncertain-word" onClick={() => setPopupWord(isOpen ? null : uw.word)}>
          {uw.word}
          {isOpen && (
            <span className="uncertain-popup" onClick={e => e.stopPropagation()}>
              {uw.suggestions.map((s, si) => (
                <div
                  key={si}
                  className="suggestion-item"
                  onClick={() => {
                    onReplaceWord(uw.word, s)
                    setPopupWord(null)
                  }}
                >
                  {s}
                </div>
              ))}
            </span>
          )}
        </span>
      )
      remaining = remaining.slice(pos + uw.word.length)
    })

    if (remaining) {
      result.push(<span key="last">{remaining}</span>)
    }

    return result
  }

  return (
    <div className="card">
      <div className="card-title">
        📝 实时转写
        {uncertainWords.length > 0 && (
          <span style={{ fontSize: 11, color: '#e74c3c', fontWeight: 400 }}>
            （{uncertainWords.length} 个不确定词，点击可替换）
          </span>
        )}
      </div>
      <div className="transcript-box">
        <div className="transcript-text">{renderText()}</div>
        {interimTranscript && (
          <div className="interim-text">{interimTranscript}</div>
        )}
      </div>
    </div>
  )
}
