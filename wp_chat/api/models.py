# src/api/models.py - Pydantic models for request/response validation
import re
from typing import Any

from pydantic import BaseModel, Field, validator


class SearchRequest(BaseModel):
    """Search endpoint request model"""

    query: str = Field(..., min_length=1, max_length=500, description="検索クエリ")
    topk: int = Field(5, ge=1, le=20, description="返却する結果数")
    mode: str = Field("hybrid", pattern="^(dense|bm25|hybrid)$", description="検索モード")
    rerank: bool = Field(False, description="リランキング有効化")

    @validator("query")
    def sanitize_query(cls, v):  # noqa: N805
        """XSS対策: HTMLタグ除去"""
        return re.sub(r"<[^>]+>", "", v).strip()

    class Config:
        json_schema_extra = {
            "example": {"query": "VBA 文字列処理", "topk": 5, "mode": "hybrid", "rerank": True}
        }


class AskRequest(BaseModel):
    """Ask endpoint request model"""

    question: str = Field(..., min_length=1, max_length=1000, description="質問文")
    topk: int = Field(5, ge=1, le=20, description="返却する結果数")
    mode: str = Field("hybrid", pattern="^(dense|bm25|hybrid)$", description="検索モード")
    rerank: bool = Field(False, description="リランキング有効化")
    highlight: bool = Field(True, description="ハイライト有効化")
    use_morphology: bool = Field(True, description="形態素解析の使用")

    @validator("question")
    def sanitize_question(cls, v):  # noqa: N805
        """XSS対策: HTMLタグ除去"""
        return re.sub(r"<[^>]+>", "", v).strip()

    class Config:
        json_schema_extra = {
            "example": {
                "question": "VBAで文字列を処理する方法を教えて",
                "topk": 5,
                "mode": "hybrid",
                "rerank": False,
                "highlight": True,
                "use_morphology": True,
            }
        }


class GenerateRequest(BaseModel):
    """Generate endpoint request model"""

    question: str = Field(..., min_length=1, max_length=1000, description="質問文")
    topk: int = Field(5, ge=1, le=10, description="返却する結果数")
    mode: str = Field("hybrid", pattern="^(dense|bm25|hybrid)$", description="検索モード")
    rerank: bool = Field(True, description="リランキング有効化")
    stream: bool = Field(True, description="ストリーミング応答")
    user_id: str = Field("anonymous", description="ユーザーID (カナリアデプロイ用)")

    @validator("question")
    def sanitize_question(cls, v):  # noqa: N805
        """XSS対策: HTMLタグ除去"""
        return re.sub(r"<[^>]+>", "", v).strip()

    class Config:
        json_schema_extra = {
            "example": {
                "question": "VBAで文字列を処理する方法を教えて",
                "topk": 5,
                "mode": "hybrid",
                "rerank": True,
                "stream": False,
                "user_id": "user123",
            }
        }


class SearchResult(BaseModel):
    """Search result model"""

    id: int
    title: str
    url: str
    snippet: str
    score: float
    hybrid_score: float | None = None
    dense_score: float | None = None
    bm25_score: float | None = None


class SearchResponse(BaseModel):
    """Search endpoint response model"""

    results: list[SearchResult]
    total: int
    query: str
    mode: str
    took_ms: float


class Reference(BaseModel):
    """Reference model for citations"""

    id: int
    title: str
    url: str


class GenerateResponse(BaseModel):
    """Generate endpoint response model (non-streaming)"""

    answer: str
    references: list[Reference]
    metadata: dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str
    uptime_seconds: float
    timestamp: str
    version: str | None = None


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str
    message: str
    details: dict[str, Any] | None = None


# Canary management models
class CanaryRolloutRequest(BaseModel):
    """Canary rollout request model"""

    percentage: float = Field(
        ..., ge=0.0, le=1.0, description="Canary rollout percentage (0.0-1.0)"
    )


class CanaryStatusResponse(BaseModel):
    """Canary status response model"""

    enabled: bool
    percentage: float
    user_count: int
    canary_users: int
    control_users: int
