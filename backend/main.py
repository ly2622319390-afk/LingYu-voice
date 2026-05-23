"""
智能语音输入法 — 后端主入口 (v2.0 AI 架构版)

架构:
  前端 → API 路由 → services / ai-services → 数据库层 → SQLite
                      ↕
              PromptManager → LLM (按需)
                      ↕
                CacheManager
"""

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径，使 ai_services 可导入
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import hashlib
import json
import logging

logger = logging.getLogger("voice-input")

from config import settings
from database.db_manager import db_manager
from database import lexicon_db, corrections_db, history_db, emoji_db, documents_db
from services.optimization_service import office_polish, chat_recommend, creation_process

# ─── AI 服务层 ───
from ai_services.nlp.punctuation import PunctuationRestorer, PunctuationService
from ai_services.nlp.correction import TermCorrector
from ai_services.nlp.rewrite_engine import RewriteEngine
from ai_services.emotion.emotion_detector import EmotionDetector
from ai_services.emotion.emoji_recommender import EmojiRecommender
from ai_services.lexicon.lexicon_rag import LexiconRAG
from ai_services.lexicon.user_profile import UserProfile
from ai_services.asr.hotwords import HotwordManager
from ai_services.cache.cache_manager import CacheManager
from ai_services.prompts.prompt_manager import PromptManager

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 全局 AI 服务实例 ───
punctuation_service = PunctuationService()
punctuation_restorer = PunctuationRestorer()
term_corrector = TermCorrector()
rewrite_engine = RewriteEngine()
emotion_detector = EmotionDetector()
emoji_recommender = EmojiRecommender()
lexicon_rag = LexiconRAG()
hotword_manager = HotwordManager(max_hotwords=settings.MAX_HOTWORDS)
cache_manager = CacheManager()
prompt_manager = PromptManager()
user_profiles: dict[str, UserProfile] = {}

# ASR 模型（全局共享，避免重复加载）
_asr_model = None
_asr_model_loaded = False


def get_user_profile(user_id: str = "default") -> UserProfile:
    if user_id not in user_profiles:
        user_profiles[user_id] = UserProfile(user_id)
    return user_profiles[user_id]


# ─── 生命周期 ───
@app.on_event("startup")
def startup():
    # 初始化数据库
    lexicon_db.init_db()
    corrections_db.init_db()
    history_db.init_db()
    emoji_db.init_db()
    documents_db.init_db()

    # 注册 Prompt 模板
    if not settings.MVP_MODE:
        prompt_manager.register_default_templates()

    # 同步热词
    _sync_hotwords()

    # 预加载 ASR 引擎（非阻塞，后台线程）
    if settings.ASR_ENGINE == "funasr" and not _asr_engine_loaded:
        import threading
        threading.Thread(target=_init_asr_engine, daemon=True).start()


def _init_asr_engine():
    """后台预加载 ASR 引擎（避免阻塞启动）"""
    global _asr_engine_instance, _asr_engine_loaded
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        from ai_services.asr.funasr_adapter import FunASRAdapter
        engine = FunASRAdapter(device=settings.ASR_DEVICE)
        loop.run_until_complete(engine.initialize())
        hotwords_list = hotword_manager.get_top_hotwords()
        if hotwords_list:
            loop.run_until_complete(engine.set_hotwords(hotwords_list))
        _asr_engine_instance = engine
        _asr_engine_loaded = True
        logger.info(f"ASR 引擎预加载完成: {settings.ASR_ENGINE}")
    except Exception as e:
        logger.warning(f"ASR 引擎预加载失败，将使用时加载: {e}")


@app.on_event("shutdown")
def shutdown():
    db_manager.close_all()


def _sync_hotwords():
    """从用户词库同步热词到 HotwordManager"""
    words = lexicon_db.get_all_words()
    hotword_manager.sync_from_lexicon(words)
    # 如果有行业词库配置，也同步
    for industry in ["互联网", "金融", "法律", "医疗"]:
        industry_words = lexicon_db.get_industry_words(industry)
        hotword_manager.sync_from_industry(industry_words)


# ─── 数据模型 ───
class WordAdd(BaseModel):
    word: str
    word_type: str = "自定义"
    industry_tag: str = ""
    source: str = "手动添加"


class CorrectionLog(BaseModel):
    original_word: str
    corrected_word: str
    scene_type: str = ""
    original_text: str = ""
    corrected_text: str = ""


