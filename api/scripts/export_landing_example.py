"""Precompute the landing page's example goal with the real engine.

The hero must draw instantly, even while a free API instance is still waking up, so its figures
are exported once from the same simulation, glide path and ledger code the API uses, and bundled
with the web app. Run from api/:  uv run python scripts/export_landing_example.py
"""

import json
from pathlib import Path

from cairn.domain.glide_path import glide_path_for, yearly_allocations
from cairn.domain.money import split_cents
from cairn.domain.profiles import ASSET_CLASSES, RiskProfile, equity_share
from cairn.domain.simulation import simulate

OUTPUT = (
    Path(__file__).resolve().parents[2] / "web" / "src" / "features" / "landing" / "example.json"
)

PROFILE = RiskProfile.BALANCED
HORIZON_MONTHS = 180
INITIAL_CENTS = 5_000_00
TARGET_CENTS = 100_000_00
MONTHLY_STOPS = range(100_00, 700_00 + 1, 25_00)  # 100 to 700 euros a month
SAMPLE_EVERY = 6  # months
SEED = 2024


def main() -> None:
    stops = []
    for monthly in MONTHLY_STOPS:
        result = simulate(
            initial_cents=INITIAL_CENTS,
            monthly_contribution_cents=monthly,
            horizon_months=HORIZON_MONTHS,
            allocation=glide_path_for(PROFILE),
            target_cents=TARGET_CENTS,
            paths=2_000,
            seed=SEED,
        )
        pick = slice(None, None, SAMPLE_EVERY)
        stops.append(
            {
                "monthly_contribution_cents": monthly,
                "months": result.months[pick],
                **{f"p{p}": result.percentiles[p][pick] for p in (10, 25, 50, 75, 90)},
                "contributed": result.contributed[pick],
                "success_probability": result.success_probability,
            }
        )

    glide = [
        {
            "year": year,
            "equity_share": round(equity_share(weights), 4),
            "weights": {a: round(w, 4) for a, w in weights.items()},
        }
        for year, _, weights in yearly_allocations(PROFILE, HORIZON_MONTHS)
    ]

    deposit = 300_00
    split = split_cents(deposit, glide[0]["weights"], ASSET_CLASSES)  # type: ignore[arg-type]
    ledger_lines = [{"account": "external_bank", "amount_cents": -deposit}] + [
        {"account": f"holding:{a}", "amount_cents": cents} for a, cents in split.items()
    ]

    example = {
        "profile": PROFILE,
        "horizon_months": HORIZON_MONTHS,
        "initial_cents": INITIAL_CENTS,
        "target_cents": TARGET_CENTS,
        "seed": SEED,
        "stops": stops,
        "glide": glide,
        "ledger_lines": ledger_lines,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(example, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
