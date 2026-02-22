"""
SQLAlchemy ORM models — all 9 tables plus schema addenda.

Addenda applied vs. schema.md v1.0:
  users:           + password_hash, + is_active
  feedback:        + given_by (FK users), + created_at
  messages:        + retrieved_doc_ids (JSON)
  canned_questions: new table
  validation_runs:  new table
"""

from __future__ import annotations

import uuid
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from policy_system.db.base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ResponseFormat(str, PyEnum):
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"
    DETAILED_RESPONSE = "DETAILED_RESPONSE"


class RoleType(str, PyEnum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    GLOBAL_AUDITOR = "GLOBAL_AUDITOR"
    DOMAIN_AUDITOR = "DOMAIN_AUDITOR"
    FUNCTIONAL = "FUNCTIONAL"


class MessageRole(str, PyEnum):
    user = "user"
    assistant = "assistant"


# ---------------------------------------------------------------------------
# 1. User & Access Management
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    default_format: Mapped[ResponseFormat] = mapped_column(
        Enum(ResponseFormat, name="response_format_enum"),
        nullable=False,
        default=ResponseFormat.EXECUTIVE_SUMMARY,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    roles: Mapped[list[UserRole]] = relationship("UserRole", back_populates="user", lazy="select")
    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation", back_populates="user", lazy="select"
    )
    uploaded_documents: Mapped[list[Document]] = relationship(
        "Document", back_populates="uploader", lazy="select"
    )
    feedback_given: Mapped[list[Feedback]] = relationship(
        "Feedback", back_populates="given_by_user", lazy="select", foreign_keys="Feedback.given_by"
    )


class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    role_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    role_type: Mapped[RoleType] = mapped_column(
        Enum(RoleType, name="role_type_enum"), nullable=False
    )
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    user_roles: Mapped[list[UserRole]] = relationship("UserRole", back_populates="role")
    document_access: Mapped[list[DocumentAccess]] = relationship(
        "DocumentAccess", back_populates="role"
    )


class UserRole(Base):
    """Join table: users ↔ roles (many-to-many)."""

    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="roles")
    role: Mapped[Role] = relationship("Role", back_populates="user_roles")


# ---------------------------------------------------------------------------
# 2. Document & RAG Metadata
# ---------------------------------------------------------------------------


class Document(Base):
    __tablename__ = "documents"

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    uploader: Mapped[User | None] = relationship("User", back_populates="uploaded_documents")
    access_roles: Mapped[list[DocumentAccess]] = relationship(
        "DocumentAccess", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentAccess(Base):
    """Join table: documents ↔ roles (which roles can see which docs)."""

    __tablename__ = "document_access"

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.doc_id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.role_id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships
    document: Mapped[Document] = relationship("Document", back_populates="access_roles")
    role: Mapped[Role] = relationship("Role", back_populates="document_access")


# ---------------------------------------------------------------------------
# 3. Interaction & Feedback
# ---------------------------------------------------------------------------


class Conversation(Base):
    __tablename__ = "conversations"

    conv_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    is_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    msg_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conv_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.conv_id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role_enum"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    format_used: Mapped[ResponseFormat] = mapped_column(
        Enum(ResponseFormat, name="response_format_enum"),
        nullable=False,
        default=ResponseFormat.EXECUTIVE_SUMMARY,
    )
    # Links response to source docs; enables citation audit
    retrieved_doc_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")
    feedback: Mapped[list[Feedback]] = relationship(
        "Feedback", back_populates="message", cascade="all, delete-orphan"
    )


class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    msg_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.msg_id", ondelete="CASCADE"),
        nullable=False,
    )
    # Who submitted this feedback (needed for auditor weight computation)
    given_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = thumbs-down, 5 = thumbs-up
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    message: Mapped[Message] = relationship("Message", back_populates="feedback")
    given_by_user: Mapped[User | None] = relationship(
        "User", back_populates="feedback_given", foreign_keys=[given_by]
    )


# ---------------------------------------------------------------------------
# 4. Automated Validation (new tables per addenda)
# ---------------------------------------------------------------------------


class CannedQuestion(Base):
    __tablename__ = "canned_questions"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    gold_answer: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    validation_runs: Mapped[list[ValidationRun]] = relationship(
        "ValidationRun", back_populates="question", cascade="all, delete-orphan"
    )


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canned_questions.question_id", ondelete="CASCADE"),
        nullable=False,
    )
    ai_answer: Mapped[str] = mapped_column(Text, nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    run_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    question: Mapped[CannedQuestion] = relationship("CannedQuestion", back_populates="validation_runs")
