"""
缓存管理器 — AI 架构第 5 项

支持:
  - 内存缓存 (MemoryCache) — 高频低延迟
  - 磁盘缓存 (DiskCache) — 大模型输出持久化
  - 分层策略 (TTL + LRU)
"""

import time
import json
import os
import hashlib
from pathlib import Path
from typing import Optional, Any

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache"


class MemoryCache:
    """
    内存缓存 — 高频轻量数据

    适用: 情绪识别结果、标点恢复、用户偏好查询
    特征: TTL 自动过期、LRU 淘汰
    """

    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        self._cache: dict[str, tuple[float, Any]] = {}
        self.ttl = ttl_seconds
        self.max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        expire_at, value = self._cache[key]
        if time.time() > expire_at:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        if len(self._cache) >= self.max_size:
            self._evict()
        self._cache[key] = (time.time() + (ttl or self.ttl), value)

    def _evict(self):
        """淘汰最早过期的 20%"""
        items = sorted(self._cache.items(), key=lambda x: x[1][0])
        for k, _ in items[:len(items) // 5]:
            del self._cache[k]

    def clear(self):
        self._cache.clear()

    def invalidate(self, pattern: str):
        """按前缀失效"""
        for k in list(self._cache.keys()):
            if k.startswith(pattern):
                del self._cache[k]


class DiskCache:
    """
    磁盘缓存 — 大模型输出持久化

    适用: 办公润色结果、创作整理、Prompt 输出
    存储: .cache/ 目录
    """

    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir or CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Optional[str]:
        path = self._path(key)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def set(self, key: str, value: str):
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(value)

    def _path(self, key: str) -> Path:
        hashed = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / hashed[:2] / hashed[2:4] / hashed

    def clear(self):
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True)


class CacheManager:
    """
    缓存管理器 — 统一入口

    自动选择合适的缓存层:
      - 情绪/标点 → MemoryCache (短 TTL)
      - LLM 输出 → DiskCache (长 TTL)
    """

    def __init__(self):
        self.memory = MemoryCache(ttl_seconds=300)    # 5 分钟
        self.memory_long = MemoryCache(ttl_seconds=3600)  # 1 小时
        self.disk = DiskCache()

    def get_optimization(self, text_hash: str, scene: str) -> Optional[dict]:
        """获取缓存的优化结果"""
        key = f"optimize:{scene}:{text_hash}"
        cached = self.memory_long.get(key)
        if cached:
            return cached
        cached = self.disk.get(key)
        if cached:
            import json
            return json.loads(cached)
        return None

    def set_optimization(self, text_hash: str, scene: str, result: dict):
        """缓存优化结果"""
        key = f"optimize:{scene}:{text_hash}"
        self.memory_long.set(key, result, ttl=3600)
        self.disk.set(key, json.dumps(result, ensure_ascii=False))

    def get_emotion(self, text_hash: str) -> Optional[dict]:
        """获取缓存的情绪结果"""
        return self.memory.get(f"emotion:{text_hash}")

    def set_emotion(self, text_hash: str, result: dict):
        self.memory.set(f"emotion:{text_hash}", result, ttl=300)
