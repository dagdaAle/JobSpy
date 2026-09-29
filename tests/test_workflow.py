"""Offline regression tests; never access real CVs, APIs or the production DB."""
import datetime
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'webapp'), str(ROOT)]
import storage
import analyzer
from jobspy.presets import search_site
from jobspy.recency import within_recency
from jobspy.model import ScraperInput


def job(url='https://example.com/1', **overrides):
    return dict(job_url=url, title='Python developer', company='Example', location='Verona, Veneto',
                is_remote=False, description='Develop Python services using FastAPI. ' * 10,
                job_type='fulltime', **overrides)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = patch.object(storage, '_DB_PATH', str(Path(self.tmp.name) / 'test.db'))
        self.backups = patch.object(storage, '_BACKUP_DIR', str(Path(self.tmp.name) / 'backups'))
        self.db.start(); self.backups.start()
        storage.init_db()
        storage.configure_analysis('test-model', 'v2')

    def tearDown(self):
        self.db.stop(); self.backups.stop(); self.tmp.cleanup()

    def channel(self):
        return storage.create_channel(site='linkedin', search_term='Python', location='Verona')

    def test_duplicate_feedback_preserves_different_roles_and_locations(self):
        first = job()
        exact = {**first, 'job_url': 'https://example.com/copy'}
        other_location = {**first, 'job_url': 'https://example.com/milan', 'location': 'Milano'}
        other_role = {**first, 'job_url': 'https://example.com/role', 'description': 'Different team. '*30}
        short = {**first, 'job_url': 'https://example.com/short', 'description': ''}
        storage.upsert_jobs([first, exact, other_location, other_role, short])
        self.assertEqual(len(storage.get_all_jobs()), 4)
        storage.set_feedback(first['job_url'], 'dislike')
        self.assertEqual(set(storage.get_all_feedback()), {first['job_url'], exact['job_url']})
        storage.upsert_jobs([{**other_location, 'job_url': 'https://example.com/new-milan'}])
        self.assertNotIn('https://example.com/new-milan', storage.get_all_feedback())

    def test_new_flag_resets_even_when_next_refresh_is_empty(self):
        cid = self.channel()
        storage.upsert_channel_jobs(cid, [job()])
        self.assertTrue(storage.get_all_jobs()[0]['is_new'])
        self.assertEqual(storage.list_channels()[0]['new_count'], 1)
        storage.upsert_channel_jobs(cid, [])
        self.assertFalse(storage.get_channel_jobs(cid)[0]['is_new'])
        self.assertFalse(storage.get_all_jobs()[0]['is_new'])
        self.assertEqual(storage.list_channels()[0]['new_count'], 0)

    def test_new_flags_are_per_channel(self):
        a, b = self.channel(), self.channel()
        storage.upsert_channel_jobs(a, [job()]); storage.upsert_channel_jobs(b, [job()])
        storage.upsert_channel_jobs(a, [job()])
        self.assertFalse(storage.get_channel_jobs(a)[0]['is_new'])
        self.assertTrue(storage.get_channel_jobs(b)[0]['is_new'])

    def test_cv_and_prompt_change_invalidate_cache_not_history(self):
        storage.upsert_jobs([job()]); storage.set_cv_text('CV 1')
        ctx = storage.analysis_context()
        result = {'relevance_score': 75}
        storage.add_analysis_run(job()['job_url'], {'provider': 'test', 'status': 'ok', 'result': result, 'context_key': ctx})
        storage.set_analysis(job()['job_url'], result, ctx)
        self.assertEqual(storage.count_pending_analysis(), 0)
        storage.set_cv_text('CV 1')
        self.assertEqual(storage.count_pending_analysis(), 0)
        storage.set_cv_text('CV 2')
        self.assertEqual(storage.count_pending_analysis(), 1)
        self.assertEqual(storage.get_all_analysis(), {})
        storage.set_analysis(job()['job_url'], result)
        storage.configure_analysis('test-model', 'v3')
        self.assertEqual(storage.count_pending_analysis(), 1)
        with storage._connect() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM analysis_runs').fetchone()[0], 1)

    def test_failure_limit_resets_for_new_context_and_does_not_starve_batch(self):
        storage.upsert_jobs([{**job(str(i)), 'title': str(i)} for i in range(60)])
        first = storage.jobs_pending_analysis(50)
        self.assertEqual(len(storage.jobs_pending_analysis(50, {r['job_url'] for r in first})), 10)
        for _ in range(3):
            storage.add_analysis_run('0', {'provider': 'test', 'status': 'error', 'context_key': storage.analysis_context()})
        self.assertEqual(storage.count_pending_analysis(), 59)
        storage.set_cv_text('new CV')
        self.assertEqual(storage.count_pending_analysis(), 60)

    def test_archive_restore_and_application_survive_cleanup(self):
        storage.upsert_jobs([job()])
        with storage._connect() as conn:
            conn.execute("UPDATE jobs SET first_seen_at = '2020-01-01 00:00:00'")
        self.assertEqual(storage.archive_stale_jobs(), 1)
        self.assertEqual(storage.get_all_jobs(), [])
        self.assertEqual(len(storage.get_all_jobs(archived_only=True)), 1)
        storage.restore_job(job()['job_url'])
        self.assertEqual(storage.archive_stale_jobs(), 0)
        self.assertTrue(storage.get_all_jobs()[0]['feed_since'])
        storage.set_application(job()['job_url'], 'applied', '2026-09-29', 'Sent CV', 'Follow up', '2026-10-01')
        with storage._connect() as conn:
            conn.execute("UPDATE jobs SET feed_since = '2020-01-01 00:00:00'")
        self.assertEqual(storage.archive_stale_jobs(), 0)
        self.assertEqual(storage.get_applications()[job()['job_url']]['status'], 'applied')
        storage.init_db()  # migration is repeatable and keeps notes
        self.assertEqual(storage.get_applications()[job()['job_url']]['notes'], 'Sent CV')

    def test_tracked_copies_remain_individually_editable(self):
        a, b = job(), job('https://example.com/copy')
        storage.upsert_jobs([a, b]); storage.set_application(b['job_url'], 'interview')
        self.assertIn(b['job_url'], {j['job_url'] for j in storage.get_all_jobs()})

    def test_local_search_keeps_verona_and_remote_is_optional(self):
        with patch('jobspy.presets.scrape_jobs') as scrape:
            search_site('linkedin', 'Python', location='Verona, Veneto', distance_km=50)
            args = scrape.call_args.kwargs
            self.assertEqual(args['location'], 'Verona, Veneto')
            self.assertFalse(args['is_remote'])
            self.assertEqual(args['distance'], 31)
            for board in ['remotive', 'remoteok', 'weworkremotely', 'workingnomads']:
                search_site(board, 'Python', hours_old=336)
                self.assertEqual(scrape.call_args.kwargs['hours_old'], 336)

    def test_remote_recency_date_precision_and_unknown_dates(self):
        today = datetime.datetime.now(datetime.timezone.utc).date()
        self.assertTrue(within_recency(today, 24))
        self.assertFalse(within_recency(today-datetime.timedelta(days=30), 336))
        self.assertTrue(within_recency(None, 24))
        self.assertTrue(within_recency(today-datetime.timedelta(days=30), None))

    def test_remotive_filters_before_result_limit(self):
        from jobspy.remotive import Remotive
        response = MagicMock()
        response.json.return_value = {'jobs': [
            {'url': 'https://example.com/old', 'title': 'Python', 'publication_date': '2020-01-01'},
            {'url': 'https://example.com/new', 'title': 'Python', 'publication_date': datetime.date.today().isoformat()},
        ]}
        session = MagicMock(); session.get.return_value = response
        with patch('jobspy.remotive.create_session', return_value=session):
            result = Remotive().scrape(ScraperInput(site_type=[], results_wanted=1, hours_old=24))
        self.assertEqual([j.job_url for j in result.jobs], ['https://example.com/new'])

    def test_insufficient_data_is_not_a_zero_match(self):
        data = analyzer._normalize({'relevance_score': None, 'assessment': {'location_fit': 'invalid'}})
        self.assertIsNone(data['relevance_score'])
        self.assertEqual(data['assessment']['location_fit'], 'unknown')

    def test_upgrade_from_old_database_preserves_data(self):
        # Recreate an old minimal schema, then exercise the real migration.
        import sqlite3
        legacy = Path(self.tmp.name) / 'legacy.db'
        with sqlite3.connect(legacy) as conn:
            conn.executescript("""
                CREATE TABLE jobs (job_url TEXT PRIMARY KEY, site TEXT, title TEXT, company TEXT,
                    location TEXT, is_remote TEXT, job_type TEXT, date_posted TEXT, description TEXT,
                    seen_at TEXT DEFAULT (datetime('now')));
                INSERT INTO jobs(job_url,title,company) VALUES ('legacy', 'Developer', 'Example');
                CREATE TABLE cv (id INTEGER PRIMARY KEY, text TEXT, updated_at TEXT DEFAULT (datetime('now')));
                INSERT INTO cv(id,text) VALUES (1, 'Old CV');
            """)
        with patch.object(storage, '_DB_PATH', str(legacy)):
            storage.init_db(); storage.init_db()
            self.assertEqual(storage.get_job('legacy')['title'], 'Developer')
            self.assertEqual(storage.get_cv_text(), 'Old CV')
            self.assertEqual(storage.get_all_jobs()[0]['is_new'], False)
            self.assertTrue(list(Path(storage._BACKUP_DIR).glob('pre-workflow-v2-*.db')))

    def test_failed_first_batch_does_not_block_later_jobs(self):
        import app
        storage.upsert_jobs([{**job(str(i)), 'title': str(i)} for i in range(60)])
        with patch.object(analyzer, 'is_configured', return_value=True), \
             patch.object(analyzer, 'analyze_job', side_effect=RuntimeError('offline')) as call:
            app._analyze_backlog('test')
        self.assertEqual(call.call_count, 60)
        self.assertEqual(storage.list_logs()[0]['analysis_failed'], 60)

    def test_all_remote_boards_filter_old_results(self):
        from jobspy.remoteok import RemoteOK
        from jobspy.workingnomads import WorkingNomads
        from jobspy.weworkremotely import WeWorkRemotely
        today = datetime.datetime.now(datetime.timezone.utc)
        recent = today.isoformat()
        cases = [
            ('remoteok', RemoteOK, [{}, {'url': 'https://example.com/old', 'position': 'Python', 'date': '2020-01-01'},
                                   {'url': 'https://example.com/new', 'position': 'Python', 'date': recent}]),
            ('workingnomads', WorkingNomads, [{'url': 'https://example.com/old', 'title': 'Python', 'pub_date': '2020-01-01'},
                                             {'url': 'https://example.com/new', 'title': 'Python', 'pub_date': recent}]),
        ]
        for module, cls, payload in cases:
            response = MagicMock(); response.json.return_value = payload
            session = MagicMock(); session.get.return_value = response
            with patch(f'jobspy.{module}.create_session', return_value=session):
                result = cls().scrape(ScraperInput(site_type=[], results_wanted=1, hours_old=24))
            self.assertEqual([j.job_url for j in result.jobs], ['https://example.com/new'])
        from email.utils import format_datetime
        response = MagicMock()
        response.content = f"""<rss><channel>
          <item><title>Example: Python</title><link>https://example.com/old</link><pubDate>Wed, 01 Jan 2020 00:00:00 +0000</pubDate></item>
          <item><title>Example: Python</title><link>https://example.com/new</link><pubDate>{format_datetime(today)}</pubDate></item>
        </channel></rss>""".encode()
        session = MagicMock(); session.get.return_value = response
        with patch('jobspy.weworkremotely.create_session', return_value=session):
            result = WeWorkRemotely().scrape(ScraperInput(site_type=[], results_wanted=1, hours_old=24))
        self.assertEqual([j.job_url for j in result.jobs], ['https://example.com/new'])
        self.assertIn('non specificata', result.jobs[0].location.country)

    def test_application_history_is_atomic_and_ignores_noop_saves(self):
        storage.upsert_jobs([job()])
        url = job()['job_url']
        storage.set_application(url, 'applied', applied_on='2026-09-29', cv_label='CV Python v2', contact='Recruiter')
        storage.set_application(url, 'applied', applied_on='2026-09-29', cv_label='CV Python v2', contact='Recruiter')
        self.assertEqual(len(storage.application_events(url)), 1)
        storage.set_application(url, 'contacted', applied_on='2026-09-29', cv_label='CV Python v2', contact='Recruiter')
        events = storage.application_events(url)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['content']['status'], {'from': 'applied', 'to': 'contacted'})
        storage.add_application_note(url, 'Colloquio concordato', '2026-09-30')
        self.assertEqual(storage.application_events(url)[0]['content']['text'], 'Colloquio concordato')
        with self.assertRaises(KeyError):
            storage.add_application_note('unknown', 'Note', '2026-09-29')
        self.assertEqual(storage.application_events('unknown'), [])

    def test_manual_application_api_without_link_and_duplicate_protection(self):
        import app
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        body = {'title': 'Python developer', 'company': 'Example', 'status': 'applied', 'cv_label': 'CV v2'}
        response = client.post('/applications/manual', json=body)
        self.assertEqual(response.status_code, 201)
        url = response.json()['job_url']
        self.assertTrue(url.startswith('manual:'))
        self.assertEqual(storage.get_applications()[url]['cv_label'], 'CV v2')
        self.assertEqual(storage.count_pending_analysis(), 0)
        self.assertEqual(client.get('/applications/history', params={'url': url}).status_code, 200)
        self.assertEqual(client.post('/applications/notes', json={'job_url': url, 'text': 'Risposta ricevuta', 'occurred_on': '2026-09-29'}).status_code, 201)
        body['url'] = 'https://example.com/manual'
        self.assertEqual(client.post('/applications/manual', json=body).status_code, 201)
        self.assertEqual(client.post('/applications/manual', json=body).status_code, 409)
        self.assertEqual(len(storage.get_applications()), 2)

    def test_manual_input_rejects_blank_titles_unsafe_urls_and_invalid_dates(self):
        import app
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        body = {'title': 'Python', 'company': 'Example', 'status': 'applied'}
        for patch_value in [{'title': '  '}, {'company': ' '}, {'url': 'javascript:alert(1)'}, {'follow_up_on': 'not-a-date'}]:
            self.assertEqual(client.post('/applications/manual', json={**body, **patch_value}).status_code, 422)
        self.assertEqual(storage.get_applications(), {})
        self.assertEqual(client.post('/applications/notes', json={'job_url': 'x', 'text': ' ', 'occurred_on': '2026-09-29'}).status_code, 422)

    def test_existing_application_migrates_to_history_once(self):
        storage.upsert_jobs([job()])
        with storage._connect() as conn:
            conn.execute("DELETE FROM meta WHERE key='application_history_v1'")
            conn.execute("DROP TABLE applications")
            conn.execute("CREATE TABLE applications(job_url TEXT PRIMARY KEY, status TEXT NOT NULL, applied_on TEXT, notes TEXT NOT NULL DEFAULT '', next_step TEXT NOT NULL DEFAULT '', follow_up_on TEXT, updated_at TEXT NOT NULL)")
            conn.execute("INSERT INTO applications VALUES (?, 'interview', '2026-09-20', 'Existing note', 'Call', '2026-09-30', '2026-09-20 12:00:00')", (job()['job_url'],))
        storage.init_db(); storage.init_db()
        app = storage.get_applications()[job()['job_url']]
        self.assertEqual(app['notes'], 'Existing note')
        self.assertEqual(app['cv_label'], '')
        events = storage.application_events(job()['job_url'])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['kind'], 'imported')
        self.assertEqual(events[0]['content']['notes'], 'Existing note')

    def test_manual_creation_rolls_back_on_invalid_status(self):
        with self.assertRaises(ValueError):
            storage.create_manual_application('Role', 'Company', None, '', status='invalid')
        self.assertEqual(storage.get_all_jobs(), [])
        self.assertEqual(storage.get_applications(), {})

    def test_api_validation_and_archived_workflow(self):
        import app
        from fastapi.testclient import TestClient
        # No context manager: startup (real scheduler) must not run in tests.
        client = TestClient(app.app)
        storage.upsert_jobs([job()])
        self.assertEqual(client.post('/maintenance/archive?days=-1').status_code, 422)
        self.assertEqual(client.post('/maintenance/recency?hours=-1').status_code, 422)
        self.assertEqual(client.post('/applications', json={'job_url': 'missing', 'status': 'applied'}).status_code, 404)
        self.assertEqual(client.post('/applications', json={'job_url': job()['job_url'], 'status': 'applied', 'applied_on': 'bad'}).status_code, 422)
        self.assertEqual(client.post('/applications', json={'job_url': job()['job_url'], 'status': 'applied'}).status_code, 200)
        self.assertEqual(client.get('/applications').json()['count'], 1)
        self.assertEqual(client.get('/jobs?archived=true').json()['count'], 0)


if __name__ == '__main__':
    os.chdir(ROOT / 'webapp')
    unittest.main()
