"""临时测试：验证行业词库系统"""
import sys
from pathlib import Path

# 和 main.py 同样的路径设置
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# 测试行业列表
r = client.get("/api/industry-lexicon/industries")
print(f"行业列表: {r.json()}")
print(f"状态码: {r.status_code}")

# 测试搜索
r = client.get("/api/industry-lexicon/search?keyword=LangChain")
print(f"\n搜索 'LangChain': {len(r.json().get('results', []))} 条结果")

# 测试选择行业
r = client.post("/api/industry-lexicon/select", json={
    "user_id": "default",
    "industries": ["互联网/AI", "游戏/二次元"]
})
print(f"\n选择行业: {r.json()}")

# 测试热词
r = client.get("/api/industry-lexicon/hotwords?user_id=default")
print(f"\n热词: {r.json()}")
