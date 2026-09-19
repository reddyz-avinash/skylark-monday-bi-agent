from __future__ import annotations

import asyncio
import re
import traceback
from types import SimpleNamespace

import pandas as pd

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .schemas import ChatRequest, ChatResponse
from .monday import MondayClient, MondayError

from .analytics import (
    prepare,
    pipeline_summary,
    pipeline_by_sector,
    stage_summary,
    operations_summary,
    operations_by_sector,
    billing_summary,
    billing_by_sector,
    data_quality,
    money,
)

from .planner import plan
from .llm import polish_answer


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Skylark Monday.com Business Intelligence Agent",
    version="2.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
async def root():
    return {
        "service": "Skylark Monday.com Business Intelligence Agent",
        "status": "running",
        "health": "/api/health",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "skylark-bi-agent",
        "monday_connected": bool(
            settings.monday_api_token
        ),
        "deals_board_configured": bool(
            settings.monday_deals_board_id
        ),
        "work_orders_board_configured": bool(
            settings.monday_work_orders_board_id
        ),
    }


# ============================================================
# LOAD LIVE MONDAY.COM DATA
# ============================================================

async def load_data():
    """
    Always read fresh data from Monday.com.

    The assignment requires the agent to dynamically query
    Monday.com rather than hardcoding Excel/CSV data.
    """

    if not settings.monday_api_token:
        raise MondayError(
            "MONDAY_API_TOKEN is not configured."
        )

    if not settings.monday_deals_board_id:
        raise MondayError(
            "MONDAY_DEALS_BOARD_ID is not configured."
        )

    if not settings.monday_work_orders_board_id:
        raise MondayError(
            "MONDAY_WORK_ORDERS_BOARD_ID is not configured."
        )

    client = MondayClient(
        settings.monday_api_token
    )

    deals, work_orders = await asyncio.gather(
        client.get_board_items(
            settings.monday_deals_board_id
        ),
        client.get_board_items(
            settings.monday_work_orders_board_id
        ),
    )

    return prepare(
        deals,
        work_orders,
    )


# ============================================================
# QUESTION NORMALIZATION
# ============================================================

def normalize_question(message: str) -> str:
    text = (message or "").strip().lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


# ============================================================
# SECTOR HELPERS
# ============================================================

KNOWN_SECTORS = [
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
    "security",
    "surveillance",
    "others",
]


def detect_sector(message: str):
    """
    Detect a sector directly from the user's question.

    This is intentionally deterministic because sector
    extraction should not depend entirely on the LLM/planner.
    """

    text = normalize_question(message)

    # Longer names first.
    ordered = sorted(
        KNOWN_SECTORS,
        key=len,
        reverse=True,
    )

    for sector in ordered:
        if sector in text:
            if sector == "security":
                return "Security And Surveillance"

            if sector == "surveillance":
                return "Security And Surveillance"

            if sector == "dsp":
                return "Dsp"

            return sector.title()

    return None


def extract_comparison_sectors(message: str):
    """
    Detect multiple sectors from comparison questions.
    """

    text = normalize_question(message)

    found = []

    sector_aliases = {
        "mining": "Mining",
        "renewables": "Renewables",
        "railways": "Railways",
        "powerline": "Powerline",
        "construction": "Construction",
        "aviation": "Aviation",
        "manufacturing": "Manufacturing",
        "tender": "Tender",
        "dsp": "Dsp",
        "security and surveillance":
            "Security And Surveillance",
    }

    for key, value in sector_aliases.items():
        if key in text and value not in found:
            found.append(value)

    return found


def enrich_planner(
    planned,
    message: str,
):
    """
    Add deterministic sector information to the planner result.

    The existing planner may already provide these attributes.
    We only fill them when necessary.
    """

    if planned is None:
        planned = SimpleNamespace(
            intent="clarify"
        )

    sector = detect_sector(message)

    if sector and not getattr(
        planned,
        "sector",
        None,
    ):
        setattr(
            planned,
            "sector",
            sector,
        )

    comparison_sectors = (
        extract_comparison_sectors(
            message
        )
    )

    if comparison_sectors:
        setattr(
            planned,
            "comparison_sectors",
            comparison_sectors,
        )

    return planned


