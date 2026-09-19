from __future__ import annotations

from dataclasses import dataclass


# All known sectors from the Skylark datasets.
SECTORS = [
    "mining",
    "renewables",
    "railways",
    "powerline",
    "construction",
    "aviation",
    "manufacturing",
    "tender",
    "dsp",
    "security and surveillance",
    "others",
]


@dataclass
class Plan:
    intent: str
    sector: str | None = None
    comparison_sectors: list[str] | None = None


def extract_sectors(text: str) -> list[str]:
    """
    Extract every known sector mentioned in the question.

    Longer sector names are checked first so that
    'security and surveillance' is detected correctly.
    """
    text = text.lower()

    found = []

    for sector in sorted(SECTORS, key=len, reverse=True):
        if sector in text:
            found.append(sector)

    return found


def extract_sector(text: str) -> str | None:
    """
    Return the first matching sector.
    """
    sectors = extract_sectors(text)
    return sectors[0] if sectors else None


def plan(message: str) -> Plan:
    q = message.lower().strip()

    sectors_found = extract_sectors(q)
    sector = sectors_found[0] if sectors_found else None

    # =========================================================
    # 1. Explicit comparison between sectors
    # =========================================================

    comparison_words = [
        "compare",
        "comparison",
        "versus",
        " vs ",
        "vs.",
        "against",
    ]

    cross_board_words = [
        "across sales and operations",
        "across both",
        "both boards",
        "sales pipeline and work order",
        "sales pipeline and execution",
        "pipeline and execution",
        "pipeline and operations",
        "sales and operations",
    ]

    if (
        any(word in q for word in comparison_words)
        and len(sectors_found) >= 2
    ):
        return Plan(
            intent="sector_comparison",
            comparison_sectors=sectors_found[:6],
        )

    if (
        any(word in q for word in cross_board_words)
        and len(sectors_found) >= 2
    ):
        return Plan(
            intent="sector_comparison",
            comparison_sectors=sectors_found[:6],
        )

    # =========================================================
    # 2. Leadership / executive update
    # =========================================================

    leadership_words = [
        "leadership update",
        "leadership summary",
        "executive update",
        "executive summary",
        "management update",
        "management summary",
        "founder update",
        "founder summary",
        "business update",
    ]

    if any(word in q for word in leadership_words):
        return Plan(
            intent="leadership_update",
            sector=sector,
        )

    # =========================================================
    # 3. Sector + receivables / billing analysis
    # =========================================================

    receivable_words = [
        "receivable",
        "receivables",
        "amount receivable",
        "outstanding",
        "outstanding amount",
        "money receivable",
    ]

    billing_words = [
        "billed",
        "billing",
        "invoice",
        "invoiced",
        "collected",
        "collection",
        "collections",
        "to be billed",
        "to bill",
    ]

    ranking_words = [
        "highest",
        "lowest",
        "most",
        "least",
        "top",
        "bottom",
        "best",
        "largest",
        "smallest",
    ]

    if (
        any(word in q for word in receivable_words)
        and (
            "sector" in q
            or "sectors" in q
            or any(word in q for word in ranking_words)
        )
    ):
        return Plan(
            intent="billing_by_sector",
            sector=sector,
        )

    if (
        any(word in q for word in billing_words)
        and (
            "sector" in q
            or "sectors" in q
        )
        and any(word in q for word in ranking_words)
    ):
        return Plan(
            intent="billing_by_sector",
            sector=sector,
        )

    # =========================================================
    # 4. Sector + work-order / operations analysis
    # =========================================================

    operations_words = [
        "work order",
        "work orders",
        "work-order",
        "operations",
        "execution",
        "project status",
        "ongoing",
        "completed",
        "not started",
        "paused",
        "struck",
    ]

    if (
        any(word in q for word in operations_words)
        and (
            "sector" in q
            or "sectors" in q
            or any(word in q for word in ranking_words)
        )
    ):
        return Plan(
            intent="operations_by_sector",
            sector=sector,
        )

    # =========================================================
    # 5. Pipeline by sector
    # =========================================================

    pipeline_words = [
        "pipeline",
        "open pipeline",
        "sales pipeline",
        "open deals",
        "open deal",
    ]

    if (
        any(word in q for word in pipeline_words)
        and (
            "sector" in q
            or "sectors" in q
            or any(word in q for word in ranking_words)
            or "by sector" in q
            or "across sectors" in q
            or "per sector" in q
        )
    ):
        return Plan(
            intent="pipeline_by_sector",
            sector=sector,
        )

    # =========================================================
    # 6. Deal stage analysis
    # =========================================================

    stage_words = [
        "pipeline by stage",
        "pipeline stage",
        "deal stages",
        "stage breakdown",
        "which stage",
        "stages are",
        "deal stage",
    ]

    if any(word in q for word in stage_words):
        return Plan(
            intent="stage_summary",
            sector=sector,
        )

    # =========================================================
    # 7. Billing overall
    # =========================================================

    if any(word in q for word in billing_words + receivable_words):
        return Plan(
            intent="billing",
            sector=sector,
        )

    # =========================================================
    # 8. Operations overall
    # =========================================================

    if any(word in q for word in operations_words):
        return Plan(
            intent="operations",
            sector=sector,
        )

    # =========================================================
    # 9. Pipeline / deals overall
    # =========================================================

    if any(
        word in q
        for word in [
            "pipeline",
            "open deals",
            "open deal",
            "deal",
            "deals",
            "sales",
            "revenue",
        ]
    ):
        return Plan(
            intent="pipeline",
            sector=sector,
        )

    # =========================================================
    # 10. General sector question
    # =========================================================

    if "sector" in q or "sectors" in q:
        return Plan(
            intent="pipeline_by_sector",
            sector=sector,
        )

    # =========================================================
    # 11. Fallback
    # =========================================================

    return Plan("clarify")