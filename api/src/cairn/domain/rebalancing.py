"""Drift-based rebalancing: trade back to target weights only when an asset class drifts too far."""

from collections.abc import Mapping

from cairn.domain.money import split_cents
from cairn.domain.profiles import ASSET_CLASSES, AssetClass, Weights

DRIFT_THRESHOLD = 0.05  # 5 percentage points


def current_weights(holdings: Mapping[AssetClass, int]) -> Weights:
    total = sum(holdings.values())
    return {a: (holdings.get(a, 0) / total if total else 0.0) for a in ASSET_CLASSES}


def max_drift(holdings: Mapping[AssetClass, int], target: Weights) -> float:
    """Largest absolute gap between current and target weight, in fractions (0.05 = 5 points)."""
    if sum(holdings.values()) == 0:
        return 0.0
    weights = current_weights(holdings)
    return max(abs(weights[a] - target[a]) for a in ASSET_CLASSES)


def rebalance_transfers(
    holdings: Mapping[AssetClass, int],
    target: Weights,
    threshold: float = DRIFT_THRESHOLD,
) -> dict[AssetClass, int]:
    """Signed cents to move into (+) or out of (-) each holding. Empty when no rebalance is due.

    When due, every class goes back to its target weight; the transfers sum to zero exactly.
    """
    if max_drift(holdings, target) <= threshold:
        return {}
    desired = split_cents(sum(holdings.values()), target, ASSET_CLASSES)
    transfers = {a: desired[a] - holdings.get(a, 0) for a in ASSET_CLASSES}
    return {a: cents for a, cents in transfers.items() if cents != 0}
