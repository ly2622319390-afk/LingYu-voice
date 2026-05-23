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
