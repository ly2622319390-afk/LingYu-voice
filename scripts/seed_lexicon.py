"""手动导入行业词库种子数据"""
import sys
from pathlib import Path

# 添加 backend 目录到 path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from database import industry_lexicon_db
from database.seed_industry_words import INDUSTRY_WORDS, get_word_count, get_industry_list

# 初始化
industry_lexicon_db.init_db()
existing = industry_lexicon_db.get_all_industries()
print(f"数据库中已有行业: {existing}")

if not existing:
    count = industry_lexicon_db.add_industry_words(INDUSTRY_WORDS)
    print(f"\n✅ 已导入 {count} 条行业词条")
    print(f"\n行业分布:")
    for ind, cnt in get_word_count().items():
        print(f"  📂 {ind}: {cnt} 条")
    print(f"\n共 {len(get_industry_list())} 个行业分类")
else:
    print(f"已有数据，跳过导入。各行业词条数:")
    for ind in existing:
        words = industry_lexicon_db.get_industry_words(ind)
        print(f"  {ind}: {len(words)} 条")
