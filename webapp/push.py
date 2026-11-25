"""
Web Push (VAPID) for the installed PWA: subscriptions, sending, and one grouped
notification per area after the scheduler run (specs/005-pwa-notifiche).

The keys come only from the environment; without them nothing is sent. What
counts as news reuses the decisions the areas already compute (ADR 005/007).
"""

from __future__ import annotations

import datetime
import json
import os
import traceback
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse

import storage
from area_common import Area
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pywebpush import WebPushException, webpush

AREAS = ("lavoro", "pa", "gare")
LABELS = {"lavoro": "Lavoro", "pa": "Concorsi PA", "gare": "Gare P.IVA"}
URLS = {"lavoro": "/", "pa": "/?area=pa", "gare": "/?area=gare"}
# At most one notification per area in this many hours; what is held back goes in the next one.
MIN_HOURS = float(os.environ.get("PUSH_MIN_HOURS", "12"))
DEADLINE_DAYS = 3
# Only real push services: the server POSTs to the endpoint, so it must not be any URL.
PUSH_HOSTS = (
    "push.apple.com",
    "googleapis.com",
    "push.services.mozilla.com",
    "notify.windows.com",
)


def _keys() -> tuple[str, str, str]:
    return (
        os.environ.get("VAPID_PUBLIC_KEY", ""),
        os.environ.get("VAPID_PRIVATE_KEY", ""),
        os.environ.get("VAPID_SUBJECT", ""),
    )


def configured() -> bool:
    return all(_keys())


# ------------------------------------------------------------------ storage
def init_tables() -> None:
    with storage._lock, storage._connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                endpoint TEXT PRIMARY KEY, p256dh TEXT NOT NULL, auth TEXT NOT NULL,
                areas TEXT NOT NULL DEFAULT '["lavoro", "pa", "gare"]',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS push_sent (
                area TEXT NOT NULL, key TEXT NOT NULL, kind TEXT NOT NULL,
                sent_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (area, key, kind)
            );
        """)


def subscribe(
    endpoint: str, p256dh: str, auth: str, areas: list[str] | None
) -> list[str]:
    """Insert or refresh a subscription; ``areas`` None keeps the stored choice."""
    with storage._lock, storage._connect() as conn:
        conn.execute(
            "INSERT INTO push_subscriptions (endpoint, p256dh, auth) VALUES (?, ?, ?) "
            "ON CONFLICT(endpoint) DO UPDATE SET p256dh = excluded.p256dh, auth = excluded.auth",
            (endpoint, p256dh, auth),
        )
        if areas is not None:
            conn.execute(
                "UPDATE push_subscriptions SET areas = ? WHERE endpoint = ?",
                (json.dumps([a for a in AREAS if a in areas]), endpoint),
            )
        row = conn.execute(
            "SELECT areas FROM push_subscriptions WHERE endpoint = ?", (endpoint,)
        ).fetchone()
    areas_saved: list[str] = json.loads(row["areas"])
    return areas_saved


def unsubscribe(endpoint: str) -> None:
    with storage._lock, storage._connect() as conn:
        conn.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))


def subscriptions(
    area: str | None = None, endpoint: str | None = None
) -> list[dict[str, Any]]:
    with storage._lock, storage._connect() as conn:
        rows = conn.execute("SELECT * FROM push_subscriptions").fetchall()
    out = [dict(r) | {"areas": json.loads(r["areas"])} for r in rows]
    return [
        s
        for s in out
        if (area is None or area in s["areas"])
        and (endpoint is None or s["endpoint"] == endpoint)
    ]


def _unsent(
    area: str, kind: str, items: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    with storage._lock, storage._connect() as conn:
        sent = {
            r[0]
            for r in conn.execute(
                "SELECT key FROM push_sent WHERE area = ? AND kind = ?", (area, kind)
            )
        }
    return [i for i in items if i[0] not in sent]


def _mark_sent(area: str, kind: str, items: list[tuple[str, str]]) -> None:
    with storage._lock, storage._connect() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO push_sent (area, key, kind) VALUES (?, ?, ?)",
            [(area, key, kind) for key, _ in items],
        )
        conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (f"push_last_{area}", storage._now()),
        )


def _too_soon(area: str) -> bool:
    with storage._lock, storage._connect() as conn:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = ?", (f"push_last_{area}",)
        ).fetchone()
    if not row:
        return False
    last = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=datetime.timezone.utc
    )
    return datetime.datetime.now(datetime.timezone.utc) - last < datetime.timedelta(
        hours=MIN_HOURS
    )


# ------------------------------------------------------------------ sending
def send(
    payload: dict[str, Any], area: str | None = None, endpoint: str | None = None
) -> int:
    """Send to every matching subscription; returns how many accepted it. Gone ones (404/410) are deleted."""
    public, private, subject = _keys()
    if not (public and private and subject):
        return 0
    sent = 0
    for sub in subscriptions(area, endpoint):
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                },
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=private,
                vapid_claims={"sub": subject},
                ttl=24 * 3600,
                timeout=10,
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                unsubscribe(sub["endpoint"])
            else:
                print(f"[push] send failed ({status}): {exc}", flush=True)
        except Exception as exc:  # network errors must not stop the caller
            print(f"[push] send failed: {exc}", flush=True)
    return sent


# ------------------------------------------------------------ what to notify
def _lavoro_items() -> list[tuple[str, str]]:
    """Feed jobs the analysis says to apply to, without a verdict or an application."""
    analysis = storage.get_all_analysis()
    feedback = storage.get_all_feedback()
    applications = storage.get_applications()
    return [
        (j["job_url"], j.get("title") or "")
        for j in storage.get_all_jobs()
        if (analysis.get(j["job_url"]) or {}).get("assessment", {}).get("decision")
        == "apply"
        and j["job_url"] not in feedback
        and j["job_url"] not in applications
    ]


def _area_items(area: Area) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(``adatto`` items in the feed, saved or ``adatto`` items due within DEADLINE_DAYS — PA only)."""
    feed = area.items("feed", None)
    fits = [i for i in feed if i["decision"] == "adatto"]
    if area.store.p != "pa":
        return [(i["key"], i["title"]) for i in fits], []
    today = datetime.date.today()
    last = (today + datetime.timedelta(days=DEADLINE_DAYS)).isoformat()
    due = [
        i
        for i in fits + area.items("saved", None)
        if i.get("deadline") and today.isoformat() <= i["deadline"][:10] <= last
    ]
    return [(i["key"], i["title"]) for i in fits], list(
        {i["key"]: (i["key"], i["title"]) for i in due}.values()
    )


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def digest(
    area: str, new: list[tuple[str, str]], due: list[tuple[str, str]]
) -> dict[str, Any] | None:
    """One grouped payload for an area, or None when there is nothing to say."""
    if not new and not due:
        return None
    parts = []
    if new:
        parts.append(
            {
                "lavoro": _plural(
                    len(new), "offerta da candidarti", "offerte da candidarti"
                ),
                "pa": _plural(len(new), "bando adatto", "bandi adatti"),
                "gare": _plural(len(new), "gara adatta", "gare adatte"),
            }[area]
        )
    if due:
        parts.append(
            _plural(len(due), "bando", "bandi")
            + f" in scadenza entro {DEADLINE_DAYS} giorni"
        )
    titles = [t for _, t in (new + due) if t][:3]
    more = "…" if len(new) + len(due) > len(titles) else ""
    body = " · ".join(parts) + ("\n" + ", ".join(titles) + more if titles else "")
    return {
        "title": f"JobSpy · {LABELS[area]}",
        "body": body,
        "url": URLS[area],
        "tag": f"jobspy-{area}",
    }


