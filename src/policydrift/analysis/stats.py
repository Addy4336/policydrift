"""Small, dependency-free statistics: exact McNemar, Holm, cluster bootstrap."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Hashable, Sequence


def mcnemar_one_sided(fixed: int, broke: int) -> float:
    """Exact one-sided p that discordant pairs favour a reduction: P(X >= fixed | n, 0.5)."""
    n = fixed + broke
    if n == 0:
        return 1.0
    return float(sum(math.comb(n, i) for i in range(fixed, n + 1)) / 2**n)


def mcnemar_two_sided(a: int, b: int) -> float:
    n = a + b
    if n == 0:
        return 1.0
    k = min(a, b)
    return float(min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n))


def holm(pvalues: Sequence[float]) -> list[float]:
    """Holm-adjusted p-values, in the input order."""
    order = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    adjusted = [0.0] * len(pvalues)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvalues) - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def cluster_bootstrap_ci(
    values: Sequence[float],
    clusters: Sequence[Hashable],
    *,
    resamples: int = 10_000,
    seed: int = 20261101,
) -> tuple[float, float, float]:
    """Mean of ``values`` with a 95% percentile CI from resampling whole clusters."""
    if not values:
        return math.nan, math.nan, math.nan
    by: dict[Hashable, list[float]] = defaultdict(list)
    for v, c in zip(values, clusters, strict=True):
        by[c].append(v)
    groups = list(by.values())
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(resamples):
        total = count = 0.0
        for g in (rng.choice(groups) for _ in groups):
            total += sum(g)
            count += len(g)
        means.append(total / count)
    means.sort()
    point = sum(values) / len(values)
    return point, means[int(0.025 * resamples)], means[min(resamples - 1, int(0.975 * resamples))]