# ============================================================
# INTENT RESOLUTION
# ============================================================

def resolve_intent(
    planned,
    message: str,
):
    """
    Deterministic intent resolution.

    IMPORTANT:
    Specific intents are checked BEFORE generic intents.

    Example:
        "Compare Mining and Renewables across sales
         and operations"

    contains the word "sales".

    If generic pipeline detection happened first,
    it would incorrectly become "pipeline".

    Therefore comparison/leadership/sector queries
    are handled before generic pipeline/billing/operations.
    """

    text = normalize_question(message)

    original_intent = getattr(
        planned,
        "intent",
        "clarify",
    )

    print()
    print("=" * 70)
    print("INTENT DEBUG")
    print("Question :", message)
    print("Normalized:", text)
    print("Planner intent:", original_intent)
    print("=" * 70)

    # ========================================================
    # 1. LEADERSHIP / EXECUTIVE UPDATE
    # ========================================================

    leadership_phrases = [
        "leadership update",
        "leadership summary",
        "executive update",
        "executive summary",
        "business update",
        "overall business update",
        "overall business",
        "overall update",
        "overall status",
        "give me an overall business update",
        "prepare a leadership update",
        "prepare leadership update",
        "prepare an executive update",
    ]

    if any(
        phrase in text
        for phrase in leadership_phrases
    ):
        print("RESOLVED INTENT: leadership_update")

        return "leadership_update"

    # ========================================================
    # 2. CROSS-BOARD COMPARISON
    # ========================================================

    comparison_phrases = [
        "compare",
        "comparison",
        "versus",
        " vs ",
        "across sales and operations",
        "across sales and execution",
        "across sales and work orders",
        "sales and operations",
    ]

    comparison_sectors = (
        extract_comparison_sectors(
            message
        )
    )

    if (
        any(
            phrase in text
            for phrase in comparison_phrases
        )
        and len(comparison_sectors) >= 2
    ):
        print(
            "RESOLVED INTENT: sector_comparison"
        )
        print(
            "Comparison sectors:",
            comparison_sectors,
        )

        return "sector_comparison"

    # ========================================================
    # 3. RECEIVABLES BY SECTOR
    # ========================================================

    receivable_phrases = [
        "receivable",
        "receivables",
        "outstanding",
        "amount due",
        "money due",
        "collection due",
    ]

    sector_phrases = [
        "sector",
        "sectors",
        "industry",
    ]

    if (
        any(
            phrase in text
            for phrase in receivable_phrases
        )
        and any(
            phrase in text
            for phrase in sector_phrases
        )
    ):
        print(
            "RESOLVED INTENT: billing_by_sector"
        )

        return "billing_by_sector"

    if (
        "highest receivable" in text
        or "highest receivables" in text
        or "most receivable" in text
        or "highest outstanding" in text
        or "highest outstanding amount" in text
        or "receivables by sector" in text
        or "receivable by sector" in text
        or "show receivables by sector" in text
        or "show receivable by sector" in text
    ):
        print(
            "RESOLVED INTENT: billing_by_sector"
        )

        return "billing_by_sector"

    # ========================================================
    # 4. PIPELINE BY SECTOR
    # ========================================================

    pipeline_by_sector_phrases = [
        "pipeline by sector",
        "open pipeline by sector",
        "pipeline across sectors",
        "highest open pipeline",
        "highest pipeline",
        "which sectors have the highest open pipeline",
        "which sectors have highest open pipeline",
        "sectors have the highest open pipeline",
        "sectors have highest pipeline",
        "show pipeline by sector",
    ]

    if any(
        phrase in text
        for phrase in pipeline_by_sector_phrases
    ):
        print(
            "RESOLVED INTENT: pipeline_by_sector"
        )

        return "pipeline_by_sector"

    # ========================================================
    # 5. OPERATIONS BY SECTOR
    # ========================================================

    operations_by_sector_phrases = [
        "execution by sector",
        "operations by sector",
        "work orders by sector",
        "work order execution by sector",
        "execution status by sector",
        "work order status by sector",
    ]

    if any(
        phrase in text
        for phrase in operations_by_sector_phrases
    ):
        print(
            "RESOLVED INTENT: operations_by_sector"
        )

        return "operations_by_sector"

    # ========================================================
    # 6. SPECIFIC SECTOR RECEIVABLE
    # ========================================================

    # Example:
    # "How much receivable is there in Mining?"

    if any(
        phrase in text
        for phrase in receivable_phrases
    ):
        sector = detect_sector(
            message
        )

        if sector:
            print(
                "RESOLVED INTENT: billing_by_sector"
            )
            print(
                "Sector:",
                sector,
            )

            return "billing_by_sector"

    # ========================================================
    # 7. TO-BE-BILLED
    # ========================================================

    to_bill_phrases = [
        "still to be billed",
        "still need to be billed",
        "yet to be billed",
        "remaining to be billed",
        "amount to be billed",
        "amount-to-be-billed",
        "unbilled",
        "to bill",
        "to be billed",
        "how much is still to be billed",
        "how much remains to be billed",
    ]

    if any(
        phrase in text
        for phrase in to_bill_phrases
    ):
        print(
            "RESOLVED INTENT: billing"
        )

        return "billing"

    # ========================================================
    # 8. GENERAL BILLING
    # ========================================================

    billing_words = [
        "billing",
        "billed",
        "collected",
        "collection",
        "invoice",
        "invoiced",
    ]

    if any(
        word in text
        for word in billing_words
    ):
        print(
            "RESOLVED INTENT: billing"
        )

        return "billing"

    # ========================================================
    # 9. OPEN PIPELINE
    # ========================================================

    pipeline_words = [
        "pipeline",
        "open deals",
        "open deal",
        "sales pipeline",
        "sales funnel",
    ]

    if any(
        word in text
        for word in pipeline_words
    ):
        print(
            "RESOLVED INTENT: pipeline"
        )

        return (
            original_intent
            if original_intent != "clarify"
            else "pipeline"
        )

    # ========================================================
    # 10. OPERATIONS
    # ========================================================

    operation_words = [
        "work order",
        "work orders",
        "ongoing",
        "execution",
        "executed",
        "completed",
        "not started",
        "paused",
        "struck",
        "operations",
        "project status",
    ]

    if any(
        word in text
        for word in operation_words
    ):
        print(
            "RESOLVED INTENT: operations"
        )

        return (
            original_intent
            if original_intent != "clarify"
            else "operations"
        )

    # ========================================================
    # 11. DEAL STAGES
    # ========================================================

    stage_words = [
        "deal stage",
        "deal stages",
        "sales stage",
        "sales stages",
        "stage breakdown",
        "pipeline stage",
    ]

    if any(
        word in text
        for word in stage_words
    ):
        print(
            "RESOLVED INTENT: stage_summary"
        )

        return "stage_summary"

    # ========================================================
    # 12. PLANNER FALLBACK
    # ========================================================

    print(
        "RESOLVED INTENT:",
        original_intent,
    )

    return original_intent


