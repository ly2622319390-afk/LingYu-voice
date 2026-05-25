"""100+ AI 高频术语补充 — 2025年常用英文词汇的常见 ASR 误识别别名

直接运行此脚本即可生成 JSON 文件:
    python _gen_ai_supplement.py

输出: 10_AI_补充术语.json（约 110 条）
"""
import json
import os

ENTRIES = []

def add(word, aliases, sub_industry="", weight=0.85, typ="", lang="en", freq=0.8, desc=""):
    ENTRIES.append({
        "word": word,
        "aliases": aliases,
        "industry": "互联网/AI",
        "sub_industry": sub_industry,
        "weight": weight,
        "type": typ,
        "language": lang,
        "frequency": freq,
        "description": desc,
        "category": "专业层"
    })

# ─── 1. 大模型/前沿模型 ────────────────────────────────────
add("GPT-4o", ["G P T 四欧", "GPT4o", "GPT四欧", "chat GPT 4o", "四欧模型"], "AI模型", 0.95, "model", "en", 0.90, "OpenAI 多模态旗舰模型")
add("GPT-4.5", ["G P T 四五", "GPT4 5", "GPT 4.5", "GPT四点五"], "AI模型", 0.90, "model", "en", 0.80, "OpenAI 最新模型")
add("GPT-5", ["G P T 五", "GPT5", "GPT五", "第五代GPT"], "AI模型", 0.90, "model", "en", 0.70, "OpenAI 下一代模型")
add("o1", ["O一", "O1模型", "欧一", "OpenAI o1", "推理模型o1"], "AI模型", 0.90, "model", "en", 0.85, "OpenAI 推理增强模型")
add("o3", ["O三", "O3模型", "欧三", "OpenAI o3", "推理模型o3"], "AI模型", 0.85, "model", "en", 0.70, "OpenAI 最新推理模型")
add("4o", ["四欧", "4o模型", "fogo", "for欧"], "AI模型", 0.90, "model", "en", 0.85, "GPT-4o的简称")
add("DeepSeek-V3", ["迪普西克V3", "deepseek v3", "deep seek V3", "深度求索V3"], "AI模型", 0.90, "model", "en", 0.85, "DeepSeek 大语言模型")
add("DeepSeek-R1", ["迪普西克R1", "deepseek r1", "deep seek R1", "深度求索R1", "R1推理模型"], "AI模型", 0.90, "model", "en", 0.85, "DeepSeek 推理增强模型")
add("Qwen2.5", ["困二点五", "qwen 2 5", "千问2.5", "通义千问2.5"], "AI模型", 0.85, "model", "en", 0.80, "阿里通义千问最新版")
add("QwQ", ["困困", "Q W Q", "千问Q", "阿里推理模型"], "AI模型", 0.80, "model", "en", 0.60, "阿里推理模型")
add("Llama 4", ["拉玛四", "llama4", "羊驼4", "Meta Llama 4", "meta开源模型"], "AI模型", 0.85, "model", "en", 0.70, "Meta 最新开源大模型")
add("Mistral", ["密斯特拉尔", "mistral AI", "m斯特劳", "法国AI模型"], "AI模型", 0.85, "model", "en", 0.75, "Mistral AI 开源模型")
add("Grok", ["格绕克", "grok AI", "马斯克AI", "xAI模型", "grock"], "AI模型", 0.85, "model", "en", 0.80, "xAI 对话助手")
add("Gemini 2.5", ["杰米奈2 5", "gemini 2 5", "谷歌双子星2.5", "Gemini二点五"], "AI模型", 0.85, "model", "en", 0.75, "Google 最新多模态模型")
add("Sonnet", ["索尼特", "sonnet模型", "Claude Sonnet", "sonnet 4"], "AI模型", 0.85, "model", "en", 0.80, "Claude Sonnet 系列模型")
add("Haiku", ["海库", "haiku模型", "Claude Haiku", "hiku"], "AI模型", 0.80, "model", "en", 0.70, "Claude Haiku 系列模型")

