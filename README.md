# 扫地机器人智能客服

基于 RAG（检索增强生成）+ Agent（智能体）架构的扫地机器人智能客服系统，使用 Streamlit 搭建前端交互界面，LangChain/LangGraph 构建 Agent 推理链路，Chroma 作为向量数据库存储知识库，通义千问（Qwen）作为大语言模型提供对话能力。

## 技术栈

- **语言**: Python 3.10+
- **Web 框架**: Streamlit
- **LLM 框架**: LangChain + LangGraph
- **向量数据库**: ChromaDB
- **大模型**: 通义千问（DashScope）
- **配置管理**: PyYAML
- **日志**: Rich

## 项目结构

```
扫地机器人智能客服/
├── agent/                    # Agent 智能体模块
│   ├── tools/                # 工具函数（天气、用户信息等）
│   │   ├── agent_tools.py    # 业务工具实现
│   │   ├── middleware.py     # 中间件（工具监控、日志）
│   │   └── react_agent.py    # ReAct 推理引擎
├── config/                   # 配置文件
│   ├── agent.yml             # Agent 配置
│   ├── chroma.yml            # ChromaDB 配置
│   ├── prompts.yml           # 提示词配置
│   └── rag.yml               # RAG 配置
├── data/                     # 原始知识库与业务数据
│   ├── external/
│   │   └── records.csv       # 模拟用户设备业务记录（报表工具读取）
│   ├── 故障排除.txt
│   ├── 扫地机器人100问.pdf
│   ├── 扫地机器人100问2.txt
│   ├── 扫拖一体机器人100问.txt
│   ├── 维护保养.txt
│   └── 选购指南.txt
├── model/                    # 模型工厂
│   └── factory.py            # 模型工厂（支持多模型切换）
├── prompts/                  # 提示词模板
│   ├── main_prompt.txt       # 主对话提示词
│   ├── rag_summarize.txt     # RAG 总结提示词
│   └── report_prompt.txt     # 报告生成提示词
├── rag/                      # RAG 服务模块
│   ├── rag_service.py        # RAG 检索增强服务
│   └── vector_store.py       # 向量存储（含 MD5 去重）
├── utils/                    # 工具函数
│   ├── config_handler.py     # 配置加载器
│   ├── file_handler.py       # 文件处理（MD5 校验等）
│   ├── logger_handler.py     # 日志处理器
│   ├── path_tool.py          # 路径工具
│   └── prompt_loader.py      # 提示词加载器
├── app.py                    # 应用入口（Streamlit UI）
├── requirements.txt          # 依赖清单
└── README.md                 # 项目说明
```

## 功能特性

- **RAG 检索增强生成**: 实现"检索 -> 上下文构建 -> 提示词组装 -> 模型生成"的完整 RAG 链路
- **ReAct Agent 推理**: 基于 LangGraph 实现 Thought -> Action -> Observation 的推理循环
- **向量知识库**: 使用 ChromaDB 存储扫地机器人相关知识，支持增量更新（MD5 去重机制）
- **配置驱动**: 通过 YAML 配置文件集中管理 Agent 参数、模型配置、提示词模板等
- **工厂模式**: 模型实例化采用抽象基类 + 工厂模式，支持轻松切换不同 LLM/Embedding 模型
- **中间件模式**: 利用 LangGraph 中间件机制实现工具调用监控、日志记录等横切关注点
- **动态提示词切换中间件**：检测报表业务场景，运行时自动切换报表专用系统Prompt
- **流式对话输出**：Web端实现打字机流式返回，保留会话对话上下文记忆


## 快速开始

### 1. 环境准备

确保已安装 Python 3.10 或更高版本。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

在项目根目录创建 `.env` 文件，填入你的通义千问 API Key：

```
DASHSCOPE_API_KEY=your_api_key_here
```

### 4. 运行应用

```bash
streamlit run app.py
```

应用将在浏览器中启动，默认地址为 `http://localhost:8501`。

## 配置说明

项目使用 YAML 配置文件管理各项参数，主要配置文件说明：

| 配置文件 | 说明 |
|---------|------|
| `config/agent.yml` | Agent 推理参数配置（最大步数、温度等） |
| `config/chroma.yml` | ChromaDB 向量数据库连接配置 |
| `config/prompts.yml` | 各场景提示词模板配置 |
| `config/rag.yml` | RAG 检索参数配置（top_k、阈值等） |

## 知识库管理

知识库文件存放在 `data/` 目录下，支持以下格式：

- **TXT 文件**: 纯文本知识库（如产品问答、故障排除指南等）
- **PDF 文件**: PDF 格式的产品手册
- **CSV 文件**: 结构化用户记录数据

系统会自动计算文件 MD5 值进行去重，新增或更新知识库文件后无需手动清理，系统会自动识别增量变化。

## 扩展开发

### 添加新的 LLM 模型

在 `model/factory.py` 中继承 `ChatModelFactory` 基类，实现新的模型工厂即可支持更多 LLM。

### 添加新的工具函数

在`agent/tools/agent_tools.py`使用`@tool`装饰器定义工具；在`react_agent.py`实例化 agent 时，将新工具加入 tools 列表。

### 替换向量数据库

修改 `rag/vector_store.py` 中的向量存储实现，可替换为 Milvus、Faiss 等其他向量数据库。

## 项目亮点

1. **模块化架构**: agent/rag/model/utils 四层分工明确，符合高内聚低耦合原则
2. **配置与代码分离**: 所有可调参数外置到 YAML 配置，便于环境切换和调优
3. **生产级设计模式**: 应用了工厂模式、中间件模式、单例模式等设计模式
4. **完整的 RAG Pipeline**: 涵盖文档加载、分块、向量化、检索、提示词组装、模型生成全流程
5. **增量更新机制**: 基于 MD5 的文件去重，支持知识库热更新
6. **LangGraph中间件高级用法**：监控工具调用、异常捕获、运行时动态切换系统提示词（报表场景）。
7. **Web会话状态管理**：完整对话上下文，流式打字机输出。


## 注意事项

- 项目中的部分工具函数（如天气查询、用户信息获取）当前使用 Mock 数据，实际部署时需替换为真实 API 调用
- 敏感配置（API Key 等）请勿直接提交到代码仓库，建议使用 `.env` 文件管理
- chroma_db 向量库、md5_hex.txt、logs 日志目录为运行产物，不会进入 git 版本；日志输出由`utils/logger_handler.py`统一管控。

## 许可证

本项目仅供学习交流使用。
