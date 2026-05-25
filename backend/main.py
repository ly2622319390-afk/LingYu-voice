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

import asyncio
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import hashlib
import json
import logging
import threading

logger = logging.getLogger("voice-input")

# 文件日志配置（用户可复制日志内容报告错误）
_log_file = Path(PROJECT_ROOT) / "backend.log"
_fh = logging.FileHandler(str(_log_file), encoding="utf-8", mode="a")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logger.addHandler(_fh)
logger.setLevel(logging.INFO)

from config import settings
from database.db_manager import db_manager
from database import lexicon_db, corrections_db, history_db, documents_db, profiles_db, edit_log_db
from services.term_extraction_service import extract_terms
from services.edit_analyzer import analyze_edits
from services.profile_prompt_builder import build_full_context
from database import industry_lexicon_db
from database import creation_db
from database.seed_industry_words import INDUSTRY_WORDS
from services.optimization_service import office_polish, chat_recommend, creation_process
from services.creation_service import (create_session, get_session, finish_session,
                                       add_round, process_with_llm, rule_based_fallback,
                                       mark_copy_organized, mark_copy_raw,
                                       get_active_sessions)

# ─── AI 服务层 ───
from ai_services.nlp.punctuation import PunctuationRestorer, PunctuationService
from ai_services.nlp.correction import TermCorrector
from ai_services.nlp.rewrite_engine import RewriteEngine
from ai_services.lexicon.lexicon_rag import LexiconRAG
from ai_services.lexicon.user_profile import UserProfile
from ai_services.lexicon.industry_lexicon_system import IndustryLexiconSystem, get_industry_lexicon_system
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
lexicon_rag = LexiconRAG()
hotword_manager = HotwordManager(max_hotwords=settings.MAX_HOTWORDS)
cache_manager = CacheManager()
prompt_manager = PromptManager()
user_profiles: dict[str, UserProfile] = {}

# 行业词库系统
industry_lexicon = get_industry_lexicon_system()

# ASR 引擎实例（全局共享，避免重复加载）
_asr_engine_instance = None
_asr_engine_loaded = False
_asr_engine_lock = threading.Lock()


def get_user_profile(user_id: str = "default") -> UserProfile:
    if user_id not in user_profiles:
        user_profiles[user_id] = UserProfile(user_id)
    return user_profiles[user_id]


def _seed_industry_words():
    """启动时自动导入种子行业词库 + 增量更新别名 + 新增词条"""
    existing_industries = industry_lexicon_db.get_all_industries()
    if not existing_industries:
        count = industry_lexicon_db.add_industry_words(INDUSTRY_WORDS)
        logger.info(f"行业词库初始化完成: 已导入 {count} 条词条")
        industry_lexicon._clear_cache()
        return
    logger.info(f"行业词库已存在: {len(existing_industries)} 个行业")

    # 1. 增量导入新词条（种子数据中有但数据库里没有的）
    existing_words = industry_lexicon_db.get_all_word_names()
    new_entries = [w for w in INDUSTRY_WORDS if w["word"] not in existing_words]
    if new_entries:
        added = industry_lexicon_db.add_industry_words(new_entries)
        logger.info(f"增量新增 {added} 条词条 (共 {len(new_entries)} 个新词)")

    # 2. 增量更新关键术语的别名
    UPDATED_ALIASES: dict[str, list[str]] = {}
    for w in INDUSTRY_WORDS:
        if w.get("word") in UPDATED_ALIASES:
            continue
        aliases = w.get("aliases", [])
        if len(aliases) >= 5:
            UPDATED_ALIASES[w["word"]] = aliases
    if UPDATED_ALIASES:
        updated = industry_lexicon_db.patch_word_aliases(UPDATED_ALIASES)
        if updated:
            logger.info(f"别名更新完成: {updated} 个词条")

    # 3. 清空缓存，让新数据生效
    industry_lexicon._clear_cache()


