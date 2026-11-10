from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AssistantQuery(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    language: Literal["en", "kn"] = "en"
    batch_id: int | None = Field(default=None, gt=0)
    state: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=100)


class AssistantSource(BaseModel):
    title: str
    kind: str
    detail: str


class AssistantResponse(BaseModel):
    answer: str
    mode: Literal["local_grounded", "openai_grounded"]
    sources: list[AssistantSource]
    suggestions: list[str]
    disclaimer: str
