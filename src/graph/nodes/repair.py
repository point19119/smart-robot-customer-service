from graph.state import AgentState
from langchain_core.messages import AIMessage
from services.ticket_service import create_ticket
from graph.nodes._llm_extract_slots import _llm_extract_slots


def repair_collect_node(state: AgentState):
    """报修槽位收集节点 收集槽位 + 模拟创建工单(Day 4-5 实现)"""
    print("\n---  进入 [报修槽位收集] 节点 ---")

    # 1. 从 state 里取用户最新输入的 query
    last_msg = state.get("user_query") or ""
    slots = state.get("repair_slots", {})

    # 上一轮已生成工单，这一轮是新报修，清空旧状态
    if state.get("ticket_status") == "created":
        slots = {}

    reset_keywords = ["重新报修", "重新开始", "从头", "换一个", "取消"]
    if any(k in last_msg for k in reset_keywords):
        slots = {}
        return {
            "messages": [AIMessage(content="好的，重新开始报修，请提供设备型号和故障现象。")],
            "repair_slots": slots,
            "ticket_status": "collecting",
            }

    # 2 .槽位提取（Day 4 先用关键词匹配，Day 5 再用 LLM 提取）
    slots = _llm_extract_slots(last_msg, slots)

    # 3. 判断槽位是否收集完整
    #    我们定义：至少要有 device_model 和 issue 两个字段
    has_model = bool(slots.get("device_model"))
    has_issue = bool(slots.get("issue"))

    if not has_model or not has_issue:
        # --- 信息不全，进入追问（对应流程图的 L 节点）---
        missing = []
        if not has_model:
            missing.append("设备型号")
        if not has_issue:
            missing.append("故障现象")

        prompt = "收到您的报修需求。为了帮您生成工单，请补充以下信息："
        for item in missing:
            prompt += f"\n- {item}"
        prompt += "\n\n您可以这样回复：型号是 X1，故障是无法充电。"


        return {
            "messages": [AIMessage(content=prompt)],
            "repair_slots": slots,
            "ticket_status": "collecting",
        }

    # 4. 槽位齐全，模拟调用业务 API 创建工单
    try:
        ticket = create_ticket(device_model=slots["device_model"], issue=slots["issue"])
        slots["ticket_id"] = ticket["ticket_id"]

        reply = (
            f" 工单已为您成功创建！\n\n"
            f" 工单号：**{slots['ticket_id']}**\n"
            f"️ 设备型号：{slots['device_model']}\n"
            f" 故障现象：{slots['issue']}\n"
            f"️ 预计处理时间：24 小时内\n\n"
            f"售后专员将尽快与您联系，请留意短信或电话通知。"
        )

        return {
            "messages": [AIMessage(content=reply)],
            "repair_slots": slots,
            "ticket_id": slots["ticket_id"],
            "ticket_status": "created",
        }
    except Exception as e:
        print(f"[警告] 工单创建失败: {e}")
        return {
            "error_info": f"api_call_failed: {str(e)}",
            "ticket_status": "human_transfer",
        }
