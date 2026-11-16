"""Similarity scoring helpers with no heavy dependencies.

These live outside embeddings.py on purpose: the chat service needs them on
deployments where the optional CLIP stack (torch/transformers) is not
installed, and importing embeddings.py there would drag torch in as well.
"""

from __future__ import annotations

import math
from typing import List, Sequence


def cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """Cosine similarity of two vectors. Returns 0.0 for unusable input."""
    if vec1 is None or vec2 is None:
        return 0.0
    if len(vec1) == 0 or len(vec2) == 0 or len(vec1) != len(vec2):
        return 0.0

    dot = 0.0
    norm1 = 0.0
    norm2 = 0.0
    for a, b in zip(vec1, vec2):
        dot += a * b
        norm1 += a * a
        norm2 += b * b

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (math.sqrt(norm1) * math.sqrt(norm2))


def normalize_score(raw_score: float) -> int:
    """Map a raw cosine similarity onto a human-friendly 0-100 percentage.

    CLIP similarity scores for high-dimensional vectors are naturally low.
    A score of 0.2 is a decent match, 0.35 is a very strong match.
    We map [0.18, 0.38] to [0, 100] with clipping.
    """
    try:
        raw_score = float(raw_score)
    except (TypeError, ValueError):
        return 0

    low, high = 0.18, 0.38

    if raw_score <= low:
        return 0
    if raw_score >= high:
        return 100

    # Linear interpolation.
    percentage = (raw_score - low) / (high - low) * 100
    return int(round(percentage))
