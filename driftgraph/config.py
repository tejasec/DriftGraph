"""
Configuration settings for DriftGraph.
"""

from pathlib import Path
from typing import List, Optional
import os
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    provider: str = "ollama"
    model: str = "llama3.1:8b-instruct-q4_K_M"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout: int = 120


class GraphConfig(BaseModel):
    community_resolution: float = 1.0
    min_community_size: int = 2
    max_levels: int = 3
    similarity_threshold: float = 0.70


class RetrievalConfig(BaseModel):
    top_k: int = 8
    hybrid_alpha: float = 0.5


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["*"]


class EvalConfig(BaseModel):
    ragas_metrics: List[str] = ["context_precision", "faithfulness", "answer_relevance"]
    benchmark_runs: int = 3


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

    model_config = SettingsConfigDict(
        env_prefix="DRIFTGRAPH_",
        env_nested_delimiter="__",
        extra="ignore"
    )

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "Config":
        path = Path(config_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        return cls()


config = Config.load()
