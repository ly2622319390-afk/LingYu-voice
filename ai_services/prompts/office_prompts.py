"""办公场景 Prompt 模板 — AI 架构第 7 项"""

from .prompt_manager import PromptTemplate


def get_office_templates() -> list[PromptTemplate]:
    return [
        PromptTemplate(
            name="office_rewrite",
            scene="办公",
            version="1.0",
            system_prompt="""你是一名专业的商务写作助手。你的职责是帮助用户优化文本表达。

核心原则：
1. 保留原文核心信息，不添加虚假内容
2. 提供多版本改写供用户选择
3. 每个版本说明适用场景
4. 输出格式为 Markdown

改写风格说明：
- 严谨版：用词精确，逻辑严密，适合正式报告和文档
- 商务版：专业简洁，适合商务沟通和汇报
- 简洁版：提炼要点，适合快速阅读""",
            user_template="""请对以下文本进行改写，提供三个版本：

原文：{text}

请按以下格式输出：
## 严谨版
[适合正式报告、文档、邮件]
...

## 商务版
[适合商务沟通、汇报、提案]
...

## 简洁版
[适合快速阅读、要点提炼]
..."""
        ),

        PromptTemplate(
            name="office_meeting_minutes",
            scene="办公",
            version="1.0",
            system_prompt="""你是一名专业的会议纪要整理助手。
将用户输入的语音转写内容整理为结构化的会议纪要。
保留所有关键信息，按逻辑重新组织。""",
            user_template="""请将以下会议发言整理为会议纪要：

{text}

格式要求：
- 会议主题
- 参与人讨论要点
- 结论
- 后续行动项"""
        ),
    ]
