"""Style profiles are data. A style is selectable only when its checklist is verified."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import PagedrillRefusal

IMPLEMENTED_ENGINES = {"apa-author-date", "ar25-50-memorandum"}


def profiles_dir() -> Path:
    import os

    override = os.environ.get("PAGEDRILL_PROFILES")
    if override:
        return Path(override)
    here = Path(__file__).resolve()
    return here.parents[2] / "profiles"


def load_profiles() -> list[dict]:
    folder = profiles_dir()
    found: list[dict] = []
    if not folder.is_dir():
        return found
    for path in sorted(folder.glob("*.json")):
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["_path"] = str(path)
        profile["selectable"] = is_selectable(profile)
        found.append(profile)
    return found


def is_selectable(profile: dict) -> bool:
    status = str(profile.get("status") or "")
    sources = profile.get("sources")
    return bool(
        profile.get("checklist_verified") is True
        and status.startswith("verified")
        and profile.get("engine") in IMPLEMENTED_ENGINES
        and isinstance(profile.get("verified_on"), str)
        and len(profile["verified_on"]) >= 10
        and isinstance(sources, list)
        and len(sources) >= 1
    )


def get_profile(style_id: str) -> dict:
    for profile in load_profiles():
        if profile.get("id") == style_id:
            return profile
    raise PagedrillRefusal("That style is not on this server.", "unknown_style")


def require_selectable(style_id: str) -> dict:
    profile = get_profile(style_id)
    if not profile["selectable"]:
        raise PagedrillRefusal(
            "That style does not have a fully verified checklist, so it cannot be selected.",
            "style_not_selectable",
        )
    return profile