# ─── 2. AI 开发工具/IDE ────────────────────────────────────
add("Cursor", ["科索", "cursor IDE", "cursor编程", "AI代码编辑器", "科瑟"], "AI开发工具", 0.90, "tool", "en", 0.85, "AI 驱动代码编辑器")
add("Windsurf", ["温德瑟夫", "windsurf IDE", "windsurf编程", "wind surf", "AI编辑器"], "AI开发工具", 0.80, "tool", "en", 0.70, "AI 编程 IDE")
add("Copilot", ["靠派特", "co pilot", "Github Copilot", "AI编程助手", "靠拍劳特"], "AI开发工具", 0.90, "tool", "en", 0.90, "GitHub AI 编程助手")
add("vibecoding", ["web coding", "vibe coding", "vibe编程", "wide coding", "cloud code", "AI编程", "vive coding", "webcode"], "AI开发工具", 0.85, "concept", "en", 0.75, "AI 辅助直觉式编程")
add("Bolt.new", ["波尔特纽", "bolt new", "bolt点new", "bolt 点 new", "AI全栈工具"], "AI开发工具", 0.80, "tool", "en", 0.65, "AI 全栈 Web 应用生成")
add("Lovable", ["拉乌波", "lovable dev", "AI应用构建", "拉乌伯"], "AI开发工具", 0.75, "product", "en", 0.50, "AI 全栈应用构建平台")
add("Replit Agent", ["瑞普利特agent", "replit agent", "replit 智能体", "瑞普里特"], "AI开发工具", 0.80, "tool", "en", 0.60, "Replit AI 编程智能体")
add("v0", ["V零", "V0工具", "Vercel v0", "v zero", "V零工具"], "AI开发工具", 0.80, "tool", "en", 0.55, "Vercel AI UI 生成工具")
add("Devin", ["德文", "devin AI", "AI软件工程师", "德温"], "AI开发工具", 0.80, "tool", "en", 0.65, "AI 全栈软件工程师")
add("Codeium", ["扣迪厄姆", "code ium", "AI编程", "扣迪乌姆", "windsurf原名"], "AI开发工具", 0.70, "tool", "en", 0.50, "AI 代码补全工具")

# ─── 3. 框架/库/工具 ───────────────────────────────────────
add("PyTorch", ["拍 touch", "pytouch", "拍他吃", "Python torch", "拍他尺", "拍他曲"], "AI框架", 0.95, "framework", "en", 0.90, "Meta 深度学习框架")
add("TensorFlow", ["探瑟夫劳", "tensor flow", "tenserflow", "探色夫娄", "张量流"], "AI框架", 0.90, "framework", "en", 0.85, "Google 机器学习框架")
add("JAX", ["加克斯", "jax框架", "Google JAX", "贾克斯"], "AI框架", 0.80, "framework", "en", 0.65, "Google 高性能数值计算")
add("LangChain", ["lang chain", "浪链", "浪陈", "langchain框架", "狼陈"], "AI框架", 0.90, "framework", "en", 0.85, "LLM 应用开发框架")
add("LangGraph", ["lang graph", "浪 graph", "langgraf", "浪格拉夫", "lang graph框架"], "AI框架", 0.80, "framework", "en", 0.70, "LangChain 多智能体框架")
add("LlamaIndex", ["拉玛 index", "llama index", "羊驼 index", "拉玛索引", "lang chain索引"], "AI框架", 0.85, "framework", "en", 0.75, "LLM 数据索引框架")
add("Haystack", ["黑斯戴克", "hay stack", "黑斯太克", "AI搜索框架"], "AI框架", 0.75, "framework", "en", 0.55, "开源 NLP 框架")
add("vLLM", ["V L L M", "vllm推理", "V LLM", "高并发推理"], "AI框架", 0.85, "framework", "en", 0.80, "高性能 LLM 推理引擎")
add("Ollama", ["欧拉玛", "ollama模型", "本地大模型", "ollama本地"], "AI框架", 0.90, "tool", "en", 0.85, "本地 LLM 运行工具")
add("llama.cpp", ["拉玛 cpp", "llama cpp", "羊驼 cpp", "拉玛C加加", "C加加推理"], "AI框架", 0.85, "framework", "en", 0.75, "C++ 实现的 LLM 推理")
add("Gradio", ["格瑞迪欧", "grad io", "AI演示", "guadio", "格拉丁欧"], "AI框架", 0.85, "tool", "en", 0.75, "Hugging Face 演示工具")
add("Streamlit", ["斯春里特", "stream lit", "数据应用", "streamlight", "斯创里特"], "AI框架", 0.85, "tool", "en", 0.80, "Python 数据应用框架")

