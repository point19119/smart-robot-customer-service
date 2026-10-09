"""
售后工单服务模拟层。
真实场景下这里会调用内部工单系统的 API 来创建工单。
"""

import random
from datetime import datetime


def create_ticket(device_model, issue):

    # 模拟 20% 概率的服务异常，用于测试 human_fallback 兜底路径
    if random.random() < 0.2:
        raise ConnectionError("售后工单系统暂时不可用，请稍后重试")

    # 生成格式化工单号：TKT-YYYYMMDD-XXX
    ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{random.randint(100, 999)}"

    return {
        "ticket_id": ticket_id,
        "device_model": device_model,
        "issue": issue,
        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending",
    }