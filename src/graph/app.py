from langgraph.graph import StateGraph, END
from .state import AgentState, UserIntent
from langchain_core.messages import HumanMessage, AIMessage

# ==========================================
# 1. 定义节点 (Node) - 机器人具体干活的地方
# ==========================================


def intent_route_node(state:AgentState):
    """
    意图识别节点 (Day 2 会升级为大模型识别)
    目前先用硬编码模拟，让你看到流程跑通
    """
    print("\n---  进入 [意图识别] 节点 ---")

    #获取用户最后说的一句话
    last_message = state["messages"][-1].content


    #根据最后一句话的内容，硬编码模拟意图识别
    if"报修"in last_message or"坏了"in last_message or "不转" in last_message:
        intent = UserIntent.REPAIR
        reply="收到，您是需要报修对嘛？请告诉我设备SN码和故障现象。" 
    elif"怎么"in last_message or"如何"in last_message or "说明书" in last_message:
        intent =UserIntent.CONSULT
        reply="好的，我来帮您查询相关知识库。请问您想了解什么？"
    else:
        intent =UserIntent.CHITCHAT
        reply="您好！我是扫地机器人售后助手。您可以问我关于设备维修、使用指南等问题。"


    print(f"识别结果：意图={intent.value},回复={reply}")

    # 更新状态：记录意图，并返回AI回复
    return  {
        "current_intent": intent,
        "messages":[AIMessage(content=reply)]
    }


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

# 【临时边】先全部连到兜底节点，确保能跑通
# Day 2 我们会改成 "条件路由"，根据 intent 动态选择下一个节点
graph.add_edge("intent_route", "human_fallback")
graph.add_edge("rag_consult",END)
graph.add_edge("repair_collect",END)
graph.add_edge("human_fallback",END)

app = graph.compile()
print(" LangGraph 初始化成功！\n")
