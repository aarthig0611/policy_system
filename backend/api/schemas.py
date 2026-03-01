"""
Pydantic request/response schemas for all API endpoints.

These are separate from SQLAlchemy ORM models to maintain a clean API contract.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.db.models import ResponseFormat, RoleType


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    email: str
    default_format: ResponseFormat


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    default_format: ResponseFormat = ResponseFormat.EXECUTIVE_SUMMARY


class UserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    default_format: ResponseFormat
    is_active: bool
    created_at: datetime
    roles: list[RoleResponse] = []

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    default_format: ResponseFormat | None = None
    is_active: bool | None = None


class UserSelfUpdate(BaseModel):
    default_format: ResponseFormat


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


class RoleResponse(BaseModel):
    role_id: uuid.UUID
    role_name: str
    role_type: RoleType
    domain: str | None

    model_config = {"from_attributes": True}


class RoleAssign(BaseModel):
    role_id: uuid.UUID


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    storage_uri: str = Field(min_length=1)
    role_ids: list[uuid.UUID] = Field(
        min_length=1, description="At least one role must be specified"
    )


class DocumentResponse(BaseModel):
    doc_id: uuid.UUID
    title: str
    storage_uri: str
    is_archived: bool
    uploaded_by: uuid.UUID | None
    created_at: datetime
    roles: list[RoleResponse] = []

    model_config = {"from_attributes": True}


class DocumentArchiveToggle(BaseModel):
    is_archived: bool


class DocumentAccessUpdate(BaseModel):
    role_ids: list[uuid.UUID] = Field(min_length=1)


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    format_override: ResponseFormat | None = None
    include_archived: bool = False
    domain_filter: str | None = None
    conv_id: uuid.UUID | None = None


class CitationResponse(BaseModel):
    doc_id: str
    doc_title: str
    page_number: int | None
    para_number: int | None


class QueryResponse(BaseModel):
    msg_id: uuid.UUID
    conv_id: uuid.UUID
    content: str
    format_used: ResponseFormat
    citations: list[CitationResponse] = []
    retrieved_doc_ids: list[str] = []


class ConversationResponse(BaseModel):
    conv_id: uuid.UUID
    user_id: uuid.UUID
    is_flagged: bool
    started_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    msg_id: uuid.UUID
    conv_id: uuid.UUID
    role: str
    content: str
    format_used: ResponseFormat
    created_at: datetime

    model_config = {"from_attributes": True}


class CrossDomainPrompt(BaseModel):
    """Returned when no chunks match after role filtering."""
    type: str = "cross_domain_permission_required"
    message: str
    available_domains: list[str]


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


class FeedbackCreate(BaseModel):
    msg_id: uuid.UUID
    rating: int = Field(ge=1, le=5, description="1=thumbs-down, 5=thumbs-up")
    comments: str | None = None

    @field_validator("comments")
    @classmethod
    def comment_required_for_negative(cls, v: str | None, info) -> str | None:
        rating = info.data.get("rating")
        if rating is not None and rating < 3 and not v:
            raise ValueError("Comments are required for negative feedback (rating < 3)")
        return v


class FeedbackResponse(BaseModel):
    feedback_id: uuid.UUID
    msg_id: uuid.UUID
    rating: int
    comments: str | None
    weight: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class CannedQuestionCreate(BaseModel):
    question_text: str = Field(min_length=1)
    gold_answer: str = Field(min_length=1)
    domain: str | None = None


class ValidationRunResponse(BaseModel):
    run_id: uuid.UUID
    question_id: uuid.UUID
    ai_answer: str
    similarity_score: float
    passed: bool
    model_name: str
    run_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------


class MessageResponse(BaseModel):
    message: str


class PaginatedResponse(BaseModel):
    total: int
    items: list
