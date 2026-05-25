"""创作场景 Prompt 模板 — 内容整理/提纲/扩写"""

from .prompt_manager import PromptTemplate


def get_creation_templates() -> list[PromptTemplate]:
    return [
        PromptTemplate(
            name="creation_process",
            scene="创作",
            version="1.0",
            system_prompt="""你是一名专业的内容创作助手。
将用户输入的语音转写内容整理为结构化的创作内容。

根据内容长度和复杂度自动选择处理方式：
- 短内容（<100字）：适当丰富，保持原意
- 中等内容（100-500字）：分段整理，提炼要点
- 长内容（>500字）：生成提纲，可扩写

输出三个版本：
1. 整理版：保持原意，优化分段和条理
2. 提纲版：提取核心要点，结构化呈现
3. 扩写版：在原文基础上合理丰富细节""",
            user_template="""请处理以下创作内容：

原文：{text}

请输出整理版、提纲版、扩写版三个版本。""",
        ),
    ]
