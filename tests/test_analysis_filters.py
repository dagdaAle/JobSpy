"""Offline tests for analysis v3 normalisation, active-only re-analysis and channel filters."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'webapp'), str(ROOT)]
import analyzer
import channel_filters
import storage


def job(url='https://example.com/1', **overrides):
    base = dict(job_url=url, title='Python developer', company='Example', location='Verona, Veneto',
                is_remote=False, description='Develop Python services using FastAPI. ' * 10, job_type='fulltime')
    return {**base, **overrides}


class AnalyzerV3Tests(unittest.TestCase):
    def test_extracts_structured_fields_and_caps_lists(self):
        data = analyzer._normalize({
            'decision': 'apply', 'relevance_score': 82, 'summary': 'Ruolo LLM remoto. Buon match.',
            'assessment': {'work_mode': 'remote', 'remote_scope': 'italy', 'location_fit': 'compatible',
                           'seniority': 'mid', 'confidence': 'high', 'salary': '35-45k RAL',
                           'stack': [f't{i}' for i in range(20)], 'languages': ['Inglese B2'],
                           'cv_match': ['Python', 'LangChain'], 'blockers': []},
        })
        a = data['assessment']
        self.assertEqual(a['decision'], 'apply')
        self.assertEqual((a['remote_scope'], a['seniority'], a['salary']), ('italy', 'mid', '35-45k RAL'))
        self.assertEqual(len(a['stack']), 10)
        self.assertEqual(a['cv_match'], ['Python', 'LangChain'])

    def test_hard_constraints_override_model_decision(self):
        for assessment in ({'blockers': ['Solo cittadini USA']}, {'location_fit': 'incompatible'},
                           {'remote_scope': 'restricted'}):
            with self.subTest(assessment=assessment):
                data = analyzer._normalize({'decision': 'apply', 'relevance_score': 90,
                                            'assessment': {'confidence': 'high', **assessment}})
                self.assertEqual(data['assessment']['decision'], 'skip')

    def test_unsure_apply_becomes_maybe_and_invalid_values_default(self):
        data = analyzer._normalize({'decision': 'apply', 'relevance_score': None,
                                    'assessment': {'seniority': 'guru', 'stack': 'Python'}})
        self.assertEqual(data['assessment']['decision'], 'maybe')
        self.assertEqual(data['assessment']['seniority'], 'unknown')
        self.assertEqual(data['assessment']['stack'], [])
        self.assertEqual(analyzer._normalize({'decision': 'boh'})['assessment']['decision'], 'maybe')


class ActiveOnlyReanalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = patch.object(storage, '_DB_PATH', str(Path(self.tmp.name) / 'test.db'))
        self.backups = patch.object(storage, '_BACKUP_DIR', str(Path(self.tmp.name) / 'backups'))
        self.db.start(); self.backups.start()
        storage.init_db()
        storage.configure_analysis('test-model', 'v2')

    def tearDown(self):
        self.db.stop(); self.backups.stop(); self.tmp.cleanup()

    def test_prompt_change_reanalyses_only_active_jobs_and_keeps_old_results_visible(self):
        urls = ['https://e.com/active', 'https://e.com/archived', 'https://e.com/disliked']
        # Distinct titles: identical jobs share feedback as duplicates.
        storage.upsert_jobs([job(u, title=f'Role {i}') for i, u in enumerate(urls)])
        for u in urls:
            storage.set_analysis(u, {'summary': 'old', 'relevance_score': 50})
        with storage._connect() as conn:
            conn.execute("UPDATE jobs SET archived_at = datetime('now') WHERE job_url = ?", (urls[1],))
        storage.set_feedback(urls[2], 'dislike')

        storage.configure_analysis('test-model', 'v3')

        self.assertEqual([r['job_url'] for r in storage.jobs_pending_analysis(50)], [urls[0]])
        self.assertEqual(storage.count_pending_analysis(), 1)
        self.assertEqual(sorted(storage.get_all_analysis()), sorted(urls[1:]))


class ChannelFilterTests(unittest.TestCase):
    def test_keywords_companies_and_work_mode(self):
        records = [
            job('1', title='AI Engineer', description='LLM e LangChain, full remote'),
            job('2', title='Senior AI Engineer', description='LLM, remote'),
            job('3', title='Java developer', description='Spring, in sede'),
            job('4', title='ML engineer', company='Randstad Italia', description='python, remote'),
            job('5', title='Data scientist', description='Python, modalità ibrida a Verona'),
            job('6', title='Email marketing', description='mailing python'),
        ]
        channel = {'include_keywords': ['llm', 'python'], 'exclude_keywords': ['senior'],
                   'exclude_companies': ['randstad'], 'work_mode': 'remote_or_hybrid'}
        kept, removed = channel_filters.filter_records(records, channel)
        self.assertEqual([r['job_url'] for r in kept], ['1', '5'])
        self.assertEqual(removed, 4)
        kept, _ = channel_filters.filter_records(records, {**channel, 'work_mode': 'remote'})
        self.assertEqual([r['job_url'] for r in kept], ['1'])

    def test_word_boundaries_and_empty_filters(self):
        records = [job('1', title='Email specialist', description='mail'), job('2', title='AI dev', description='')]
        self.assertEqual(len(channel_filters.filter_records(records, {})[0]), 2)
        kept, _ = channel_filters.filter_records(records, {'include_keywords': ['ai']})
        self.assertEqual([r['job_url'] for r in kept], ['2'])


class ChannelApiFilterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = patch.object(storage, '_DB_PATH', str(Path(self.tmp.name) / 'test.db'))
        self.backups = patch.object(storage, '_BACKUP_DIR', str(Path(self.tmp.name) / 'backups'))
        self.db.start(); self.backups.start()
        storage.init_db()

    def tearDown(self):
        self.db.stop(); self.backups.stop(); self.tmp.cleanup()

    def test_put_updates_filters_and_refresh_applies_them(self):
        import app
        import pandas as pd
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        cid = storage.create_channel(site='linkedin', search_term='AI')
        self.assertEqual(storage.get_channel(cid)['include_keywords'], [])

        r = client.put(f'/channels/{cid}', json={'exclude_keywords': [' senior ', 'lead'], 'work_mode': 'remote'})
        self.assertEqual(r.status_code, 200)
        ch = r.json()['channel']
        self.assertEqual((ch['exclude_keywords'], ch['work_mode'], ch['search_term']), (['senior', 'lead'], 'remote', 'AI'))
        self.assertEqual(client.put(f'/channels/{cid}', json={'work_mode': 'office'}).status_code, 422)
        self.assertEqual(client.put(f'/channels/{cid}', json={'exclude_keywords': ['']}).status_code, 422)

        df = pd.DataFrame([job('https://e.com/a', title='AI engineer', description='remote'),
                           job('https://e.com/b', title='Senior AI engineer', description='remote'),
                           job('https://e.com/c', title='AI engineer', description='in sede')])
        with patch.object(app, 'search_site', return_value=df):
            self.assertEqual(app._refresh_channel(storage.get_channel(cid)), 1)
        self.assertEqual([j['job_url'] for j in storage.get_channel_jobs(cid)], ['https://e.com/a'])
        log = storage.list_logs()[0]
        self.assertEqual((log['found'], log['removed'], log['new_count']), (3, 2, 1))


if __name__ == '__main__':
    unittest.main()
