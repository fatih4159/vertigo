"""Pydantic models for Ollama API request/response shapes."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OllamaModelDetails(BaseModel):
    format: Optional[str] = None
    family: Optional[str] = None
    families: Optional[List[str]] = None
    parameter_size: Optional[str] = None
    quantization_level: Optional[str] = None


class OllamaModel(BaseModel):
    name: str
    modified_at: Optional[str] = None
    size: Optional[int] = None
    digest: Optional[str] = None
    details: Optional[OllamaModelDetails] = None


class OllamaMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str
    images: Optional[List[str]] = None  # base64-encoded for multimodal


class GenerateRequest(BaseModel):
    model: str
    prompt: str
    system: str = ""
    stream: bool = True
    options: Dict[str, Any] = Field(default_factory=dict)
    images: Optional[List[str]] = None


class GenerateResponse(BaseModel):
    model: str
    response: str
    done: bool
    context: Optional[List[int]] = None
    total_duration: Optional[int] = None
    eval_count: Optional[int] = None
    prompt_eval_count: Optional[int] = None


class ChatRequest(BaseModel):
    model: str
    messages: List[OllamaMessage]
    stream: bool = True
    format: Optional[str] = None  # "json" for structured output
    options: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    model: str
    message: OllamaMessage
    done: bool
    total_duration: Optional[int] = None
    eval_count: Optional[int] = None


class EmbeddingRequest(BaseModel):
    model: str
    prompt: str


class EmbeddingResponse(BaseModel):
    embedding: List[float]


class PullProgress(BaseModel):
    status: str
    digest: Optional[str] = None
    total: Optional[int] = None
    completed: Optional[int] = None


# Supported model families for reference
SUPPORTED_MODEL_FAMILIES = [
    "qwen2.5-coder",
    "qwen2.5",
    "deepseek-coder",
    "deepseek-r1",
    "llama3",
    "llama3.1",
    "llama3.2",
    "codellama",
    "mistral",
    "mixtral",
    "gemma2",
    "phi3",
    "phi4",
    "starcoder2",
    "granite-code",
    "nomic-embed-text",
]
