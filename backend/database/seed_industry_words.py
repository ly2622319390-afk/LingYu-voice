"""9 大行业种子词库数据 — 从 JSON 文件加载

每个词条包含:
  - word: 正确词
  - aliases: 常见误识别映射
  - industry: 所属行业
  - sub_industry: 子行业
  - weight: 重要度 0~1
  - type: 类型 (framework/tool/concept/brand/protocol/...)
  - language: en/zh/mixed
  - frequency: 使用频率 0~1
  - description: 简短说明
"""

import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "ai_services" / "lexicon" / "data"

def _load_all() -> list[dict]:
    """从 data/ 目录加载所有 JSON 行业词库文件并合并"""
    words = []
    if not DATA_DIR.exists():
        print(f"[seed] 数据目录不存在: {DATA_DIR}")
        return words
    for fname in sorted(os.listdir(DATA_DIR)):
        if fname.endswith(".json"):
            fpath = DATA_DIR / fname
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    words.extend(data)
                    print(f"[seed] 已加载 {fname}: {len(data)} 条")
                else:
                    print(f"[seed] 跳过 {fname}: 不是数组格式")
            except Exception as e:
                print(f"[seed] 加载 {fname} 失败: {e}")
    return words

INDUSTRY_WORDS: list[dict] = _load_all()


def get_all() -> list[dict]:
    return INDUSTRY_WORDS


def get_industry_list() -> list[str]:
    """获取所有行业分类列表"""
    seen = set()
    result = []
    for w in INDUSTRY_WORDS:
        ind = w["industry"]
        if ind not in seen:
            seen.add(ind)
            result.append(ind)
    return result


def get_word_count() -> dict[str, int]:
    """按行业统计词条数量"""
    counts = {}
    for w in INDUSTRY_WORDS:
        ind = w["industry"]
        counts[ind] = counts.get(ind, 0) + 1
    return counts
