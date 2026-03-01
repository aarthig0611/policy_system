"""Validation router: run the QA harness and inspect results via REST."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.providers import get_providers
from backend.api.schemas import (
    CannedQuestionResponse,
    ValidationRunResponse,
    ValidationSummary,
)
from backend.auth.dependencies import get_current_user
from backend.db.models import CannedQuestion, RoleType, User, ValidationRun
from backend.db.session import get_db_session
from backend.validation.runner import load_gold_standards, run_validation
from backend.validation.scorer import DEFAULT_PASS_THRESHOLD

router = APIRouter(prefix="/validation", tags=["validation"])


def _require_auditor_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allow SYSTEM_ADMIN or GLOBAL_AUDITOR roles only."""
    allowed = {RoleType.SYSTEM_ADMIN, RoleType.GLOBAL_AUDITOR}
    has_access = any(
        ur.role.role_type in allowed
        for ur in current_user.roles
        if ur.role is not None
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires SYSTEM_ADMIN or GLOBAL_AUDITOR role",
        )
    return current_user


@router.get("/gold", response_model=list[CannedQuestionResponse])
async def list_gold_standards(
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(_require_auditor_or_admin),
) -> list[CannedQuestionResponse]:
    """List all canned questions (gold standards) in the database."""
    result = await session.execute(
        select(CannedQuestion).order_by(CannedQuestion.created_at)
    )
    return [CannedQuestionResponse.model_validate(q) for q in result.scalars().all()]


@router.get("/runs", response_model=list[ValidationRunResponse])
async def list_validation_runs(
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(_require_auditor_or_admin),
) -> list[ValidationRunResponse]:
    """List past validation runs, most recent first."""
    result = await session.execute(
        select(ValidationRun)
        .order_by(ValidationRun.run_at.desc())
        .limit(limit)
    )
    return [ValidationRunResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/run", response_model=list[ValidationRunResponse])
async def trigger_validation_run(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(_require_auditor_or_admin),
) -> list[ValidationRunResponse]:
    """
    Run the full validation harness.

    Loads gold standards from YAML, runs each question through the query engine
    using the current user's role access, scores responses via cosine similarity,
    and stores results in the validation_runs table.

    Note: this calls Ollama for each question and may take 30–120 seconds.
    """
    rag_provider, llm_provider = get_providers()

    questions = await load_gold_standards(session, created_by=current_user.user_id)
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No gold standards found. Check validation/gold_standards/sample_gold.yaml.",
        )

    runs = await run_validation(
        session=session,
        rag_provider=rag_provider,
        llm_provider=llm_provider,
        runner_user=current_user,
        questions=questions,
        pass_threshold=DEFAULT_PASS_THRESHOLD,
    )

    return [ValidationRunResponse.model_validate(r) for r in runs]


@router.get("/run/summary", response_model=ValidationSummary)
async def latest_run_summary(
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(_require_auditor_or_admin),
) -> ValidationSummary:
    """
    Summarise the most recent validation run (latest run_at batch).

    Returns pass rate and average similarity score across all questions
    from the most recent batch of runs.
    """
    # Find the most recent run_at timestamp
    latest_result = await session.execute(
        select(ValidationRun.run_at).order_by(ValidationRun.run_at.desc()).limit(1)
    )
    latest_run_at = latest_result.scalar_one_or_none()
    if latest_run_at is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No validation runs found. POST /validation/run to start one.",
        )

    # Fetch all runs from that batch (same second — close enough for grouping)
    from sqlalchemy import func
    result = await session.execute(
        select(ValidationRun).where(
            func.date_trunc("second", ValidationRun.run_at)
            == func.date_trunc("second", latest_run_at)
            if hasattr(func, "date_trunc")
            else ValidationRun.run_at == latest_run_at
        )
    )
    runs = result.scalars().all()

    if not runs:
        runs_result = await session.execute(
            select(ValidationRun).order_by(ValidationRun.run_at.desc()).limit(20)
        )
        runs = runs_result.scalars().all()

    total = len(runs)
    passed = sum(1 for r in runs if r.passed)
    avg_score = sum(r.similarity_score for r in runs) / total if total else 0.0

    return ValidationSummary(
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=round(passed / total, 3) if total else 0.0,
        avg_score=round(avg_score, 3),
    )
