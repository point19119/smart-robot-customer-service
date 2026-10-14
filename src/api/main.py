# FastAPI 入口 - 扫地机器人智能售后 Agent API\
# 启动命令: cd src && uvicorn api.main:api --reload


from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from graph.app import get_graph


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


@api.post("/chat")
async def chat(request: ChatRequest):
    """
    同步对话接口
    POST /chat
    Body: {"message": "你好", "session_id": "user_001"}
    """
    if _graph_app is None:
        raise HTTPException(status_code=503, detail="服务未就绪")

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

    async def event_stream():
        yield f'data: {{"type": "open"}}\n\n'

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

        async for event in _graph_app.astream_events(state, config={"configurable": {"thread_id": session_id}}, version="v1"):
            etype = event.get("event")
            if etype == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield f'data: {{"type": "message", "content": "{content}"}}\n\n'
            elif etype == "on_chain_end":
                yield 'data: {"type": "end"}\n\n'
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000, reload=True)