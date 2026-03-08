from typing import Optional, List
from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name: str
    category: str
    quantity: float = Field(ge=0)
    unit: str
    expiry_date: Optional[str] = None
    daily_usage_rate: float = Field(ge=0)
    threshold: float = Field(ge=0)


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = Field(default=None, ge=0)
    unit: Optional[str] = None
    expiry_date: Optional[str] = None
    daily_usage_rate: Optional[float] = Field(default=None, ge=0)
    threshold: Optional[float] = Field(default=None, ge=0)


class Item(ItemCreate):
    id: int
    sustainability_score: int
    created_at: str

    class Config:
        from_attributes = True


class AIResponse(BaseModel):
    days_until_reorder: Optional[int]
    reorder_date: Optional[str]
    sustainable_alternatives: List[str]
    reasoning: str
    source: str  # "ai" or "fallback"


class ScoreExplanation(BaseModel):
    explanation: str
    source: str   # "ai", "fallback", or "cached"
    cached: bool


class ParseRequest(BaseModel):
    description: str


class ParsedItem(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expiry_date: Optional[str] = None
    daily_usage_rate: Optional[float] = None
    threshold: Optional[float] = None
