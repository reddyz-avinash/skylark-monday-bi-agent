from __future__ import annotations

import math
import pandas as pd

from .normalize import (
    frame_from_items,
    standardize_columns,
    numeric_series,
    normalized_text_series,
    missing_count,
)


# ============================================================
# DEAL COLUMN ALIASES
# ============================================================

DEAL_ALIASES = {
    "deal_name": ["name", "Deal Name"],
    "owner": ["Owner code"],
    "client_code": ["Client Code"],
    "deal_status": ["Deal Status"],
    "close_date": ["Close Date (A)", "Close Date"],
    "probability": ["Closure Probability"],
    "deal_value": ["Masked Deal value", "Deal value"],
    "tentative_close": ["Tentative Close Date"],
    "deal_stage": ["Deal Stage"],
    "product": ["Product deal"],
    "sector": ["Sector/service", "Sector"],
    "created_date": ["Created Date"],
}


# ============================================================
# WORK ORDER COLUMN ALIASES
# ============================================================

WO_ALIASES = {
    "deal_name": ["Deal name masked"],
    "customer_code": ["Customer Name Code"],
    "serial": ["Serial #"],
    "nature": ["Nature of Work"],
    "execution_status": ["Execution Status"],
    "delivery_date": ["Data Delivery Date"],
    "po_date": ["Date of PO/LOI"],
    "document_type": ["Document Type"],
    "start_date": ["Probable Start Date"],
    "end_date": ["Probable End Date"],
    "owner": ["BD/KAM Personnel code"],
    "sector": ["Sector"],
    "type_of_work": ["Type of Work"],
    "software": [
        "Is any Skylark software platform part of the client deliverables in this deal?"
    ],
    "invoice_date": ["Last invoice date"],
    "invoice_no": ["latest invoice no."],
    "amount_ex_gst": [
        "Amount in Rupees (Excl of GST) (Masked)"
    ],
    "amount_inc_gst": [
        "Amount in Rupees (Incl of GST) (Masked)"
    ],
    "billed_ex_gst": [
        "Billed Value in Rupees (Excl of GST.) (Masked)"
    ],
    "billed_inc_gst": [
        "Billed Value in Rupees (Incl of GST.) (Masked)"
    ],
    "collected": [
        "Collected Amount in Rupees (Incl of GST.) (Masked)"
    ],
    "to_bill_ex_gst": [
        "Amount to be billed in Rs. (Exl. of GST) (Masked)"
    ],
    "to_bill_inc_gst": [
        "Amount to be billed in Rs. (Incl. of GST) (Masked)"
    ],
    "receivable": ["Amount Receivable (Masked)"],
    "ar_priority": ["AR Priority account"],
    "quantity_ops": ["Quantity by Ops"],
    "quantity_po": ["Quantities as per PO"],
    "quantity_billed": ["Quantity billed (till date)"],
    "quantity_balance": ["Balance in quantity"],
    "invoice_status": ["Invoice Status"],
    "expected_billing": ["Expected Billing Month"],
    "actual_billing": ["Actual Billing Month"],
    "actual_collection": ["Actual Collection Month"],
    "wo_status": ["WO Status (billed)"],
    "collection_status": ["Collection status"],
    "collection_date": ["Collection Date"],
    "billing_status": ["Billing Status"],
}


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare(deal_items, wo_items):
    deals = standardize_columns(
        frame_from_items(deal_items),
        DEAL_ALIASES,
    )

    work_orders = standardize_columns(
        frame_from_items(wo_items),
        WO_ALIASES,
    )

    return deals, work_orders


# ============================================================
# FORMATTING
# ============================================================

def money(x):
    """
    Format Indian currency.

    1 Cr = 10,000,000
    1 L  = 100,000
    """

    if x is None:
        return "N/A"

    try:
        x = float(x)
    except (TypeError, ValueError):
        return "N/A"

    if math.isnan(x):
        return "N/A"

    if abs(x) >= 10_000_000:
        return f"₹{x / 10_000_000:.2f} Cr"

    if abs(x) >= 100_000:
        return f"₹{x / 100_000:.2f} L"

    return f"₹{x:,.0f}"


