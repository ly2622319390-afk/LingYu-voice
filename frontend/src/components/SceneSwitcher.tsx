import { SceneType } from '../types'

const scenes: { type: SceneType; icon: string; label: string; desc: string }[] = [
  { type: '办公', icon: '💼', label: '办公模式', desc: '正式·专业·结构化' },
  { type: '聊天', icon: '💬', label: '聊天模式', desc: '自然·轻松·情绪化' },
  { type: '创作', icon: '✍️', label: '创作模式', desc: '灵感·整理·提纲化' },
]

interface SceneSwitcherProps {
  scene: SceneType
  onChange: (scene: SceneType) => void
}

export default function SceneSwitcher({ scene, onChange }: SceneSwitcherProps) {
  return (
    <div className="card">
      <div className="card-title">🔄 场景切换</div>
      <div className="scene-switcher">
        {scenes.map(s => (
          <button
            key={s.type}
            className={`scene-btn ${scene === s.type ? 'active' : ''}`}
            onClick={() => onChange(s.type)}
          >
            <span className="scene-icon">{s.icon}</span>
            <span>{s.label}</span>
            <span className="scene-label">{s.desc}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
