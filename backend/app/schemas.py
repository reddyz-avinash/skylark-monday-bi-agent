from typing import Any
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str
    intent: str
    metrics: dict[str, Any] = {}
    caveats: list[str] = []
    sources: list[str] = []