# ============================================================
# DATA QUALITY
# ============================================================

def select_caveats(
    all_caveats,
    intent,
):
    """
    Only show warnings relevant to the current question.
    """

    if not all_caveats:
        return []

    deal_intents = {
        "pipeline",
        "pipeline_by_sector",
        "stage_summary",
    }

    if intent in deal_intents:
        return [
            note
            for note in all_caveats
            if note.startswith("Deals:")
        ]

    work_order_intents = {
        "operations",
        "operations_by_sector",
        "billing",
        "billing_by_sector",
    }

    if intent in work_order_intents:
        return [
            note
            for note in all_caveats
            if note.startswith(
                "Work Orders:"
            )
        ]

    cross_board_intents = {
        "sector_comparison",
        "leadership_update",
    }

    if intent in cross_board_intents:
        return list(
            all_caveats
        )

    return list(
        all_caveats
    )


# ============================================================
# ROBUST NUMERIC CONVERSION
# ============================================================

def safe_numeric_series(
    series,
):
    """
    Convert messy currency/number values into numeric values.

    Missing or invalid values become NaN.

    Missing values are NOT converted to zero.
    """

    if series is None:
        return pd.Series(
            dtype="float64"
        )

    if not isinstance(
        series,
        pd.Series,
    ):
        series = pd.Series(
            series
        )

    def parse_value(value):

        if pd.isna(value):
            return float("nan")

        text = str(
            value
        ).strip()

        if not text:
            return float("nan")

        # Remove common currency formatting.
        text = (
            text
            .replace("₹", "")
            .replace("Rs.", "")
            .replace("Rs", "")
            .replace(",", "")
            .replace("INR", "")
            .strip()
        )

        # Handle parentheses as negatives.
        if (
            text.startswith("(")
            and text.endswith(")")
        ):
            text = "-" + text[1:-1]

        try:
            return float(
                text
            )
        except (
            TypeError,
            ValueError,
        ):
            return float("nan")

    return series.apply(
        parse_value
    )