def _init_llm():
    """初始化大模型客户端（根据 LLM_PROVIDER 配置选择）"""
    if not settings.LLM_ENABLED:
        logger.info("大模型未启用 (LLM_ENABLED=False)，使用规则处理")
        return

    provider = settings.LLM_PROVIDER

    if provider == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("LLM_PROVIDER=anthropic 但未配置 ANTHROPIC_API_KEY，降级到规则处理")
            settings.LLM_ENABLED = False
            return
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            prompt_manager.llm = client
            rewrite_engine.llm = client
            logger.info(f"Anthropic 客户端初始化成功 (model={settings.ANTHROPIC_MODEL})")
        except Exception as e:
            logger.warning(f"Anthropic 初始化失败，降级到规则处理: {e}")
            settings.LLM_ENABLED = False

    elif provider == "deepseek":
        if not settings.DEEPSEEK_API_KEY:
            logger.warning("LLM_PROVIDER=deepseek 但未配置 DEEPSEEK_API_KEY，降级到规则处理")
            settings.LLM_ENABLED = False
            return
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
            )
            prompt_manager.llm = client
            rewrite_engine.llm = client
            prompt_manager.model_name = settings.DEEPSEEK_MODEL
            logger.info(f"DeepSeek 客户端初始化成功 (model={settings.DEEPSEEK_MODEL}, base_url={settings.DEEPSEEK_BASE_URL})")
        except Exception as e:
            logger.warning(f"DeepSeek 初始化失败，降级到规则处理: {e}")
            settings.LLM_ENABLED = False

    elif provider == "openai":
        if not settings.OPENAI_API_KEY:
            logger.warning("LLM_PROVIDER=openai 但未配置 OPENAI_API_KEY，降级到规则处理")
            settings.LLM_ENABLED = False
            return
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            prompt_manager.llm = client
            rewrite_engine.llm = client
            prompt_manager.model_name = settings.OPENAI_MODEL
            logger.info(f"OpenAI 客户端初始化成功 (model={settings.OPENAI_MODEL})")
        except Exception as e:
            logger.warning(f"OpenAI 初始化失败，降级到规则处理: {e}")
            settings.LLM_ENABLED = False

    else:
        logger.warning(f"未知 LLM_PROVIDER: {provider}，降级到规则处理")
        settings.LLM_ENABLED = False


# ─── 生命周期 ───
@app.on_event("startup")
def startup():
    logger.info("=" * 60)
    logger.info(f"  智能语音输入法 v{settings.VERSION} 启动")
    logger.info(f"  ASR 引擎: {settings.ASR_ENGINE}")
    logger.info(f"  LLM 模式: {'已启用' if settings.LLM_ENABLED else '未启用'}")
    logger.info(f"  日志文件: {_log_file}")
    logger.info("=" * 60)

    # 初始化数据库
    lexicon_db.init_db()
    corrections_db.init_db()
    history_db.init_db()
    documents_db.init_db()
    industry_lexicon_db.init_db()
    profiles_db.init_db()
    edit_log_db.init_db()
    creation_db.init_db()
    _seed_industry_words()

    # 配置大模型
    _init_llm()

    # 注册 Prompt 模板（LLM 模式需要）
    if settings.LLM_ENABLED:
        prompt_manager.register_default_templates()

    # 同步热词
    _sync_hotwords()

    # 预加载 ASR 引擎（非阻塞，后台线程）
    if settings.ASR_ENGINE in ("funasr", "sensevoice") and not _asr_engine_loaded:
        threading.Thread(target=_init_asr_engine, daemon=True).start()


