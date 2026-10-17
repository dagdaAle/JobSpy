"""Review previews cannot overwrite a CV or silently apply stale edits."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'webapp'), str(ROOT)]
import analyzer
import cv_review
import cv_render
import storage
from fastapi.testclient import TestClient
import app as webapp


class CvReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = patch.object(storage, '_DB_PATH', str(Path(self.tmp.name) / 'test.db'))
        self.backups = patch.object(storage, '_BACKUP_DIR', str(Path(self.tmp.name) / 'backups'))
        self.db.start(); self.backups.start()
        storage.init_db()
        storage.configure_analysis('test', 'v2')
        self.text = '# Test Candidate\n\ntest@example.com\n\n## Esperienze\n\nSviluppo API REST con FastAPI.\n\n## Competenze\n\nPython, Docker, Git'
        self.id = storage.create_cv('Base', self.text)
        self.client = TestClient(webapp.app)
        self.patch = {'before': 'Sviluppo API REST con FastAPI.',
                      'after': 'Progettazione e sviluppo di API REST con FastAPI.', 'reason': 'Chiarezza delle mansioni'}

    def tearDown(self):
        self.db.stop(); self.backups.stop(); self.tmp.cleanup()

    def test_review_is_preview_and_passes_only_explicit_facts(self):
        model = MagicMock()
        model.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            'patches': [self.patch], 'observations': [], 'questions': ['Dove hai usato Java?']})
        with patch.object(analyzer, '_client', return_value=model):
            res = self.client.post(f'/cvs/{self.id}/review', json={'confirmed_facts': 'Email corretta: test@example.com'})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()['patches'], [self.patch])
        self.assertEqual(storage.get_cv(self.id)['markdown'], self.text)
        self.assertEqual(len(storage.list_cvs()), 1)
        messages = model.chat.completions.create.call_args.kwargs['messages']
        self.assertIn('Email corretta: test@example.com', messages[1]['content'])

    def test_selected_patch_creates_copy_preserving_original_and_default(self):
        res = self.client.post(f'/cvs/{self.id}/revision', json={
            'source_hash': cv_review.source_hash(self.text), 'patches': [self.patch]})
        self.assertEqual(res.status_code, 201, res.text)
        revised = res.json()['cv']
        self.assertEqual(revised['parent_id'], self.id)
        self.assertFalse(revised['is_default'])
        self.assertIn(self.patch['after'], revised['markdown'])
        self.assertEqual(storage.get_cv(self.id)['markdown'], self.text)
        self.assertEqual(storage.get_cv_text(), self.text)

    def test_stale_review_rejected_without_new_copy(self):
        storage.update_cv(self.id, markdown=self.text + '\nLinux')
        res = self.client.post(f'/cvs/{self.id}/revision', json={
            'source_hash': cv_review.source_hash(self.text), 'patches': [self.patch]})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(len(storage.list_cvs()), 1)

    def test_fabricated_and_overlapping_excerpts_are_not_applied(self):
        for patches in [[{**self.patch, 'before': 'Esperienza Java Spring'}],
                        [self.patch, {'before': 'FastAPI', 'after': 'Spring'}],
                        [{**self.patch, 'before': '## Esperienze', 'after': '## Nuova sezione'}]]:
            with self.subTest(patches=patches):
                res = self.client.post(f'/cvs/{self.id}/revision', json={
                    'source_hash': cv_review.source_hash(self.text), 'patches': patches})
                self.assertEqual(res.status_code, 422, res.text)
        self.assertEqual(len(storage.list_cvs()), 1)

    def test_normalization_filters_unusable_patches_and_rejects_empty_response(self):
        result = cv_review.normalize_review({'patches': [
            {**self.patch, 'before': 'Inesistente'}, self.patch, self.patch],
            'observations': [], 'questions': []}, self.text)
        self.assertEqual(result['patches'], [self.patch])
        with self.assertRaises(ValueError):
            cv_review.normalize_review({}, self.text)

    def test_replacements_use_original_positions(self):
        text = 'Python developer. Docker deployment.'
        edits = [{'before': 'Python developer.', 'after': 'Docker deployment.'},
                 {'before': 'Docker deployment.', 'after': 'Deployment con Docker.'}]
        self.assertEqual(cv_review.apply_patches(text, edits), 'Docker deployment. Deployment con Docker.')

    def test_pdf_check_extracts_saved_text_without_ai_or_mutation(self):
        res = self.client.post(f'/cvs/{self.id}/check')
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data['pages'], 1)
        for value in ['Test Candidate', 'test@example.com', 'FastAPI', 'Docker']:
            self.assertIn(value, data['text'])
        self.assertLess(data['text'].index('Esperienze'), data['text'].index('Competenze'))
        self.assertEqual(storage.get_cv(self.id)['markdown'], self.text)

    def test_review_failure_and_unknown_cv(self):
        with patch.object(analyzer, 'review_cv', side_effect=analyzer.AnalyzerNotConfigured()):
            res = self.client.post(f'/cvs/{self.id}/review', json={})
        self.assertEqual(res.status_code, 503)
        self.assertEqual(self.client.post('/cvs/999/review', json={}).status_code, 404)
        self.assertEqual(len(storage.list_cvs()), 1)

    def test_export_preserves_plain_text_lines_from_pdf_import(self):
        result = cv_render.check_pdf('Test Candidate\ntest@example.com\nESPERIENZA\nPython developer')
        self.assertIn('Test Candidate\ntest@example.com\nESPERIENZA\nPython developer', result['text'])


if __name__ == '__main__':
    unittest.main()
