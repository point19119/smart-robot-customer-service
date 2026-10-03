

from enum import Enum
from typing import Annotated, List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class UserIntent(str, Enum):
    REPAIR = "repair"       #报修
    CONSULT = "consult"     #咨询/问答 
    CHITCHAT = "chitchat"       #闲聊
    HUMAN = "human"         #人工
    UNKNOWN = "unknown"       #无法识别


class AgentState(TypedDict):
    """
    LangGraph 全局状态定义
    机器人每一轮对话都会读取和更新这个状态
    """

    # --- 基础对话信息 ---
    # messages: 存储完整的对话历史 (人类提问 + AI回答)
    # add_messages 是一个 reducer，会自动把新消息追加到列表末尾，而不是覆盖
    messages: Annotated[List[BaseMessage], add_messages] 

    # --- 会话与路由状态 ---
    session_id: str  # 会话ID
    current_intent: Optional[UserIntent]  # 当前意图
    confidence_score: float # 用户意图置信度

     # --- 业务对象与槽位 (Day 4-5 会用) ---
    # focused_device: Optional[DeviceCard]   # 当前聚焦的设备卡片
    # repair_slots: Optional[RepairSlots]    # 报修收集到的槽位
    
    # --- 控制流标记 (Day 6-8 会用) ---
    is_task_interrupted: bool          # 任务是否被打断
    fallback_count: int                # 兜底/重试次数
    user_query: Optional[str]              # 用户最新输入的 query