def _init_asr_engine():
    """后台预加载 ASR 引擎（避免阻塞启动）"""
    global _asr_engine_instance, _asr_engine_loaded
    with _asr_engine_lock:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            if settings.ASR_ENGINE == "sensevoice":
                from ai_services.asr.sensevoice_adapter import SenseVoiceAdapter
                engine = SenseVoiceAdapter(device=settings.ASR_DEVICE)
            else:
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
    """从用户词库 + 行业词库同步热词到 HotwordManager"""
    words = lexicon_db.get_all_words()
    hotword_manager.sync_from_lexicon(words)
    # 从行业词库系统获取热词（如果没有已选行业，自动选中互联网/AI）
    active_industries = industry_lexicon.get_selected_industries("default")
    if not active_industries:
        industry_lexicon.select_industries("default", ["互联网/AI"])
        logger.info("首次启动 — 已自动选中「互联网/AI」行业")
        active_industries = ["互联网/AI"]
    industry_hotwords = industry_lexicon.get_hotwords("default", force_refresh=True)
    hotword_manager.sync_from_industry_system(industry_hotwords)
    logger.info(f"行业热词已同步: {len(industry_hotwords)} 个 ({active_industries})")


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


class IndustrySelectRequest(BaseModel):
    user_id: str = "default"
    industries: list[str]


class IndustryWordImport(BaseModel):
    words: list[dict]


class AIPipelineRequest(BaseModel):
    """AI 全链路处理请求"""
    text: str
    scene_type: str = "办公"
    user_id: str = "default"
    use_llm: bool = False


class AnalyzeEditsRequest(BaseModel):
    """编辑分析请求"""
    original_text: str
    edited_text: str
    scene_type: str = ""
    user_id: str = "default"
    session_id: str = ""


class CreateSessionRequest(BaseModel):
    """创建创作会话请求"""
    mode: str