class HistorySave(BaseModel):
    content_raw: str
    content_optimized: str = ""
    scene_type: str = ""
    title: str = ""
    tags: str = ""


class OptimizeRequest(BaseModel):
    text: str
    scene_type: str = "办公"


class AIPipelineRequest(BaseModel):
    """AI 全链路处理请求"""
    text: str
    scene_type: str = "办公"
    user_id: str = "default"
    use_llm: bool = False


# ═══════════════════════════════════════════════
#  1. ASR / 语音识别
# ═══════════════════════════════════════════════

@app.post("/api/transcribe")
def transcribe():
    return {
        "status": "ok",
        "message": "前端使用 Web Speech API 进行语音识别",
        "engine": settings.ASR_ENGINE,
        "hotwords": hotword_manager.get_top_hotwords(10)
    }


@app.websocket("/ws/asr")
async def asr_websocket(websocket: WebSocket):
    """WebSocket 流式 ASR 识别链路

    接收: 二进制音频数据 (WebM/Opus 块)
    发送: {"type":"partial","text":"...","confidence":0.9}
          {"type":"final","text":"...","confidence":0.95}
          {"type":"error","message":"..."}

    支持 FunASR（若已安装）和模拟模式两种后端。
    """
    await websocket.accept()

    # 使用全局 ASR 引擎（如果尚未加载，则尝试加载）
    global _asr_engine_instance, _asr_engine_loaded
    asr_engine = None
    if settings.ASR_ENGINE == "funasr":
        if _asr_engine_loaded and _asr_engine_instance:
            asr_engine = _asr_engine_instance
        else:
            try:
                from ai_services.asr.funasr_adapter import FunASRAdapter
                asr_engine = FunASRAdapter(device=settings.ASR_DEVICE)
                await asr_engine.initialize()
                hotwords_list = hotword_manager.get_top_hotwords()
                if hotwords_list:
                    await asr_engine.set_hotwords(hotwords_list)
                _asr_engine_instance = asr_engine
                _asr_engine_loaded = True
            except Exception as e:
                logger.warning(f"FunASR 加载失败，使用模拟模式: {e}")
                asr_engine = None

    # 模拟模式：音频缓冲区
    simulated_chunks = 0
    simulated_texts = [
        "今天", "今天的天气", "今天的天气真不错", "今天的天气真不错我们",
        "今天的天气真不错我们一起去", "今天的天气真不错我们一起去公园",
        "今天的天气真不错我们一起去公园散步",
    ]

    try:
        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                break

            if message["type"] == "websocket.receive":
                msg_data = message.get("text") or message.get("bytes")

                # 文本消息 (JSON 控制命令)
                if isinstance(msg_data, str):
                    msg = json.loads(msg_data)
                    msg_type = msg.get("type", "")

                    if msg_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "asr_engine": "funasr" if asr_engine else "simulated",
                            "hotwords": len(hotword_manager._hotwords),
                        })
                    elif msg_type == "set_hotwords":
                        hw = msg.get("hotwords", [])
                        hotword_manager._hotwords = {w: 50 for w in hw}
                        if asr_engine:
                            await asr_engine.set_hotwords(hw)
                        await websocket.send_json({"type": "hotword_updated"})
                    elif msg_type == "stop":
                        if asr_engine:
                            # FunASR 模式：对累积音频做最终识别
                            result = await asr_engine.transcribe_buffer()
                            if result.get("text"):
                                await websocket.send_json({
                                    "type": "final",
                                    "text": result["text"],
                                    "confidence": result.get("confidence", 0.95),
                                })
                        else:
                            # 模拟模式
                            if simulated_chunks > 0:
                                final_text = simulated_texts[-1] if simulated_chunks >= len(simulated_texts) else simulated_texts[min(simulated_chunks, len(simulated_texts) - 1)]
                                await websocket.send_json({
                                    "type": "final", "text": final_text, "confidence": 0.85
                                })
                        await websocket.send_json({"type": "end"})
                        break

                # 二进制消息（音频数据）
                elif isinstance(msg_data, bytes):
                    if asr_engine:
                        # FunASR 模式
                        async for result in asr_engine.transcribe_stream(msg_data):
                            await websocket.send_json(result)
                    else:
                        # 模拟模式：每接收 5 块音频发送一次 partial 结果
                        simulated_chunks += 1
                        if simulated_chunks % 3 == 0:
                            idx = min(simulated_chunks // 3, len(simulated_texts) - 1)
                            await websocket.send_json({
                                "type": "partial",
                                "text": simulated_texts[idx],
                                "confidence": 0.85,
                            })

    except WebSocketDisconnect:
        pass
    finally:
        # 不关闭全局共享引擎
        if asr_engine and asr_engine is not _asr_engine_instance:
            await asr_engine.close()


# ═══════════════════════════════════════════════
#  2. 热词
# ═══════════════════════════════════════════════

@app.get("/api/hotwords")
def list_hotwords():
    return {"hotwords": hotword_manager.get_top_hotwords(), "total": len(hotword_manager._hotwords)}


@app.post("/api/hotwords/sync")
def sync_hotwords():
    _sync_hotwords()
    return {"status": "synced", "count": len(hotword_manager._hotwords)}


# ═══════════════════════════════════════════════
#  3. 词库管理 (用户词库 + 行业词库)
# ═══════════════════════════════════════════════

@app.get("/api/lexicon")
def list_lexicon(user_id: str = "default", keyword: str = ""):
    if keyword:
        return lexicon_db.search_word(user_id, keyword)
    return lexicon_db.get_all_words(user_id)


@app.post("/api/lexicon")
def add_lexicon(word: WordAdd, user_id: str = "default"):
    result = lexicon_db.add_word(user_id, word.word, word.word_type, word.industry_tag, word.source)
    # 同步到热词
    hotword_manager.add_hotword(word.word)
    return result


@app.delete("/api/lexicon/{word_id}")
def delete_lexicon(word_id: int):
    if not lexicon_db.delete_word(word_id):
        raise HTTPException(404, "词条不存在")
    return {"status": "deleted"}


@app.get("/api/lexicon/check")
def check_word(word: str = Query(...), user_id: str = "default"):
    result = lexicon_db.check_known_word(user_id, word)
    return {"word": word, "known": result is not None, "detail": result}


@app.get("/api/lexicon/rag")
def lexicon_rag_query(text: str = Query(...), user_id: str = "default", industry: str = ""):
    """RAG 词库检索 — AI 架构第 3 项"""
    user_words = lexicon_db.get_all_words(user_id)
    industry_words = lexicon_db.get_industry_words(industry) if industry else []
    candidates = lexicon_rag.retrieve(text, user_words, industry_words)
    return {"text": text, "candidates": candidates, "total": len(candidates)}


@app.get("/api/industry-lexicon/{industry}")
def get_industry_lexicon(industry: str):
    return lexicon_db.get_industry_words(industry)


# ═══════════════════════════════════════════════
#  4. 修正记录
# ═══════════════════════════════════════════════

@app.get("/api/corrections")
def list_corrections(user_id: str = "default", limit: int = 50):
    return corrections_db.get_history(user_id, limit)


@app.post("/api/corrections")
def log_correction(log: CorrectionLog, user_id: str = "default"):
    # 记录到数据库
    result = corrections_db.log_correction(
        user_id, log.original_word, log.corrected_word,
        log.scene_type, log.original_text, log.corrected_text
    )
    # 更新用户画像
    profile = get_user_profile(user_id)
    profile.record_correction(log.original_word, log.corrected_word)
    # 自动加入词库
    lexicon_db.add_word(user_id, log.corrected_word, source="用户修正")
    return result


@app.get("/api/corrections/frequent")
def frequent_corrections(user_id: str = "default", limit: int = 20):
    return corrections_db.get_frequent_corrections(user_id, limit)


# ═══════════════════════════════════════════════
#  5. 历史记录
# ═══════════════════════════════════════════════

@app.get("/api/history")
def list_history(user_id: str = "default", scene_type: str = "",
                 page: int = 1, page_size: int = 20):
    return history_db.get_history(user_id, scene_type, page, page_size)


@app.post("/api/history")
def save_history(item: HistorySave, user_id: str = "default"):
    return history_db.save_history(
        user_id, item.content_raw, item.content_optimized,
        item.scene_type, item.title, item.tags
    )


@app.get("/api/history/{item_id}")
def history_detail(item_id: int):
    item = history_db.get_history_detail(item_id)
    if not item:
        raise HTTPException(404, "记录不存在")
    return item


@app.delete("/api/history/{item_id}")
def delete_history(item_id: int):
    if not history_db.delete_history(item_id):
        raise HTTPException(404, "记录不存在")
    return {"status": "deleted"}


# ═══════════════════════════════════════════════
#  6. 场景化优化 (AI 链路)
# ═══════════════════════════════════════════════

@app.post("/api/optimize")
def optimize_text(req: OptimizeRequest):
    """
    场景化文本处理

    按 AI 架构:
      MVP 模式 → 规则处理 (services/optimization_service.py)
      LLM 模式 → prompt_manager → LLM 重写 (ai-services/prompts + nlp)
    """
    profile = get_user_profile()
    profile.record_scene_usage(req.scene_type)

    # 缓存检查
    text_hash = hashlib.md5(req.text.encode()).hexdigest()
    if settings.CACHE_ENABLED:
        cached = cache_manager.get_optimization(text_hash, req.scene_type)
        if cached:
            return cached

    result = None
    if req.scene_type == "办公":
        if settings.MVP_MODE or not settings.LLM_ENABLED:
            result = office_polish(req.text)
        else:
            result = rewrite_engine._rule_office_rewrite(req.text)
    elif req.scene_type == "聊天":
        result = chat_recommend(req.text)
    elif req.scene_type == "创作":
        if settings.MVP_MODE or not settings.LLM_ENABLED:
            result = creation_process(req.text)
        else:
            result = rewrite_engine._rule_creation_process(req.text)
    else:
        raise HTTPException(400, f"未知场景: {req.scene_type}")

    # 写入缓存
    if settings.CACHE_ENABLED and result:
        cache_manager.set_optimization(text_hash, req.scene_type, result)

    return result


# ═══════════════════════════════════════════════
#  7. AI 全链路处理 (Pipeline)
# ═══════════════════════════════════════════════

@app.post("/api/ai-pipeline")
def ai_pipeline(req: AIPipelineRequest):
    """
    AI 全链路处理:
      原文 → 标点恢复 → 词库纠错 → 情绪识别 → 场景优化 → 输出

    这个接口演示完整的 AI 模块协同流程
    """
    text = req.text
    scene = req.scene_type
    profile = get_user_profile(req.user_id)
    pipeline_steps = []

    # Step 1: 标点恢复
    restored = punctuation_restorer.restore(text, scene)
    pipeline_steps.append({"step": "punctuation", "input": text, "output": restored})

    # Step 2: 词库纠错 + RAG
    user_words = lexicon_db.get_all_words(req.user_id)
    correction_result = term_corrector.correct(restored, user_words)
    corrected = correction_result["text"]
    pipeline_steps.append({"step": "correction", "output": corrected, "details": correction_result})

    # Step 3: 情绪识别
    emotion_result = emotion_detector.detect(corrected)
    pipeline_steps.append({"step": "emotion", "result": emotion_result})

    # Step 4: 场景优化
    if scene == "办公":
        optimized = office_polish(corrected)
    elif scene == "聊天":
        emoji_rec = emoji_recommender.recommend(corrected, scene, emotion_result)
        optimized = emoji_rec
    else:
        optimized = creation_process(corrected)

    pipeline_steps.append({"step": "optimize", "result": optimized})

    # 记录用户行为
    profile.record_session()
    profile.record_scene_usage(scene)

    return {
        "origin": text,
        "pipeline": pipeline_steps,
        "final": {
            "text": corrected,
            "emotion": emotion_result,
            "optimization": optimized
        }
    }


# ═══════════════════════════════════════════════
#  8. 情绪 & Emoji
# ═══════════════════════════════════════════════

@app.post("/api/emotion/detect")
def detect_emotion(text: str = Query(...)):
    """情绪识别 — AI 架构第 5 项"""
    # 缓存检查
    text_hash = hashlib.md5(text.encode()).hexdigest()
    if settings.CACHE_ENABLED:
        cached = cache_manager.get_emotion(text_hash)
        if cached:
            return cached

    result = emotion_detector.detect(text)
    if settings.CACHE_ENABLED:
        cache_manager.set_emotion(text_hash, result)
    return result


@app.get("/api/emoji")
def get_emoji(scene: str = "聊天", emotion: str = "", limit: int = 10):
    if emotion:
        return emoji_db.get_emoji_by_emotion(emotion, scene, min(limit, 10))
    return emoji_db.get_emoji_by_scene(scene, min(limit, 10))


@app.post("/api/emoji/recommend")
def recommend_emoji(text: str = Query(...), scene: str = "聊天"):
    """结合情绪识别的 emoji 推荐"""
    emotion_result = emotion_detector.detect(text)
    emoji_list = emoji_db.get_emoji_by_emotion(
        emotion_result["primary_emotion"], scene, 10
    )
    return {
        "text": text,
        "emotion": emotion_result,
        "emoji_suggestions": [
            {"label": "推荐", "emojis": " ".join(e["emoji"] for e in emoji_list[:4])}
        ],
        "all_emojis": [{"emoji": e["emoji"], "desc": e.get("emotion_tags", "")} for e in emoji_list[:6]]
    }


# ═══════════════════════════════════════════════
#  9. 文档导入
# ═══════════════════════════════════════════════

@app.get("/api/documents")
def list_documents(user_id: str = "default"):
    return documents_db.get_documents(user_id)


@app.post("/api/documents")
def import_document(file_name: str, file_type: str, extracted_terms: list[str],
                    user_id: str = "default"):
    result = documents_db.save_document(user_id, file_name, file_type, extracted_terms)
    # 将提取的术语自动加入词库
    for term in extracted_terms:
        lexicon_db.add_word(user_id, term, source="文档导入")
        hotword_manager.add_hotword(term)
    return result


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int):
    if not documents_db.delete_document(doc_id):
        raise HTTPException(404, "文档不存在")
    return {"status": "deleted"}


