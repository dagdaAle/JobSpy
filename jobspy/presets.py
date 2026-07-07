"""
Convenience presets for common searches, tuned for the Italian market and for
remote-only job boards.

These are thin wrappers around :func:`jobspy.scrape_jobs`; they don't add new
scraping logic, they just fix the ergonomics that make Italian searches fail in
the raw API:

* ``distance`` in JobSpy is expressed in **miles**. In Italy people think in
  **kilometers**, so ``search_italy`` accepts ``distance_km`` and converts it.
* Indeed/Glassdoor Italy index Italian-language postings, so an English-only
  ``search_term`` under-matches. ``search_italy`` can broaden the query.
* ``country_indeed`` must be ``"Italy"`` for the Italian Indeed/Glassdoor
  domains; the preset sets it automatically.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from jobspy import scrape_jobs

# Boards that operate on the local Indeed/Glassdoor domain (support country_indeed).
ITALY_LOCAL_SITES = ["indeed", "glassdoor", "linkedin"]

# Remote-only boards added by this fork.
REMOTE_ONLY_SITES = ["remotive", "remoteok", "weworkremotely", "workingnomads"]

_MILES_PER_KM = 0.621371


def km_to_miles(distance_km: float) -> int:
    """Convert kilometers to whole miles (JobSpy's distance unit)."""
    return max(1, round(distance_km * _MILES_PER_KM))


def search_italy(
    search_term: str,
    location: str,
    *,
    distance_km: int = 25,
    results_wanted: int = 25,
    hours_old: int | None = None,
    include_linkedin: bool = True,
    sites: list[str] | None = None,
    **kwargs,
) -> pd.DataFrame:
    """
    Search Italian job boards around a city, with sensible Italian defaults.

    :param search_term: e.g. "sviluppatore" or "python developer".
    :param location: e.g. "Verona" (region is helpful: "Verona, Veneto").
    :param distance_km: radius in KILOMETERS (converted to miles internally).
    :param results_wanted: results per site.
    :param hours_old: only jobs posted within N hours (optional).
    :param include_linkedin: include LinkedIn (global, no country filter).
    :param sites: override the site list entirely.
    """
    if sites is None:
        sites = ["indeed", "glassdoor"]
        if include_linkedin:
            sites.append("linkedin")

    return scrape_jobs(
        site_name=sites,
        search_term=search_term,
        location=location,
        distance=km_to_miles(distance_km),
        country_indeed="Italy",
        results_wanted=results_wanted,
        hours_old=hours_old,
        **kwargs,
    )


def search_site(
    site: str,
    search_term: str,
    *,
    location: str = "",
    distance_km: int = 25,
    results_wanted: int = 25,
    hours_old: int | None = None,
    is_remote: bool = False,
    **kwargs,
) -> pd.DataFrame:
    """
    Scrape a **single** job board with one query, returning the full DataFrame
    (no columns dropped). This is the per-site "channel" primitive.

    Two worlds are handled automatically:

    * Local Italian boards (``indeed``, ``glassdoor``, ``linkedin``) get
      ``location``, ``distance`` (km -> miles), ``country_indeed="Italy"`` and
      ``hours_old``. For ``indeed``/``linkedin`` we set
      ``linkedin_fetch_description=True`` so the full description is fetched
      (needed by the detail page).
    * Remote-only boards (``remotive``, ``remoteok``, ``weworkremotely``,
      ``workingnomads``) are scraped with ``is_remote=True`` and no
      location/distance.

    :param site: one site name, e.g. ``"indeed"`` or ``"remotive"``.
    :param search_term: the query for that site.
    :param location: city (Italian boards only), e.g. ``"Verona, Veneto"``.
    :param distance_km: radius in KILOMETERS (Italian boards only).
    :param results_wanted: number of results to fetch.
    :param hours_old: only jobs posted within N hours (optional).
    :param is_remote: force a remote search (implied for remote-only boards).
    """
    site = site.strip().lower()

    if site in REMOTE_ONLY_SITES:
        return scrape_jobs(
            site_name=[site],
            search_term=search_term,
            results_wanted=results_wanted,
            is_remote=True,
            **kwargs,
        )

    # Local Italian boards (indeed / glassdoor / linkedin) — and any other site
    # treated as location-aware.
    params: dict[str, Any] = {
        "site_name": [site],
        "search_term": search_term,
        "results_wanted": results_wanted,
        "country_indeed": "Italy",
        "is_remote": is_remote,
    }
    if location:
        params["location"] = location
        params["distance"] = km_to_miles(distance_km)
    if hours_old is not None:
        params["hours_old"] = hours_old
    if site in ("indeed", "linkedin"):
        # Fetch full descriptions so the detail page has rich content.
        params["linkedin_fetch_description"] = True

    params.update(kwargs)
    return scrape_jobs(**params)


def search_remote(
    search_term: str,
    *,
    results_wanted: int = 25,
    sites: list[str] | None = None,
    include_indeed_remote: bool = False,
    **kwargs,
) -> pd.DataFrame:
    """
    Search remote-only job boards (Remotive, RemoteOK, WeWorkRemotely,
    Working Nomads). Location/distance are ignored — every result is remote.

    :param search_term: e.g. "python", "react", "devops".
    :param results_wanted: results per site.
    :param include_indeed_remote: also query Indeed Italy with is_remote=True.
    :param sites: override the remote site list entirely.
    """
    if sites is None:
        sites = list(REMOTE_ONLY_SITES)

    frames = [
        scrape_jobs(
            site_name=sites,
            search_term=search_term,
            results_wanted=results_wanted,
            is_remote=True,
            **kwargs,
        )
    ]

    if include_indeed_remote:
        frames.append(
            scrape_jobs(
                site_name=["indeed"],
                search_term=search_term,
                location="Italia",
                country_indeed="Italy",
                is_remote=True,
                results_wanted=results_wanted,
            )
        )

    non_empty = [f for f in frames if f is not None and not f.empty]
    if not non_empty:
        return pd.DataFrame()
    return pd.concat(non_empty, ignore_index=True)