class SubmitInputRequest(BaseModel):
    """提交创作输入请求"""
    text: str


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
    """WebSocket 流式 ASR 识别链路"""
    await websocket.accept()
    ws_client = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
    logger.info(f"[WS] 新连接: {ws_client}")

    global _asr_engine_instance, _asr_engine_loaded
    asr_engine = None
    audio_chunks_received = 0

    if settings.ASR_ENGINE in ("funasr", "sensevoice"):
        if _asr_engine_loaded and _asr_engine_instance:
            asr_engine = _asr_engine_instance
            logger.info(f"[WS] ✓ 使用预加载的 SenseVoice 引擎")
        else:
            logger.info(f"[WS] ⏳ SenseVoice 模型尚未加载完成，异步等待...")
            for _ in range(30):
                if _asr_engine_loaded and _asr_engine_instance:
                    asr_engine = _asr_engine_instance
                    logger.info(f"[WS] ✓ 异步等待成功，引擎已就绪")
                    break
                await asyncio.sleep(1)
            if not asr_engine:
                if _asr_engine_lock.acquire(blocking=False):
                    try:
                        logger.info(f"[WS] 自行加载 SenseVoice 引擎...")
                        if settings.ASR_ENGINE == "sensevoice":
                            from ai_services.asr.sensevoice_adapter import SenseVoiceAdapter
                            asr_engine = SenseVoiceAdapter(device=settings.ASR_DEVICE)
                        else:
                            from ai_services.asr.funasr_adapter import FunASRAdapter
                            asr_engine = FunASRAdapter(device=settings.ASR_DEVICE)
                        await asr_engine.initialize()
                        _asr_engine_instance = asr_engine
                        _asr_engine_loaded = True
                        logger.info(f"[WS] ✓ 自行加载成功")
                    except Exception as e:
                        logger.error(f"[WS] ✗ 自行加载失败: {e}")
                        asr_engine = None
                    finally:
                        _asr_engine_lock.release()
                else:
                    logger.error(f"[WS] ✗ 引擎加载超时（>30秒），ModelScope 下载可能被阻断")
                if not asr_engine:
                    await websocket.send_json({
                        "type": "error",
                        "message": "ASR 引擎加载失败（模型下载超时），请检查网络后重启软件"
                    })

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
                logger.info(f"[WS] 客户端断开: {ws_client}")
                break

            if message["type"] == "websocket.receive":
                msg_data = message.get("text") or message.get("bytes")

                # 文本消息 (JSON 控制命令)
                if isinstance(msg_data, str):
                    msg = json.loads(msg_data)
                    msg_type = msg.get("type", "")
                    logger.info(f"[WS] 收到命令: {msg_type} (engine={'sensevoice' if asr_engine else 'simulated'}, chunks={audio_chunks_received})")

                    if msg_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "asr_engine": "sensevoice" if asr_engine else "simulated",
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
                            result = await asr_engine.transcribe_buffer()
                            text = result.get("text", "")
                            confidence = result.get("confidence", 0.0)
                            logger.info(f"[WS] transcribe_buffer 返回: text_len={len(text)}, confidence={confidence}, text='{text[:50]}...' " + ("" if len(text) <= 50 else ""))
                            if text:
                                # 第一步：立即发送 raw final（不等待 LLM 纠错）
                                await websocket.send_json({
                                    "type": "final",
                                    "text": text,
                                    "confidence": confidence,
                                    "corrections": [],
                                })
                                logger.info(f"[WS] ✓ 已发送 raw final ({len(text)} 字)")

                                # 第二步：LLM 纠错（可能耗时 20s+，不影响前端的转录显示）
                                if settings.LLM_ENABLED:
                                    try:
                                        corrected = industry_lexicon.correct_text_llm(text)
                                        if corrected["corrected"] != text:
                                            await websocket.send_json({
                                                "type": "final",
                                                "text": corrected["corrected"],
                                                "confidence": confidence,
                                                "corrections": corrected["corrections"],
                                            })
                                            logger.info(f"[WS] ✓ 已发送 llm corrected final ({len(corrected['corrected'])} 字) 替换 raw")
                                    except Exception as e:
                                        logger.warning(f"[WS] LLM 纠错失败，保留 raw 文本: {e}")
                            else:
                                logger.warning(f"[WS] ✗ transcribe_buffer 返回空文本！音频块数: {audio_chunks_received}")
                        else:
                            if simulated_chunks > 0:
                                final_text = simulated_texts[-1] if simulated_chunks >= len(simulated_texts) else simulated_texts[min(simulated_chunks, len(simulated_texts) - 1)]
                                corrected = industry_lexicon.correct_text(final_text)
                                await websocket.send_json({
                                    "type": "final", "text": corrected["corrected"], "confidence": 0.85,
                                    "corrections": corrected["corrections"],
                                })
                        await websocket.send_json({"type": "end"})
                        logger.info(f"[WS] ✓ 已发送 end，关闭连接")
                        break

                # 二进制消息（音频数据）
                elif isinstance(msg_data, bytes):
                    audio_chunks_received += 1
                    if asr_engine:
                        async for result in asr_engine.transcribe_stream(msg_data):
                            await websocket.send_json(result)
                    else:
                        simulated_chunks += 1
                        if simulated_chunks % 3 == 0:
                            idx = min(simulated_chunks // 3, len(simulated_texts) - 1)
                            await websocket.send_json({
                                "type": "partial",
                                "text": simulated_texts[idx],
                                "confidence": 0.85,
                            })

    except WebSocketDisconnect:
        logger.info(f"[WS] 连接异常断开: {ws_client}")
    finally:
        if asr_engine and asr_engine is not _asr_engine_instance:
            await asr_engine.close()
        logger.info(f"[WS] 连接关闭: {ws_client}，共接收 {audio_chunks_received} 个音频块")


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
async def optimize_text(req: OptimizeRequest):
    """
    场景化文本处理（直接 LLM 优化）

    使用大模型直接生成优化结果，不经过规则中间阶段。
    """
    profile = get_user_profile()
    profile.record_scene_usage(req.scene_type)

    # 行业词库纠错（对所有模式生效）
    text = req.text
    correction = industry_lexicon.correct_text(text)
    if correction["corrections"]:
        text = correction["corrected"]
        logger.info(f"[optimize] 行业词库纠错 {correction['correction_count']} 处: {correction['corrections']}")

    # 缓存检查
    text_hash = hashlib.md5(text.encode()).hexdigest()
    if settings.CACHE_ENABLED:
        cached = cache_manager.get_optimization(text_hash, req.scene_type)
        if cached:
            return cached

    # LLM 优化（直接等待结果）
    if not settings.MVP_MODE and settings.LLM_ENABLED and prompt_manager.llm:
        if req.scene_type == "办公":
            result = await _llm_office_optimize(text)
        elif req.scene_type == "聊天":
            result = await _llm_chat_optimize(text)
        elif req.scene_type == "创作":
            result = await _llm_creation_process(text)
        else:
            raise HTTPException(400, f"未知场景: {req.scene_type}")
    else:
        # 降级到规则处理（当 LLM 不可用时）
        if req.scene_type == "办公":
            result = office_polish(text)
        elif req.scene_type == "聊天":
            result = chat_recommend(text)
        elif req.scene_type == "创作":
            result = creation_process(text)
        else:
            raise HTTPException(400, f"未知场景: {req.scene_type}")

    # 写入缓存
    if settings.CACHE_ENABLED and result:
        cache_manager.set_optimization(text_hash, req.scene_type, result)

    return result


async def _llm_office_optimize(text: str) -> dict:
    """
    使用大模型进行办公场景优化

    1. 注入用户偏好上下文
    2. 通过 prompt_manager 获取并渲染办公场景模板
    3. 调用大模型
    4. 解析 markdown 输出为前端期望的 versions 格式
    """
    profile_context = build_full_context()
    llm_output = await prompt_manager.execute("office_rewrite", text=text,
                                               profile_context=profile_context)
    versions = _parse_llm_versions(llm_output)
    # 确保至少有一个版本
    if not versions:
        logger.warning("LLM 输出解析结果为空，使用规则处理结果")
        return office_polish(text)
    return {
        "origin": text,
        "versions": versions
    }


async def _llm_chat_optimize(text: str) -> dict:
    """使用大模型进行聊天场景优化 — 生成 emoji/颜文字版本"""
    profile_context = build_full_context()
    llm_output = await prompt_manager.execute("chat_emoji", text=text,
                                               profile_context=profile_context,
                                               use_cache=True)
    versions = _parse_llm_versions(llm_output)
    if not versions:
        logger.warning("LLM 聊天输出解析结果为空，使用规则处理结果")
        return chat_recommend(text)
    return {
        "origin": text,
        "versions": versions
    }


async def _llm_creation_process(text: str) -> dict:
    """使用大模型进行创作场景优化（注入用户偏好）"""
    profile_context = build_full_context()
    llm_output = await prompt_manager.execute("creation_process", text=text,
                                               profile_context=profile_context)
    # 尝试解析为三个版本
    versions = _parse_llm_versions(llm_output)
    if versions:
        return {
            "origin": text,
            "organized": versions[0],
            "outline": versions[1] if len(versions) > 1 else versions[0],
            "expanded": versions[2] if len(versions) > 2 else versions[0],
        }
    return creation_process(text)


def _parse_llm_versions(markdown_text: str) -> list[dict]:
    """
    将大模型输出的 markdown 解析为 versions 列表
    自动清理 **场景判断**、---、**适用场景** 等多余内容。
    """
    import re

    # ── 预处理：彻底清理多余内容 ──
    text = markdown_text

    # 去掉 **场景判断** 行及类似行
    text = re.sub(r'\*\*?场景判断\*\*?[^\n]*', '', text)
    text = re.sub(r'\*\*?适用场景\*\*?[^\n]*', '', text)

    # 去掉所有 --- 分隔线（独立行）
    text = re.sub(r'\n[ \t]*---+[ \t]*\n', '\n', text)

    # 去掉 ** 包裹的标记行（如 **沟通润色**）
    text = re.sub(r'\n[ \t]*\*\*[^*]+\*\*[^\n]*', '\n', text)

    # 去掉多余的空白行，只保留一个换行
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    versions = []

    # 按 ### 分割版本块（兼容开头就是 ### 的情况）
    blocks = re.split(r'(?:^|\n)###\s+', text)
    for block in blocks:
        if not block.strip():
            continue

        lines = block.strip().split('\n')

        # 第一行是版本标题，清理 ### 前缀和 "版本一：" 前缀
        title_line = lines[0].strip().lstrip('#').strip()
        style_match = re.match(r'(?:版本[一二三]\s*[：:]\s*)?(.+)', title_line)
        style = style_match.group(1).strip() if style_match else title_line

        # 剩下的是正文（跳过空行和加粗标记行）
        body_lines = []
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('**') and stripped.endswith('**') and len(stripped) > 4:
                continue
            body_lines.append(line)

        text_body = '\n'.join(body_lines).strip()
        if text_body:
            versions.append({
                "style": style,
                "description": "",
                "text": text_body
            })

    # 如果没有按 ### 分割到版本，尝试把整段当作文本
    if not versions and text.strip():
        versions.append({
            "style": "整理版",
            "description": "",
            "text": text.strip()
        })

    return versions

    return versions


# ═══════════════════════════════════════════════
#  6.5 编辑分析 (Edit Tracking & Learning)
# ═══════════════════════════════════════════════

@app.post("/api/analyze-edits")
def analyze_edits_endpoint(req: AnalyzeEditsRequest):
    """
    分析用户对转写文本的手动编辑。

    全流程:
      1. 词级别 diff（jieba + difflib）
      2. 分类每处改动（asr_fix / style_change / content_add / content_delete / punctuation）
      3. 执行学习动作（更新热词 / 词库 / 偏好）
      4. 写入 edit_log
    """
    result = analyze_edits(
        original=req.original_text,
        edited=req.edited_text,
        scene=req.scene_type,
        user_id=req.user_id,
        session_id=req.session_id
    )
    return result


@app.get("/api/analyze-edits/history")
def analyze_edits_history(user_id: str = "default"):
    """获取编辑历史"""
    return edit_log_db.get_edit_history(user_id)


# ═══════════════════════════════════════════════
#  6.7 创作工作区 (Interactive Creation)
# ═══════════════════════════════════════════════

@app.post("/api/creation/session")
def create_creation_session(req: CreateSessionRequest):
    """创建新的创作会话"""
    if req.mode not in ("novel", "project"):
        raise HTTPException(400, "mode must be 'novel' or 'project'")
    session = create_session(req.mode)
    creation_db.save_session(session.session_id, session.mode)
    return {
        "session_id": session.session_id,
        "mode": session.mode,
        "status": session.status,
        "created_at": session.created_at,
    }


@app.post("/api/creation/session/{session_id}/input")
async def submit_creation_input(session_id: str, req: SubmitInputRequest):
    """提交新一轮语音输入"""
    if not req.text.strip():
        raise HTTPException(400, "Input text cannot be empty")

    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found or already finished")

    # LLM 处理
    try:
        llm_result = await process_with_llm(session, req.text, prompt_manager)
    except Exception as e:
        logger.warning(f"LLM creation round failed, using fallback: {e}")
        llm_result = rule_based_fallback(session.mode, req.text)

    # 记录到会话
    new_round = add_round(session_id, req.text, llm_result)

    # 持久化到数据库
    creation_db.save_round(
        session_id, new_round.round_number, req.text,
        new_round.organized_output,
        new_round.extraction,
        new_round.tips, new_round.innovations, new_round.improvements,
    )

    # 记录场景使用
    try:
        from database import profiles_db
        profiles_db.record_scene_usage("default", "创作")
    except Exception:
        pass

    return new_round.to_dict()


@app.post("/api/creation/session/{session_id}/finish")
def finish_creation_session(session_id: str):
    """结束创作会话并保存到历史"""
    session = finish_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    creation_db.finish_session_in_db(session_id)

    # 写入历史记录摘要 — 存储可读文本而非 JSON
    mode_label = "写小说" if session.mode == "novel" else "代码项目策划"
    last_round = session.rounds[-1] if session.rounds else None
    summary = f"[创作] {mode_label} 共{len(session.rounds)}轮"
    try:
        # 构建可读的优化文本摘要
        clean_parts = [f"【{mode_label}】共{len(session.rounds)}轮创作"]
        for r in session.rounds:
            clean_parts.append(f"\n\n=== 第{r.round_number}轮 ===")
            clean_parts.append(f"原始语音：{r.raw_input}")
            clean_parts.append(f"整理内容：{r.organized_output}")
        clean_text = "".join(clean_parts)

        history_db.save_history(
            "default",
            content_raw=last_round.raw_input if last_round else "",
            content_optimized=clean_text,
            scene_type="创作",
            title=summary,
            tags=f"creation_session,{session.mode}",
        )
    except Exception as e:
        logger.warning(f"保存创作历史失败: {e}")

    return {"status": "finished", "session": session.to_dict()}


@app.post("/api/creation/session/{session_id}/round/{round_number}/copy-organized")
def track_copy_organized(session_id: str, round_number: int):
    """记录复制推荐文本"""
    mark_copy_organized(session_id, round_number)
    creation_db.update_copy_status(session_id, round_number, "organized")
    return {"ok": True}


@app.post("/api/creation/session/{session_id}/round/{round_number}/copy-raw")
def track_copy_raw(session_id: str, round_number: int):
    """记录复制原始语音"""
    mark_copy_raw(session_id, round_number)
    creation_db.update_copy_status(session_id, round_number, "raw")
    return {"ok": True}


@app.get("/api/creation/session/{session_id}")
def get_creation_session(session_id: str):
    """获取会话详情"""
    session = get_session(session_id)
    if session:
        return session.to_dict()

    # 从数据库获取
    db_session = creation_db.get_session_by_id(session_id)
    if not db_session:
        raise HTTPException(404, "Session not found")
    rounds = creation_db.get_rounds_by_session(session_id)
    return {"session": db_session, "rounds": rounds}


@app.get("/api/creation/sessions")
def list_creation_sessions(status: str = ""):
    """列出历史创作会话"""
    return creation_db.get_all_sessions(status=status)


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

    # Step 3: 场景优化
    if scene == "办公":
        optimized = office_polish(corrected)
    elif scene == "聊天":
        optimized = chat_recommend(corrected)
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
            "optimization": optimized
        }
    }



	# ═══════════════════════════════════════════════
	#  8. （已移除 emoji/emotion 本地模块，聊天模式改用 LLM）


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


