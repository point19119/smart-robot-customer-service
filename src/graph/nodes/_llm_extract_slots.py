from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv() # 加载.env
import json
import os


load_dotenv()
llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME", "qwen3-max"),
    openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
    openai_api_base=os.getenv("DASHSCOPE_BASE_URL"),
    temperature=0,
    timeout=30,
)

def _llm_extract_slots(last_msg: str, existing_slots: dict) -> dict:
    """用 LLM 从用户话语中提取报修槽位，并与已有槽位合并"""
    slots = existing_slots.copy()

    prompt = f"""你是一个报修信息提取助手。从用户输入中提取以下字段：
- device_model：设备型号（如 X1、Pro Max、S8 等）
- issue：故障现象的简要描述

用户已有信息：{existing_slots}
用户最新输入：{last_msg}

请以 JSON 格式返回，只返回 JSON，不要其他内容。示例：
{{"device_model": "X1", "issue": "无法充电"}}
如果某个字段无法提取，该字段值为 null。"""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        result = json.loads(response.content)
        if result.get("device_model"):
            slots["device_model"] = result["device_model"]
        if result.get("issue"):
            slots["issue"] = result["issue"]
    except Exception as e:
        print(f"[警告] LLM 槽位提取失败: {e}，保留已有槽位")

    return slots