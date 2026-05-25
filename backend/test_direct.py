"""直接测试行业词库系统（不依赖 uvicorn）"""
import sys
from pathlib import Path

# 和 main.py 同样的路径设置
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))

from database import industry_lexicon_db
from database.seed_industry_words import INDUSTRY_WORDS

print("=" * 50)
print("行业词库系统直接测试")
print("=" * 50)

# 1. 初始化
industry_lexicon_db.init_db()
print("\n1. 数据库初始化完成")

# 2. 确保有种子数据
count = industry_lexicon_db.ensure_seeded()
print(f"\n2. 行业词条数: {count}")

# 3. 获取行业列表
industries = industry_lexicon_db.get_all_industries()
print(f"\n3. 行业列表 ({len(industries)}):")
for ind in industries:
    words = industry_lexicon_db.get_industry_words(ind)
    print(f"   [行业] {ind}: {len(words)} 条")

# 4. 测试完整系统
from ai_services.lexicon.industry_lexicon_system import get_industry_lexicon_system
system = get_industry_lexicon_system()
system.select_industries("default", ["互联网/AI", "游戏/二次元"])
hotwords = system.get_hotwords("default")
print(f"\n4. 热词 ({len(hotwords)}):")
print(f"   {hotwords[:10]}...")

# 5. 测试纠错
correction = system.correct_text("今天我们讨论langchain和rag架构", "default")
print(f"\n5. 纠错测试:")
print(f"   原文: {correction['original']}")
print(f"   纠错: {correction['corrected']}")
print(f"   修正数: {correction['correction_count']}")

# 6. 测试 RAG
candidates = system.retrieve_candidates("langchain rag transformer", "default")
print(f"\n6. RAG 检索 ({len(candidates)}):")
for c in candidates:
    print(f"   {c['word']} (score={c['score']}, {c['industry']})")

print("\n=== 测试完成 ===")
