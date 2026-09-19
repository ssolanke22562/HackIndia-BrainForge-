import os
from pathlib import Path
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "SecondSelf"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Base Workspace Root
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)

    # API Keys
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Storage Paths
    RAW_DIR_NAME: str = "raw"
    WIKI_DIR_NAME: str = "wiki"
    DB_DIR_NAME: str = "backend/db"
    VECTOR_DIR_NAME: str = "backend/db/vector_store"
    DB_FILE_NAME: str = "secondself.db"

    # Embedding & AI Parameters
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    COSINE_SIMILARITY_THRESHOLD: float = 0.70
    MAX_LINK_DEGREE: int = 5
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100

    # File Size Limits (in MegaBytes)
    MAX_FILE_SIZE_PDF_DOCX_MB: int = 25
    MAX_FILE_SIZE_AUDIO_MB: int = 50
    MAX_FILE_SIZE_IMAGE_MB: int = 15
    MAX_FILE_SIZE_CSV_TEXT_MB: int = 10

    # CORS Settings
    CORS_ORIGINS: list[str] | str = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    @property
    def cors_origins_list(self) -> list[str]:
        if isinstance(self.CORS_ORIGINS, str):
            if self.CORS_ORIGINS.strip() == "*":
                return ["*"]
            return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return self.CORS_ORIGINS

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def raw_path(self) -> Path:
        p = self.BASE_DIR / self.RAW_DIR_NAME
        p.mkdir(parents=True, exist_ok=True)
        (p / "quarantine").mkdir(parents=True, exist_ok=True)
        return p

    @property
    def wiki_path(self) -> Path:
        p = self.BASE_DIR / self.WIKI_DIR_NAME
        p.mkdir(parents=True, exist_ok=True)
        for cat in ["Projects", "Areas", "Resources", "Archives"]:
            (p / cat).mkdir(parents=True, exist_ok=True)
        return p

    @property
    def db_path(self) -> Path:
        p = self.BASE_DIR / self.DB_DIR_NAME
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def db_file_path(self) -> Path:
        return self.db_path / self.DB_FILE_NAME

    @property
    def sqlite_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_file_path.as_posix()}"

    @property
    def sync_sqlite_url(self) -> str:
        return f"sqlite:///{self.db_file_path.as_posix()}"

    @property
    def vector_path(self) -> Path:
        p = self.BASE_DIR / self.VECTOR_DIR_NAME
        p.mkdir(parents=True, exist_ok=True)
        return p

    def ensure_directories(self) -> None:
        _ = self.raw_path
        _ = self.wiki_path
        _ = self.db_path
        _ = self.vector_path

@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings

settings = get_settings()
