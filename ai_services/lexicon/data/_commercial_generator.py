"""
商业级行业词库生成系统 v2.0
为每个行业生成 1000-2000 条高质量专业词条
使用紧凑格式定义，高效扩展
"""
import json, os, re

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

CAT_BASIC = "基础层"
CAT_PROFESSIONAL = "专业层"
CAT_OFFICE = "办公层"
CAT_SLANG = "黑话层"

def normalize_key(w):
    return w.lower().replace(" ", "").replace(".", "").replace("-", "").replace("_", "").replace("+", "pp")

def make_entry(word, aliases, sub_industry, industry, weight, typ, lang, freq, desc, category):
    return {
        "word": word, "aliases": aliases, "industry": industry,
        "sub_industry": sub_industry, "category": category,
        "weight": weight, "type": typ, "language": lang,
        "frequency": freq, "description": desc,
    }

def load_existing(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return {normalize_key(e["word"]): e for e in json.load(f)}
    return {}

def generate_industry(industry, filename, terms, force=False):
    """terms: list of (word, aliases_list, sub_industry, weight, type, lang, freq, desc, category)"""
    filepath = os.path.join(DATA_DIR, filename)
    existing = {} if force else load_existing(filepath)
    existing_count = len(existing)
    new_dict = dict(existing)
    added = 0
    dupes = 0

    for t in terms:
        word, aliases, sub, wt, typ, lang, freq, desc, cat = t
        key = normalize_key(word)
        if key in new_dict and not force:
            dupes += 1
            continue
        new_dict[key] = make_entry(word, aliases, sub, industry, wt, typ, lang, freq, desc, cat)
        added += 1

    result = sorted(new_dict.values(), key=lambda x: (x["sub_industry"], x["word"]))
    print(f"  {industry}: 已有={existing_count} 新增={added} 重复={dupes} 总计={len(result)}")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return len(result)