# ============================================================
# COMMON HELPERS
# ============================================================

def status_mask(df, column, value):
    if column not in df:
        return pd.Series(
            [False] * len(df),
            index=df.index,
        )

    return (
        normalized_text_series(df, column)
        == value.lower()
    )


def sector_series(df):
    """
    Normalize sector values.

    Missing sectors become 'Unknown'.
    """

    if "sector" not in df:
        return pd.Series(
            ["Unknown"] * len(df),
            index=df.index,
        )

    result = normalized_text_series(df, "sector")

    return (
        result
        .replace("", "unknown")
        .str.title()
    )


# ============================================================
# PIPELINE
# ============================================================

def pipeline_summary(deals, sector=None):

    d = deals.copy()

    if sector:
        d = d[
            normalized_text_series(d, "sector")
            == sector.lower()
        ]

    d = d[
        status_mask(
            d,
            "deal_status",
            "open",
        )
    ]

    values = numeric_series(
        d,
        "deal_value",
    )

    valid = values.dropna()

    return {
        "open_deals": int(len(d)),
        "valued_open_deals": int(valid.size),
        "missing_open_values": int(values.isna().sum()),
        "open_pipeline": (
            float(valid.sum())
            if valid.size
            else 0
        ),
    }


def pipeline_by_sector(deals):

    d = deals[
        status_mask(
            deals,
            "deal_status",
            "open",
        )
    ].copy()

    d["_value"] = numeric_series(
        d,
        "deal_value",
    )

    d["_sector"] = sector_series(d)

    grouped = (
        d.groupby("_sector")
        .agg(
            open_deals=(
                "deal_name",
                "count",
            ),
            valued_open_deals=(
                "_value",
                lambda x: int(x.notna().sum()),
            ),
            pipeline=(
                "_value",
                "sum",
            ),
        )
        .reset_index()
    )

    grouped = grouped.sort_values(
        "pipeline",
        ascending=False,
    )

    results = []

    for _, row in grouped.iterrows():

        results.append(
            {
                "sector": str(row["_sector"]),
                "open_deals": int(
                    row["open_deals"]
                ),
                "valued_open_deals": int(
                    row["valued_open_deals"]
                ),
                "pipeline": (
                    float(row["pipeline"])
                    if pd.notna(row["pipeline"])
                    else 0
                ),
            }
        )

    return results


# ============================================================
# DEAL STAGES
# ============================================================

def stage_summary(deals):

    d = deals[
        status_mask(
            deals,
            "deal_status",
            "open",
        )
    ].copy()

    d["_value"] = numeric_series(
        d,
        "deal_value",
    )

    if "deal_stage" in d:
        stage = (
            d["deal_stage"]
            .fillna("Unknown")
            .replace("", "Unknown")
        )
    else:
        stage = pd.Series(
            ["Unknown"] * len(d),
            index=d.index,
        )

    grouped = (
        d.groupby(stage)
        .agg(
            deals=(
                "deal_name",
                "count",
            ),
            pipeline=(
                "_value",
                "sum",
            ),
        )
        .reset_index()
    )

    grouped = grouped.sort_values(
        "deals",
        ascending=False,
    )

    return [
        {
            "stage": str(row.iloc[0]),
            "deals": int(row["deals"]),
            "pipeline": (
                float(row["pipeline"])
                if pd.notna(row["pipeline"])
                else 0
            ),
        }
        for _, row in grouped.iterrows()
    ]


# ============================================================
# OPERATIONS
# ============================================================

def operations_summary(work, sector=None):

    d = work.copy()

    if sector:
        d = d[
            normalized_text_series(d, "sector")
            == sector.lower()
        ]

    statuses = normalized_text_series(
        d,
        "execution_status",
    )

    return {
        "work_orders": int(len(d)),

        "ongoing": int(
            statuses.str.contains(
                "ongoing",
                na=False,
            ).sum()
        ),

        "completed": int(
            statuses.str.contains(
                "completed",
                na=False,
            ).sum()
        ),

        "not_started": int(
            statuses.str.contains(
                "not started",
                na=False,
            ).sum()
        ),

        "paused": int(
            statuses.str.contains(
                "pause|struck",
                regex=True,
                na=False,
            ).sum()
        ),
    }


