import os
from pathlib import Path
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv() # 加载.env

def init_vector_store():
    """
    读取知识库文件夹下的所有txt，切片后存入本地向量数据库
    """
    # 找到知识库文件夹：从 knowledge.py 向上回退两层到 src/，再进 data/knowledge/
    current_dir = Path(__file__).parent
    knowledge_dir = current_dir.parent / "data" / "knowledge"
    db_dir = current_dir.parent / "db" / "chroma_db"
    print(f"正在加载知识库目录: {knowledge_dir}")
    # 读取所有 txt 文件
    documents = []
    for file in knowledge_dir.glob("*.txt"):
        loader = TextLoader(str(file),encoding="utf-8")
        documents.extend(loader.load())

    if not documents:
        raise ValueError("没有找到任何txt文件")

    print(f"正在处理 {len(documents)} 个文件,正在切片...")
    # 文本切片
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n\n","\n",".",",","?","!","。","，","？","！"," "]
    )
    texts = text_splitter.split_documents(documents)

    embeddings = DashScopeEmbeddings(
        model="text-embedding-v3",
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
    )

    # 构建向量库
    print("正在向量化并写入数据库，首次运行可能较慢，请耐心等待...")
    vectorstore = Chroma.from_documents(
        documents=texts,
        embedding=embeddings,
        persist_directory=str(db_dir),
    )
    print("✅ 知识库向量化完成！")
    return vectorstore


def retrieve(query: str, k: int = 3):
    """从已有向量库中检索最相关的 k 条知识"""

    # 当前文件所在目录
    current_dir = Path(__file__).parent
    # 向量数据库文件夹路径
    db_dir = current_dir.parent / "db" / "chroma_db"

    # 初始化embedding模型，用来把用户query转向量
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v3",
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    )

    # 加载**已经建好、持久化保存在本地**的向量库，不是新建！
    vectorstore = Chroma(
        persist_directory=str(db_dir),
        embedding_function=embeddings,
    )
    # 相似度检索：把query转向量，在库里面找距离最近k条
    docs_with_score = vectorstore.similarity_search_with_score(query, k=k)
    return docs_with_score



llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME", "qwen3-max"),
    openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
    openai_api_base=os.getenv("DASHSCOPE_BASE_URL"),
    temperature=0,
    timeout=30,
)

def ask(question: str, k: int = 3) -> str:
    """RAG 问答入口：检索 -> 拼 prompt -> 调大模型 -> 返回答案和置信度"""
    # 1. 检索相关知识
    docs_with_score = retrieve(question, k=k)

    if not docs_with_score:
        return {"answer": "抱歉，知识库中未找到相关内容", "confidence": 0.0, "sources": []}

    # 2. 取最高相似度作为置信度
    # Chroma 的 similarity_search_with_score 返回的是余弦相似度，范围约 -1 ~ 1
    # 归一化到 0 ~ 1：(1 + score) / 2
    top_score = docs_with_score[0][1]
    confidence = max(0.0, min(1.0, (1 + top_score) / 2))

    # 3. 拼上下文
    docs = [doc for doc, _ in docs_with_score]
    context = "\n".join(doc.page_content for doc in docs)

    # 4. 拼 prompt
    prompt = f"""你是一个客服助手，请严格根据以下知识库内容回答用户问题。
如果知识库中没有相关信息，请说"抱歉，知识库中未找到相关内容"，不要编造。

知识库内容：
{context}

用户问题：{question}"""

    # 5. 调用大模型
    response = llm.invoke([{"role": "user", "content": prompt}])
    answer = response.content
    # LLM 自己说答不上来，置信度直接归零
    if not answer or "未找到" in answer or "不知道" in answer:
        confidence = 0.0
    return {"answer": answer, "confidence": round(confidence,4), "sources": docs_with_score}


if __name__ == "__main__":

    results = retrieve("迷路怎么办")
    for doc in results:
        print(doc.page_content)
        print("=" * 20)

    # 测试完整问答
    print("\n=== RAG问答测试 ===")
    answer = ask("机器人迷路了怎么办？")
    print(answer)