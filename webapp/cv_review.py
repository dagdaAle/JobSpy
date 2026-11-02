"""Small, explicit edits to an existing CV; never replace its whole body."""
from __future__ import annotations

import hashlib
from typing import Any


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def validate_patches(text: str, patches: list[dict[str, Any]]) -> None:
    if not 1 <= len(patches) <= 6:
        raise ValueError("Seleziona da una a sei correzioni")
    spans: list[tuple[int, int]] = []
    for patch in patches:
        before, after = patch.get("before"), patch.get("after")
        if not isinstance(before, str) or not isinstance(after, str):
            raise ValueError("Correzione non valida")
        if not before.strip() or not after.strip() or before == after:
            raise ValueError("La correzione deve contenere due testi diversi e non vuoti")
        if before.strip() == text.strip():
            raise ValueError("La revisione mirata non può sostituire l'intero CV")
        if len(before) > 500 or len(after) > 750 or before.count("\n") > 4 or after.count("\n") > 4:
            raise ValueError("Sono ammesse solo correzioni brevi, non riscritture del CV")
        if any(line.lstrip().startswith("#") for line in (before + "\n" + after).splitlines()):
            raise ValueError("La revisione mirata mantiene i titoli delle sezioni")
        if text.count(before) != 1:
            raise ValueError("Il passaggio originale deve comparire una sola volta nel CV")
        start = text.index(before)
        end = start + len(before)
        if any(start < b and a < end for a, b in spans):
            raise ValueError("Le correzioni selezionate si sovrappongono")
        spans.append((start, end))


def normalize_review(data: Any, text: str) -> dict[str, Any]:
    if not isinstance(data, dict) or not all(isinstance(data.get(k), list) for k in ("patches", "observations", "questions")):
        raise ValueError("Risposta di revisione non valida: riprova")
    patches: list[dict[str, str]] = []
    for item in data.get("patches", []) if isinstance(data.get("patches"), list) else []:
        if not isinstance(item, dict):
            continue
        patch = {key: item.get(key) for key in ("before", "after")}
        try:
            validate_patches(text, [*patches, patch])
        except ValueError:
            continue
        patches.append({**patch, "reason": str(item.get("reason") or "Chiarezza del testo")[:600]})
        if len(patches) == 6:
            break
    def strings(key: str) -> list[str]:
        values = data.get(key)
        return [v.strip()[:800] for v in values[:8] if isinstance(v, str) and v.strip()] if isinstance(values, list) else []
    return {"source_hash": source_hash(text), "patches": patches,
            "observations": strings("observations"), "questions": strings("questions")}


def apply_patches(text: str, patches: list[dict[str, Any]]) -> str:
    validate_patches(text, patches)
    # Apply against original positions: replacement text must never be edited
    # by a later patch that happens to contain the same words.
    edits = sorted(((text.index(p["before"]), p) for p in patches), reverse=True)
    for start, patch in edits:
        text = text[:start] + patch["after"] + text[start + len(patch["before"]):]
    return text
