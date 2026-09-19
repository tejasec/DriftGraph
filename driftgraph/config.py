"""
Configuration settings for DriftGraph.
"""

from pathlib import Path
from typing import List, Optional
import os
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class AppConfig(BaseModel):
    name: str = "DriftGraph"
    version: str = "0.1.0"
    debug: bool = True


class PathsConfig(BaseModel):
    notes_dir: str = "./data/notes"
    data_dir: str = "./data"
    exports_dir: str = "./data/exports"


class DatabaseConfig(BaseModel):
    sqlite_path: str = "./data/driftgraph.db"
    vector_index_path: str = "./data/faiss.index"


class EmbeddingConfig(BaseModel):
    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "cpu"
    batch_size: int = 32
    normalize: bool = True
    dimension: int = 384


class LLMConfig(BaseModel):
    provider: str = "ollama"  # "ollama" | "openai_compatible"
    model: str = "llama3.1:8b-instruct-q4_K_M"
    base_url: str = "http://localhost:11434/v1"
    api_key_env: str = "LLM_API_KEY"
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout: int = 120

    def get_api_key(self) -> Optional[str]:
        """Read the API key from the environment variable named in api_key_env."""
        if not self.api_key_env:
            return None
        val = os.environ.get(self.api_key_env)
        if val is not None:
            val = val.strip()
        return val or None

    def validate_provider(self) -> None:
        """Fail fast if provider is openai_compatible and the key is missing or empty."""
        if self.provider == "openai_compatible":
            key = self.get_api_key()
            if not key:
                raise ValueError(
                    f"LLM provider is configured as '{self.provider}', but the API key environment variable "
                    f"'{self.api_key_env}' is missing or empty. Please set {self.api_key_env} in your environment or .env file."
                )


class GraphConfig(BaseModel):
    community_resolution: float = 1.0
    min_community_size: int = 2
    max_levels: int = 3
    similarity_threshold: float = 0.70


class RetrievalConfig(BaseModel):
    top_k: int = 8
    hybrid_alpha: float = 0.5
    dual_level: bool = True
    dual_level_weight: float = 0.5


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["*"]


class EvalConfig(BaseModel):
    ragas_metrics: List[str] = ["context_precision", "faithfulness", "answer_relevance"]
    benchmark_runs: int = 3


class OCRConfig(BaseModel):
    engine: str = "tesseract"
    available_engines: List[str] = Field(default_factory=lambda: ["tesseract", "google_vision", "local"])
    google_vision_api_key: Optional[str] = None
    speed_mode: str = "balanced"  # fast, balanced, accurate
    psm: int = 6
    lang: str = "eng"
    dpi: int = 300
    min_confidence: float = 60.0
    error_confidence_threshold: float = 60.0
    table_detection: bool = True
    layout_preservation: bool = True
    batch_concurrency: int = 3
    cache_dir: str = "./data/ocr_cache"


class Config(BaseSettings):
    app: AppConfig = Field(default_factory=AppConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    eval: EvalConfig = Field(default_factory=EvalConfig)
    ocr: OCRConfig = Field(default_factory=OCRConfig)

    model_config = SettingsConfigDict(
        env_prefix="DRIFTGRAPH_",
        env_nested_delimiter="__",
        extra="ignore"
    )

    def validate_startup(self) -> None:
        """Validate startup preconditions (e.g. LLM provider and credentials)."""
        self.llm.validate_provider()

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "Config":
        path = Path(config_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        return cls()


config = Config.load()