@app.post("/api/documents/extract-terms")
def extract_document_terms(data: dict):
    """AI 自动提取文档中的专业术语"""
    text = data.get("text", "")
    doc_type = data.get("doc_type", "")
    if not text.strip():
        return {"terms": []}
    terms = extract_terms(text, doc_type, use_llm=settings.LLM_ENABLED)
    return {
        "terms": terms,
        "count": len(terms),
        "mode": "llm" if settings.LLM_ENABLED else "rule",
    }


# ═══════════════════════════════════════════════
#  10. 行业专业词库系统 (Industry Lexicon System)
# ═══════════════════════════════════════════════

@app.get("/api/industry-lexicon/industries")
def list_industries():
    """获取所有可用行业分类"""
    industries = industry_lexicon_db.get_all_industries()
    counts = industry_lexicon_db.get_all_industry_word_counts()
    return {"industries": industries, "_debug": {"counts": counts}}


@app.get("/api/industry-lexicon/words")
def get_industry_words(industry: str = Query(...)):
    """获取指定行业的词条"""
    return {"industry": industry, "words": industry_lexicon_db.get_industry_words(industry)}


@app.get("/api/industry-lexicon/categories")
def get_industry_categories(industry: str = Query(...)):
    """获取行业各层级的词条数量统计"""
    counts = industry_lexicon_db.get_category_counts(industry)
    return {"industry": industry, "categories": counts}


