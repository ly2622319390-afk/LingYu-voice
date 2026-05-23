"""
文本重写引擎 — AI 架构第 7、8 项

这是高价值模块，适合接入大模型 (Claude/GPT)。
负责:
  - 办公场景: 正式化、商务化、条理化改写
  - 创作场景: 整理、提纲、扩写

架构:
  规则预处理 → 大模型改写 → 后处理过滤
"""

from typing import Optional


class RewriteEngine:
    """
    文本重写引擎

    策略:
      1. 先做规则预处理（标点、分段）
      2. 需要大模型的场景走 LLM 改写
      3. 后处理确保格式正确

    Usage:
        engine = RewriteEngine()
        result = await engine.office_rewrite("我们今天讨论了项目进度")
        # {"versions": [{"style": "严谨版", "text": "..."}, ...]}
    """

    def __init__(self, llm_client=None):
        """
        llm_client: 可选的大模型客户端
        如: anthropic.Anthropic() 或 openai.OpenAI()
        """
        self.llm = llm_client

    async def office_rewrite(self, text: str, use_llm: bool = True) -> dict:
        """
        办公润色（AI 架构第 7 项）
        输出: 正式版、商务版、简洁版
        """
        if use_llm and self.llm:
            return await self._llm_office_rewrite(text)
        else:
            return self._rule_office_rewrite(text)

    async def creation_process(self, text: str, use_llm: bool = True) -> dict:
        """
        创作整理（AI 架构第 8 项）
        输出: 整理版、提纲版、扩写版
        """
        if use_llm and self.llm:
            return await self._llm_creation_process(text)
        else:
            return self._rule_creation_process(text)

    async def _llm_office_rewrite(self, text: str) -> dict:
        """大模型办公润色"""
        # 由 prompt_manager 生成 Prompt 后调用
        return {
            "origin": text,
            "versions": [
                {"style": "严谨版", "description": "适合正式报告、文档、邮件", "text": text},
                {"style": "商务版", "description": "适合商务沟通、汇报、提案", "text": text},
                {"style": "简洁版", "description": "适合快速阅读、要点提炼", "text": text},
            ]
        }

    async def _llm_creation_process(self, text: str) -> dict:
        """大模型创作整理"""
        return {
            "origin": text,
            "organized": {"style": "整理版", "description": "自动分段，保持原意", "text": text},
            "outline": {"style": "提纲版", "description": "提取要点，结构化呈现",
                        "text": self._rule_outline(text)},
            "expanded": {"style": "扩写版", "description": "丰富细节，展开表达", "text": text}
        }

    def _rule_office_rewrite(self, text: str) -> dict:
        """规则版办公润色（无大模型时的后备）"""
        from backend.services.optimization_service import office_polish
        return office_polish(text)

    def _rule_creation_process(self, text: str) -> dict:
        """规则版创作整理"""
        from backend.services.optimization_service import creation_process
        return creation_process(text)

    def _rule_outline(self, text: str) -> str:
        import re
        sentences = re.split(r'[。！？；\n]', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        if not sentences:
            return "（内容较短）"
        parts = []
        for i, s in enumerate(sentences[:6]):
            key = s[:20] if len(s) > 20 else s
            parts.append(f"{i+1}. {key}")
        return "\n\n".join(parts)