# ─── 4. 向量数据库/存储 ───────────────────────────────────
add("ChromaDB", ["克罗马DB", "chroma db", "向量数据库chroma", "chrome a DB"], "向量数据库", 0.85, "database", "en", 0.75, "开源向量数据库")
add("Pinecone", ["派因扣恩", "pine cone", "pinecone数据库", "派恩空", "向量数据库pinecone"], "向量数据库", 0.85, "database", "en", 0.75, "托管向量数据库")
add("Weaviate", ["微危提", "weaviate数据库", "维危提", "waviator", "向量搜索"], "向量数据库", 0.80, "database", "en", 0.65, "开源向量搜索引擎")
add("Milvus", ["米尔乌斯", "milvus数据库", "milvos", "milvus向量", "米尔沃斯"], "向量数据库", 0.80, "database", "en", 0.70, "开源向量数据库")
add("FAISS", ["费斯", "faiss向量", "Facebook AI相似度搜索", "fais", "fai SS"], "向量数据库", 0.85, "tool", "en", 0.75, "Meta 向量相似度搜索库")
add("pgvector", ["P G vector", "pg vector", "p g向量", "PostgreSQL向量", "PG victor"], "向量数据库", 0.80, "database", "en", 0.70, "PostgreSQL 向量扩展")

# ─── 5. 关键概念/技术 ───────────────────────────────────────
add("RAG", ["拉格", "rag", "睿艾格", "RAAG", "瑞艾格", "尔艾吉", "R A G", "检索增强生成"], "AI架构", 0.95, "concept", "en", 0.90, "检索增强生成")
add("Agent", ["诶振特", "agent智能体", "AI agent", "智能体agent", "爱整体", "诶正特"], "AI架构", 0.95, "concept", "en", 0.90, "AI 智能体")
add("Multi-agent", ["玛提agent", "multi agent", "多agent", "multi-agent系统", "马尔提诶振特"], "AI架构", 0.85, "concept", "en", 0.80, "多智能体系统")
add("Fine-tuning", ["发恩提由宁", "fine tuning", "微调", "faintuning", "发恩图宁", "fine tunning"], "AI技术", 0.90, "concept", "en", 0.85, "模型微调")
add("LoRA", ["劳拉", "lora微调", "低秩适应", "lora模型", "laura"], "AI技术", 0.90, "concept", "en", 0.85, "低秩适应微调")
add("QLoRA", ["Q劳拉", "qlora微调", "Q lora", "量化lora", "库劳拉"], "AI技术", 0.85, "concept", "en", 0.75, "量化低秩适应微调")
add("RLHF", ["R L H F", "强化学习人类反馈", "rlhf训练", "人类反馈强化"], "AI技术", 0.85, "concept", "en", 0.75, "基于人类反馈的强化学习")
add("DPO", ["D P O", "dpo训练", "直接偏好优化", "迪皮欧"], "AI技术", 0.80, "concept", "en", 0.70, "直接偏好优化")
add("GRPO", ["G R P O", "grpo训练", "组相对偏好优化", "giro"], "AI技术", 0.75, "concept", "en", 0.55, "组相对策略优化")
add("MoE", ["M O E", "moe架构", "混合专家", "mix of expert", "莫一"], "AI架构", 0.85, "concept", "en", 0.75, "混合专家模型架构")
add("Quantization", ["宽提zation", "quantization量化", "模型量化", "宽提zation", "权提zation"], "AI技术", 0.85, "concept", "en", 0.75, "模型量化技术")
add("Distillation", ["迪斯提雷申", "知识蒸馏", "模型蒸馏", "distilation", "迪斯提雷训"], "AI技术", 0.80, "concept", "en", 0.70, "知识蒸馏技术")
add("Hallucination", ["哈鲁西内训", "AI幻觉", "hallucination幻觉", "模型幻觉", "哈路西奈训"], "AI概念", 0.90, "concept", "en", 0.80, "AI 幻觉")
add("Alignment", ["阿莱门特", "AI对齐", "alignment对齐", "alighnment", "阿赖门特"], "AI概念", 0.85, "concept", "en", 0.75, "AI 对齐")
add("Tokenization", ["偷肯咋训", "tokenization分词", "tokenization", "偷肯咋审"], "AI技术", 0.85, "concept", "en", 0.75, "文本分词技术")
add("Embedding", ["爱姆贝丁", "embedding向量", "词嵌入", "爱mbeding", "embedding嵌入"], "AI技术", 0.90, "concept", "en", 0.85, "向量嵌入")

