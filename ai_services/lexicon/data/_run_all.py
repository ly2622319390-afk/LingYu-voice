"""
词库生成总控脚本 — 运行所有行业生成器
将各 generator 模块的 term 数据送入 _commercial_generator.py
生成/更新 9 大行业 JSON 文件
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _commercial_generator import generate_industry

# ── 需要手动注册的模块（使用 run() 而非 populate） ──
# _gen_ai_fin_med.py 的 run() 覆盖 AI+金融+医疗，但我们只用其 AI 部分
# 金融和医疗由独立专用模块提供更全面覆盖
import _gen_ai_fin_med
AI_TERMS = _gen_ai_fin_med.AI_TERMS

# ── 适配器：将 agent 的 populate(lexicon) 模式接入 generate_industry ──
class Collector:
    """兼容 agent 生成器的 lexicon 收集器

    支持三种 add 调用格式:
      add(word, aliases, sub_industry, weight, type, lang, freq, desc)                    # 8 参
      add(word, aliases, sub_industry, weight, type, lang, freq, desc, category)           # 9 参
      add(word, aliases, sub_industry, weight, type, lang, freq, desc, embedding, category) # 10 参
    """
    def __init__(self, industry, filename, default_category="专业层"):
        self.industry = industry
        self.filename = filename
        self.default_category = default_category
        self.terms = []

    def add(self, *args):
        word = args[0]
        aliases = args[1] if len(args) > 1 else []
        sub = args[2] if len(args) > 2 else ""
        wt = args[3] if len(args) > 3 else 0.5
        typ = args[4] if len(args) > 4 else "concept"
        lang = args[5] if len(args) > 5 else "zh"
        freq = args[6] if len(args) > 6 else 0.5
        desc = args[7] if len(args) > 7 else ""
        # Determine category based on arg count
        if len(args) >= 10:
            # 10-param format: (..., embedding, category)
            cat = args[9] if args[9] else self.default_category
        elif len(args) >= 9:
            # 9-param format: (..., category)
            cat = args[8] if args[8] else self.default_category
        else:
            cat = self.default_category
        self.terms.append((word, aliases, sub, wt, typ, lang, freq, desc, cat))

    def __len__(self):
        return len(self.terms)

    def run(self, force=False):
        return generate_industry(self.industry, self.filename, self.terms, force)


# ── 各行业映射 ──
POPULATE_MODULES = [
    # (module_name, industry_name, filename, default_category)
    ("_gen_finance",   "金融",       "02_金融.json",        "专业层"),
    ("_gen_medical",   "医疗",       "03_医疗.json",        "专业层"),
    ("_gen_law",       "法律",       "04_法律.json",        "基础层"),
    ("_gen_education", "教育",       "05_教育.json",        "基础层"),
    ("_gen_ecommerce", "电商/运营",  "07_电商_运营.json",    "专业层"),
    ("_gen_media",     "视频/自媒体","08_视频_自媒体.json",  "专业层"),
    ("_gen_internet_ai","互联网/AI", "01_互联网_AI.json",    "专业层"),
    ("_gen_game",      "游戏/二次元","06_游戏_二次元.json",  "专业层"),
    ("_gen_academic",  "学术/科研",  "09_学术_科研.json",    "基础层"),
]


def run_module(mod_name, industry, filename, default_cat, force=False):
    try:
        mod = __import__(mod_name)
    except ImportError as e:
        print(f"[{industry}] 跳过: 找不到模块 {mod_name} ({e})")
        return 0
    if hasattr(mod, "populate"):
        collector = Collector(industry, filename, default_cat)
        mod.populate(collector)
        return collector.run(force=force)
    print(f"[{industry}] 跳过: 无 populate()")
    return 0


def run_all(force=False):
    totals = {}
    grand_total = 0

    # 1) 互联网/AI — 使用 _gen_ai_fin_med 的 AI_TERMS（有完整 4 层分类）
    cnt = generate_industry("互联网/AI", "01_互联网_AI.json", AI_TERMS, force)
    totals["互联网/AI"] = cnt
    grand_total += cnt

    # 2) populate 模式模块
    for mod_name, industry, filename, default_cat in POPULATE_MODULES:
        cnt = run_module(mod_name, industry, filename, default_cat, force)
        if cnt:
            totals[industry] = cnt
            grand_total += cnt

    print("=" * 50)
    print(f"全部完成! 总计: {grand_total} 条")
    for ind, cnt in totals.items():
        print(f"  {ind}: {cnt}")
    return totals


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="运行所有行业词库生成器")
    parser.add_argument("--force", action="store_true", help="强制覆盖已有词条")
    args = parser.parse_args()
    run_all(force=args.force)
