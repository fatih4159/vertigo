from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AAOS - AGI Agent Operating System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/aaos.db"
    DATABASE_ECHO: bool = False

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "qwen2.5-coder:latest"
    OLLAMA_TIMEOUT: int = 120
    OLLAMA_CONNECT_TIMEOUT: float = 10.0
    OLLAMA_MAX_RETRIES: int = 3
    OLLAMA_KEEP_ALIVE: str = "5m"

    # Agent
    AGENT_MAX_ITERATIONS: int = 1000
    AGENT_ITERATION_DELAY: float = 1.0
    AGENT_MAX_TOKENS: int = 4096

    # Security
    WORKSPACE_ROOT: str = "./workspace"
    ALLOWED_DIRECTORIES: List[str] = ["./workspace", "./projects"]
    ALLOWED_SHELL_COMMANDS: List[str] = [
        "python", "pip", "npm", "node", "git",
        "pytest", "black", "ruff", "mypy",
    ]
    SECRET_KEY: str = "change-me-in-production"

    # Memory
    SHORT_TERM_MAX_ENTRIES: int = 50
    MID_TERM_MAX_ENTRIES: int = 200

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/aaos.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