# ─── 6. AI 应用/产品 ───────────────────────────────────────
add("Perplexity", ["普普莱克希提", "perplexity AI", "AI搜索", "普赖克斯提", "perplexity搜索"], "AI应用", 0.85, "product", "en", 0.80, "AI 搜索引擎")
add("Sora", ["索拉", "sora视频", "OpenAI视频生成", "sora模型"], "AI应用", 0.85, "product", "en", 0.75, "OpenAI 视频生成模型")
add("Suno", ["苏诺", "suno AI音乐", "AI音乐生成", "suno音乐"], "AI应用", 0.80, "product", "en", 0.70, "AI 音乐生成")
add("Midjourney", ["米的桌内", "mid journey", "AI绘画", "米德桌内", "米的桌内AI"], "AI应用", 0.90, "product", "en", 0.85, "AI 绘画工具")
add("Stable Diffusion", ["斯得伯迪夫优慎", "stable diffusion", "SD绘画", "stable difusion", "斯得伯尔迪夫优慎"], "AI应用", 0.90, "product", "en", 0.85, "开源文生图模型")
add("Runway", ["软威", "runway AI", "runway视频", "润威", "AI视频编辑"], "AI应用", 0.80, "product", "en", 0.65, "AI 视频生成编辑")
add("Hugging Face", ["哈金face", "hugging face", "HF模型", "哈金费斯", "AI模型社区"], "AI平台", 0.90, "platform", "en", 0.85, "AI 模型托管平台")
add("Replicate", ["瑞普里凯特", "replicate AI", "AI模型API", "瑞普利开特"], "AI平台", 0.80, "platform", "en", 0.65, "云端 AI 模型 API")
add("Together AI", ["图盖得AI", "together AI", "图盖的AI", "AI推理平台"], "AI平台", 0.80, "platform", "en", 0.65, "去中心化 AI 推理平台")
add("OpenRouter", ["欧喷绕特", "open router", "AI路由", "欧喷绕特尔", "模型路由"], "AI平台", 0.85, "platform", "en", 0.75, "多模型 API 路由平台")
add("Groq", ["格绕克", "groq AI", "groq推理", "groq芯片", "grok（注意和Grok区分）"], "AI平台", 0.80, "platform", "en", 0.70, "超快 AI 推理芯片/API")
add("LM Studio", ["L M 斯丢迪欧", "lm studio", "本地模型", "L M studio", "本地大模型工具"], "AI工具", 0.85, "tool", "en", 0.80, "本地 LLM 运行工具")

