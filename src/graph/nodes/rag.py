from graph.state import AgentState
from rag.knowledge import ask
from config import config
from langchain_core.messages import AIMessage

def rag_consult_node(state:AgentState):
    """RAG 知识库咨询节点 (Day 3 实现)"""
    print("\n---  进入 [RAG 咨询] 节点 ---")

     # 1. 从 state 里取用户最新输入的 query
    user_question = state.get("user_query") or ""

    # 2. 调用 knowledge.py 里的 ask 函数

    result = ask(user_question, k=3)
    answer = result.get("answer", "抱歉，知识库中未找到相关内容")
    confidence = result.get("confidence", 0.0)
    print(f"[RAG] 置信度: {confidence:.2f}, 阈值: {config.rag_confidence_threshold}")

    # 3. 判断置信度是否低于阈值, 如果低于阈值，则转人工兜底
    if confidence < config.rag_confidence_threshold:
        print("[RAG] 置信度低于阈值，转人工兜底")
        return {
            "error_info": "rag_low_confidence",
            "ticket_status": "human_transfer",
        }

    # 4. 置信度正常，则返回结果
    if not answer or answer.strip() == "":
        answer = "抱歉，知识库中未找到相关信息，您可以换个问法试试。"
    return {
        "messages": [AIMessage(content=answer)],
        "ticket_status": None,
        }

