# Smart Robot Customer Service

> 基于 LangGraph + RAG + FastAPI 的智能客服机器人系统，支持意图识别、流式输出、知识库问答、故障维修指导等功能。

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 项目简介

Smart Robot Customer Service 是一个面向扫地机器人/扫拖一体机器人的智能客服系统。系统通过 LangGraph 构建 Agent 工作流，结合 RAG（检索增强生成）技术，能够自动识别用户意图，将请求路由到对应的处理节点（知识库问答、故障维修、人工对话），并以 SSE 流式方式实时返回响应，提供流畅的对话体验。

### 核心能力

| 能力 | 说明 |
|------|------|
| 意图识别 | 自动识别用户意图（知识问答 / 故障维修 / 人工），路由到对应处理节点 |
| RAG 知识库 | 基于 ChromaDB 向量数据库，支持 PDF/TXT 格式知识库文档的检索与生成 |
| 流式输出 | SSE 协议实现 token 级流式返回，前端带光标动画，首 token 延迟低 |
| 故障维修指导 | 针对扫地机器人常见故障提供排查步骤和维修建议 |
| 对话持久化 | 基于 SQLite 存储多轮对话历史，支持上下文续接 |
| 工单服务 | 内置 ticket_service，支持复杂问题转工单处理 |

---

## 技术栈

- **后端框架**：FastAPI + Uvicorn
- **Agent 框架**：LangGraph（状态机工作流）
- **LLM 调用**：LangChain / langchain-openai（兼容 OpenAI 接口的大模型）
- **向量数据库**：ChromaDB
- **对话存储**：SQLite（via SQLAlchemy / aiosqlite）
- **前端**：原生 HTML + CSS + JavaScript（SSE 客户端）

---

## 项目结构

```
src/
├── api/                  # FastAPI 路由层
│   ├── main.py           # API 入口（/health, /chat, /stream 等）
│   └── __init__.py
├── graph/                # LangGraph Agent 工作流
│   ├── app.py            # 图构建与编译入口
│   ├── state.py          # Agent 状态定义
│   ├── __init__.py
│   └── nodes/            # 工作流节点
│       ├── intent.py     # 意图识别节点 - 判断用户意图类型
│       ├── rag.py        # RAG 问答节点 - 检索知识库并生成回答
│       ├── repair.py     # 故障维修节点 - 提供维修排查指导
│       ├── human.py      # 闲聊/人工节点 - 处理非业务对话
│       ├── _llm_intent.py          # LLM 意图提取辅助
│       ├── _llm_extract_slots.py   # LLM 槽位提取辅助
│       └── __init__.py
├── rag/                  # RAG 检索模块
│   ├── knowledge.py      # 知识库加载与向量检索
│   └── __init__.py
├── services/             # 业务服务层
│   ├── ticket_service.py # 工单服务
│   └── __init__.py
├── prompts/              # 提示词模板
│   ├── intent.txt        # 意图识别提示词
│   └── __init__.py
├── data/                 # 数据目录
│   └── knowledge/        # 知识库文档
│       ├── 扫地机器人100问.pdf
│       ├── 扫地机器人100问2.txt
│       ├── 扫拖一体机器人100问.txt
│       ├── 故障排除.txt
│       ├── 维护保养.txt
│       └── 选购指南.txt
├── db/                   # 数据库（chroma、db‑shm/db‑wal为运行自动生成，git忽略）
│   ├── chroma_db/        # ChromaDB 向量数据库文件
│   ├── conversation.db   # SQLite 对话历史数据库
│   └── __init__.py
├── screenshots/          # README演示截图
│   ├── chat_interface.png
│   └── intent_demo.png
├── static/               # 静态资源
│   └── index.html        # 前端对话页面
├── config.py             # 全局配置（模型、API Key、数据库路径等）
├── main.py               # CLI入口
├── requirements.txt      # Python 依赖清单
└── .gitignore
```


---

## 快速开始

### 环境要求

- Python >= 3.11
- pip / venv

### 安装依赖

```bash
cd src
pip install -r requirements.txt
```

### 配置环境变量

在项目根目录创建 `.env` 文件，参考以下配置：

```env
# LLM 配置
LLM_MODEL_NAME=dashscope
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 数据库配置
DB_PATH=db/conversation.db
CHROMA_DB_PATH=db/chroma_db

# 服务器配置
HOST=0.0.0.0
PORT=8000
```

> **注意**：`.env` 文件已加入 `.gitignore`，请勿提交到仓库。

### 启动服务

```bash
cd src
python main.py
```

服务启动后访问：

- 对话页面：http://localhost:8000
- API 健康检查：http://localhost:8000/health

### API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| /health | GET | 服务健康检查 |
| /chat | POST | 同步对话接口 |
| /stream | GET | SSE 流式对话接口 |

---

## 工作流架构

系统基于 LangGraph 构建有向图工作流，核心流程如下：

