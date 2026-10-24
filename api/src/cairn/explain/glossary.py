"""Curated, human-written glossary in plain English and French.

It grounds the language model and is the fallback when the model is not used. Entries contain no
digits on purpose, so they never introduce numbers that are not in the facts.
"""

from dataclasses import dataclass
from typing import Literal

Language = Literal["en", "fr"]


@dataclass(frozen=True)
class Entry:
    term: dict[Language, str]
    definition: dict[Language, str]
    analogy: dict[Language, str]


def _e(term_en: str, term_fr: str, def_en: str, def_fr: str, an_en: str, an_fr: str) -> Entry:
    return Entry(
        {"en": term_en, "fr": term_fr}, {"en": def_en, "fr": def_fr}, {"en": an_en, "fr": an_fr}
    )


GLOSSARY: dict[str, Entry] = {
    "volatility": _e(
        "Volatility",
        "Volatilité",
        "How much an investment's value moves up and down. High volatility means bigger swings, "
        "in both directions.",
        "L'ampleur des hausses et des baisses d'un placement. Une forte volatilité veut dire de "
        "plus grands écarts, dans les deux sens.",
        "Like the weather in spring: some days are much warmer or colder than the average.",
        "Comme la météo au printemps : certains jours sont bien plus chauds ou froids que la "
        "moyenne.",
    ),
    "diversification": _e(
        "Diversification",
        "Diversification",
        "Spreading money across many different investments, so one bad result does not sink the "
        "whole plan.",
        "Répartir son argent sur de nombreux placements différents, pour qu'un mauvais résultat "
        "ne coule pas tout le projet.",
        "Not putting all your eggs in one basket.",
        "Ne pas mettre tous ses œufs dans le même panier.",
    ),
    "etf": _e(
        "ETF",
        "ETF",
        "An exchange-traded fund: one product that holds a whole basket of shares or bonds and "
        "can be bought like a single share.",
        "Un fonds coté en bourse : un seul produit qui contient tout un panier d'actions ou "
        "d'obligations et s'achète comme une action.",
        "Like buying a ready-made fruit basket instead of choosing each fruit.",
        "Comme acheter une corbeille de fruits toute prête plutôt que choisir chaque fruit.",
    ),
    "equity": _e(
        "Shares",
        "Actions",
        "A small piece of ownership in a company. Shares tend to grow more over long periods but "
        "can fall sharply along the way.",
        "Une petite part de propriété d'une entreprise. Les actions progressent souvent plus sur "
        "longue période, mais peuvent chuter fortement en route.",
        "Owning a slice of a bakery: you share in its good and bad years.",
        "Posséder une part d'une boulangerie : vous partagez ses bonnes et ses mauvaises années.",
    ),
    "emerging_markets": _e(
        "Emerging markets",
        "Marchés émergents",
        "Countries whose economies are growing fast, such as India or Brazil. Their shares can "
        "grow more but swing harder.",
        "Des pays dont l'économie croît vite, comme l'Inde ou le Brésil. Leurs actions peuvent "
        "progresser davantage, mais varient plus fortement.",
        "A young tree: it grows quickly but bends more in the wind.",
        "Un jeune arbre : il pousse vite mais plie davantage sous le vent.",
    ),
    "bond": _e(
        "Bond",
        "Obligation",
        "A loan you make to a government or company, which pays you interest and gives the money "
        "back at a set date.",
        "Un prêt que vous faites à un État ou une entreprise, qui vous verse des intérêts et vous "
        "rembourse à une date fixée.",
        "Lending money to a friend who pays you a little extra each year for your patience.",
        "Prêter de l'argent à un ami qui vous donne un petit supplément chaque année pour votre "
        "patience.",
    ),
    "money_market": _e(
        "Money market",
        "Monétaire",
        "Very short, very safe loans. The value barely moves, and the return is small.",
        "Des prêts très courts et très sûrs. La valeur bouge à peine et le rendement est faible.",
        "A savings jar: safe and steady, but it will not grow much.",
        "Une tirelire : sûre et stable, mais elle ne grossira pas beaucoup.",
    ),
    "asset_class": _e(
        "Asset class",
        "Classe d'actifs",
        "A family of investments that behave in a similar way, such as shares, bonds or cash.",
        "Une famille de placements qui se comportent de façon proche, comme les actions, les "
        "obligations ou les liquidités.",
        "Like food groups in a balanced meal.",
        "Comme les groupes d'aliments dans un repas équilibré.",
    ),
    "allocation": _e(
        "Allocation",
        "Allocation",
        "How your money is split between the different asset classes.",
        "La façon dont votre argent est réparti entre les différentes classes d'actifs.",
        "The recipe that says how much of each ingredient goes in the cake.",
        "La recette qui dit quelle quantité de chaque ingrédient va dans le gâteau.",
    ),
    "risk_profile": _e(
        "Risk profile",
        "Profil de risque",
        "A summary of how much ups and downs you can live with, based on your answers, your goal "
        "and your time horizon.",
        "Un résumé des hauts et des bas que vous pouvez supporter, d'après vos réponses, votre "
        "objectif et votre horizon.",
        "Choosing between a calm lake and a lively river for a canoe trip.",
        "Choisir entre un lac calme et une rivière agitée pour une sortie en canoë.",
    ),
    "time_horizon": _e(
        "Time horizon",
        "Horizon de placement",
        "How long until you need the money. A longer horizon gives more time to recover from "
        "bad years.",
        "Le temps qui reste avant d'avoir besoin de l'argent. Un horizon long laisse plus de "
        "temps pour se remettre des mauvaises années.",
        "A long journey leaves time to make up for a slow stretch of road.",
        "Un long voyage laisse le temps de rattraper un passage lent.",
    ),
    "compound_growth": _e(
        "Compound growth",
        "Intérêts composés",
        "Growth on top of growth: the gains you made start earning gains of their own.",
        "La croissance sur la croissance : les gains déjà obtenus rapportent à leur tour.",
        "A snowball rolling downhill picks up more snow the bigger it gets.",
        "Une boule de neige qui roule grossit d'autant plus vite qu'elle est déjà grosse.",
    ),
    "inflation": _e(
        "Inflation",
        "Inflation",
        "Prices rising over time, so the same amount of money buys a little less each year.",
        "La hausse des prix dans le temps : la même somme achète un peu moins chaque année.",
        "A slow leak in a bike tyre: hardly visible day to day, clear over years.",
        "Une petite fuite dans un pneu de vélo : invisible au jour le jour, nette sur des années.",
    ),
    "percentile": _e(
        "Percentile",
        "Percentile",
        "A way to rank possible outcomes. A low percentile is a tough-market result that only a "
        "small share of scenarios fall below.",
        "Une façon de classer les résultats possibles. Un percentile bas correspond à un marché "
        "difficile, que peu de scénarios font pire.",
        "Lining up all the possible futures from worst to best and picking one spot in the line.",
        "Aligner tous les futurs possibles du pire au meilleur et choisir une place dans la file.",
    ),
    "median": _e(
        "Median",
        "Médiane",
        "The middle scenario: half the simulated outcomes end higher, half end lower.",
        "Le scénario du milieu : la moitié des résultats simulés finit plus haut, l'autre moitié "
        "plus bas.",
        "The person standing in the middle of a queue sorted by height.",
        "La personne au milieu d'une file rangée par taille.",
    ),
    "monte_carlo": _e(
        "Simulation",
        "Simulation",
        "Playing out thousands of possible futures for the markets, to see the range of where "
        "your savings could land.",
        "Jouer des milliers de futurs possibles pour les marchés, pour voir où votre épargne "
        "pourrait arriver.",
        "Rolling the dice many times to learn which results are common and which are rare.",
        "Lancer les dés de nombreuses fois pour voir quels résultats sont fréquents ou rares.",
    ),
    "success_probability": _e(
        "Chance of reaching the goal",
        "Chance d'atteindre l'objectif",
        "The share of simulated futures in which your savings end at or above the target. It is "
        "an estimate, not a promise.",
        "La part des futurs simulés où votre épargne atteint ou dépasse la cible. C'est une "
        "estimation, pas une promesse.",
        "A weather forecast that says how often it rained on days like this one.",
        "Une prévision météo qui dit combien de fois il a plu lors de journées semblables.",
    ),
    "glide_path": _e(
        "Glide path",
        "Trajectoire de sécurisation",
        "A plan that moves money gradually from shares to safer investments as the goal date "
        "gets closer.",
        "Un plan qui déplace peu à peu l'argent des actions vers des placements plus sûrs à "
        "l'approche de l'objectif.",
        "A plane slowing down and descending gently before landing.",
        "Un avion qui ralentit et descend doucement avant l'atterrissage.",
    ),
    "rebalancing": _e(
        "Rebalancing",
        "Rééquilibrage",
        "Moving money between investments to bring the mix back to its target after markets "
        "have pushed it off course.",
        "Déplacer de l'argent entre placements pour ramener la répartition à sa cible quand les "
        "marchés l'ont décalée.",
        "Trimming a hedge that has grown unevenly, so it keeps its shape.",
        "Tailler une haie qui a poussé de travers, pour qu'elle garde sa forme.",
    ),
    "drift": _e(
        "Drift",
        "Dérive",
        "How far the current mix has moved from its target because some investments grew faster "
        "than others.",
        "L'écart entre la répartition actuelle et sa cible, parce que certains placements ont "
        "progressé plus vite que d'autres.",
        "A boat slowly pushed off course by the current.",
        "Un bateau poussé peu à peu hors de sa route par le courant.",
    ),
    "drawdown": _e(
        "Drawdown",
        "Baisse maximale",
        "The fall from a high point to the lowest point that follows it, before values recover.",
        "La chute entre un point haut et le point le plus bas qui le suit, avant que la valeur "
        "ne remonte.",
        "The depth of a valley between two hills on a walk.",
        "La profondeur d'une vallée entre deux collines pendant une randonnée.",
    ),
    "recovery": _e(
        "Recovery",
        "Reprise",
        "The time it takes for an investment to climb back to where it was before a fall.",
        "Le temps qu'il faut à un placement pour revenir à son niveau d'avant la chute.",
        "Climbing back up the other side of the valley.",
        "Remonter l'autre versant de la vallée.",
    ),
    "interest_rates": _e(
        "Interest rates",
        "Taux d'intérêt",
        "The price of borrowing money. When rates rise quickly, existing bonds lose value.",
        "Le prix de l'emprunt. Quand les taux montent vite, les obligations existantes perdent "
        "de la valeur.",
        "When new savings accounts pay more, an old one paying less looks less attractive.",
        "Quand les nouveaux livrets rapportent plus, un ancien qui rapporte moins attire moins.",
    ),
    "ledger": _e(
        "Ledger",
        "Grand livre",
        "The record of every movement of money. Each movement is written twice, once where the "
        "money leaves and once where it arrives.",
        "Le registre de chaque mouvement d'argent. Chaque mouvement est écrit deux fois, d'où "
        "l'argent part et où il arrive.",
        "A notebook where every coin that leaves one pocket is noted entering another.",
        "Un carnet où chaque pièce qui quitte une poche est notée en entrant dans une autre.",
    ),
    "double_entry": _e(
        "Double-entry",
        "Partie double",
        "An accounting rule: every movement has two sides that cancel out, so the books always "
        "balance and errors show up.",
        "Une règle comptable : chaque mouvement a deux côtés qui s'annulent, donc les comptes "
        "s'équilibrent toujours et les erreurs se voient.",
        "A seesaw that must always stay level.",
        "Une balançoire à bascule qui doit toujours rester à l'horizontale.",
    ),
    "fees": _e(
        "Fees",
        "Frais",
        "What you pay for the investments to be managed. Small fees add up over long periods.",
        "Ce que vous payez pour la gestion des placements. De petits frais s'additionnent sur la "
        "durée.",
        "A small toll on every trip: easy to ignore once, noticeable over years.",
        "Un petit péage à chaque trajet : négligeable une fois, sensible sur des années.",
    ),
}


def term_name(key: str, language: Language) -> str:
    return GLOSSARY[key].term[language]
