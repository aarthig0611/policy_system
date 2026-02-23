"""
Cosine similarity scorer for validation harness.

Uses sentence-transformers to compute semantic similarity between
AI answers and gold standard answers.
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Default pass threshold
DEFAULT_PASS_THRESHOLD = 0.75


@lru_cache(maxsize=1)
def _get_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    """Load the sentence transformer model (cached after first load)."""
    return SentenceTransformer(model_name)


def score_answer(
    ai_answer: str,
    gold_answer: str,
    model_name: str = "all-MiniLM-L6-v2",
) -> float:
    """
    Compute cosine similarity between the AI answer and gold standard answer.

    Returns a score between 0.0 (completely different) and 1.0 (identical semantics).
    """
    model = _get_model(model_name)
    embeddings = model.encode([ai_answer, gold_answer])
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(similarity)


def evaluate_batch(
    pairs: list[tuple[str, str]],
    threshold: float = DEFAULT_PASS_THRESHOLD,
    model_name: str = "all-MiniLM-L6-v2",
) -> list[dict]:
    """
    Score a batch of (ai_answer, gold_answer) pairs.

    Returns a list of dicts with keys: score, passed, ai_answer, gold_answer
    """
    model = _get_model(model_name)
    ai_answers = [p[0] for p in pairs]
    gold_answers = [p[1] for p in pairs]

    all_texts = ai_answers + gold_answers
    embeddings = model.encode(all_texts)

    n = len(pairs)
    results = []
    for i in range(n):
        score = float(cosine_similarity([embeddings[i]], [embeddings[n + i]])[0][0])
        results.append({
            "score": score,
            "passed": score >= threshold,
            "ai_answer": ai_answers[i],
            "gold_answer": gold_answers[i],
        })

    return results
