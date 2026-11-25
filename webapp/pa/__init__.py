"""Concorsi PA area: inPA and Gazzetta Ufficiale notices, separate from the job feed."""

from __future__ import annotations

from typing import Any

from area_common import Area, area_router, llm_json

from pa import evaluate
from pa.sources import FETCHERS


def _extract(item: dict[str, Any]) -> dict[str, Any]:
    return evaluate.normalize(llm_json(evaluate.SYSTEM_PROMPT, evaluate.user_prompt(item)))


AREA = Area(
    prefix="pa",
    fetchers=FETCHERS,
    prompt_version=evaluate.PROMPT_VERSION,
    extract=_extract,
    decide=evaluate.decide,
    default_profile=evaluate.DEFAULT_PROFILE,
    vocabulary=evaluate.AREAS,
)
router = area_router(AREA)
