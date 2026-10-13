from graph.state import AgentState
from langchain_core.messages import AIMessage

def human_fallback_node(state: AgentState):
    """人工兜底节点 """
    print("\n---  进入 [人工兜底] 节点 ---")
    # 1. 读取异常来源，生成差异化提示
    error_info = state.get("error_info", "")  # 上游节点抛出的异常标识

    if error_info == "rag_low_confidence":
        # RAG 检索结果置信度低于阈值，知识库无法给出可靠答案
        reason = "知识库中未找到与您问题相关的高置信度结果"
    elif error_info.startswith("api_call_failed"):
        # 业务接口调用异常（网络超时、服务不可用等）
        reason = "后台服务暂时无响应"
    else:
        # 兜底：意图未知、用户主动要求转人工等其它情况
        reason = "我暂时无法理解您的意思"

    # 2. 收集已积累的报修信息，传递给人工客服
    slots = state.get("repair_slots", {})  # 此前槽位收集节点已填写的信息
    info_parts = []

    if slots.get("device_model"):
        info_parts.append(f"设备型号：{slots['device_model']}")
    if slots.get("issue"):
        info_parts.append(f"故障现象：{slots['issue']}")

    # 有信息则拼接，无信息则显示“无”
    context = "\n".join(info_parts) if info_parts else "无"

    # 3. 组装最终回复
    reply = (
        f"抱歉，{reason}，已为您转接人工客服。\n\n"
        f"【已为您同步的信息】\n{context}\n\n"
        f"客服热线：400-800-1234（工作日 9:00-18:00）\n"
        f"您也可以直接拨打热线，报上工单号可加快处理。"
    )

    return {
        "messages": [AIMessage(content=reply)],
        "ticket_status": "human_transfer"
        }