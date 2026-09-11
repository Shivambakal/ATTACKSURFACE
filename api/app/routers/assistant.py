"""Assistant API Router — Interactive Cyber Intelligence Chatbot."""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.cyber_assistant_service import answer_cyber_query

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


class ChatQueryRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="The user question or intelligence query")
    conversation_history: list[dict[str, str]] | None = Field(default=None, description="Previous messages")


class ChatQueryResponse(BaseModel):
    response: str
    company: dict[str, Any] | None = None
    grounded_data: dict[str, Any] | None = None
    model: str = "AttackSurface-CyberAnalyst-v2"


@router.post("/chat", response_model=ChatQueryResponse)
def handle_assistant_chat(
    payload: ChatQueryRequest,
    session: Session = Depends(get_db),
):
    """Query the Cyber Threat Intelligence AI Assistant with grounded database facts."""
    result = answer_cyber_query(
        session=session,
        query=payload.message,
        conversation_history=payload.conversation_history,
    )
    return ChatQueryResponse(
        response=result.get("response", ""),
        company=result.get("company"),
        grounded_data=result.get("grounded_data"),
        model=result.get("model", "AttackSurface-CyberAnalyst-v2"),
    )
