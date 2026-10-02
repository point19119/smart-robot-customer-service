from langgraph.graph import StateGraph, END
from .state import AgentState, UserIntent
from langchain_core.messages import HumanMessage, AIMessage

# ==========================================
# 1. 定义节点 (Node) - 机器人具体干活的地方
# ==========================================


def intent_route_node(state:AgentState):
    """
    意图识别节点 (总指挥)
    读取用户最新消息，调用判断逻辑，更新状态里的意图
    """
    print("\n---  进入 [意图识别] 节点 ---")

    #1.获取用户最后说的一句话
    last_message = state["messages"][-1].content

    #2.判断意图，调用独立的意识判断函数（获取意图枚举和给用户的回复)
    intent,reply = _keyword_fallback(last_message)

    #3.打印日志，方便调试
    print(f"意图识别：意图={intent.value},回复={reply}")

    #4.返回字典，更新状态机里的状态（current_intent 和 messages)
    return {
        "current_intent": intent,
        "messages": [AIMessage(content=reply)]
    }

def _keyword_fallback(last_message:str):
    """
    临时关键词兜底逻辑（Day 2 使用，Day 3 将被 LLM 替换）
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



def rag_consult_node(state:AgentState):
    """RAG 知识库咨询节点 (Day 3 实现)"""
    print("\n---  进入 [RAG 咨询] 节点 ---")
    reply = "[RAG 节点] 正在查询知识库... (暂未实现)"
    return {"messages": [AIMessage(content=reply)]}

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

# 【新增】条件路由
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
        return "rag_consult"

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
