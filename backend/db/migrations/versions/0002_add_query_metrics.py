"""Add query_metrics table

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-07
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "query_metrics",
        sa.Column("metric_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "msg_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.msg_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("embed_latency_ms", sa.Float(), nullable=False),
        sa.Column("retrieve_latency_ms", sa.Float(), nullable=False),
        sa.Column("llm_latency_ms", sa.Float(), nullable=True),
        sa.Column("total_latency_ms", sa.Float(), nullable=False),
        sa.Column("chunks_retrieved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_type", sa.String(100), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_query_metrics_msg_id", "query_metrics", ["msg_id"])
    op.create_index("ix_query_metrics_user_id", "query_metrics", ["user_id"])
    op.create_index("ix_query_metrics_created_at", "query_metrics", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_query_metrics_created_at", table_name="query_metrics")
    op.drop_index("ix_query_metrics_user_id", table_name="query_metrics")
    op.drop_index("ix_query_metrics_msg_id", table_name="query_metrics")
    op.drop_table("query_metrics")