# ─── 7. 提示工程/推理 ──────────────────────────────────────
add("Prompt engineering", ["普让普特恩只你瑞", "prompt engineering", "提示工程", "prompt工程", "普让普特因镇你"], "AI技术", 0.90, "concept", "en", 0.85, "提示词工程")
add("Chain-of-thought", ["陈奥夫所特", "chain of thought", "思维链", "cot推理", "陈奥弗所特"], "AI技术", 0.90, "concept", "en", 0.85, "思维链推理")
add("Few-shot", ["飞优少特", "few shot", "少样本学习", "few shot提示"], "AI技术", 0.85, "concept", "en", 0.75, "少样本提示")
add("Zero-shot", ["贼肉少特", "zero shot", "零样本学习", "zero shot提示"], "AI技术", 0.85, "concept", "en", 0.75, "零样本提示")
add("Reasoning", ["瑞怎宁", "reasoning模型", "推理能力", "瑞森宁", "推理模型"], "AI技术", 0.85, "concept", "en", 0.80, "AI 推理能力")
add("Context window", ["康太克斯特window", "context window", "上下文窗口", "康太科斯特window", "上下文长度"], "AI概念", 0.85, "concept", "en", 0.75, "上下文窗口/长度")

# ─── 8. MCP/协议/标准 ─────────────────────────────────────
add("MCP", ["M C P", "model context protocol", "模型上下文协议", "Anthropic MCP", "mcp协议"], "AI架构", 0.85, "protocol", "en", 0.80, "模型上下文协议")
add("A2A", ["A二A", "A to A", "agent to agent", "智能体通信协议", "谷歌A2A"], "AI架构", 0.80, "protocol", "en", 0.65, "Agent-to-Agent 协议")
add("Function Calling", ["发克训calling", "function calling", "函数调用", "function call", "fangk训靠林"], "AI架构", 0.85, "concept", "en", 0.80, "大模型函数调用")
add("Tool Use", ["图尔右斯", "tool use", "工具使用", "工具调用", "toll use"], "AI架构", 0.85, "concept", "en", 0.80, "大模型工具使用")

# ─── 9. Agent 框架 ─────────────────────────────────────────
add("AutoGPT", ["奥拓G P T", "auto GPT", "自主AI智能体", "哦头GPT", "autogpt"], "Agent框架", 0.80, "framework", "en", 0.65, "自主 AI 智能体")
add("CrewAI", ["克如AI", "crew AI", "多智能体crew", "crewAI框架", "克入AI"], "Agent框架", 0.80, "framework", "en", 0.65, "多智能体协作框架")
add("LangGraph", ["浪格拉夫", "lang graph", "langgraph框架", "long graph", "郎格拉夫"], "Agent框架", 0.85, "framework", "en", 0.75, "LangChain 多智能体框架")
add("Dify", ["迪发爱", "dify AI", "低代码AI平台", "dify平台", "迪非"], "Agent框架", 0.80, "platform", "en", 0.70, "开源 LLM 应用开发平台")
add("Coze", ["扣兹", "coze AI", "字节AI平台", "扣子", "coze智能体"], "Agent框架", 0.80, "platform", "en", 0.70, "字节跳动 AI Bot 平台")
add("FastGPT", ["发斯特G P T", "fast GPT", "fastgpt", "快速GPT", "法斯特GPT"], "Agent框架", 0.75, "framework", "en", 0.55, "开源知识库问答框架")

# ─── 10. GPU/硬件 ──────────────────────────────────────────
add("A100", ["A一百", "A1百", "NVIDIA A100", "a100显卡", "a100 GPU"], "AI硬件", 0.85, "hardware", "en", 0.80, "NVIDIA A100 GPU")
add("H100", ["H一百", "H1百", "NVIDIA H100", "h100显卡", "hopper"], "AI硬件", 0.85, "hardware", "en", 0.80, "NVIDIA H100 GPU")
add("H200", ["H两百", "H2百", "NVIDIA H200", "h200显卡", "hopper 200"], "AI硬件", 0.85, "hardware", "en", 0.75, "NVIDIA H200 GPU")
add("B200", ["B两百", "B2百", "NVIDIA B200", "b200显卡", "blackwell"], "AI硬件", 0.85, "hardware", "en", 0.70, "NVIDIA B200 GPU")
add("GB200", ["G B两百", "GB200显卡", "grace blackwell", "NVIDIA GB200"], "AI硬件", 0.80, "hardware", "en", 0.55, "NVIDIA Grace Blackwell")
add("CUDA", ["酷达", "cuda编程", "NVIDIA cuda", "库达", "酷大"], "AI硬件", 0.85, "tool", "en", 0.80, "NVIDIA GPU 计算平台")
add("T4", ["T四", "T4 GPU", "nvidia T4", "特斯拉T4"], "AI硬件", 0.80, "hardware", "en", 0.65, "NVIDIA T4 GPU")
add("V100", ["V一百", "V1百", "NVIDIA V100", "v100显卡", "volt"], "AI硬件", 0.80, "hardware", "en", 0.70, "NVIDIA V100 GPU")