def operations_by_sector(work):

    d = work.copy()

    d["_sector"] = sector_series(d)

    statuses = normalized_text_series(
        d,
        "execution_status",
    )

    d["_ongoing"] = statuses.str.contains(
        "ongoing",
        na=False,
    )

    d["_completed"] = statuses.str.contains(
        "completed",
        na=False,
    )

    d["_not_started"] = statuses.str.contains(
        "not started",
        na=False,
    )

    d["_paused"] = statuses.str.contains(
        "pause|struck",
        regex=True,
        na=False,
    )

    grouped = (
        d.groupby("_sector")
        .agg(
            work_orders=(
                "deal_name",
                "count",
            ),
            ongoing=(
                "_ongoing",
                "sum",
            ),
            completed=(
                "_completed",
                "sum",
            ),
            not_started=(
                "_not_started",
                "sum",
            ),
            paused=(
                "_paused",
                "sum",
            ),
        )
        .reset_index()
    )

    grouped = grouped.sort_values(
        "work_orders",
        ascending=False,
    )

    return [
        {
            "sector": str(row["_sector"]),
            "work_orders": int(
                row["work_orders"]
            ),
            "ongoing": int(
                row["ongoing"]
            ),
            "completed": int(
                row["completed"]
            ),
            "not_started": int(
                row["not_started"]
            ),
            "paused": int(
                row["paused"]
            ),
        }
        for _, row in grouped.iterrows()
    ]


# ============================================================
# BILLING
# ============================================================

def billing_summary(work, sector=None):

    d = work.copy()

    if sector:
        d = d[
            normalized_text_series(d, "sector")
            == sector.lower()
        ]

    output = {
        "work_orders": int(len(d))
    }

    fields = [
        (
            "billed_total",
            "billed_inc_gst",
        ),
        (
            "collected_total",
            "collected",
        ),
        (
            "to_bill_total",
            "to_bill_inc_gst",
        ),
        (
            "receivable_total",
            "receivable",
        ),
    ]

    for key, column in fields:

        values = numeric_series(
            d,
            column,
        )

        output[key] = (
            float(values.sum())
            if values.notna().any()
            else 0
        )

        output[
            key.replace(
                "_total",
                "_available",
            )
        ] = int(
            values.notna().sum()
        )

    return output


