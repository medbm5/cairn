"""Deterministic, human-written explanations filled with the facts.

Used when there is no OpenAI key, when the model fails or times out, and when its answer does not
pass the number guard. They follow the same rules as the model: plain words, no advice, no
promises, and only the numbers in the facts.
"""

from dataclasses import dataclass

from cairn.domain.profiles import AssetClass, RiskProfile
from cairn.domain.stress import Scenario
from cairn.explain.facts import (
    AllocationFacts,
    FactsModel,
    GlidePathFacts,
    LedgerEntryFacts,
    ProjectionFacts,
    RebalanceFacts,
    StressTestFacts,
    Topic,
)
from cairn.explain.glossary import GLOSSARY, Language

Level = str  # "simple" | "more_detail"


@dataclass(frozen=True)
class Text:
    title: str
    body: str
    analogy: str | None
    terms_used: list[str]


# --- Formatting ---


def money(cents: int, language: Language) -> str:
    euros = f"{round(cents / 100):,}"
    return f"{euros.replace(',', ' ')} €" if language == "fr" else f"€{euros}"


def percent(fraction: float, language: Language) -> str:
    value = round(fraction * 100)
    return f"{value} %" if language == "fr" else f"{value}%"


def years(months: int, language: Language) -> str:
    if months % 12 == 0:
        n = months // 12
        return (
            (f"{n} an" if n == 1 else f"{n} ans")
            if language == "fr"
            else (f"{n} year" if n == 1 else f"{n} years")
        )
    return f"{months} mois" if language == "fr" else f"{months} months"


PROFILE_NAMES: dict[RiskProfile, dict[Language, str]] = {
    RiskProfile.PRUDENT: {"en": "Prudent", "fr": "Prudent"},
    RiskProfile.MODERATE: {"en": "Moderate", "fr": "Modéré"},
    RiskProfile.BALANCED: {"en": "Balanced", "fr": "Équilibré"},
    RiskProfile.DYNAMIC: {"en": "Dynamic", "fr": "Dynamique"},
    RiskProfile.BOLD: {"en": "Bold", "fr": "Audacieux"},
}

ASSET_NAMES: dict[AssetClass, dict[Language, str]] = {
    AssetClass.GLOBAL_EQUITY: {"en": "global shares", "fr": "actions mondiales"},
    AssetClass.EMERGING_EQUITY: {"en": "emerging-market shares", "fr": "actions émergentes"},
    AssetClass.EURO_GOV_BONDS: {"en": "euro government bonds", "fr": "obligations d'État euro"},
    AssetClass.MONEY_MARKET: {"en": "money market", "fr": "monétaire"},
}

SCENARIO_NAMES: dict[Scenario, dict[Language, str]] = {
    Scenario.GFC_2008: {"en": "the 2008 financial crisis", "fr": "la crise financière de 2008"},
    Scenario.COVID_2020: {"en": "the 2020 Covid shock", "fr": "le choc du Covid en 2020"},
    Scenario.RATES_2022: {"en": "the 2022 rate shock", "fr": "le choc de taux de 2022"},
}


def _pick(language: Language, en: str, fr: str) -> str:
    return fr if language == "fr" else en


# --- Topics ---


def _projection(f: ProjectionFacts, level: Level, lang: Language) -> Text:
    title = _pick(lang, "Where your savings could land", "Où votre épargne pourrait arriver")
    body = _pick(
        lang,
        f"We played out thousands of possible markets over {years(f.horizon_months, lang)}. "
        f"In the middle scenario you would have {money(f.p50_cents, lang)}. "
        f"Your chance of reaching {money(f.target_cents, lang)} is "
        f"{percent(f.success_probability, lang)}.",
        f"Nous avons simulé des milliers de marchés possibles sur "
        f"{years(f.horizon_months, lang)}. Dans le scénario du milieu, vous auriez "
        f"{money(f.p50_cents, lang)}. Votre chance d'atteindre {money(f.target_cents, lang)} "
        f"est de {percent(f.success_probability, lang)}.",
    )
    if level == "more_detail":
        body += " " + _pick(
            lang,
            f"In a tough market you could end near {money(f.p10_cents, lang)}; in a great one, "
            f"near {money(f.p90_cents, lang)}. This assumes you add "
            f"{money(f.monthly_contribution_cents, lang)} each month with a "
            f"{PROFILE_NAMES[f.profile][lang]} profile that gets safer near the date. "
            "It is an estimate, not a promise.",
            f"Dans un marché difficile, vous pourriez finir vers {money(f.p10_cents, lang)} ; "
            f"dans un très bon, vers {money(f.p90_cents, lang)}. Cela suppose "
            f"{money(f.monthly_contribution_cents, lang)} versés chaque mois avec un profil "
            f"{PROFILE_NAMES[f.profile][lang]} qui se sécurise près de l'échéance. "
            "C'est une estimation, pas une promesse.",
        )
    return Text(title, body, None, ["monte_carlo", "median", "success_probability", "percentile"])


