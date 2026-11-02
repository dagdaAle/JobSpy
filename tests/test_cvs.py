"""CV library: storage rules, tailoring endpoint (LLM mocked) and PDF export."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'webapp'), str(ROOT)]
import storage
import analyzer
import cv_render


class CvTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = patch.object(storage, '_DB_PATH', str(Path(self.tmp.name) / 'test.db'))
        self.backups = patch.object(storage, '_BACKUP_DIR', str(Path(self.tmp.name) / 'backups'))
        self.db.start(); self.backups.start()
        storage.init_db()
        storage.configure_analysis('test-model', 'v2')

    def tearDown(self):
        self.db.stop(); self.backups.stop(); self.tmp.cleanup()

    def test_first_base_cv_is_default_and_feeds_analysis(self):
        a = storage.create_cv('A', '# Ale\nPython')
        b = storage.create_cv('B', '# Ale\nLangGraph')
        self.assertEqual(storage.get_cv_text(), '# Ale\nPython')
        storage.set_default_cv(b)
        self.assertEqual(storage.get_cv_text(), '# Ale\nLangGraph')
        self.assertFalse(storage.get_cv(a)['is_default'])
        with self.assertRaises(ValueError):
            storage.delete_cv(b)
        storage.update_cv(b, markdown='# Ale\nFastAPI')
        self.assertEqual(storage.get_cv_text(), '# Ale\nFastAPI')

    def test_tailored_cv_cannot_be_default_and_seed_runs_once(self):
        storage.seed_cv_from_text('testo pdf')
        storage.seed_cv_from_text('altro testo')
        self.assertEqual(len(storage.list_cvs()), 1)
        t = storage.create_cv('T', '# x', kind='tailored', parent_id=1, job_url='u', changes=['c'])
        self.assertEqual(storage.get_cv(t)['changes'], ['c'])
        with self.assertRaises(ValueError):
            storage.set_default_cv(t)

    def test_tailor_endpoint_stores_tailored_cv(self):
        from fastapi.testclient import TestClient
        import app as webapp
        storage.create_cv('Base', '# Ale\nPython')
        storage.upsert_jobs([dict(job_url='https://e.com/1', title='AI Engineer', company='Acme',
                                  description='LangGraph ' * 20)])
        fake = {'markdown': '# Ale\nPython, LangGraph', 'changes': ['Messo in evidenza LangGraph']}
        with patch.object(analyzer, 'tailor_cv', return_value=fake):
            res = TestClient(webapp.app).post('/cvs/tailor', json={'job_url': 'https://e.com/1'})
        self.assertEqual(res.status_code, 201, res.text)
        cv = res.json()['cv']
        self.assertEqual((cv['kind'], cv['parent_id'], cv['job_url']), ('tailored', 1, 'https://e.com/1'))
        pdf = TestClient(webapp.app).get(f"/cvs/{cv['id']}/pdf")
        self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_markdown_to_pdf(self):
        self.assertTrue(cv_render.markdown_to_pdf('# Nome\n## Esperienze\n- uno\n- due').startswith(b'%PDF'))


if __name__ == '__main__':
    unittest.main()
