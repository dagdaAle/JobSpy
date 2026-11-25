"""Offline tests for Web Push: no push service is ever called. Every endpoint, key and title is invented."""

import datetime
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "webapp"), str(ROOT)]
import push
import storage
from fastapi.testclient import TestClient
from pywebpush import WebPushException

KEYS = {
    "VAPID_PUBLIC_KEY": "pub",
    "VAPID_PRIVATE_KEY": "priv",
    "VAPID_SUBJECT": "mailto:test@example.invalid",
}
EP1 = "https://web.push.apple.com/one"
EP2 = "https://fcm.googleapis.com/fcm/send/two"


def in_days(n):
    return (datetime.date.today() + datetime.timedelta(days=n)).isoformat()


def fake_area(prefix, feed, saved=()):
    area = MagicMock()
    area.store.p = prefix
    area.items.side_effect = lambda view, _c: list(feed if view == "feed" else saved)
    return area


def it(key, decision="adatto", deadline=None):
    return {
        "key": key,
        "title": f"Titolo {key}",
        "decision": decision,
        "deadline": deadline,
    }


class PushTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = patch.object(
            storage, "_DB_PATH", str(Path(self.tmp.name) / "test.db")
        )
        self.db.start()
        storage.init_db()
        push.init_tables()
        self.env = patch.dict(os.environ, KEYS)
        self.env.start()
        self.webpush = patch.object(push, "webpush")
        self.sent = self.webpush.start()

    def tearDown(self):
        self.webpush.stop()
        self.env.stop()
        self.db.stop()
        self.tmp.cleanup()

    def client(self):
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(push.router)
        return TestClient(app)

    def test_subscribe_keeps_areas_and_unsubscribe(self):
        c = self.client()
        body = {"endpoint": EP1, "keys": {"p256dh": "k", "auth": "a"}}
        self.assertEqual(
            c.post("/push/subscribe", json=body).json()["areas"], list(push.AREAS)
        )
        self.assertEqual(
            c.post("/push/subscribe", json={**body, "areas": ["pa"]}).json()["areas"],
            ["pa"],
        )
        self.assertEqual(
            c.post("/push/subscribe", json=body).json()["areas"], ["pa"]
        )  # re-subscribe keeps choice
        self.assertEqual(
            c.post("/push/unsubscribe", json={"endpoint": EP1}).status_code, 200
        )
        self.assertEqual(push.subscriptions(), [])

    def test_subscribe_rejects_unknown_hosts_and_missing_keys(self):
        c = self.client()
        self.assertEqual(
            c.post(
                "/push/subscribe",
                json={
                    "endpoint": "https://evil.example/x",
                    "keys": {"p256dh": "k", "auth": "a"},
                },
            ).status_code,
            422,
        )
        self.assertEqual(
            c.post(
                "/push/subscribe",
                json={
                    "endpoint": "http://web.push.apple.com/x",
                    "keys": {"p256dh": "k", "auth": "a"},
                },
            ).status_code,
            422,
        )
        self.assertEqual(
            c.post("/push/subscribe", json={"endpoint": EP1, "keys": {}}).status_code,
            422,
        )

    def test_key_and_no_send_without_keys(self):
        push.subscribe(EP1, "k", "a", None)
        with patch.dict(os.environ, {"VAPID_PRIVATE_KEY": ""}):
            c = self.client()
            self.assertEqual(
                c.get("/push/key").json(), {"configured": False, "public_key": "pub"}
            )
            self.assertEqual(
                c.post("/push/test", json={"endpoint": EP1}).status_code, 503
            )
            self.assertEqual(push.send({"title": "t"}), 0)
            self.assertEqual(push.notify(["gare"], [fake_area("gare", [it("g1")])]), 0)
        self.sent.assert_not_called()

    def test_send_mocked_and_gone_subscription_removed(self):
        push.subscribe(EP1, "k", "a", None)
        push.subscribe(EP2, "k", "a", None)
        gone = WebPushException("gone", response=MagicMock(status_code=410))
        self.sent.side_effect = [None, gone]
        self.assertEqual(push.send({"title": "t", "body": "b"}), 1)
        self.assertEqual([s["endpoint"] for s in push.subscriptions()], [EP1])
        args = self.sent.call_args_list[0].kwargs
        self.assertEqual(args["vapid_private_key"], "priv")
        self.assertEqual(json.loads(args["data"])["title"], "t")

    def test_other_errors_keep_subscription_and_test_endpoint(self):
        push.subscribe(EP1, "k", "a", None)
        self.sent.side_effect = WebPushException(
            "boom", response=MagicMock(status_code=500)
        )
        self.assertEqual(
            self.client().post("/push/test", json={"endpoint": EP1}).status_code, 502
        )
        self.assertEqual(len(push.subscriptions()), 1)
        self.sent.side_effect = None
        self.assertEqual(
            self.client().post("/push/test", json={"endpoint": EP1}).json(), {"sent": 1}
        )

    def test_grouped_once_and_rate_limited(self):
        push.subscribe(EP1, "k", "a", None)
        gare = fake_area(
            "gare",
            [it("g1"), it("g2"), it("g3", "non_adatto"), it("g4", "da_valutare")],
        )
        self.assertEqual(push.notify(["gare"], [gare]), 1)
        self.assertEqual(
            self.sent.call_count, 1
        )  # one notification for the area, not one per item
        payload = json.loads(self.sent.call_args.kwargs["data"])
        self.assertEqual(payload["url"], "/?area=gare")
        self.assertTrue(payload["body"].startswith("2 gare adatte"))
        # New item, but inside the rate limit: nothing; the item is kept for later.
        gare.items.side_effect = lambda view, _c: (
            [it("g1"), it("g5")] if view == "feed" else []
        )
        self.assertEqual(push.notify(["gare"], [gare]), 0)
        with patch.object(push, "MIN_HOURS", 0):
            self.assertEqual(push.notify(["gare"], [gare]), 1)
            self.assertIn(
                "1 gara adatta", json.loads(self.sent.call_args.kwargs["data"])["body"]
            )
            self.assertEqual(
                push.notify(["gare"], [gare]), 0
            )  # nothing new: no notification
        self.assertEqual(self.sent.call_count, 2)

    def test_area_switch_off_and_no_subscriptions(self):
        self.assertEqual(push.notify(["gare"], [fake_area("gare", [it("g1")])]), 0)
        push.subscribe(EP1, "k", "a", ["pa"])
        self.assertEqual(push.notify(["gare"], [fake_area("gare", [it("g1")])]), 0)
        self.sent.assert_not_called()

    def test_failed_send_is_retried_next_time(self):
        push.subscribe(EP1, "k", "a", None)
        self.sent.side_effect = OSError("offline")
        gare = fake_area("gare", [it("g1")])
        self.assertEqual(push.notify(["gare"], [gare]), 0)
        self.sent.side_effect = None
        self.assertEqual(push.notify(["gare"], [gare]), 1)

    def test_pa_deadline_reminder(self):
        feed = [
            it("fit", deadline=in_days(10)),
            it("soon", deadline=in_days(2)),
            it("maybe", "da_valutare", in_days(1)),
        ]
        saved = [
            it("liked", "da_valutare", in_days(3)),
            it("late", "adatto", in_days(5)),
            it("gone", "adatto", in_days(-1)),
        ]
        new, due = push._area_items(fake_area("pa", feed, saved))
        self.assertEqual({k for k, _ in new}, {"fit", "soon"})
        self.assertEqual({k for k, _ in due}, {"soon", "liked"})
        body = push.digest("pa", new, due)["body"]
        self.assertTrue(
            body.startswith("2 bandi adatti · 2 bandi in scadenza entro 3 giorni")
        )
        self.assertIsNone(push.digest("pa", [], []))

    def test_lavoro_selects_apply_without_verdict(self):
        jobs = [
            {"job_url": u, "title": u}
            for u in ("apply", "maybe", "liked", "applied", "none")
        ]
        analysis = {
            u: {"assessment": {"decision": d}}
            for u, d in (
                ("apply", "apply"),
                ("maybe", "maybe"),
                ("liked", "apply"),
                ("applied", "apply"),
            )
        }
        with (
            patch.object(storage, "get_all_jobs", return_value=jobs),
            patch.object(storage, "get_all_analysis", return_value=analysis),
            patch.object(storage, "get_all_feedback", return_value={"liked": "like"}),
            patch.object(storage, "get_applications", return_value={"applied": {}}),
        ):
            self.assertEqual(push._lavoro_items(), [("apply", "apply")])
            push.subscribe(EP1, "k", "a", None)
            self.assertEqual(push.notify(["lavoro"], []), 1)
        payload = json.loads(self.sent.call_args.kwargs["data"])
        self.assertEqual(
            (payload["url"], payload["body"]), ("/", "1 offerta da candidarti\napply")
        )

    def test_notify_never_raises(self):
        push.subscribe(EP1, "k", "a", None)
        broken = fake_area("gare", [])
        broken.items.side_effect = RuntimeError("db")
        self.assertEqual(
            push.notify(["gare", "pa"], [broken]), 0
        )  # 'pa' missing too: logged, skipped


if __name__ == "__main__":
    unittest.main()
