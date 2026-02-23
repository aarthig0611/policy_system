"""
Validation runner: runs canned questions through the query engine and scores responses.

Loads gold standards from YAML, runs each question as a user with appropriate role access,
computes similarity scores, and stores results in the validation_runs table.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.interfaces import LLMProvider, RAGProvider
from backend.core.models import CrossDomainPermissionRequired
from backend.db.models import (
    CannedQuestion,
    ResponseFormat,
    User,
    ValidationRun,
)
from backend.query.engine import run_query
from backend.validation.scorer import DEFAULT_PASS_THRESHOLD, score_answer


async def load_gold_standards(
    session: AsyncSession,
    yaml_path: str | Path | None = None,
    created_by: uuid.UUID | None = None,
) -> list[CannedQuestion]:
    """
    Load gold standard Q&A pairs from YAML and upsert into canned_questions table.

    Returns the list of CannedQuestion ORM objects.
    """
    if yaml_path is None:
        yaml_path = Path(__file__).parent / "gold_standards" / "sample_gold.yaml"

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    questions = []
    for item in data.get("questions", []):
        # Check if already exists by question_text
        existing = await session.execute(
            select(CannedQuestion).where(
                CannedQuestion.question_text == item["question_text"]
            )
        )
        cq = existing.scalar_one_or_none()

        if cq is None:
            cq = CannedQuestion(
                question_text=item["question_text"],
                gold_answer=item["gold_answer"].strip(),
                domain=item.get("domain"),
                created_by=created_by,
            )
            session.add(cq)
            await session.flush()
        else:
            # Update gold answer in case it changed
            cq.gold_answer = item["gold_answer"].strip()

        questions.append(cq)

    return questions


async def run_validation(
    session: AsyncSession,
    rag_provider: RAGProvider,
    llm_provider: LLMProvider,
    runner_user: User,
    questions: list[CannedQuestion],
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
) -> list[ValidationRun]:
    """
    Run each canned question through the query engine and record results.

    Args:
        runner_user: The user account used for queries. Should have GLOBAL_AUDITOR
                     role to bypass domain filtering for comprehensive QA.
        questions: CannedQuestion objects to run.
        pass_threshold: Minimum similarity score to count as "passed".

    Returns:
        List of ValidationRun ORM objects (already persisted).
    """
    model_name = llm_provider._chat_model if hasattr(llm_provider, "_chat_model") else "unknown"
    runs = []

    for cq in questions:
        result = await run_query(
            session=session,
            rag_provider=rag_provider,
            llm_provider=llm_provider,
            user=runner_user,
            message=cq.question_text,
            format_override=ResponseFormat.EXECUTIVE_SUMMARY,
            domain_filter=cq.domain,
        )

        if isinstance(result, CrossDomainPermissionRequired):
            ai_answer = "No documents accessible for this question."
            similarity_score = 0.0
        else:
            ai_answer = result.content
            similarity_score = score_answer(ai_answer, cq.gold_answer)

        run = ValidationRun(
            question_id=cq.question_id,
            ai_answer=ai_answer,
            similarity_score=similarity_score,
            passed=similarity_score >= pass_threshold,
            model_name=model_name,
        )
        session.add(run)
        await session.flush()
        runs.append(run)

    return runs


def print_validation_report(runs: list[ValidationRun], questions: list[CannedQuestion]) -> None:
    """Print a human-readable validation report."""
    passed = sum(1 for r in runs if r.passed)
    total = len(runs)
    avg_score = sum(r.similarity_score for r in runs) / total if total else 0.0

    print(f"\n{'='*60}")
    print(f"VALIDATION REPORT — {passed}/{total} passed ({100*passed/total:.0f}%)")
    print(f"Average similarity score: {avg_score:.3f}")
    print("=" * 60)

    for run, cq in zip(runs, questions):
        status = "✓ PASS" if run.passed else "✗ FAIL"
        print(f"\n{status} | Score={run.similarity_score:.3f} | Domain={cq.domain or 'all'}")
        print(f"  Q: {cq.question_text[:80]}")
        print(f"  AI:   {run.ai_answer[:120]}...")
        print(f"  Gold: {cq.gold_answer[:120]}...")
