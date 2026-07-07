from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from dotenv import load_dotenv


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatabaseConfig:
    url: str
    sqlite_path: Path
    echo_sql: bool = False


@dataclass(frozen=True)
class VectorStoreConfig:
    api_key: Optional[str] = None
    index_name: Optional[str] = None


@dataclass(frozen=True)
class LlmConfig:
    api_key: Optional[str] = None
    model_name: str = "gemini-2.5-flash"


@dataclass(frozen=True)
class AppConfig:
    root_dir: Path
    database: DatabaseConfig
    vector_store: VectorStoreConfig
    genai: LlmConfig
    log_level: str = "INFO"

    @classmethod
    def load(cls) -> "AppConfig":
        root_dir = Path(__file__).resolve().parent
        load_dotenv(cls._env_path(root_dir))

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            database_path = cls._database_path(root_dir)
            database_url = f"sqlite:///{database_path}"

        return cls(
            root_dir=root_dir,
            database=DatabaseConfig(
                url=database_url,
                sqlite_path=cls._database_path(root_dir),
                echo_sql=os.getenv("DATABASE_ECHO", "0").strip().lower() in ("1", "true", "yes"),
            ),
            vector_store=VectorStoreConfig(
                api_key=os.getenv("PINECONE_API_KEY"),
                index_name=os.getenv("PINECONE_INDEX_NAME"),
            ),
            genai=LlmConfig(
                api_key=os.getenv("GEMINI_API_KEY"),
                model_name=os.getenv("GENAI_MODEL", "gemini-2.5-flash"),
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    @staticmethod
    def _database_path(root_dir: Path) -> Path:
        return root_dir / "fashion_gallery.db"

    @staticmethod
    def _env_path(root_dir: Path) -> str:
        return str(root_dir / ".env")


_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config


def reset_config_cache() -> None:
    global _config
    _config = None