```
用户输入
    |
    v
[Intent Node]  意图识别 - 判断用户意图类型 (rag_query / repair / human)
    |
    +-- rag_query --> [RAG Node]    检索知识库 -> LLM 生成回答
    |
    +-- repair  --> [Repair Node]   故障排查 -> 维修建议
    |
    +-- human   --> [Human Node]    通用对话
```

### 节点说明

- **Intent Node**：使用 LLM 进行意图分类，将用户输入路由到对应的处理节点
- **RAG Node**：从 ChromaDB 检索与用户问题相关的知识库片段，结合 LLM 生成准确回答
- **Repair Node**：针对扫地机器人故障场景，提供结构化的排查步骤和维修指导
- **Human Node**：处理不在知识库范围内的闲聊或通用对话

---

## 技术亮点与踩坑记录

### 技术亮点

**1. 基于 LangGraph 构建多意图路由状态机**

用 LangGraph 的 StateGraph 实现了完整的对话状态机，替代了传统的"if-else 路由"。定义了 AgentState 统一管理会话上下文（messages、session_id、intent、slots），通过 add_messages reducer 实现对话历史的自动追加，避免了手动拼接消息列表的易错问题。意图识别节点支持报修、咨询、转人工三类意图的动态分发，后续可无缝接入大模型做语义级意图理解。

**2. RAG 知识库检索 + 置信度防幻觉机制**

集成 Chroma 向量数据库实现产品手册、故障排除文档的语义检索。关键设计是在 RAG 节点后增加了检索置信度判断：当 Top-1 文档相关性得分低于阈值时，不强行让 LLM 回答，而是走人工兜底分支。这个设计有效抑制了大模型"胡编乱造"的问题，在售后场景下比"宁可错说不可错过"更安全。

**3. 报修槽位自动收集与追问闭环**

针对售后报修场景，设计了结构化的槽位收集流程（设备 SN 码、故障现象、购买时间、联系地址）。当用户输入信息不完整时，系统会自动追问缺失字段，而不是像传统聊天机器人一样直接回答或报错。槽位校验层支持正则格式验证（如 SN 码长度、手机号格式），确保录入数据的质量。


**4. 全链路日志埋点与异常降级**

每个对话轮次的关键节点（意图识别、RAG 检索、槽位收集、API 调用）都做了日志记录，包含输入输出、耗时、状态码等信息，方便后续问题排查和效果评估。同时实现了多层降级策略：LLM 调用超时自动重试、RAG 检索失败走规则回复、未知异常转人工兜底，保证系统在生产环境下的鲁棒性。

### 踩坑记录

**坑 1：LangGraph State 的 messages 字段被覆盖**

一开始定义 State 时，messages 字段用了普通的 List[BaseMessage]，结果每个节点返回新消息后，之前的对话历史全丢了——机器人变成"金鱼记忆"，每轮对话都失忆。排查了半天才发现是 LangGraph 的默认行为：节点返回的字段会直接覆盖 State 中对应的值。解决方案是用 `Annotated[List[BaseMessage], add_messages]` 告诉框架用追加策略而不是覆盖策略，这样新消息会自动追加到历史列表末尾。

**坑 2：意图识别关键词匹配的局限性**

初期用 if-elif 关键词匹配做意图路由（比如包含"坏了"→报修，包含"怎么"→咨询），跑起来简单但问题明显：用户说"我的机器怎么不走了"会被识别成咨询而不是报修，因为"怎么"在前面。后来在 prompt 里加了 few-shot 示例，让 LLM 做意图分类并输出结构化 JSON（含 intent 和 confidence），低于阈值的走兜底分支，误判率明显下降。不过这也意味着需要调大模型接口，增加了延迟。


**坑 3：向量库重复入库导致检索结果重复**

每次启动服务都会重新加载知识库文档到 Chroma，导致同一条文档出现多个副本，检索时返回重复结果。后来改成启动时检查集合中是否已有文档（通过 metadata 中的 source 字段去重），只在首次启动或文档文件有变更时才重新嵌入。这个优化让启动速度也从每次重新嵌入变快了。

**坑 4：Python 模块导入路径的坑**

把 main.py 放在 src/ 目录里面，代码里写 `from src.graph.app import app`，结果报 ModuleNotFoundError。原因是 Python 运行脚本时，会把脚本所在目录加入模块搜索路径，main.py 在 src/ 里面时 Python 从 src/ 开始找 src/graph/，当然找不到。解决方案是把 main.py 移到项目根目录（与 src/ 平级），这样 Python 从根目录开始找就能定位到 src/graph/。另外每个包目录下必须放 __init__.py 文件，否则 Python 不识别为模块。


---

## 演示截图

> 以下为项目运行截图位置，请替换为实际截图：

**图1：对话界面**

![对话界面](./screenshots/chat_interface.png)


**图2：意图识别效果**

![意图识别](./screenshots/intent_demo.png)


---


## 联系方式

- GitHub：[point19119/smart-robot-customer-service](https://github.com/point19119/smart-robot-customer-service)
- 分支：feat/enterprise-v2