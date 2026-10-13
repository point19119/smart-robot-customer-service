import json
from config import config
from graph.state import UserIntent
from langchain_openai import ChatOpenAI
from pathlib import Path


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
    PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"
    system_prompt = (PROMPTS_DIR / "intent.txt").read_text(encoding="utf-8")

    try:
        # 1. 调用大模型

        llm = ChatOpenAI(
            model=config.intent_model,
            api_key=config.dashscope_api_key,
            base_url=config.dashscope_base_url,
            temperature=0,
)
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
