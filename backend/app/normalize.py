from __future__ import annotations
import math
import re
from typing import Any
import pandas as pd

def clean_key(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return re.sub(r"[\s_/-]+", " ", str(value).strip().lower())

def to_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    text = re.sub(r"[₹$€£,]", "", str(value).strip())
    try:
        return float(text)
    except ValueError:
        return None

def to_date(value: Any):
    if value is None or value == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed

def item_to_record(item: dict[str, Any]) -> dict[str, Any]:
    record = {
        "name": item.get("name"),
        "id": item.get("id"),
    }

    for col in item.get("column_values", []):
        column_id = col.get("id", "")
        column_title = col.get("title", "")

        value = col.get("text")

        # Keep the Monday column ID as a fallback.
        if column_id:
            record[column_id] = value

        # Prefer the human-readable Monday column title.
        if column_title:
            record[column_title] = value

    return record
def frame_from_items(items: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame([item_to_record(i) for i in items])

def standardize_columns(df: pd.DataFrame, aliases: dict[str, list[str]]) -> pd.DataFrame:
    if df.empty:
        return df
    lookup = {clean_key(c): c for c in df.columns}
    rename = {}
    for target, candidates in aliases.items():
        for candidate in candidates:
            source = lookup.get(clean_key(candidate))
            if source:
                rename[source] = target
                break
    return df.rename(columns=rename)

def missing_count(df: pd.DataFrame, column: str) -> int:
    if column not in df:
        return len(df)
    s = df[column]
    return int(s.isna().sum() + (s.astype(str).str.strip() == "").sum())

def numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df:
        return pd.Series(dtype="float64")
    return pd.to_numeric(
        df[column].astype(str).str.replace(",", "", regex=False).str.replace("₹", "", regex=False),
        errors="coerce",
    )

def normalized_text_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df:
        return pd.Series([""] * len(df), index=df.index)
    return df[column].map(clean_key)
