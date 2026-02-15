"""Shared protocol type metadata for reference-node."""

from __future__ import annotations

from typing import Dict

TYPE_TO_FAMILY: Dict[str, str] = {
    "eo": "ExperienceObject",
    "trace": "TraceObject",
    "request": "RequestObject",
    "rr": "ReuseReceipt",
    "aao": "AgentAnnouncement",
    "referral": "ReferralObject",
    "seedupdate": "SeedUpdateObject",
}

TYPE_DIR: Dict[str, str] = {
    "eo": "eo",
    "trace": "trace",
    "request": "request",
    "rr": "rr",
    "aao": "aao",
    "referral": "referral",
    "seedupdate": "seedupdate",
}

ID_FIELD_MAP: Dict[str, str] = {
    "eo": "eo_id",
    "trace": "trace_id",
    "request": "rq_id",
    "rr": "rr_id",
    "aao": "aao_id",
    "referral": "ref_id",
    "seedupdate": "su_id",
}

SEARCH_OPS = {"equals", "contains", "prefix"}


def type_to_family(object_type: str) -> str:
    family = TYPE_TO_FAMILY.get(object_type)
    if family:
        return family
    allowed = ", ".join(sorted(TYPE_TO_FAMILY.keys()))
    raise ValueError(f"Unknown type '{object_type}'. Allowed types: {allowed}")