# ═══════════════════════════════════════════════
#  10. Prompt 管理
# ═══════════════════════════════════════════════

@app.get("/api/prompts")
def list_prompts(scene: str = ""):
    if scene:
        return [{"name": t.name, "scene": t.scene, "version": t.version}
                for t in prompt_manager.get_by_scene(scene)]
    return [{"name": t.name, "scene": t.scene, "version": t.version}
            for t in prompt_manager._templates.values()]


# ═══════════════════════════════════════════════
#  11. 缓存管理
# ═══════════════════════════════════════════════

@app.post("/api/cache/clear")
def clear_cache():
    cache_manager.memory.clear()
    cache_manager.memory_long.clear()
    cache_manager.disk.clear()
    return {"status": "cleared"}


@app.get("/api/cache/stats")
def cache_stats():
    return {
        "memory": len(cache_manager.memory._cache),
        "memory_long": len(cache_manager.memory_long._cache),
    }


# ═══════════════════════════════════════════════
#  12. AI 架构状态
# ═══════════════════════════════════════════════

@app.get("/api/ai/status")
def ai_status():
    """返回当前 AI 架构各模块状态"""
    return {
        "version": settings.VERSION,
        "mvp_mode": settings.MVP_MODE,
        "llm_enabled": settings.LLM_ENABLED,
        "modules": {
            "asr": {"engine": settings.ASR_ENGINE, "status": "ready"},
            "punctuation": {"mode": settings.PUNCTUATION_MODEL, "status": "ready"},
            "correction": {"status": "ready", "hotwords": len(hotword_manager._hotwords)},
            "emotion": {"status": "ready"},
            "emoji": {"status": "ready"},
            "rewrite": {"mode": "rule" if settings.MVP_MODE else "llm", "status": "ready"},
            "cache": {"enabled": settings.CACHE_ENABLED, "type": "memory+disk"},
            "prompts": {"templates": len(prompt_manager._templates)},
            "rag": {"status": "ready"},
            "user_profile": {"status": "ready"},
        }
    }


# ═══════════════════════════════════════════════
#  13. WebSocket 调试
# ═══════════════════════════════════════════════

@app.websocket("/ws/debug")
async def debug_websocket(websocket: WebSocket):
    """调试 WebSocket — 实时推送系统状态"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "stats": {
                        "hotwords": len(hotword_manager._hotwords),
                        "cache_memory": len(cache_manager.memory._cache),
                        "users": len(user_profiles),
                    }
                })
    except WebSocketDisconnect:
        pass


# ═══════════════════════════════════════════════
#  14. 健康检查
# ═══════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": settings.VERSION,
        "mode": "MVP" if settings.MVP_MODE else "LLM",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
