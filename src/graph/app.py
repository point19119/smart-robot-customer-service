from langgraph.graph import StateGraph, END
from graph.state import AgentState, UserIntent
from graph.nodes.intent import intent_route_node
from graph.nodes.rag import rag_consult_node
from graph.nodes.repair import repair_collect_node
from graph.nodes.human import human_fallback_node

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
import os

# ==========================================
# 构建图 (Graph) - 定义数据流向
# ==========================================
        


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
        return "human_fallback"

def route_after_repair(state: AgentState):
    if state.get("ticket_status") == "created":
        return END
    elif state.get("ticket_status") == "human_transfer":
        return "human_fallback"
    else:
        return END


graph.add_conditional_edges("intent_route",route_by_intent)

graph.add_conditional_edges("repair_collect",route_after_repair)

def route_after_rag(state: AgentState):
    if state.get("ticket_status") == "human_transfer":
        return "human_fallback"
    else:
        return END

graph.add_conditional_edges("rag_consult", route_after_rag)

graph.add_edge("human_fallback",END)

@asynccontextmanager
async def get_graph():
    # 确保 db 目录存在
    _db_dir = os.path.join(os.path.dirname(__file__), '..', 'db')
    os.makedirs(_db_dir, exist_ok=True)
    _db_path = os.path.join(_db_dir, 'conversation.db')

    # from_conn_string 返回的是 async context manager，直接用 async with 接管
    async with AsyncSqliteSaver.from_conn_string(_db_path) as checkpointer:
        compiled = graph.compile(checkpointer=checkpointer)
        print(" LangGraph 初始化成功，已启用会话持久化\n")
        yield compiled

app = graph.compile()