@app.get("/api/industry-lexicon/words/category")
def get_industry_words_by_category(industry: str = Query(...), category: str = Query(...)):
    """按层级获取行业词条"""
    words = industry_lexicon_db.get_words_by_category(industry, category)
    return {"industry": industry, "category": category, "words": words}


@app.get("/api/industry-lexicon/search")
def search_industry_lexicon(keyword: str = Query(...), industry: str = ""):
    """搜索行业词条"""
    return {"results": industry_lexicon.search_words(keyword, industry)}


@app.post("/api/industry-lexicon/select")
def select_industries(req: IndustrySelectRequest):
    """用户选择行业"""
    industry_lexicon.select_industries(req.user_id, req.industries)
    # 选择后自动同步热词
    hotwords = industry_lexicon.get_hotwords(req.user_id, force_refresh=True)
    hotword_manager.sync_from_industry_system(hotwords)
    return {
        "status": "ok",
        "industries": req.industries,
        "hotwords_loaded": len(hotwords)
    }


@app.get("/api/industry-lexicon/selected")
def get_selected_industries(user_id: str = "default"):
    """获取用户已选择的行业"""
    industries = industry_lexicon.get_selected_industries(user_id)
    return {"industries": industries}


@app.post("/api/industry-lexicon/import")
def import_industry_words(data: IndustryWordImport):
    """批量导入行业词条"""
    result = industry_lexicon.import_words(data.words)
    return result


