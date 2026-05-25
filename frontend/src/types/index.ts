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

export interface OfficeResult {
  style: string;
  description: string;
  text: string;
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

// ─── 行业词库 ───

export interface IndustryWord {
  id: number;
  word: string;
  aliases: string[];
  industry: string;
  sub_industry: string;
  category: string;        // 基础层 / 专业层 / 办公层 / 黑话层
  weight: number;
  type: string;
  language: string;
  frequency: number;
  description: string;
}

export interface CategoryCounts {
  [category: string]: number;
}

export interface IndustrySelectRequest {
  user_id: string;
  industries: string[];
}

export interface CorrectionResult {
  original: string;
  corrected: string;
  correction_count: number;
  details: { wrong: string; correct: string; pos: number }[];
}

export interface RAGCandidate {
  word: string;
  score: number;
  industry: string;
  type: string;
  match_type: string;
}

export interface HotwordEntry {
  text: string;
  weight: number;
  source: string;
}

// ─── 编辑分析 ───

export interface EditChange {
  type: 'replace' | 'insert' | 'delete';
  original_word: string;
  edited_word: string;
  position: number;
  classification: string;  // asr_fix | style_change | content_add | content_delete | punctuation
}

export interface EditAnalysis {
  has_changes: boolean;
  changes: EditChange[];
  classifications: Record<string, number>;
  learn_actions: { learned: boolean; action: string; word?: string; original?: string; edited?: string }[];
  edit_type: string;
}

// ─── 创作工作区 ───

export type CreationMode = 'novel' | 'project';

export interface CreationExtraction {
  [key: string]: any;
}

export interface CreationRound {
  round_number: number;
  raw_input: string;
  organized_output: string;
  extraction: CreationExtraction;
  tips: string[];
  innovations: string[];
  improvements: string[];
  user_copied_organized: boolean;
  user_copied_raw: boolean;
  created_at: string;
}

export interface CreationSession {
  session_id: string;
  mode: CreationMode;
  status: 'active' | 'finished';
  rounds: CreationRound[];
  accumulated_context: string;
  created_at: string;
  finished_at: string | null;
}

export interface SubmitInputResponse {
  round_number: number;
  raw_input: string;
  organized_output: string;
  extraction: CreationExtraction;
  tips: string[];
  innovations: string[];
  improvements: string[];
  user_copied_organized: boolean;
  user_copied_raw: boolean;
  created_at: string;
}
