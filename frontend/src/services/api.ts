const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

// 词库
export const lexiconApi = {
  list: (keyword = '') => request<any[]>(`/lexicon?keyword=${keyword}`),
  add: (word: string, wordType = '自定义', industry = '', source = '手动添加') =>
    request('/lexicon', {
      method: 'POST',
      body: JSON.stringify({ word, word_type: wordType, industry_tag: industry, source }),
    }),
  delete: (id: number) => request(`/lexicon/${id}`, { method: 'DELETE' }),
  check: (word: string) => request(`/lexicon/check?word=${encodeURIComponent(word)}`),
};

// 修正记录
export const correctionsApi = {
  list: (limit = 50) => request<any[]>(`/corrections?limit=${limit}`),
  log: (originalWord: string, correctedWord: string, sceneType = '', originalText = '', correctedText = '') =>
    request('/corrections', {
      method: 'POST',
      body: JSON.stringify({
        original_word: originalWord, corrected_word: correctedWord,
        scene_type: sceneType, original_text: originalText, corrected_text: correctedText,
      }),
    }),
  frequent: () => request<any[]>('/corrections/frequent'),
};

// 历史记录
export const historyApi = {
  list: (page = 1, sceneType = '') =>
    request<any>(`/history?page=${page}&page_size=20&scene_type=${sceneType}`),
  save: (contentRaw: string, contentOptimized = '', sceneType = '', title = '', tags = '') =>
    request('/history', {
      method: 'POST',
      body: JSON.stringify({
        content_raw: contentRaw, content_optimized: contentOptimized,
        scene_type: sceneType, title, tags,
      }),
    }),
  detail: (id: number) => request<any>(`/history/${id}`),
  delete: (id: number) => request(`/history/${id}`, { method: 'DELETE' }),
};

// 场景优化
export const optimizeApi = {
  process: (text: string, sceneType: string) =>
    request<any>('/optimize', {
      method: 'POST',
      body: JSON.stringify({ text, scene_type: sceneType }),
    }),
};

// 表情
export const emojiApi = {
  list: (scene = '聊天', emotion = '', limit = 10) =>
    request<any[]>(`/emoji?scene=${scene}&emotion=${emotion}&limit=${limit}`),
};

// 行业专业词库
export const industryApi = {
  /** 获取所有行业分类 */
  industries: () => request<{ industries: string[]; _debug: any }>('/industry-lexicon/industries'),

  /** 获取指定行业的所有词条 */
  wordsByIndustry: (industry: string) =>
    request<{ industry: string; words: any[] }>(`/industry-lexicon/industries/${encodeURIComponent(industry)}`),

  /** 获取行业各层级的词条数量 */
  categories: (industry: string) =>
    request<{ industry: string; categories: Record<string, number> }>(`/industry-lexicon/categories/${encodeURIComponent(industry)}`),

  /** 按层级获取词条列表 */
  wordsByCategory: (industry: string, category: string) =>
    request<{ industry: string; category: string; words: any[] }>(`/industry-lexicon/${encodeURIComponent(industry)}/${encodeURIComponent(category)}`),

  /** 搜索行业词条 */
  search: (keyword: string, industry = '') =>
    request<{ results: any[] }>(`/industry-lexicon/search?keyword=${encodeURIComponent(keyword)}&industry=${industry}`),

  /** 用户选择行业 */
  select: (user_id: string, industries: string[]) =>
    request<{ status: string; industries: string[]; hotwords_loaded: number }>('/industry-lexicon/select', {
      method: 'POST',
      body: JSON.stringify({ user_id, industries }),
    }),

  /** 获取用户已选的行业 */
  selected: (user_id = 'default') =>
    request<{ industries: string[] }>(`/industry-lexicon/selected?user_id=${user_id}`),

  /** 批量导入行业词条 */
  import: (words: any[]) =>
    request<any>('/industry-lexicon/import', {
      method: 'POST',
      body: JSON.stringify({ words }),
    }),

  /** ASR 文本纠错 */
  correct: (text: string, user_id = 'default') =>
    request<any>(`/industry-lexicon/correct?text=${encodeURIComponent(text)}&user_id=${user_id}`, {
      method: 'POST',
    }),

  /** 用户修正学习 */
  learn: (original_word: string, corrected_word: string, user_id = 'default') =>
    request<any>(`/industry-lexicon/learn?original_word=${encodeURIComponent(original_word)}&corrected_word=${encodeURIComponent(corrected_word)}&user_id=${user_id}`, {
      method: 'POST',
    }),

  /** 获取当前行业热词 */
  hotwords: (user_id = 'default') =>
    request<{ hotwords: any[]; count: number }>(`/industry-lexicon/hotwords?user_id=${user_id}`),

  /** RAG 检索 */
  rag: (text: string, user_id = 'default', top_k = 5) =>
    request<any>(`/industry-lexicon/rag?text=${encodeURIComponent(text)}&user_id=${user_id}&top_k=${top_k}`),
};

// 文档
export const documentsApi = {
  list: () => request<any[]>('/documents'),
  import: (fileName: string, fileType: string, extractedTerms: string[]) =>
    request('/documents', {
      method: 'POST',
      body: JSON.stringify({
        file_name: fileName, file_type: fileType, extracted_terms: extractedTerms,
      }),
    }),
  delete: (id: number) => request(`/documents/${id}`, { method: 'DELETE' }),
};
