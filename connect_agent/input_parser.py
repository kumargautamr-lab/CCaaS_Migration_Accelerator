from __future__ import annotations

from io import BytesIO

import pandas as pd


MAX_ROWS_PER_SHEET = 200
MAX_COLUMNS_PER_SHEET = 30
MAX_CELL_CHARS = 500


def workbook_to_prompt(data: bytes, filename: str) -> str:
    """Convert a workbook to a bounded, readable prompt without executing formulas."""
    sheets = pd.read_excel(BytesIO(data), sheet_name=None, dtype=str)
    if not sheets:
        raise ValueError("The workbook has no readable sheets.")

    sections = [f"Workbook: {filename}"]
    for name, frame in sheets.items():
        if name.strip().lower() == "instructions":
            continue
        frame = frame.dropna(how="all").dropna(axis=1, how="all")
        if frame.empty:
            continue
        frame = frame.iloc[:MAX_ROWS_PER_SHEET, :MAX_COLUMNS_PER_SHEET].fillna("")
        frame = frame.map(lambda value: str(value)[:MAX_CELL_CHARS])
        sections.extend((f"\nSheet: {name}", frame.to_csv(index=False)))

    if len(sections) == 1:
        raise ValueError("The workbook contains no non-empty cells.")
    return "\n".join(sections)
