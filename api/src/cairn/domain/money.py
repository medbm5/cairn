"""Integer-cent helpers."""

from collections.abc import Mapping, Sequence


def split_cents[K](
    total_cents: int, weights: Mapping[K, float], order: Sequence[K]
) -> dict[K, int]:
    """Split a whole number of cents by weights, so the parts sum exactly to the total.

    Uses the largest-remainder method; ties go to the key that comes first in `order`.
    Weights must be non-negative and not all zero.
    """
    weight_sum = sum(weights[k] for k in order)
    if weight_sum <= 0:
        raise ValueError("At least one weight must be positive.")
    sign = -1 if total_cents < 0 else 1
    magnitude = abs(total_cents)
    exact = {k: magnitude * weights[k] / weight_sum for k in order}
    parts = {k: int(exact[k]) for k in order}
    leftover = magnitude - sum(parts.values())
    by_remainder = sorted(order, key=lambda k: (-(exact[k] - parts[k]), order.index(k)))
    for k in by_remainder[:leftover]:
        parts[k] += 1
    return {k: sign * v for k, v in parts.items()}
