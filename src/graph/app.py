from langgraph.graph import StateGraph, END
from .state import AgentState, UserIntent
from langchain_core.messages import HumanMessage, AIMessage
import os 
import json
from langchain_openai import ChatOpenAI
from  dotenv import load_dotenv
from pathlib import Path


# ==========================================
# 1. 加载环境变量 & 初始化大模型 (LLM)
# ==========================================

load_dotenv()

llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME","qwen3-max"),
    openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
    openai_api_base=os.getenv("DASHSCOPE_BASE_URL"),
    temperature=0,
)


# ==========================================
# 2. 定义核心函数
# ==========================================


def _keyword_fallback(last_message:str):
    """
    关键词兜底逻辑(Day 3 降级用，防止大模型调用失败)
    """
    if any(k in last_message for k in ["报修","坏了","故障","不转"]):
        intent = UserIntent.REPAIR
        reply="收到，您是需要报修对嘛？请告诉我设备SN码和故障现象。"
    elif any(k in last_message for k in ["怎么","如何","说明书"]):
        intent = UserIntent.CONSULT
        reply="好的，我来帮您查询相关知识库。请问您想了解什么？"
    elif any(k in last_message for k in ["人工","客服"]):
        intent = UserIntent.HUMAN
        reply="正在为您转接人工客服，请稍候..."
    else:
        intent = UserIntent.CHITCHAT
        reply="您好！我是扫地机器人售后助手。您可以问我关于设备维修、使用指南等问题。"

    return intent,reply



def _llm_intent_recognition(last_message:str):
    """
    Day 3 核心：大模型意识识别函数
    让 AI 听懂人话，并输出结构化 JSON
    """
    PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
    system_prompt = (PROMPTS_DIR / "intent.txt").read_text(encoding="utf-8")

    try:
        # 1. 调用大模型
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": last_message},
        ])

        # 2. 解析大模型返回的 JSON
        result = json.loads(response.content)
        intent_name = result["intent"]
        reply_text = result["reply"]

        # 3. 将字符串转为枚举对象
        intent_map = {
            "CHITCHAT": UserIntent.CHITCHAT,
            "CONSULT": UserIntent.CONSULT,
            "HUMAN": UserIntent.HUMAN,
            "REPAIR": UserIntent.REPAIR,
        }
        intent = intent_map.get(intent_name, UserIntent.CHITCHAT)

    except Exception as e:
         # 大模型调用失败时，降级为关键词兜底（防止系统不可用）
        print(f"[警告] 大模型调用失败: {e}，降级使用关键词兜底")
        intent, reply_text = _keyword_fallback(last_message)

    return intent, reply_text

    
# ==========================================
# 3. 定义节点 (Node)
# ==========================================

def intent_route_node(state: AgentState):
    print("\n---  进入 [意图识别] 节点 ---")

    last_message = state["messages"][-1].content

    intent, reply_text = _llm_intent_recognition(last_message)

    print(f"[意图识别] 意图：{intent.value}，回复：{reply_text}")

    return {
        "messages": [AIMessage(content=reply_text)],
        "current_intent": intent,
        "user_query": last_message,
    }
    

def rag_consult_node(state:AgentState):
    """RAG 知识库咨询节点 (Day 3 实现)"""
    print("\n---  进入 [RAG 咨询] 节点 ---")
     # 1. 从 state 里取用户最新输入的 query
    user_question = state.get("user_query") or ""

    # 2. 调用 knowledge.py 里的 ask 函数
    from rag.knowledge import ask
    answer = ask(user_question, k=3)
    # 3. 兜底处理
    if not answer or answer.strip() == "":
        answer = "抱歉，知识库中未找到相关信息，您可以换个问法试试。"

    # 4. 返回
    return {"messages": [AIMessage(content=answer)]}
def repair_collect_node(state: AgentState):
    """报修槽位收集节点 (Day 4-5 实现)"""
    print("\n---  进入 [报修收集] 节点 ---")
    reply = "[报修节点] 正在收集SN码和故障信息... (暂未实现)"
    return {"messages": [AIMessage(content=reply)]}

def human_fallback_node(state: AgentState):
    """人工兜底节点 (Day 6 实现)"""
    print("\n---  进入 [人工兜底] 节点 ---")
    reply = "抱歉，我没太理解您的问题。是否需要转接人工客服？"
    return {"messages": [AIMessage(content=reply)]}


# ==========================================
# 2. 构建图 (Graph) - 定义数据流向
# ==========================================
        

print("️  正在初始化 LangGraph 状态机...")
# 创建图实例，绑定状态类型

graph = StateGraph(AgentState)

# 将所有节点添加到图中
graph.add_node("intent_route", intent_route_node)
graph.add_node("rag_consult", rag_consult_node)
graph.add_node("repair_collect", repair_collect_node)
graph.add_node("human_fallback", human_fallback_node)

# 设置入口点：程序启动后，第一个执行的节点
graph.set_entry_point("intent_route")

# 条件路由：根据意图，选择执行节点
def route_by_intent(state:AgentState)->str:
    """根据意图，选择执行节点"""
    intent = state["current_intent"]
    if intent == UserIntent.CONSULT:
        return "rag_consult"
    elif intent == UserIntent.REPAIR:
        return "repair_collect"
    elif intent == UserIntent.HUMAN:
        return "human_fallback"
    else:
        return "__end__"

graph.add_conditional_edges(
    "intent_route",
    route_by_intent,
    {
        "rag_consult":"rag_consult",
        "repair_collect": "repair_collect",
        "human_fallback": "human_fallback"
    }
)


graph.add_edge("rag_consult",END)
graph.add_edge("repair_collect",END)
graph.add_edge("human_fallback",END)

app = graph.compile()
print(" LangGraph 初始化成功！\n")