def _allocation(f: AllocationFacts, level: Level, lang: Language) -> Text:
    name = PROFILE_NAMES[f.profile][lang]
    ordered = sorted(f.weights.items(), key=lambda kv: -kv[1])
    parts = [f"{percent(w, lang)} {ASSET_NAMES[a][lang]}" for a, w in ordered if w > 0]
    title = _pick(lang, f"Your {name} profile", f"Votre profil {name}")
    body = _pick(
        lang,
        f"Your money would be spread as {', '.join(parts)}. "
        "Shares aim for growth; bonds and money market soften the bumps.",
        f"Votre argent serait réparti ainsi : {', '.join(parts)}. "
        "Les actions visent la croissance ; obligations et monétaire amortissent les secousses.",
    )
    if level == "more_detail":
        body += " " + _pick(
            lang,
            "Mixing families of investments that do not move together is called "
            "diversification: when one has a bad year, the others often hold up. "
            "This mix comes from your answers about time, income and how you react to falls.",
            "Mélanger des familles de placements qui ne bougent pas ensemble s'appelle la "
            "diversification : quand l'une a une mauvaise année, les autres tiennent souvent. "
            "Cette répartition vient de vos réponses sur le temps, vos revenus et vos réactions "
            "aux baisses.",
        )
    return Text(title, body, None, ["allocation", "diversification", "equity", "bond"])


def _glide_path(f: GlidePathFacts, level: Level, lang: Language) -> Text:
    title = _pick(lang, "Safer as the date gets closer", "Plus sûr à l'approche de l'échéance")
    body = _pick(
        lang,
        f"Today {percent(f.equity_share_now, lang)} of your money is in shares. As your goal "
        f"approaches, it moves step by step toward safer investments, down to "
        f"{percent(f.equity_share_at_goal, lang)} at the goal date.",
        f"Aujourd'hui, {percent(f.equity_share_now, lang)} de votre argent est en actions. À "
        f"l'approche de l'objectif, il passe peu à peu vers des placements plus sûrs, jusqu'à "
        f"{percent(f.equity_share_at_goal, lang)} à l'échéance.",
    )
    if level == "more_detail":
        body += " " + _pick(
            lang,
            f"With {years(f.years_remaining * 12, lang)} to go, there is time to recover from "
            "a bad year. Close to the date there is not, so a big fall would hurt more. "
            "Shifting gradually avoids having to sell everything at a bad moment.",
            f"Avec encore {years(f.years_remaining * 12, lang)}, il reste du temps pour se "
            "remettre d'une mauvaise année. Près de l'échéance, non : une forte baisse ferait "
            "plus mal. Avancer peu à peu évite de tout vendre au mauvais moment.",
        )
    return Text(title, body, None, ["glide_path", "time_horizon", "equity"])


def _rebalance(f: RebalanceFacts, level: Level, lang: Language) -> Text:
    title = _pick(lang, "Back to the planned mix", "Retour à la répartition prévue")
    if f.largest_drift is None:
        drift_en = (
            f"Markets moved your mix off target by more than the {percent(f.threshold, lang)}"
        )
        drift_fr = (
            f"Les marchés ont décalé votre répartition de plus des {percent(f.threshold, lang)}"
        )
        tail_en, tail_fr = " we allow.", " tolérés."
    else:
        drift_en = f"Markets moved your mix off target by up to {percent(f.largest_drift, lang)}"
        drift_fr = (
            f"Les marchés ont décalé votre répartition jusqu'à {percent(f.largest_drift, lang)}"
        )
        tail_en = f", more than the {percent(f.threshold, lang)} we allow."
        tail_fr = f", plus que les {percent(f.threshold, lang)} tolérés."
    body = _pick(
        lang,
        f"{drift_en}{tail_en} We moved {money(f.moved_cents, lang)} between investments to bring "
        "it back.",
        f"{drift_fr}{tail_fr} Nous avons déplacé {money(f.moved_cents, lang)} entre placements "
        "pour la ramener à sa cible.",
    )
    if level == "more_detail":
        body += " " + _pick(
            lang,
            "Rebalancing sells a little of what grew and buys what lagged, so your risk stays "
            "the one you chose. No money enters or leaves your goal; it only changes place, and "
            "the ledger records both sides.",
            "Rééquilibrer vend un peu de ce qui a monté et achète ce qui a pris du retard, pour "
            "que votre risque reste celui choisi. Aucun argent n'entre ni ne sort de l'objectif "
            "; il change seulement de place, et le grand livre note les deux côtés.",
        )
    return Text(title, body, None, ["rebalancing", "drift", "ledger"])


