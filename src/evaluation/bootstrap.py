# -*- coding: utf-8 -*-
"""Deterministic bootstrap confidence interval helpers for VietIDP evaluation."""

from __future__ import annotations

import math
import random
from statistics import mean
from typing import Any, Callable, Iterable

DEFAULT_BOOTSTRAP_ITERATIONS = 1000
DEFAULT_CONFIDENCE = 0.95
DEFAULT_SEED = 42


def _round_metric(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _ci_payload(
    *,
    lower: float | None,
    upper: float | None,
    confidence: float,
    iterations: int,
    seed: int,
    sample_size: int,
) -> dict:
    return {
        "lower": _round_metric(lower),
        "upper": _round_metric(upper),
        "confidence": confidence,
        "iterations": iterations,
        "seed": seed,
        "sample_size": sample_size,
    }


def _percentile(sorted_values: list[float], quantile: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (len(sorted_values) - 1) * quantile
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return sorted_values[lower_index]

    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    fraction = position - lower_index
    return lower_value + (upper_value - lower_value) * fraction


def bootstrap_percentile_ci(
    values: Iterable[float],
    *,
    confidence: float = DEFAULT_CONFIDENCE,
    iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    seed: int = DEFAULT_SEED,
    statistic: Callable[[list[float]], float] | None = None,
) -> dict:
    """Return a deterministic percentile bootstrap confidence interval."""
    if iterations <= 0:
        raise ValueError("iterations must be a positive integer")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")

    sample = [float(value) for value in values]
    sample_size = len(sample)
    statistic = statistic or mean

    if sample_size == 0:
        return _ci_payload(
            lower=None,
            upper=None,
            confidence=confidence,
            iterations=iterations,
            seed=seed,
            sample_size=0,
        )

    if sample_size == 1:
        single_value = statistic(sample)
        return _ci_payload(
            lower=single_value,
            upper=single_value,
            confidence=confidence,
            iterations=iterations,
            seed=seed,
            sample_size=1,
        )

    rng = random.Random(seed)
    bootstrap_statistics = []
    for _ in range(iterations):
        resample = [sample[rng.randrange(sample_size)] for _ in range(sample_size)]
        bootstrap_statistics.append(float(statistic(resample)))

    bootstrap_statistics.sort()
    alpha = 1 - confidence
    lower = _percentile(bootstrap_statistics, alpha / 2)
    upper = _percentile(bootstrap_statistics, 1 - (alpha / 2))
    return _ci_payload(
        lower=lower,
        upper=upper,
        confidence=confidence,
        iterations=iterations,
        seed=seed,
        sample_size=sample_size,
    )


def metric_values_from_results(results: Iterable[dict[str, Any]], metric_path: str) -> list[float]:
    """Extract numeric metric values from a list of nested result dictionaries."""
    path_parts = [part for part in metric_path.split(".") if part]
    values: list[float] = []

    for result in results:
        current: Any = result
        for part in path_parts:
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
        if isinstance(current, (int, float)):
            values.append(float(current))

    return values


def bootstrap_ci_from_metric_path(
    results: Iterable[dict[str, Any]],
    metric_path: str,
    *,
    confidence: float = DEFAULT_CONFIDENCE,
    iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    seed: int = DEFAULT_SEED,
    statistic: Callable[[list[float]], float] | None = None,
) -> dict:
    """Extract numeric values by dotted path and return a deterministic CI."""
    values = metric_values_from_results(results, metric_path)
    return bootstrap_percentile_ci(
        values,
        confidence=confidence,
        iterations=iterations,
        seed=seed,
        statistic=statistic,
    )
