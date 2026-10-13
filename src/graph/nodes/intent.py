from graph.state import AgentState, UserIntent
from graph.nodes._llm_intent import _llm_intent_recognition

def intent_route_node(state: AgentState):
    print("\n---  进入 [意图识别] 节点 ---")

    # 如果正在报修收集中，跳过意图识别，直接回 repair_collect
    if state.get("ticket_status") == "collecting":
        print("[意图识别] 检测到报修收集中，跳过意图识别")
        return {"current_intent": UserIntent.REPAIR}

    # 只取最后一条 HumanMessage，跳过 AI 的回复
    last_message = state["user_query"]

    intent , _ = _llm_intent_recognition(last_message)

    print(f"[意图识别] 意图：{intent.value}")

    return {
        "current_intent": intent,
    }

