import os
from dotenv import load_dotenv
from graph.app import app  # 导入我们刚写的图
from langchain_core.messages import HumanMessage

load_dotenv()
def main():
    print(" 欢迎使用扫地机器人智能售后系统 v2.0")
    print("输入 'quit' 退出对话\n")
    
    # 模拟一个固定的 Session ID (Day 8 会改成动态生成)
    session_id = "session_001"


    # 在循环外初始化持久化状态，跨轮次保留上下文
    state = {
        "session_id": session_id,
        "messages": [],
        "user_query": "",
        "current_intent": None,
        "confidence_score": 0.0,
        "is_task_interrupted": False,
        "fallback_count": 0,
        "repair_slots": {},
        "ticket_id": None,
        "ticket_status": None,
    }
    while True:
        # 获取用户输入
        user_input = input(" 您: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print(" 再见！")
            break
        
        if not user_input:
            continue

        # 只更新每轮变化的字段，其他字段保留上一轮的值
        state["user_query"] = user_input
        state["messages"].append(HumanMessage(content=user_input))
        
        
        #  运行 LangGraph 状态机
        print("\n  机器人思考中...\n")
        result = app.invoke(state)

         # 把图执行后的 state 覆盖回去，保留 repair_slots / ticket_status 等
        state = result
        
        # 提取并打印机器人的回复 (最后一条消息)
        ai_response = result["messages"][-1].content
        print(f" 机器人: {ai_response}\n")
        print("-" * 50)



if __name__ == "__main__":
    main()