# ============================================================
# ROBUST SECTOR NORMALIZATION
# ============================================================

def normalized_sector_series(
    work,
):
    """
    Normalize Work Order sector values.
    """

    if work is None or work.empty:
        return pd.Series(
            dtype="object"
        )

    if "sector" not in work.columns:
        return pd.Series(
            ["Unknown"] * len(work),
            index=work.index,
        )

    result = (
        work["sector"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    result = result.replace(
        "",
        "Unknown",
    )

    # Normalize common capitalization.
    result = result.str.title()

    return result


# ============================================================
# ROBUST RECEIVABLES BY SECTOR
# ============================================================

def robust_receivables_by_sector(
    work,
):
    """
    Calculate receivables by sector directly from the
    normalized Work Orders dataframe.

    This avoids depending entirely on billing_by_sector()
    for the receivables ranking.

    Missing receivable values are excluded from totals.
    """

    print()
    print("=" * 70)
    print("RECEIVABLE DEBUG")
    print("=" * 70)

    if work is None:
        print(
            "Work Orders dataframe is None."
        )
        return []

    if work.empty:
        print(
            "Work Orders dataframe is empty."
        )
        return []

    print(
        "Work Order rows:",
        len(work),
    )

    print(
        "Columns:",
        list(work.columns),
    )

    if "receivable" not in work.columns:
        print(
            "ERROR: normalized 'receivable' "
            "column is missing."
        )
        return []

    df = work.copy()

    df["_sector"] = normalized_sector_series(
        df
    )

    df["_receivable"] = safe_numeric_series(
        df["receivable"]
    )

    available = int(
        df["_receivable"]
        .notna()
        .sum()
    )

    missing = int(
        df["_receivable"]
        .isna()
        .sum()
    )

    print(
        "Receivable values available:",
        available,
    )

    print(
        "Receivable values missing:",
        missing,
    )

    print(
        "Sample receivable values:"
    )

    print(
        df[
            [
                "_sector",
                "receivable",
                "_receivable",
            ]
        ]
        .head(10)
        .to_string()
    )

    grouped = (
        df.groupby(
            "_sector",
            dropna=False,
        )
        .agg(
            work_orders=(
                "_sector",
                "size",
            ),
            receivable=(
                "_receivable",
                lambda x: float(
                    x.sum(
                        skipna=True
                    )
                ),
            ),
            receivable_available=(
                "_receivable",
                lambda x: int(
                    x.notna().sum()
                ),
            ),
        )
        .reset_index()
    )

    grouped = grouped.sort_values(
        "receivable",
        ascending=False,
    )

    results = []

    for _, row in grouped.iterrows():

        results.append(
            {
                "sector": str(
                    row["_sector"]
                ),
                "work_orders": int(
                    row["work_orders"]
                ),
                "receivable": float(
                    row["receivable"]
                ),
                "receivable_available": int(
                    row[
                        "receivable_available"
                    ]
                ),
            }
        )

    print(
        "Receivable sector count:",
        len(results),
    )

    print(
        "Receivable results:",
        results,
    )

    print(
        "=" * 70
    )

    return results


# ============================================================
# RECEIVABLE ANSWER
# ============================================================

def build_receivable_answer(
    work,
    message,
    caveats,
):
    """
    Answer both:
      - Which sectors have highest receivables?
      - How much receivable is there in Mining?
    """

    rows = robust_receivables_by_sector(
        work
    )

    if not rows:
        return (
            "I couldn't find sector-level receivable "
            "records in the current Work Orders board.",
            {
                "sectors": []
            },
            caveats,
        )

    requested_sector = detect_sector(
        message
    )

    # ========================================================
    # SPECIFIC SECTOR
    # ========================================================

    if requested_sector:

        matching = [
            row
            for row in rows
            if row["sector"].strip().lower()
            == requested_sector.strip().lower()
        ]

        if matching:

            row = matching[0]

            answer = (
                f"**{row['sector']}** has "
                f"**{money(row['receivable'])}** "
                f"in reported receivables across "
                f"**{row['work_orders']} work orders**. "
                f"Receivable data is available for "
                f"**{row['receivable_available']}** "
                f"of those work orders."
            )

            return (
                answer,
                {
                    "sector": row,
                    "sectors": rows,
                },
                caveats,
            )

    # ========================================================
    # ALL SECTORS
    # ========================================================

    lines = [
        "**Receivables by sector:**"
    ]

    for row in rows[:10]:

        lines.append(
            f"- **{row['sector']}**: "
            f"**{money(row['receivable'])}** "
            f"across "
            f"{row['work_orders']} work orders "
            f"({row['receivable_available']} "
            f"with receivable data)"
        )

    top = rows[0]

    lines.append("")

    lines.append(
        f"**Highest reported receivable:** "
        f"{top['sector']} — "
        f"**{money(top['receivable'])}**."
    )

    return (
        "\n".join(lines),
        {
            "sectors": rows,
            "top_sector": top,
        },
        caveats,
    )


# ============================================================
# BUILD BUSINESS ANSWER
# ============================================================

def build_answer(
    planned,
    deals,
    work,
    intent,
    message,
):
    """
    Deterministically calculate the business answer.

    The LLM is never responsible for calculating numbers.
    """

    # data_quality() takes only deals and work.
    all_caveats = data_quality(
        deals,
        work,
    )

    caveats = select_caveats(
        all_caveats,
        intent,
    )

    # ========================================================
    # 1. PIPELINE
    # ========================================================

    if intent == "pipeline":

        sector = getattr(
            planned,
            "sector",
            None,
        )

        x = pipeline_summary(
            deals,
            sector,
        )

        scope = (
            f" for {sector.title()}"
            if sector
            else ""
        )

        answer = (
            f"Open pipeline{scope} is "
            f"**{money(x['open_pipeline'])}** "
            f"across "
            f"**{x['valued_open_deals']} "
            f"valued open deals**. "
            f"There are "
            f"**{x['open_deals']} open deals** "
            f"in scope; "
            f"**{x['missing_open_values']}** "
            f"do not have a usable deal value."
        )

        return (
            answer,
            x,
            caveats,
        )

    # ========================================================
    # 2. PIPELINE BY SECTOR
    # ========================================================

    if intent == "pipeline_by_sector":

        rows = pipeline_by_sector(
            deals
        )

        rows = [
            row
            for row in rows
            if row.get(
                "open_deals",
                0,
            ) > 0
        ]

        rows = sorted(
            rows,
            key=lambda row: row.get(
                "pipeline",
                0,
            ),
            reverse=True,
        )

        lines = [
            "**Open pipeline by sector:**"
        ]

        for row in rows[:10]:

            lines.append(
                f"- **{row['sector']}**: "
                f"{money(row['pipeline'])} "
                f"across "
                f"{row['open_deals']} "
                f"open deals "
                f"({row['valued_open_deals']} valued)"
            )

        return (
            "\n".join(lines),
            {
                "sectors": rows
            },
            caveats,
        )

    # ========================================================
    # 3. DEAL STAGES
    # ========================================================

    if intent == "stage_summary":

        rows = stage_summary(
            deals
        )

        lines = [
            "**Open deals by stage:**"
        ]

        for row in rows[:10]:

            lines.append(
                f"- **{row['stage']}**: "
                f"{row['deals']} deals, "
                f"{money(row['pipeline'])}"
            )

        return (
            "\n".join(lines),
            {
                "stages": rows
            },
            caveats,
        )

    # ========================================================
    # 4. OPERATIONS
    # ========================================================

    if intent == "operations":

        sector = getattr(
            planned,
            "sector",
            None,
        )

        x = operations_summary(
            work,
            sector,
        )

        scope = (
            f" for {sector.title()}"
            if sector
            else ""
        )

        answer = (
            f"Work-order status{scope}: "
            f"**{x['work_orders']}** "
            f"work orders, "
            f"**{x['ongoing']} ongoing**, "
            f"**{x['completed']} completed**, "
            f"**{x['not_started']} not started**, "
            f"and **{x['paused']} paused/struck**."
        )

        return (
            answer,
            x,
            caveats,
        )

    # ========================================================
    # 5. OPERATIONS BY SECTOR
    # ========================================================

    if intent == "operations_by_sector":

        rows = operations_by_sector(
            work
        )

        rows = [
            row
            for row in rows
            if row.get(
                "work_orders",
                0,
            ) > 0
        ]

        lines = [
            "**Work-order execution by sector:**"
        ]

        for row in rows[:10]:

            lines.append(
                f"- **{row['sector']}**: "
                f"{row['work_orders']} work orders, "
                f"{row['ongoing']} ongoing, "
                f"{row['completed']} completed, "
                f"{row['not_started']} not started, "
                f"{row['paused']} paused/struck"
            )

        return (
            "\n".join(lines),
            {
                "sectors": rows
            },
            caveats,
        )

    # ========================================================
    # 6. BILLING
    # ========================================================

    if intent == "billing":

        sector = getattr(
            planned,
            "sector",
            None,
        )

        x = billing_summary(
            work,
            sector,
        )

        answer = (
            f"Billing position: "
            f"**{money(x['to_bill_total'])}** "
            f"remains to be billed based on "
            f"**{x['to_bill_available']} work orders "
            f"with available amount-to-be-billed data**.\n\n"

            f"Currently billed: "
            f"**{money(x['billed_total'])}** "
            f"from "
            f"{x['billed_available']} work orders.\n\n"

            f"Collected: "
            f"**{money(x['collected_total'])}** "
            f"from "
            f"{x['collected_available']} work orders.\n\n"

            f"Receivable: "
            f"**{money(x['receivable_total'])}** "
            f"from "
            f"{x['receivable_available']} work orders."
        )

        return (
            answer,
            x,
            caveats,
        )

    # ========================================================
    # 7. RECEIVABLES BY SECTOR
    # ========================================================

    if intent == "billing_by_sector":

        return build_receivable_answer(
            work,
            message,
            caveats,
        )

    # ========================================================
    # 8. CROSS-BOARD COMPARISON
    # ========================================================

    if intent == "sector_comparison":

        sectors = getattr(
            planned,
            "comparison_sectors",
            None,
        )

        if not sectors:

            sectors = (
                extract_comparison_sectors(
                    message
                )
            )

        if not sectors:

            pipeline_rows = pipeline_by_sector(
                deals
            )

            sectors = [
                row["sector"]
                for row in pipeline_rows
                if row.get(
                    "open_deals",
                    0,
                ) > 0
            ][:6]

        comparison = []

        for sector in sectors:

            pipeline = pipeline_summary(
                deals,
                sector,
            )

            operations = operations_summary(
                work,
                sector,
            )

            comparison.append(
                {
                    "sector": sector,
                    "pipeline": pipeline,
                    "operations": operations,
                }
            )

        lines = [
            "**Sector comparison:**"
        ]

        for row in comparison:

            sector_name = row[
                "sector"
            ]

            pipeline = row[
                "pipeline"
            ]

            operations = row[
                "operations"
            ]

            lines.append(
                f"- **{sector_name}** — "
                f"pipeline "
                f"**{money(pipeline['open_pipeline'])}** "
                f"({pipeline['open_deals']} open deals); "
                f"{operations['work_orders']} work orders, "
                f"{operations['ongoing']} ongoing, "
                f"{operations['completed']} completed."
            )

        # IMPORTANT:
        # Keep metrics structure compatible with the
        # current React frontend.
        #
        # Frontend versions may expect either:
        #
        # comparison:
        # [
        #   [
        #       "Mining",
        #       pipeline,
        #       operations
        #   ]
        # ]
        #
        # So provide that format.

        frontend_comparison = []

        for row in comparison:

            frontend_comparison.append(
                [
                    row["sector"],
                    row["pipeline"],
                    row["operations"],
                ]
            )

        return (
            "\n".join(lines),
            {
                "comparison":
                    frontend_comparison,
                "comparison_rows":
                    comparison,
            },
            caveats,
        )

    # ========================================================
    # 9. LEADERSHIP UPDATE
    # ========================================================

    if intent == "leadership_update":

        sector = getattr(
            planned,
            "sector",
            None,
        )

        pipeline = pipeline_summary(
            deals,
            sector,
        )

        operations = operations_summary(
            work,
            sector,
        )

        billing = billing_summary(
            work,
            sector,
        )

        answer = (
            "## Leadership update\n\n"

            f"**Commercial:** "
            f"{pipeline['open_deals']} open deals "
            f"with "
            f"{money(pipeline['open_pipeline'])} "
            f"in valued open pipeline.\n\n"

            f"**Operations:** "
            f"{operations['work_orders']} work orders; "
            f"{operations['ongoing']} ongoing and "
            f"{operations['completed']} completed.\n\n"

            f"**Billing:** "
            f"{money(billing['billed_total'])} billed, "
            f"{money(billing['collected_total'])} collected, "
            f"{money(billing['receivable_total'])} receivable, "
            f"and "
            f"{money(billing['to_bill_total'])} "
            f"still to be billed based on populated fields.\n\n"

            "**Data quality:** "
            "Missing fields are not treated as zero; "
            "see the caveats below."
        )

        return (
            answer,
            {
                "pipeline": pipeline,
                "operations": operations,
                "billing": billing,
            },
            caveats,
        )

    # ========================================================
    # 10. CLARIFICATION / FALLBACK
    # ========================================================

    return (
        "Could you be more specific? I can analyze "
        "**pipeline**, **deal stages**, "
        "**work-order execution**, "
        "**billing/receivables**, "
        "**sector performance**, "
        "cross-board comparisons, "
        "or prepare a **leadership update**.\n\n"

        "Try something like:\n"
        "- How is our Mining pipeline looking?\n"
        "- Which sectors have the highest open pipeline?\n"
        "- Which sectors have the highest receivables?\n"
        "- How much is still to be billed?\n"
        "- How many work orders are ongoing?\n"
        "- Compare Mining and Renewables across sales and operations.\n"
        "- Prepare a leadership update.",

        {},

        caveats,
    )


# ============================================================
# CHAT ENDPOINT
# ============================================================

@app.post(
    "/api/chat",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
):

    try:

        # ====================================================
        # 1. LOAD LIVE DATA
        # ====================================================

        deals, work = await load_data()

        print()
        print("=" * 70)
        print("LIVE DATA LOADED")
        print(
            "Deals:",
            len(deals),
        )
        print(
            "Work Orders:",
            len(work),
        )
        print("=" * 70)

        # ====================================================
        # 2. PLAN QUESTION
        # ====================================================

        try:

            planned = plan(
                request.message
            )

        except Exception as e:

            print(
                "Planner error:",
                str(e),
            )

            planned = SimpleNamespace(
                intent="clarify"
            )

        # ====================================================
        # 3. ADD DETERMINISTIC CONTEXT
        # ====================================================

        planned = enrich_planner(
            planned,
            request.message,
        )

        # ====================================================
        # 4. RESOLVE INTENT
        # ====================================================

        intent = resolve_intent(
            planned,
            request.message,
        )

        # ====================================================
        # 5. DATA QUALITY
        # ====================================================

        all_caveats = data_quality(
            deals,
            work,
        )

        # ====================================================
        # 6. CLARIFICATION
        # ====================================================

        if intent == "clarify":

            return ChatResponse(
                answer=(
                    "Could you be more specific? "
                    "I can analyze **pipeline**, "
                    "**deal stages**, "
                    "**work-order execution**, "
                    "**billing/receivables**, "
                    "**sector performance**, "
                    "or prepare a "
                    "**leadership update**."
                ),
                intent="clarify",
                metrics={},
                caveats=select_caveats(
                    all_caveats,
                    "clarify",
                ),
                sources=[
                    "Monday.com Deals board",
                    "Monday.com Work Orders board",
                ],
            )

        # ====================================================
        # 7. BUILD DETERMINISTIC ANSWER
        # ====================================================

        answer, metrics, caveats = build_answer(
            planned,
            deals,
            work,
            intent,
            request.message,
        )

        # ====================================================
        # 8. OPTIONAL LLM POLISH
        # ====================================================
        #
        # The LLM can improve wording only.
        #
        # It does NOT calculate business numbers.
        #
        # If the OpenAI key is missing or the LLM fails,
        # the deterministic answer is returned unchanged.
        # ====================================================

        try:

            polished = await polish_answer(
                settings.openai_api_key,
                settings.openai_model,
                request.message,
                answer,
            )

            if polished:
                answer = polished

        except Exception as e:

            print(
                "Optional LLM polishing failed:",
                str(e),
            )

        # ====================================================
        # 9. FINAL RESPONSE
        # ====================================================

        return ChatResponse(
            answer=answer,
            intent=intent,
            metrics=metrics,
            caveats=caveats[:8],
            sources=[
                "Monday.com Deals board",
                "Monday.com Work Orders board",
            ],
        )

    # ========================================================
    # MONDAY ERROR
    # ========================================================

    except MondayError as e:

        print()
        print(
            "MONDAY.COM ERROR:"
        )
        print(
            str(e)
        )

        return JSONResponse(
            status_code=502,
            content={
                "detail": (
                    "The Monday.com connection "
                    "could not be completed."
                ),
                "technical_detail": str(e),
            },
        )

    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as e:

        print()
        print(
            "=" * 70
        )
        print(
            "UNEXPECTED SERVER ERROR"
        )
        print(
            str(e)
        )
        traceback.print_exc()
        print(
            "=" * 70
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": (
                    "The agent encountered "
                    "an unexpected error."
                ),
                "technical_detail": str(e),
            },
        )