@app.post("/api/industry-lexicon/correct")
def correct_asr_text(text: str = Query(...), user_id: str = "default", use_llm: bool = False):
    """ASR 文本纠错 — 基于行业词库（use_llm=true 时启用 LLM 上下文感知纠错）"""
    if use_llm and settings.LLM_ENABLED:
        result = industry_lexicon.correct_text_llm(text, user_id)
    else:
        result = industry_lexicon.correct_text(text, user_id)
    return result


@app.post("/api/industry-lexicon/learn")
def learn_correction(original_word: str = Query(...), corrected_word: str = Query(...), user_id: str = "default"):
    """用户修正学习"""
    industry_lexicon.learn_correction(user_id, original_word, corrected_word)
    hotword_manager.add_hotword(corrected_word)
    return {"status": "learned"}


@app.get("/api/industry-lexicon/hotwords")
def get_industry_hotwords(user_id: str = "default"):
    """获取当前行业的热词列表"""
    hotwords = industry_lexicon.get_hotwords(user_id)
    return {"hotwords": hotwords, "count": len(hotwords)}


@app.get("/api/industry-lexicon/rag")
def industry_rag_query(text: str = Query(...), user_id: str = "default", top_k: int = 5):
    """行业词库 RAG 检索"""
    candidates = industry_lexicon.retrieve_candidates(text, user_id, top_k)
    return {"text": text, "candidates": candidates, "count": len(candidates)}


# ═══════════════════════════════════════════════
#  11. Prompt 管理
# ═══════════════════════════════════════════════

@app.get("/api/prompts")
def list_prompts(scene: str = ""):
    if scene:
        return [{"name": t.name, "scene": t.scene, "version": t.version}
                for t in prompt_manager.get_by_scene(scene)]
    return [{"name": t.name, "scene": t.scene, "version": t.version}
            for t in prompt_manager._templates.values()]


# ═══════════════════════════════════════════════
#  12. 缓存管理
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
#  13. AI 架构状态
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
            "industry_lexicon": {
                "status": "ready",
                "industries": len(industry_lexicon_db.get_all_industries()),
                "active": industry_lexicon._active_industries
            },
        }
    }


# ═══════════════════════════════════════════════
#  14. WebSocket 调试
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
#  15. 健康检查
# ═══════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": settings.VERSION,
        "mode": "MVP" if settings.MVP_MODE else "LLM",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True,
                reload_dirs=[str(PROJECT_ROOT)])
