export type SceneType = '办公' | '聊天' | '创作';

export interface LexiconWord {
  id: number;
  user_id: string;
  word: string;
  word_type: string;
  industry_tag: string;
  source: string;
  confidence: number;
  usage_count: number;
  last_used_at: string;
  created_at: string;
}

export interface HistoryItem {
  id: number;
  user_id: string;
  content_raw: string;
  content_optimized: string;
  scene_type: string;
  title: string;
  tags: string;
  created_at: string;
}

export interface HistoryPage {
  items: HistoryItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CorrectionLog {
  id: number;
  user_id: string;
  original_word: string;
  corrected_word: string;
  scene_type: string;
  original_text: string;
  corrected_text: string;
  accepted_by_user: number;
  timestamp: string;
}

export interface EmojiItem {
  id: number;
  emoji: string;
  emotion_tags: string;
  scene_tags: string;
  usage_priority: number;
}

export interface OfficeResult {
  style: string;
  description: string;
  text: string;
}

export interface ChatResult {
  origin: string;
  emotion: string;
  emoji_suggestions: { label: string; emojis: string }[];
  all_emojis: { emoji: string; desc: string }[];
}

export interface CreationResult {
  origin: string;
  organized: { style: string; description: string; text: string };
  outline: { style: string; description: string; text: string };
  expanded: { style: string; description: string; text: string };
}

export interface UncertainWord {
  word: string;
  suggestions: string[];
  position: number;
}