def billing_by_sector(work):

    d = work.copy()

    d["_sector"] = sector_series(d)

    billing_columns = {
        "billed": "billed_inc_gst",
        "collected": "collected",
        "to_bill": "to_bill_inc_gst",
        "receivable": "receivable",
    }

    for output_name, column in billing_columns.items():

        d[f"_{output_name}"] = numeric_series(
            d,
            column,
        )

    grouped = (
        d.groupby("_sector")
        .agg(
            work_orders=(
                "deal_name",
                "count",
            ),
            billed=(
                "_billed",
                "sum",
            ),
            collected=(
                "_collected",
                "sum",
            ),
            to_bill=(
                "_to_bill",
                "sum",
            ),
            receivable=(
                "_receivable",
                "sum",
            ),
            billed_available=(
                "_billed",
                lambda x: int(x.notna().sum()),
            ),
            collected_available=(
                "_collected",
                lambda x: int(x.notna().sum()),
            ),
            to_bill_available=(
                "_to_bill",
                lambda x: int(x.notna().sum()),
            ),
            receivable_available=(
                "_receivable",
                lambda x: int(x.notna().sum()),
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
                "sector": str(row["_sector"]),

                "work_orders": int(
                    row["work_orders"]
                ),

                "billed": (
                    float(row["billed"])
                    if pd.notna(row["billed"])
                    else 0
                ),

                "collected": (
                    float(row["collected"])
                    if pd.notna(row["collected"])
                    else 0
                ),

                "to_bill": (
                    float(row["to_bill"])
                    if pd.notna(row["to_bill"])
                    else 0
                ),

                "receivable": (
                    float(row["receivable"])
                    if pd.notna(row["receivable"])
                    else 0
                ),

                "billed_available": int(
                    row["billed_available"]
                ),

                "collected_available": int(
                    row["collected_available"]
                ),

                "to_bill_available": int(
                    row["to_bill_available"]
                ),

                "receivable_available": int(
                    row["receivable_available"]
                ),
            }
        )

    return results


# ============================================================
# DATA QUALITY HELPERS
# ============================================================

DEAL_QUALITY_FIELDS = {
    "deal_value": "deal value",
    "probability": "probability",
    "close_date": "close date",
}

WORK_ORDER_QUALITY_FIELDS = {
    "receivable": "receivable",
    "billed_inc_gst": "billed incl. GST",
    "collected": "collected amount",
    "billing_status": "billing status",
}


def _quality_notes_for_columns(
    df,
    fields,
    prefix,
):
    """
    Build data-quality notes only for the requested dataset.
    """

    notes = []

    for column, label in fields.items():

        if column not in df:
            continue

        count = missing_count(
            df,
            column,
        )

        if count:
            notes.append(
                f"{prefix}: {count} records have missing {label}."
            )

    return notes


def data_quality_for_intent(
    deals,
    work,
    intent: str | None = None,
):
    """
    Return only the data-quality notes relevant to the
    current question.

    This prevents an operations question from displaying
    unrelated Deal warnings and vice versa.
    """

    intent = (intent or "").lower().strip()

    # --------------------------------------------------------
    # PIPELINE / SALES
    # --------------------------------------------------------

    pipeline_intents = {
        "pipeline",
        "pipeline_by_sector",
        "stage_summary",
        "sector_comparison",
        "leadership_update",
    }

    # --------------------------------------------------------
    # OPERATIONS
    # --------------------------------------------------------

    operations_intents = {
        "operations",
    }

    # --------------------------------------------------------
    # BILLING
    # --------------------------------------------------------

    billing_intents = {
        "billing",
        "billing_by_sector",
    }

    # --------------------------------------------------------
    # COMPARISON / LEADERSHIP
    # --------------------------------------------------------

    if intent in pipeline_intents:
        notes = _quality_notes_for_columns(
            deals,
            DEAL_QUALITY_FIELDS,
            "Deals",
        )

        # Cross-board questions also need relevant
        # Work Order quality information.
        if intent in {
            "sector_comparison",
            "leadership_update",
        }:
            notes.extend(
                _quality_notes_for_columns(
                    work,
                    WORK_ORDER_QUALITY_FIELDS,
                    "Work Orders",
                )
            )

        return notes

    if intent in operations_intents:
        return _quality_notes_for_columns(
            work,
            WORK_ORDER_QUALITY_FIELDS,
            "Work Orders",
        )

    if intent in billing_intents:
        return _quality_notes_for_columns(
            work,
            WORK_ORDER_QUALITY_FIELDS,
            "Work Orders",
        )

    # Unknown / clarification question:
    # show a small cross-board quality summary.
    notes = []

    notes.extend(
        _quality_notes_for_columns(
            deals,
            DEAL_QUALITY_FIELDS,
            "Deals",
        )
    )

    notes.extend(
        _quality_notes_for_columns(
            work,
            WORK_ORDER_QUALITY_FIELDS,
            "Work Orders",
        )
    )

    return notes


# ============================================================
# BACKWARD-COMPATIBLE DATA QUALITY FUNCTION
# ============================================================

def data_quality(
    deals,
    work,
    intent: str | None = None,
):
    """
    Backward-compatible wrapper.

    Existing code can continue calling:

        data_quality(deals, work)

    New code should call:

        data_quality(deals, work, intent)
    """

    return data_quality_for_intent(
        deals,
        work,
        intent,
    )