# FastAPI 入口 - 扫地机器人智能售后 Agent API\
# 启动命令: cd src && uvicorn api.main:api --reload


from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from graph.app import get_graph
from graph.state import UserIntent
import json
from pathlib import Path
from fastapi.responses import HTMLResponse


# 全局变量：由 lifespan 在启动时初始化
_graph_app = None


class ChatRequest(BaseModel):
    """对话请求体"""
    message: str
    session_id: str = "default"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    应用生命周期管理：
    - 启动时：打开 SQLite 连接，编译带 Checkpointer 的图
    - 关闭时：自动释放数据库连接
    """
    global _graph_app
    print("[API] 正在启动服务...")
    async with get_graph() as graph_app:
        _graph_app = graph_app
        print("[API] LangGraph 状态机就绪")
        yield
        _graph_app = None
    print("[API] 服务已关闭")


api = FastAPI(
    title="Smart Robot Customer Service",
    version="2.0.0",
    lifespan=lifespan,
)


@api.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok"}



@api.get("/")
def index():
    html_path = Path(__file__).parent.parent / "static" / "index.html"
    content = html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=content)

@api.post("/chat")
async def chat(request: ChatRequest):
    """
    同步对话接口
    POST /chat
    Body: {"message": "你好", "session_id": "user_001"}
    """
    if _graph_app is None:
        raise HTTPException(status_code=503, detail="服务未就绪")

    # 1. 先拿上一轮状态
    snapshot = await _graph_app.aget_state(
        {"configurable": {"thread_id": request.session_id}}
    )
    prev = snapshot.values if snapshot else None

    # 2. 构建初始 state
    state = {
        "session_id": request.session_id,
        "messages": [HumanMessage(content=request.message)],
        "user_query": request.message,
        "current_intent": None,
        "confidence_score": 0.0,
        "is_task_interrupted": False,
        "fallback_count": 0,
        "repair_slots": {},
        "ticket_id": None,
        "ticket_status": None,
    }

    # 3. 如果上一轮正在报修收集，把状态续上
    if prev:
        if prev.get("ticket_status") == "collecting":
            state["ticket_status"] = "collecting"
            state["repair_slots"] = prev.get("repair_slots", {})
            state["current_intent"] = UserIntent.REPAIR 

    result = await _graph_app.ainvoke(state, config={"configurable": {"thread_id": request.session_id}})
    ai_response = result["messages"][-1].content

    return {
        "session_id": request.session_id,
        "response": ai_response,
        "intent": str(result.get("current_intent")),
    }


@api.get("/stream")
async def stream_chat(
    message: str = Query(...),
    session_id: str = Query("default"),
):
    """
    SSE 流式接口
    GET /stream?message=你好&session_id=user_001
    """
    if _graph_app is None:
        raise HTTPException(status_code=503, detail="服务未就绪")

    # 1. 取上一轮状态
    snapshot = await _graph_app.aget_state(
        {"configurable": {"thread_id": session_id}}
    )
    prev = snapshot.values if snapshot else None

    # 2. 初始 state
    
    state = {
        "session_id": session_id,
        "messages": [HumanMessage(content=message)],
        "user_query": message,
        "current_intent": None,
        "confidence_score": 0.0,
        "is_task_interrupted": False,
        "fallback_count": 0,
        "repair_slots": {},
        "ticket_id": None,
        "ticket_status": None,
    }

    # 3. 续报修收集状态
    if prev:
        if prev.get("ticket_status") == "collecting":
            state["ticket_status"] = "collecting"
            state["repair_slots"] = prev.get("repair_slots", {})
            state["current_intent"] = UserIntent.REPAIR
    async def event_stream():
        yield f'data: {json.dumps({"type": "open"})}\n\n'

        final_reply = None

        async for event in _graph_app.astream_events(
            state, config={"configurable": {"thread_id": session_id}},
        ):
            etype = event.get("event")
            name = event.get("name")
            node = event.get("metadata", {}).get("langgraph_node")

            # 1. 流式 token：只放行节点名包含 "rag" 的（模糊匹配，不怕改名）
            if etype == "on_chat_model_stream" and node and "rag" in node.lower():
                chunk = event["data"]["chunk"].content
                if chunk:
                    yield f"data: {json.dumps({'type': 'message', 'content': chunk})}\n\n"

            # 2. 节点结束时收集最终回复（不判断节点名，谁结束都记一下）
            elif etype == "on_chain_end":
                output = event["data"].get("output", {})
                if isinstance(output, dict):
                    messages = output.get("messages", [])
                    last_msg = messages[-1] if messages else None
                    if last_msg and hasattr(last_msg, "content") and last_msg.content:
                        final_reply = last_msg.content

        # 3. 兜底：如果流式 token 一个都没收到，把最终回复一次性发出去
        if final_reply:
            yield f"data: {json.dumps({'type': 'message', 'content': final_reply})}\n\n"

        yield 'data: {"type": "end"}\n\n'
        
    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000, reload=True)