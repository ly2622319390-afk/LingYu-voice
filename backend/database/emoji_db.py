"""表情库数据库 - databases/emoji/emoji.db"""
from .db_manager import db_manager

DB_NAME = "emoji"


def init_db():
    conn = db_manager.get_connection(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS emotion_emoji (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emoji TEXT NOT NULL,
            emotion_tags TEXT DEFAULT '',
            score_map TEXT DEFAULT '{}',
            scene_tags TEXT DEFAULT '',
            usage_priority INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    _seed_default_emoji()


def _seed_default_emoji():
    conn = db_manager.get_connection(DB_NAME)
    count = conn.execute("SELECT COUNT(*) as cnt FROM emotion_emoji").fetchone()["cnt"]
    if count > 0:
        return

    default_emojis = [
        # 积极情绪
        ("😊", "开心,满意,友好", '{"joy":0.9,"satisfaction":0.8}', "聊天", 90),
        ("😂", "好笑,开心,大笑", '{"joy":0.95,"humor":0.9}', "聊天", 95),
        ("🥰", "爱,喜欢,温暖", '{"love":0.9,"warmth":0.8}', "聊天,创作", 85),
        ("😍", "喜爱,赞赏,热情", '{"love":0.85,"admiration":0.8}', "聊天", 80),
        ("👍", "赞同,肯定,鼓励", '{"agreement":0.9,"encouragement":0.8}', "办公,聊天", 90),
        ("🎉", "庆祝,祝贺,成功", '{"joy":0.9,"celebration":0.95}', "办公,聊天", 85),
        ("✨", "闪耀,美好,精彩", '{"positive":0.8,"beauty":0.85}', "办公,聊天,创作", 80),
        ("🌟", "优秀,突出,成功", '{"praise":0.85,"success":0.9}', "办公,聊天", 75),
        ("💪", "努力,坚持,力量", '{"determination":0.9,"strength":0.8}', "办公,聊天", 80),
        ("🔥", "热门,厉害,激情", '{"excitement":0.85,"passion":0.8}', "聊天", 85),
        # 中性情绪
        ("🤔", "思考,疑惑,考虑", '{"thinking":0.9,"doubt":0.5}', "办公,聊天,创作", 85),
        ("😌", "安心,放松,满意", '{"relief":0.8,"calm":0.85}', "聊天,创作", 75),
        ("💡", "灵感,想法,创意", '{"inspiration":0.95,"creativity":0.9}', "办公,创作", 90),
        ("📝", "记录,写作,笔记", '{"writing":0.9,"recording":0.85}', "办公,创作", 85),
        # 消极情绪
        ("😢", "伤心,难过,失落", '{"sadness":0.9,"disappointment":0.7}', "聊天", 80),
        ("😅", "尴尬,无奈,苦笑", '{"embarrassment":0.8,"awkward":0.75}', "聊天", 85),
        ("😤", "沮丧,不满,挫败", '{"frustration":0.85,"anger":0.6}', "聊天", 70),
        # 办公常用
        ("✅", "完成,确认,通过", '{"completion":0.95,"agreement":0.9}', "办公", 95),
        ("📌", "重要,置顶,提醒", '{"important":0.9,"reminder":0.85}', "办公", 85),
        ("📊", "数据,报告,分析", '{"data":0.9,"report":0.85}', "办公", 80),
        ("📎", "附件,关联,附加", '{"attachment":0.95}', "办公", 85),
        ("📅", "日程,日期,安排", '{"schedule":0.9,"date":0.85}', "办公", 80),
        ("🔍", "搜索,查看,检查", '{"search":0.9,"review":0.85}', "办公", 75),
        ("🎯", "目标,精准,聚焦", '{"goal":0.9,"focus":0.85}', "办公", 85),
        # 创作常用
        ("✍️", "写作,创作,手写", '{"writing":0.9,"creation":0.85}', "办公,创作", 85),
        ("📖", "阅读,学习,书", '{"reading":0.9,"learning":0.8}', "创作", 80),
        ("🎨", "艺术,设计,创意", '{"art":0.9,"creativity":0.85}', "创作", 85),
        ("🗂️", "分类,整理,归档", '{"organization":0.9}', "办公,创作", 75),
        # 颜文字 (kaomoji)
        ("(´▽`ʃ♡ƪ)", "开心,可爱,喜欢", '{"joy":0.8,"cute":0.9}', "聊天", 70),
        ("(｀・ω・´)", "坚定,认真,积极", '{"determination":0.7,"serious":0.6}', "聊天", 65),
        ("(◕‿◕✿)", "温柔,友好,可爱", '{"warmth":0.8,"friendly":0.9}', "聊天", 70),
        ("(╯°□°）╯︵┻━┻", "生气,无奈,发泄", '{"frustration":0.9,"anger":0.8}', "聊天", 60),
        ("¯\\_(ツ)_/¯", "无奈, shrug,随意", '{"helplessness":0.7,"indifference":0.6}', "聊天", 65),
        ("(｡ŏ_ŏ)", "疑惑,惊讶,好奇", '{"doubt":0.7,"surprise":0.6}', "聊天", 55),
        ("(∼‾▽‾)∼", "轻松,愉快,摇摆", '{"joy":0.7,"relaxed":0.8}', "聊天", 60),
        ("(•̀ᴗ•́)و", "加油,努力,奋斗", '{"determination":0.8,"encouragement":0.9}', "聊天", 70),
    ]
    for emoji, tags, score_map, scenes, priority in default_emojis:
        conn.execute(
            "INSERT INTO emotion_emoji (emoji, emotion_tags, score_map, scene_tags, usage_priority) VALUES (?, ?, ?, ?, ?)",
            (emoji, tags, score_map, scenes, priority)
        )
    conn.commit()


def get_emoji_by_scene(scene_type: str, limit: int = 10) -> list[dict]:
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT * FROM emotion_emoji WHERE scene_tags LIKE ? ORDER BY usage_priority DESC LIMIT ?",
        (f"%{scene_type}%", limit)
    ).fetchall()
    return [dict(r) for r in rows]


def get_emoji_by_emotion(emotion_tag: str, scene_type: str = "", limit: int = 5) -> list[dict]:
    conn = db_manager.get_connection(DB_NAME)
    if scene_type:
        rows = conn.execute(
            "SELECT * FROM emotion_emoji WHERE emotion_tags LIKE ? AND scene_tags LIKE ? ORDER BY usage_priority DESC LIMIT ?",
            (f"%{emotion_tag}%", f"%{scene_type}%", limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM emotion_emoji WHERE emotion_tags LIKE ? ORDER BY usage_priority DESC LIMIT ?",
            (f"%{emotion_tag}%", limit)
        ).fetchall()
    return [dict(r) for r in rows]