# ─── 11. 格式/部署/工程 ──────────────────────────────────
add("ONNX", ["昂克斯", "onnx格式", "onx", "onnx模型", "欧恩叉"], "AI工程", 0.80, "format", "en", 0.70, "开放神经网络交换格式")
add("TensorRT", ["探瑟RT", "tensor RT", "tensorrt加速", "探色RT", "NVIDIA推理优化"], "AI工程", 0.80, "tool", "en", 0.70, "NVIDIA 推理优化引擎")
add("Safetensors", ["塞夫坦瑟斯", "safe tensors", "安全张量格式", "塞夫探瑟斯"], "AI工程", 0.75, "format", "en", 0.55, "安全张量文件格式")
add("GGUF", ["G G U F", "gguf格式", "llama.cpp格式", "ggml格式"], "AI工程", 0.80, "format", "en", 0.70, "LLM 量化文件格式")
add("Docker", ["道克", "docker容器", "docker部署", "刀克", "docker容气"], "AI工程", 0.90, "tool", "en", 0.85, "容器化部署工具")
add("Kubernetes", ["库伯内提斯", "k8s", "kubernetes容器", "库伯奈茨", "库本内提斯"], "AI工程", 0.85, "tool", "en", 0.80, "容器编排平台")
add("Kafka", ["卡夫卡", "kafka消息", "消息队列kafka", "kafuka"], "AI工程", 0.85, "tool", "en", 0.75, "分布式消息系统")
add("PostgreSQL", ["珀斯特格雷SQL", "postgres", "pg数据库", "珀斯格雷斯QL", "post gre SQL"], "AI工程", 0.85, "database", "en", 0.80, "开源关系型数据库")
add("Redis", ["瑞迪斯", "redis缓存", "热迪斯", "reidis", "reddis"], "AI工程", 0.85, "database", "en", 0.80, "内存缓存数据库")
add("Nginx", ["恩晶科斯", "engine x", "niginx", "恩金克斯", "ngnix"], "AI工程", 0.80, "tool", "en", 0.75, "高性能 Web 服务器")
add("WebSocket", ["web socket", "websocket协议", "web斯卡特", "web sock it", "瓦布斯卡特"], "AI工程", 0.85, "protocol", "en", 0.80, "全双工通信协议")

# ─── 12. 中文特有问题 ──────────────────────────────────────
add("Tokenizer", ["偷肯则", "tokenizer分词", "偷kanizer", "分词器", "偷坑则子"], "AI技术", 0.85, "concept", "en", 0.75, "文本分词器")
add("Benchmark", ["本地马克", "benchmark基准", "模型评测", "搬吃马克", "评测基准"], "AI概念", 0.85, "concept", "en", 0.75, "模型评测基准")
add("Latency", ["累tency", "推理延迟", "延迟latency", "累疼西", "response time"], "AI概念", 0.80, "concept", "en", 0.70, "推理延迟")
add("Throughput", ["斯汝普特", "吞吐量", "through put", "斯入普特", "throughput性能"], "AI概念", 0.80, "concept", "en", 0.70, "模型吞吐量")

if __name__ == "__main__":
    out_path = os.path.join(os.path.dirname(__file__), "10_AI_补充术语.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ENTRIES, f, ensure_ascii=False, indent=2)
    print(f"已生成 {len(ENTRIES)} 条术语 → {out_path}")
