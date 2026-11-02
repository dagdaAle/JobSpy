"""Read ordinary and two-column CV PDFs without interleaving their text."""
from __future__ import annotations

import re


def page_text(page) -> str:
    words = page.extract_words()
    if len(words) < 30:
        return page.extract_text() or ""
    body = [w for w in words if w["top"] > page.height * 0.18]
    candidates = []
    for fraction in range(23, 42):
        split = page.width * fraction / 100
        crossings = sum(w["x0"] < split < w["x1"] for w in body)
        left = [w for w in words if w["x1"] < split]
        right = [w for w in words if w["x0"] > split]
        if crossings <= max(1, len(body) // 200) and len(left) >= 20 and len(right) >= 30:
            candidates.append((crossings, abs(fraction - 30), split, left, right))
    if not candidates:
        return page.extract_text() or ""
    _, _, split, left, right = min(candidates, key=lambda c: c[:2])
    # Newer Europass headers span the top; older variants put the name on the left.
    first_left, first_right = min(w["top"] for w in left), min(w["top"] for w in right)
    cutoff = max(0, (first_left if first_left > 100 else first_right) - 2)
    header = page.crop((0, 0, page.width, cutoff)).extract_text() if cutoff else ""
    main = page.crop((split, cutoff, page.width, page.height)).extract_text() or ""
    side = page.crop((0, cutoff, split, page.height)).extract_text() or ""
    result = "\n\n".join(part for part in [header, main, side] if part)
    # Restore a section heading wrapped by the narrow original sidebar.
    return re.sub(r"(?im)^Competenze\n(linguistiche|tecniche|digitali)\s*$", r"Competenze \1", result)
