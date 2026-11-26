from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'webapp'), str(ROOT)]
import storage


class MobileGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = patch.object(storage, '_DB_PATH', str(Path(self.tmp.name) / 'test.db'))
        self.db.start()
        storage.init_db()
        import app
        for area in app._AREAS:
            area.store.init_tables()
        from fastapi.testclient import TestClient
        self.client = TestClient(app.app)

    def tearDown(self):
        self.db.stop(); self.tmp.cleanup()

    def get(self, path, key=None):
        return self.client.get(path, headers={'X-Api-Key': key} if key else {})

    def test_disabled_without_server_key(self):
        with patch.dict(os.environ, {'MOBILE_API_KEY': ''}):
            r = self.get('/mobile/pa/meta', 'x')
        self.assertEqual((r.status_code, r.json()['detail']), (503, 'accesso mobile non configurato'))

    def test_wrong_or_missing_key(self):
        with patch.dict(os.environ, {'MOBILE_API_KEY': 'segreta'}):
            self.assertEqual(self.get('/mobile/pa/meta').status_code, 401)
            self.assertEqual(self.get('/mobile/pa/meta', 'sbagliata').status_code, 401)

    def test_right_key_reaches_same_route(self):
        with patch.dict(os.environ, {'MOBILE_API_KEY': 'segreta'}):
            mobile = self.get('/mobile/pa/meta', 'segreta')
            self.assertEqual(self.get('/mobile/openapi.json', 'segreta').status_code, 200)
            # Unknown path: JSON 404, never the SPA.
            missing = self.get('/mobile/nope', 'segreta')
        self.assertEqual(mobile.status_code, 200, mobile.text)
        self.assertEqual(mobile.json(), self.get('/pa/meta').json())
        self.assertEqual((missing.status_code, missing.json()), (404, {'detail': 'Not Found'}))

    def test_every_area_and_query_string(self):
        with patch.dict(os.environ, {'MOBILE_API_KEY': 'segreta'}):
            status = self.get('/mobile/status', 'segreta')
            gare = self.get('/mobile/gare/meta', 'segreta')
            # The query string survives the prefix strip: the route answers its own 404.
            job = self.get('/mobile/job?url=https%3A%2F%2Fexample.com%2Fjob%3Fid%3D1', 'segreta')
        self.assertEqual(status.status_code, 200)
        self.assertIn('feed_days', status.json())
        self.assertEqual(gare.status_code, 200, gare.text)
        self.assertEqual((job.status_code, job.json()), (404, {'detail': 'Lavoro non trovato.'}))

    def test_static_files_and_wrong_method_never_reach_the_spa(self):
        with patch.dict(os.environ, {'MOBILE_API_KEY': 'segreta'}):
            index = self.get('/mobile/index.html', 'segreta')
            root = self.get('/mobile/', 'segreta')
            wrong = self.client.delete('/mobile/status', headers={'X-Api-Key': 'segreta'})
        for r in (index, root):
            self.assertEqual((r.status_code, r.headers['content-type']), (404, 'application/json'))
        self.assertEqual(wrong.status_code, 405)

    def test_key_is_checked_before_routing(self):
        with patch.dict(os.environ, {'MOBILE_API_KEY': 'segreta'}):
            r = self.get('/mobile/nope', 'sbagliata')
        self.assertEqual((r.status_code, r.json()['detail']), (401, 'chiave API non valida'))


if __name__ == '__main__':
    unittest.main()
