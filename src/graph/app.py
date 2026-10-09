from langgraph.graph import StateGraph, END
from .state import AgentState, UserIntent
from langchain_core.messages import HumanMessage, AIMessage
import os 
import json
from langchain_openai import ChatOpenAI
from  dotenv import load_dotenv
from pathlib import Path
from rag.knowledge import ask
import random
from datetime import datetime
from graph.nodes._llm_extract_slots import _llm_extract_slots
from services.ticket_service import create_ticket



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
        intent = UserIntent.UNKNOWN
        reply = "抱歉，我暂时无法理解您的意思。您可以询问设备维修、使用指南等问题，或回复[人工]转接客服。"

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
            "CONSULT": UserIntent.CONSULT,
            "HUMAN": UserIntent.HUMAN,
            "REPAIR": UserIntent.REPAIR,
        }
        intent = intent_map.get(intent_name, UserIntent.UNKNOWN)

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



def rag_consult_node(state:AgentState):
    """RAG 知识库咨询节点 (Day 3 实现)"""
    print("\n---  进入 [RAG 咨询] 节点 ---")
     # 1. 从 state 里取用户最新输入的 query
    user_question = state.get("user_query") or ""

    # 2. 调用 knowledge.py 里的 ask 函数

    answer = ask(user_question, k=3)
    # 3. 兜底处理
    if not answer or answer.strip() == "":
        answer = "抱歉，知识库中未找到相关信息，您可以换个问法试试。"

    # 4. 返回
    return {"messages": [AIMessage(content=answer)]}


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
        return END

def route_after_repair(state: AgentState):
    if state.get("ticket_status") == "created":
        return END
    elif state.get("ticket_status") == "human_transfer":
        return "human_fallback"
    else:
        return END


graph.add_conditional_edges("intent_route",route_by_intent)

graph.add_conditional_edges("repair_collect",route_after_repair)

graph.add_edge("rag_consult",END)

graph.add_edge("human_fallback",END)

app = graph.compile()
print(" LangGraph 初始化成功！\n")
