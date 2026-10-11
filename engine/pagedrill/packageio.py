"""Splice formatted parts back into the original package and prove the rest is untouched."""

from __future__ import annotations

import hashlib

from .errors import PagedrillRefusal
from .zippack import read_package, write_package

# Layout edits may rewrite these parts. Everything else keeps its original compressed bytes.
ALLOWED_PARTS = {
    "word/document.xml",
    "word/styles.xml",
    "word/header1.xml",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def diff_parts(before: bytes, after: bytes) -> dict:
    old = read_package(before).by_name()
    new = read_package(after).by_name()
    changed: list[str] = []
    removed: list[str] = []
    added: list[str] = []
    untouched: dict[str, str] = {}
    for name, entry in old.items():
        if name not in new:
            removed.append(name)
            continue
        if entry.compressed != new[name].compressed:
            changed.append(name)
        else:
            untouched[name] = _sha(entry.compressed)
    for name in new:
        if name not in old:
            added.append(name)
    changed.sort()
    removed.sort()
    added.sort()
    return {
        "changed_parts": changed,
        "removed_parts": removed,
        "added_parts": added,
        "untouched_part_count": len(untouched),
        "untouched_identical": True,
        "untouched_sha256": untouched,
    }


def splice_allowed(original: bytes, fresh: bytes) -> tuple[bytes, dict]:
    """Keep every untouched part's original compressed bytes. Refuse any other change."""
    old = read_package(original)
    new = read_package(fresh)
    old_map = old.by_name()
    new_map = new.by_name()
    if set(new_map) - set(old_map):
        raise PagedrillRefusal(
            "Formatting would add a package part. Pagedrill did not save the file.",
            "verification_failed",
        )
    if set(old_map) - set(new_map):
        raise PagedrillRefusal(
            "Formatting would remove a package part. Pagedrill did not save the file.",
            "verification_failed",
        )
    replacements: dict[str, bytes] = {}
    for name, entry in new_map.items():
        if entry.data != old_map[name].data:
            if name not in ALLOWED_PARTS:
                raise PagedrillRefusal(
                    "Formatting would change a part it is not allowed to touch. Pagedrill did not save the file.",
                    "verification_failed",
                )
            replacements[name] = entry.data
    if not replacements:
        report = diff_parts(original, original)
        report["untouched_identical"] = True
        return original, report
    out = write_package(old, replacements)
    report = diff_parts(original, out)
    unexpected = [name for name in report["changed_parts"] if name not in ALLOWED_PARTS]
    if unexpected or report["removed_parts"] or report["added_parts"] or not report["untouched_identical"]:
        raise PagedrillRefusal(
            "Untouched-part verification failed. Pagedrill did not save the file.",
            "verification_failed",
        )
    return out, report
