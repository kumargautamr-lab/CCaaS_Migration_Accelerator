from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from .models import ConnectInstanceSpec


MAX_ROWS_PER_SHEET = 200
MAX_COLUMNS_PER_SHEET = 30
MAX_CELL_CHARS = 500


class NotTemplateWorkbookError(ValueError):
    """Raised when a workbook does not use the downloadable template structure."""


def _clean(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _optional(value: Any) -> str | None:
    result = _clean(value)
    return result or None


def _boolean(value: Any, default: bool) -> bool:
    text = _clean(value).lower()
    if not text:
        return default
    if text in {"true", "yes", "y", "1"}:
        return True
    if text in {"false", "no", "n", "0"}:
        return False
    raise ValueError(f"Expected true or false, received {value!r}.")


def _integer(value: Any, default: int) -> int:
    text = _clean(value)
    if not text:
        return default
    return int(float(text))


def _records(frame: pd.DataFrame | None, key: str) -> list[dict[str, Any]]:
    if frame is None:
        return []
    normalized = frame.copy()
    normalized.columns = [str(column).strip() for column in normalized.columns]
    return [
        row
        for row in normalized.to_dict(orient="records")
        if _clean(row.get(key))
    ]


def workbook_to_spec(data: bytes) -> ConnectInstanceSpec:
    """Parse the downloadable workbook template without an LLM call."""
    sheets = pd.read_excel(BytesIO(data), sheet_name=None, dtype=str)
    mapped = {name.strip().lower(): frame for name, frame in sheets.items()}
    instance_frame = mapped.get("instance")
    if instance_frame is None:
        raise NotTemplateWorkbookError("The workbook has no Instance worksheet.")

    instance_frame = instance_frame.dropna(how="all")
    instance_frame.columns = [str(column).strip() for column in instance_frame.columns]
    if not {"instance_alias", "region"}.issubset(instance_frame.columns):
        raise NotTemplateWorkbookError(
            "The Instance worksheet does not use the downloadable template columns."
        )
    if instance_frame.empty:
        raise ValueError("The Instance worksheet has no requirement row.")

    instance = instance_frame.iloc[0].to_dict()
    tags = {}
    if _clean(instance.get("tag_environment")):
        tags["Environment"] = _clean(instance["tag_environment"])
    if _clean(instance.get("tag_owner")):
        tags["Owner"] = _clean(instance["tag_owner"])

    skills = [
        {
            "name": _clean(row.get("name")),
            "description": _clean(row.get("description")) or "Generated routing skill",
            "channel": _clean(row.get("channel")) or "VOICE",
            "concurrency": _integer(row.get("concurrency"), 1),
            "priority": _integer(row.get("priority"), 1),
            "delay_seconds": _integer(row.get("delay_seconds"), 0),
        }
        for row in _records(mapped.get("skills"), "name")
    ]
    agents = [
        {
            "username": _clean(row.get("username")),
            "first_name": _clean(row.get("first_name")),
            "last_name": _clean(row.get("last_name")),
            "email": _optional(row.get("email")),
            "skill_name": _clean(row.get("skill_name")),
            "phone_type": _clean(row.get("phone_type")) or "SOFT_PHONE",
            "desk_phone_number": _optional(row.get("desk_phone_number")),
            "auto_accept": _boolean(row.get("auto_accept"), False),
            "after_contact_work_seconds": _integer(
                row.get("after_contact_work_seconds"), 60
            ),
        }
        for row in _records(mapped.get("agents"), "username")
    ]
    contact_flows = [
        {
            "name": _clean(row.get("name")),
            "description": (
                _clean(row.get("description")) or "Generated inbound contact flow"
            ),
            "welcome_message": _clean(row.get("welcome_message")),
            "type": _clean(row.get("type")) or "CONTACT_FLOW",
        }
        for row in _records(mapped.get("contactflows"), "name")
    ]
    dnis = [
        {
            "name": _clean(row.get("name")),
            "country_code": _clean(row.get("country_code")),
            "number_type": _clean(row.get("number_type")) or "DID",
            "prefix": _optional(row.get("prefix")),
            "contact_flow_name": _clean(row.get("contact_flow_name")),
        }
        for row in _records(mapped.get("dnis"), "name")
    ]

    return ConnectInstanceSpec.model_validate(
        {
            "instance_alias": _clean(instance.get("instance_alias")),
            "region": _clean(instance.get("region")),
            "identity_management_type": (
                _clean(instance.get("identity_management_type")) or "CONNECT_MANAGED"
            ),
            "directory_id": _optional(instance.get("directory_id")),
            "inbound_calls_enabled": _boolean(
                instance.get("inbound_calls_enabled"), True
            ),
            "outbound_calls_enabled": _boolean(
                instance.get("outbound_calls_enabled"), True
            ),
            "contact_flow_logs_enabled": _boolean(
                instance.get("contact_flow_logs_enabled"), False
            ),
            "contact_lens_enabled": _boolean(
                instance.get("contact_lens_enabled"), True
            ),
            "auto_resolve_best_voices_enabled": _boolean(
                instance.get("auto_resolve_best_voices_enabled"), True
            ),
            "early_media_enabled": _boolean(
                instance.get("early_media_enabled"), True
            ),
            "multi_party_conference_enabled": _boolean(
                instance.get("multi_party_conference_enabled"), False
            ),
            "time_zone": _clean(instance.get("time_zone")) or "UTC",
            "tags": tags,
            "skills": skills,
            "agents": agents,
            "contact_flows": contact_flows,
            "dnis": dnis,
        }
    )


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
