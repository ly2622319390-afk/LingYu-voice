"""
标点恢复模块 — AI 架构第 2 项

目标:
  - ASR 输出无标点 → 自动加标点、断句
  - 高频调用，不使用大模型
  - 支持场景化标点策略

当前实现: 规则系统
后续升级: 轻量 punctuation model (e.g., "punc_ct-transformer_zh-cn")
"""

import re


class PunctuationRestorer:
    """
    标点恢复器

    Usage:
        restorer = PunctuationRestorer(scene="办公")
        result = restorer.restore("今天我们讨论一下项目进度")
        # -> "今天我们讨论一下项目进度。"
    """

    def __init__(self, scene: str = "办公"):
        self.scene = scene

    def restore(self, text: str, is_partial: bool = False) -> str:
        """恢复标点"""
        if not text or is_partial:
            return text

        text = text.strip()

        # 场景化策略
        if self.scene == "办公":
            text = self._apply_office_rules(text)
        elif self.scene == "聊天":
            text = self._apply_chat_rules(text)
        else:  # 创作
            text = self._apply_creation_rules(text)

        return text

    def _apply_office_rules(self, text: str) -> str:
        """办公模式：标点正式，断句清晰"""
        # 句末加句号
        if text and not text[-1] in "。！？；，、":
            text += "。"
        # 避免过多感叹号
        text = text.replace("！！", "！").replace("？？", "？")
        return text

    def _apply_chat_rules(self, text: str) -> str:
        """聊天模式：标点自然，允许省略句号"""
        text = text.replace("。。", "。").replace("！！", "！")
        if text.endswith("哦") or text.endswith("呢") or text.endswith("吧"):
            if not text[-1] in "。！？～~":
                text += "～"
        elif text.endswith("吗") or text.endswith("么"):
            if not text[-1] in "。！？":
                text += "？"
        elif text.endswith("啦"):
            if not text[-1] in "。！？":
                text += "！"
        # 聊天模式句号省略（保留自然感）
        return text

    def _apply_creation_rules(self, text: str) -> str:
        """创作模式：保留原表达，少干预"""
        if text and not text[-1] in "。！？；，、\n":
            text += "。"
        return text

    def add_periods(self, text: str) -> str:
        """为长文本断句加句号"""
        # 在 "了", "的", "呢", "吗", "吧", "啊", "啦" 后加逗号或句号
        text = re.sub(r'(了|的|呢|吗|吧|啊|啦)(?!\s*[。！？，、])', r'\1，', text)
        return text


class PunctuationService:
    """
    标点恢复服务（带场景策略）

    可被替换为模型版:
        from funasr import AutoModel
        punc_model = AutoModel(model="iic/punc_ct-transformer_zh-cn")
    """

    def __init__(self):
        self._model = None  # 预留模型装载

    def restore(self, text: str, scene: str = "办公") -> str:
        restorer = PunctuationRestorer(scene)
        return restorer.restore(text)

    async def load_model(self):
        """加载轻量标点模型（第二阶段）"""
        # punc_ct-transformer_zh-cn
        pass
