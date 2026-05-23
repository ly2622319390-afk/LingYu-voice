"""创作场景 Prompt 模板 — AI 架构第 8 项"""

from .prompt_manager import PromptTemplate


def get_creation_templates() -> list[PromptTemplate]:
    return [
        PromptTemplate(
            name="creation_process",
            scene="创作",
            version="1.0",
            system_prompt="""你是一名创作辅助助手。帮助用户整理灵感、生成提纲、扩写内容。

核心原则：
1. 必须保留原文原意
2. 不添加用户没说过的内容
3. 结构化但不改变核心表达
4. 输出格式为 Markdown""",
            user_template="""请对以下创作内容进行处理，提供三个版本：

原文：{text}

请输出：
## 整理版
[自动分段，保持原意]

## 提纲版
[提取要点，结构化呈现]

## 扩写版
[丰富细节，展开表达]"""
        ),

        PromptTemplate(
            name="creation_title",
            scene="创作",
            version="1.0",
            system_prompt="""你是一名标题生成助手。
根据内容生成 3-5 个吸引人的标题建议。""",
            user_template="""根据以下内容生成标题建议：

{text}

输出 3-5 个标题，每个标题一行。"""
        ),
    ]