def _stress_test(f: StressTestFacts, level: Level, lang: Language) -> Text:
    scenario = SCENARIO_NAMES[f.scenario][lang]
    title = _pick(lang, f"Replaying {scenario}", f"Rejouer {scenario}")
    if f.months_to_recover is None:
        recovery = _pick(
            lang,
            "It had not fully recovered by the end of the replay.",
            "Il n'était pas revenu à son niveau à la fin de la simulation.",
        )
    else:
        recovery = _pick(
            lang,
            f"It took {f.months_to_recover} months to climb back.",
            f"Il a fallu {f.months_to_recover} mois pour remonter.",
        )
    body = _pick(
        lang,
        f"In {scenario}, your current mix would have fallen by up to "
        f"{percent(f.max_drawdown, lang)} at the worst point. {recovery}",
        f"Pendant {scenario}, votre répartition actuelle aurait baissé jusqu'à "
        f"{percent(f.max_drawdown, lang)} au pire moment. {recovery}",
    )
    if level == "more_detail":
        body += " " + _pick(
            lang,
            f"With rebalancing the worst fall was {percent(f.max_drawdown_rebalanced, lang)}. "
            "This is a simplified replay of the past, not a forecast. Falls like this are "
            "normal for investments; time is what lets them recover.",
            f"Avec rééquilibrage, la pire baisse était de "
            f"{percent(f.max_drawdown_rebalanced, lang)}. C'est une reconstitution simplifiée "
            "du passé, pas une prévision. Ces baisses font partie de l'investissement ; c'est "
            "le temps qui permet de s'en remettre.",
        )
    return Text(title, body, None, ["drawdown", "recovery", "rebalancing"])


LEDGER_KINDS: dict[str, dict[Language, str]] = {
    "deposit": {"en": "A deposit", "fr": "Un versement"},
    "fee": {"en": "A fee", "fr": "Des frais"},
    "rebalance": {"en": "A rebalance", "fr": "Un rééquilibrage"},
    "market": {"en": "A market movement", "fr": "Un mouvement de marché"},
}


def _ledger_entry(f: LedgerEntryFacts, level: Level, lang: Language) -> Text:
    kind = LEDGER_KINDS.get(f.kind, {"en": "A movement", "fr": "Un mouvement"})[lang]
    title = _pick(lang, "One line of your ledger", "Une ligne de votre grand livre")
    body = _pick(
        lang,
        f"{kind} of {money(f.amount_cents, lang)}. Every euro is written twice: once where it "
        "leaves and once where it arrives, so the two sides always cancel out.",
        f"{kind} de {money(f.amount_cents, lang)}. Chaque euro est écrit deux fois : d'où il "
        "part et où il arrive, donc les deux côtés s'annulent toujours.",
    )
    if level == "more_detail":
        body += " " + _pick(
            lang,
            f"This entry touches: {', '.join(f.accounts)}. Because every entry balances, a "
            "daily check can prove that no money appeared or vanished.",
            f"Cette écriture concerne : {', '.join(f.accounts)}. Comme chaque écriture est "
            "équilibrée, une vérification quotidienne prouve qu'aucun argent n'est apparu ni "
            "n'a disparu.",
        )
    return Text(title, body, None, ["ledger", "double_entry"])


def _term(term: str, level: Level, lang: Language) -> Text:
    entry = GLOSSARY[term]
    return Text(entry.term[lang], entry.definition[lang], entry.analogy[lang], [term])


def fallback(
    topic: Topic, facts: FactsModel | None, term: str | None, level: Level, language: Language
) -> Text:
    match topic, facts:
        case Topic.TERM, _:
            assert term is not None
            return _term(term, level, language)
        case Topic.PROJECTION, ProjectionFacts():
            text = _projection(facts, level, language)
        case Topic.ALLOCATION, AllocationFacts():
            text = _allocation(facts, level, language)
        case Topic.GLIDE_PATH, GlidePathFacts():
            text = _glide_path(facts, level, language)
        case Topic.REBALANCE, RebalanceFacts():
            text = _rebalance(facts, level, language)
        case Topic.STRESS_TEST, StressTestFacts():
            text = _stress_test(facts, level, language)
        case Topic.LEDGER_ENTRY, LedgerEntryFacts():
            text = _ledger_entry(facts, level, language)
        case _:
            raise ValueError(f"No facts of the right kind for topic '{topic}'.")
    # The topic's main glossary term supplies the everyday analogy.
    main_term = GLOSSARY[text.terms_used[0]]
    return Text(text.title, text.body, main_term.analogy[language], text.terms_used)
