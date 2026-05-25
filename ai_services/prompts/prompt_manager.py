"""
Prompt 核心管理器 — AI 架构第 4 项

负责:
  - Prompt 模板注册、版本管理
  - 变量插值
  - 调用策略（直接调 LLM / 走缓存）
"""

import asyncio
from typing import Optional, Callable
import hashlib
import json
import datetime


class PromptTemplate:
    """Prompt 模板"""

    def __init__(self, name: str, system_prompt: str, user_template: str,
                 version: str = "1.0", scene: str = "",
                 model: str = "claude-3-sonnet-20241022"):
        self.name = name
        self.system_prompt = system_prompt
        self.user_template = user_template
        self.version = version
        self.scene = scene
        self.model = model
        self.created_at = datetime.datetime.now().isoformat()

    def render(self, **kwargs) -> tuple[str, str]:
        """渲染 system + user prompt，返回 (system, user)"""
        system = self.system_prompt
        user = self.user_template
        for k, v in kwargs.items():
            placeholder = "{" + k + "}"
            system = system.replace(placeholder, str(v))
            user = user.replace(placeholder, str(v))
        return system, user

    def cache_key(self, **kwargs) -> str:
        """生成缓存 key"""
        content = json.dumps({"name": self.name, "version": self.version, "params": kwargs}, sort_keys=True)
        return f"prompt:{self.name}:{hashlib.md5(content.encode()).hexdigest()}"


class PromptManager:
    """
    Prompt 管理器

    注册模板 → 按场景获取 → 渲染 → 调用 LLM（直接或缓存）

    Usage:
        pm = PromptManager()
        result = await pm.execute("office_rewrite", text="今天开会讨论了...")
    """

    def __init__(self, llm_client=None):
        """
        llm_client: 大模型客户端 (anthropic.Anthropic / openai.OpenAI)
        必须实现 messages.create() 接口
        """
        self._templates: dict[str, PromptTemplate] = {}
        self.llm = llm_client
        self._cache = {}

    def register(self, template: PromptTemplate):
        """注册 Prompt 模板"""
        self._templates[template.name] = template

    @property
    def model_name(self) -> str:
        """当前生效的模型名称（可被 _init_llm 覆盖）"""
        return getattr(self, '_model_name', "")

    @model_name.setter
    def model_name(self, val: str):
        self._model_name = val

    def get(self, name: str) -> Optional[PromptTemplate]:
        return self._templates.get(name)

    def get_by_scene(self, scene: str) -> list[PromptTemplate]:
        """按场景获取模板"""
        return [t for t in self._templates.values() if t.scene == scene]

    def render(self, name: str, **kwargs) -> tuple[str, str]:
        """渲染 Prompt"""
        template = self.get(name)
        if not template:
            raise ValueError(f"Prompt template '{name}' not found")
        return template.render(**kwargs)

    async def execute(self, name: str, use_cache: bool = True,
                      profile_context: str = "", **kwargs) -> str:
        """
        执行 Prompt（直接调 LLM）

        Args:
            name: 模板名称
            use_cache: 是否使用缓存
            profile_context: 用户偏好上下文（非空时附加到 system prompt 前缀）
            **kwargs: 模板变量

        Returns:
            LLM 输出文本
        """
        if not self.llm:
            raise RuntimeError("LLM client not configured")

        template = self.get(name)
        if not template:
            raise ValueError(f"Prompt template '{name}' not found")

        cache_key = template.cache_key(**kwargs) if use_cache else None

        # 缓存命中
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]

        # 渲染 Prompt
        system, user = template.render(**kwargs)

        # 注入用户偏好上下文
        if profile_context:
            system = profile_context + "\n\n" + system

        # 使用的模型：优先用外部配置（如 DeepSeek/OpenAI），否则用模板默认
        model = self.model_name or template.model

        # 调用 LLM
        response = await self._call_llm(system, user, model)

        # 写入缓存
        if cache_key:
            self._cache[cache_key] = response

        return response

    async def _call_llm(self, system: str, user: str, model: str) -> str:
        """调用大模型（同步客户端在线程池运行，不阻塞事件循环）"""
        loop = asyncio.get_event_loop()
        if hasattr(self.llm, 'chat'):
            response = await loop.run_in_executor(
                None,
                lambda: self.llm.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}
                    ],
                    timeout=25,
                ),
            )
            return response.choices[0].message.content
        elif hasattr(self.llm, 'messages'):
            response = await loop.run_in_executor(
                None,
                lambda: self.llm.messages.create(
                    model=model,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    timeout=25,
                ),
            )
            return response.content[0].text
        else:
            raise RuntimeError(f"不支持的大模型客户端: {type(self.llm).__name__}")

    def clear_cache(self):
        self._cache.clear()

    def register_default_templates(self):
        """注册内置默认模板"""
        from .office_prompts import get_office_templates
        from .creation_prompts import get_creation_templates
        from .chat_prompts import get_chat_templates
        for t in get_office_templates():
            self.register(t)
        for t in get_creation_templates():
            self.register(t)
        for t in get_chat_templates():
            self.register(t)
