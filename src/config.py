from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── DashScope ──────────────────────────────
    dashscope_api_key: str
    dashscope_base_url: str

    # ── 模型 ───────────────────────────────────
    intent_model: str = "qwen-max"
    rag_model: str = "qwen-max"
    embedding_model: str = "text-embedding-v3"

    # ── 业务阈值 ───────────────────────────────
    rag_confidence_threshold: float = 0.6
    llm_timeout: int = 30
    llm_max_retries: int = 2

    # ── 路径 ───────────────────────────────────
    knowledge_dir: str = "data/knowledge"
    checkpoint_db: str = "checkpoints.db"


config = AppConfig()