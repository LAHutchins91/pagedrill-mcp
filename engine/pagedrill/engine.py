"""JSON dispatch used by the MCP server. Styles that are not fully verified are refused."""

from __future__ import annotations

import base64
import hashlib
import zipfile
from io import BytesIO

from .apa import format_apa
from .bibliography import render_imported
from .checks import evaluate
from .errors import PagedrillRefusal
from .ieee import format_ieee
from .vancouver import format_vancouver
from .memo import create_memo, format_memo
from .profiles import load_profiles, require_selectable

MAX_BYTES = 25 * 1024 * 1024


def dispatch(payload: dict) -> dict:
    try:
        return {"ok": True, "result": _run(payload)}
    except PagedrillRefusal as exc:
        return {"ok": False, "error": {"code": exc.code, "reason": str(exc)}}
    except Exception:
        return {"ok": False, "error": {"code": "engine_error", "reason": "The file engine could not complete this request. The file was not changed."}}


def _run(payload: dict) -> dict:
    action = payload.get("action")
    if action == "list_styles":
        styles = []
        for profile in load_profiles():
            if profile.get("hidden") is True and not profile.get("selectable"):
                continue
            styles.append(
                {
                    "id": profile.get("id"),
                    "name": profile.get("name"),
                    "engine": profile.get("engine"),
                    "selectable": profile.get("selectable"),
                    "status": profile.get("status"),
                    "verified_on": profile.get("verified_on"),
                    "checklist_verified": profile.get("checklist_verified") is True,
                }
            )
        return {"styles": styles}
    if action == "inspect":
        _docx(_decode(payload))
        return {"kind": "docx"}
    if action == "check":
        profile = require_selectable(str(payload.get("style_id") or ""))
        original = _decode(payload)
        report = evaluate(original, profile)
        return {"checklist": report, "notice": _notice(profile)}
    if action == "format":
        profile = require_selectable(str(payload.get("style_id") or ""))
        original = _decode(payload)
        supplied = payload.get("supplied") if isinstance(payload.get("supplied"), dict) else {}
        if profile["engine"] == "apa-author-date":
            formatted = format_apa(original, profile, supplied)
        elif profile["engine"] == "ar25-50-memorandum":
            formatted = format_memo(original, profile, supplied)
        elif profile["engine"] == "ieee-conference":
            formatted = format_ieee(original, profile, supplied)
        elif profile["engine"] == "vancouver":
            formatted = format_vancouver(original, profile, supplied)
        else:
            raise PagedrillRefusal("That style is not implemented.", "style_not_selectable")
        checklist = evaluate(formatted["docx"], profile, original)
        if checklist["counts"]["FAIL"]:
            raise PagedrillRefusal("The formatted document failed a verified checklist rule. Pagedrill did not save it.", "checklist_failed")
        data = formatted["docx"]
        verification = formatted["verification"]
        return {
            "data_b64": base64.b64encode(data).decode("ascii"),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
            "changes": formatted["changes"],
            "flags": formatted["flags"],
            "verification": {
                "changed_parts": verification.get("changed_parts"),
                "removed_parts": verification.get("removed_parts"),
                "added_parts": verification.get("added_parts"),
                "untouched_part_count": verification.get("untouched_part_count"),
                "untouched_identical": verification.get("untouched_identical"),
                "basis": verification.get("basis") or "in-place",
            },
            "checklist": checklist,
            "notice": formatted.get("notice") or _notice(profile),
            "title": formatted.get("title"),
        }
    if action == "render_references":
        profile = require_selectable(str(payload.get("style_id") or ""))
        kind = str(payload.get("format") or "")
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            raise PagedrillRefusal("The reference file was empty.", "bad_request")
        return render_imported(text, kind, profile)
    if action == "create_memo":
        profile = require_selectable("army-ar25-50-memorandum")
        fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
        created = create_memo(profile, fields)
        checklist = evaluate(created["docx"], profile)
        if checklist["counts"]["FAIL"]:
            raise PagedrillRefusal("The memorandum failed a verified checklist rule. Pagedrill did not save it.", "checklist_failed")
        data = created["docx"]
        return {
            "data_b64": base64.b64encode(data).decode("ascii"),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
            "changes": created["changes"],
            "flags": created["flags"],
            "verification": created["verification"],
            "checklist": checklist,
            "notice": created.get("notice"),
            "title": created.get("title"),
        }
    raise PagedrillRefusal("Unknown engine action.", "bad_request")


def _decode(payload: dict) -> bytes:
    raw = payload.get("data_b64")
    if not isinstance(raw, str):
        raise PagedrillRefusal("The document was not included.", "bad_request")
    try:
        data = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise PagedrillRefusal("The document could not be read.", "bad_request") from exc
    if len(data) > MAX_BYTES:
        raise PagedrillRefusal("This file is above the 25 MB limit.", "file_too_large")
    return data


def _docx(data: bytes) -> None:
    if not zipfile.is_zipfile(BytesIO(data)):
        raise PagedrillRefusal("Pagedrill accepts .docx files.", "unsupported_format")
    try:
        with zipfile.ZipFile(BytesIO(data)) as package:
            names = set(package.namelist())
    except zipfile.BadZipFile as exc:
        raise PagedrillRefusal("Pagedrill accepts .docx files.", "unsupported_format") from exc
    if "word/document.xml" not in names:
        raise PagedrillRefusal("Pagedrill accepts .docx files.", "unsupported_format")


def _notice(profile: dict) -> str | None:
    if profile.get("engine") == "ar25-50-memorandum":
        return (
            "Unclassified drafting aid only. Pagedrill is not endorsed by the Department of Defense "
            "and does not display the DoD seal. Do not upload classified information or controlled unclassified information."
        )
    return None