def notify(names: Iterable[str], areas: Sequence[Area]) -> int:
    """After a scheduler run: one notification per area with something new. Never raises."""
    if not configured() or not subscriptions():
        return 0
    by_prefix = {a.store.p: a for a in areas}
    count = 0
    for name in names:
        try:
            if _too_soon(name) or not subscriptions(name):
                continue
            new, due = (
                (_lavoro_items(), [])
                if name == "lavoro"
                else _area_items(by_prefix[name])
            )
            new, due = _unsent(name, "new", new), _unsent(name, "deadline", due)
            payload = digest(name, new, due)
            if payload and send(payload, area=name):
                _mark_sent(name, "new", new)
                _mark_sent(name, "deadline", due)
                count += 1
        except Exception:
            print(f"[push] {name} notification failed:", flush=True)
            traceback.print_exc()
    return count


# --------------------------------------------------------------------- API
class SubscriptionIn(BaseModel):
    endpoint: str = Field(min_length=1, max_length=1000, pattern=r"^https://")
    keys: dict[str, str]
    areas: list[str] | None = None


class EndpointIn(BaseModel):
    endpoint: str = Field(min_length=1, max_length=1000)


router = APIRouter(prefix="/push", tags=["push"])


@router.get("/key")
def get_key() -> dict[str, Any]:
    return {"configured": configured(), "public_key": _keys()[0] or None}


@router.post("/subscribe")
def post_subscribe(req: SubscriptionIn) -> dict[str, Any]:
    host = urlparse(req.endpoint).hostname or ""
    if not any(host == h or host.endswith("." + h) for h in PUSH_HOSTS):
        raise HTTPException(status_code=422, detail="Servizio push non riconosciuto.")
    p256dh, auth = req.keys.get("p256dh", ""), req.keys.get("auth", "")
    if not (0 < len(p256dh) <= 200 and 0 < len(auth) <= 100):
        raise HTTPException(
            status_code=422, detail="Chiavi della sottoscrizione mancanti."
        )
    return {"areas": subscribe(req.endpoint, p256dh, auth, req.areas)}


@router.post("/unsubscribe")
def post_unsubscribe(req: EndpointIn) -> dict[str, Any]:
    unsubscribe(req.endpoint)
    return {"ok": True}


@router.post("/test")
def post_test(req: EndpointIn) -> dict[str, Any]:
    if not configured():
        raise HTTPException(
            status_code=503,
            detail="Notifiche non configurate: mancano le chiavi VAPID sul server.",
        )
    sent = send(
        {
            "title": "JobSpy",
            "body": "Notifica di prova: funziona.",
            "url": "/",
            "tag": "jobspy-test",
        },
        endpoint=req.endpoint,
    )
    if not sent:
        raise HTTPException(
            status_code=502,
            detail="Invio non riuscito: riattiva le notifiche su questo dispositivo.",
        )
    return {"sent": sent}
