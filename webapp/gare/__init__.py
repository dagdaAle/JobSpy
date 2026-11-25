"""Gare P.IVA area: EU public tenders (TED), separate from the job feed."""

from __future__ import annotations

from typing import Any

from area_common import Area, area_router, llm_json

from gare import evaluate
from gare.sources import FETCHERS, within_budget


def _extract(item: dict[str, Any]) -> dict[str, Any]:
    return evaluate.normalize(llm_json(evaluate.SYSTEM_PROMPT, evaluate.user_prompt(item)))


AREA = Area(
    prefix="gare",
    fetchers=FETCHERS,
    prompt_version=evaluate.PROMPT_VERSION,
    extract=_extract,
    decide=evaluate.decide,
    default_profile=evaluate.DEFAULT_PROFILE,
    vocabulary=evaluate.SERVICES,
    post_filter=within_budget,
)
router = area_router(AREA)
