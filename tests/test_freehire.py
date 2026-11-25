"""Offline tests for the freehire source. Every company, posting and URL here is invented."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'webapp'), str(ROOT)]
import storage
from jobspy.freehire import (
    FreehireClient, FreehireError, Freehire, location_filter, location_match, normalize_url,
    scrape_freehire,
)
from jobspy.model import ScraperInput


def posting(slug, **over):
    base = {
        'public_slug': slug, 'source': 'workday', 'external_id': slug,
        'url': f'https://acme.example/jobs/{slug}?utm_source=freehire.me', 'title': f'ML engineer {slug}',
        'company': 'Acme', 'location': 'Italy', 'description': '<p>' + 'Build ML systems. ' * 20 + '</p>',
        'work_mode': 'remote', 'skills': ['python', 'pytorch'], 'posted_at': '2026-11-20T10:00:00Z',
        'closed_at': None,
        'enrichment': {'salary_min': 40000, 'salary_max': 50000, 'salary_currency': 'EUR',
                       'salary_period': 'year', 'category': 'ai_engineering', 'posting_language': 'en',
                       'requirements': [{'text': 'Python', 'priority': 'required'},
                                        {'text': 'Kubernetes', 'priority': 'preferred'}]},
        'reality': {'class': 'fresh', 'fake_freshness': False, 'mass_posting_count': 1},
    }
    base.update(over)
    return base


LINKEDIN = posting('li-1', source='linkedin', external_id='4000000001',
                   url='https://www.linkedin.com/jobs/view/4000000001/?utm_source=freehire.me',
                   enrichment={'salary_min': 30000, 'salary_max': 35000, 'salary_currency': 'EUR',
                               'salary_period': 'year'})
SUSPECT = posting('sus-1', reality={'fake_freshness': True, 'mass_posting_count': 9})
CLOSED = posting('closed-1', closed_at='2026-11-23T09:00:00Z')


def response(status=200, data=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = data if data is not None else {}
    return r


def client_with(*responses):
    session = MagicMock()
    session.headers = {}
    session.get.side_effect = list(responses)
    return FreehireClient(session=session), session


class FreehireMappingTests(unittest.TestCase):
    def test_location_filter(self):
        self.assertEqual(location_filter(''), {})
        self.assertEqual(location_filter('Italia'), {'countries': 'it'})
        self.assertEqual(location_filter(' Europe '), {'regions': 'eu'})
        self.assertEqual(location_filter('Verona, Veneto, Italia'), {'cities': 'verona'})

    def test_location_match(self):
        self.assertIsNone(location_match('Italia'))
        self.assertIsNone(location_match(''))
        any_verona = location_match('Verona')
        self.assertTrue(any_verona.search('Verona, WI, US'))
        self.assertFalse(any_verona.search('Rieti, IT'))
        italian = location_match('Verona, Italia')
        for ok in ('Verona, Italy', 'Verona, IT, 37122', 'Verona', 'Verona, Veneto',
                   'Milan, Italy; Verona, Province of Verona, Italy'):
            self.assertTrue(italian.search(ok), ok)
        for ko in ('Verona, WI, US', 'Verona, New York', 'Verona, Virginia, USA', 'Rieti, IT',
                   'Veronaville, Italy'):
            self.assertFalse(italian.search(ko), ko)

    def test_normalize_url(self):
        self.assertEqual(normalize_url('https://x.example/a/?utm_source=freehire.me&id=3'),
                         'https://x.example/a?id=3')
        self.assertEqual(normalize_url('https://www.linkedin.com/jobs/view/4000000001/?utm_source=f',
                                       'linkedin', '4000000001'),
                         'https://www.linkedin.com/jobs/view/4000000001')

    def test_ignored_filter_is_an_error(self):
        client, _ = client_with(response(data={'data': [posting('a')],
                                               'meta': {'total': 9, 'ignored_params': [{'param': 'country'}]}}))
        with self.assertRaises(FreehireError):
            client.search({'country': 'it'})
        client, _ = client_with(response(data={'data': [], 'meta': {'ignored_values': {'cities': ['x']}}}))
        with self.assertRaises(FreehireError):
            client.search({'cities': 'x'})

    def test_scraper_maps_pages_and_drops_closed(self):
        page = {'data': [posting('a'), CLOSED, LINKEDIN], 'meta': {'total': 3}}
        client, session = client_with(response(data=page))
        scraper = Freehire(client=client)
        posts = scraper.scrape(ScraperInput(search_term='ML', location='Europa', is_remote=True,
                                            hours_old=30, results_wanted=10))
        params = session.get.call_args.kwargs['params']
        self.assertEqual(params['q'], 'ML')
        self.assertEqual(params['regions'], 'eu')
        self.assertEqual(params['work_mode'], 'remote')
        self.assertEqual(params['posted_within_days'], 2)
        self.assertEqual([p.job_url for p in posts],
                         ['https://acme.example/jobs/a', 'https://www.linkedin.com/jobs/view/4000000001'])
        self.assertEqual(posts[0].min_amount, 40000)
        self.assertIn('## Requisiti (dalla fonte)', posts[0].description)
        self.assertIn('[preferito] Kubernetes', posts[0].description)
        self.assertIsNone(scraper.error)

    def test_rate_limit_fails_the_scraper(self):
        client, _ = client_with(response(429))
        scraper = Freehire(client=client)
        self.assertEqual(scraper.scrape(ScraperInput(search_term='ML')), [])
        self.assertIn('429', scraper.error)

    def test_dataframe_keeps_linkedin_site_and_source_rows(self):
        client, _ = client_with(response(data={'data': [posting('a'), LINKEDIN, SUSPECT], 'meta': {'total': 3}}))
        df = scrape_freehire('ML', client=client)
        self.assertEqual(list(df['site']), ['freehire', 'linkedin', 'freehire'])
        rows = {r['slug']: r for r in df.attrs['source_rows']}
        self.assertTrue(rows['sus-1']['suspect'])
        self.assertFalse(rows['a']['suspect'])
        self.assertEqual(rows['li-1']['origin'], 'linkedin')
        self.assertEqual(df.attrs['errors'], {})

    def test_unknown_city_is_an_error(self):
        client, _ = client_with(response(data={'data': [], 'meta': {'total': 0}}),
                                response(data={'data': [], 'meta': {'total': 0}}))
        df = scrape_freehire('python', location='Xyzville', client=client)
        self.assertIn('xyzville', df.attrs['errors']['freehire'])
        client, _ = client_with(response(data={'data': [], 'meta': {'total': 0}}),
                                response(data={'data': [], 'meta': {'total': 40}}))
        self.assertEqual(scrape_freehire('cobol', location='Verona', client=client).attrs['errors'], {})

    def test_company_gone_is_an_error(self):
        client, _ = client_with(response(data={'data': [], 'meta': {'total': 0}}), response(404))
        df = scrape_freehire('Acme', company_slug='acme', client=client)
        self.assertIn('404', df.attrs['errors']['freehire'])


class FreehireAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = patch.object(storage, '_DB_PATH', str(Path(self.tmp.name) / 'test.db'))
        self.backups = patch.object(storage, '_BACKUP_DIR', str(Path(self.tmp.name) / 'backups'))
        self.db.start(); self.backups.start()
        storage.init_db()
        storage.configure_analysis('test-model', 'v2')
        import app
        self.app = app

    def tearDown(self):
        self.db.stop(); self.backups.stop(); self.tmp.cleanup()

    def refresh(self, channel_id, *responses):
        client, _ = client_with(*responses)
        with patch('jobspy.freehire.FreehireClient', return_value=client):
            return self.app._refresh_channel(storage.get_channel(channel_id))

    def freehire_channel(self, **kw):
        return storage.create_channel(site='freehire', search_term='ML', location='Italia', **kw)

    def test_scraper_error_is_logged_as_error(self):
        cid = self.freehire_channel()
        self.refresh(cid, response(429))
        log = storage.list_logs()[0]
        self.assertEqual(log['status'], 'error')
        self.assertIn('429', log['error'])

    def test_linkedin_copy_is_one_job_and_keeps_freehire_salary(self):
        li_url = 'https://www.linkedin.com/jobs/view/4000000001'
        storage.upsert_jobs([{'job_url': li_url, 'site': 'linkedin', 'title': 'ML engineer',
                              'company': 'Acme', 'description': 'x' * 200}])
        storage.set_feedback(li_url, 'like', title='ML engineer', company='Acme', site='linkedin')
        cid = self.freehire_channel()
        self.refresh(cid, response(data={'data': [LINKEDIN, posting('a')], 'meta': {'total': 2}}))
        jobs = {j['job_url']: j for j in storage.get_channel_jobs(cid)}
        self.assertEqual(set(jobs), {li_url, 'https://acme.example/jobs/a'})
        self.assertEqual(storage.get_all_feedback()[li_url], 'like')
        # The LinkedIn scraper re-saves the job without salary: the freehire salary stays visible.
        storage.upsert_jobs([{'job_url': li_url, 'site': 'linkedin', 'title': 'ML engineer',
                              'company': 'Acme', 'description': 'x' * 200}])
        card = next(j for j in storage.get_all_jobs() if j['job_url'] == li_url)
        self.assertEqual(float(card['salary_min']), 30000)
        self.assertEqual(card['site'], 'linkedin')
        self.assertEqual(card['source_origin'], 'linkedin')

    def test_suspect_and_closed_jobs_skip_the_analysis_queue(self):
        cid = self.freehire_channel()
        self.refresh(cid, response(data={'data': [posting('a'), SUSPECT], 'meta': {'total': 2}}))
        pending = {j['job_url'] for j in storage.jobs_pending_analysis()}
        self.assertEqual(pending, {'https://acme.example/jobs/a'})
        self.assertTrue(next(j for j in storage.get_all_jobs()
                             if j['job_url'] == 'https://acme.example/jobs/sus-1')['source_suspect'])

    def test_source_closures(self):
        cid = self.freehire_channel()
        self.refresh(cid, response(data={'data': [posting('a'), posting('b'), posting('c')], 'meta': {'total': 3}}))
        storage.set_feedback('https://acme.example/jobs/b', 'like', title='ML engineer', company='Acme', site='freehire')
        client, _ = client_with(
            response(data={'data': {'closed_at': '2026-11-24T08:00:00Z'}}),   # a: closed, no verdict
            response(data={'data': {'closed_at': '2026-11-24T08:00:00Z'}}),   # b: closed, liked
            response(404),                                                    # c: unknown -> no change
        )
        archived = self.app._check_source_closures(client=client)
        self.assertEqual(archived, 1)
        a = storage.get_job('https://acme.example/jobs/a')
        self.assertEqual(a['archive_reason'], 'closed_at_source')
        b = storage.get_job('https://acme.example/jobs/b')
        self.assertIsNone(b['archived_at'])
        self.assertEqual(b['source']['closed_at'], '2026-11-24T08:00:00Z')
        self.assertIsNone(storage.get_job('https://acme.example/jobs/c')['source']['closed_at'])
        # Seen open again: the closure is lifted.
        self.refresh(cid, response(data={'data': [posting('b')], 'meta': {'total': 1}}))
        self.assertIsNone(storage.get_job('https://acme.example/jobs/b')['source']['closed_at'])

    def test_rate_limit_stops_closure_checks(self):
        cid = self.freehire_channel()
        self.refresh(cid, response(data={'data': [posting('a'), posting('b')], 'meta': {'total': 2}}))
        client, session = client_with(response(429), response(200, {'data': {'closed_at': 'x'}}))
        self.assertEqual(self.app._check_source_closures(client=client), 0)
        self.assertEqual(session.get.call_count, 1)
        self.assertEqual(storage.list_logs()[0]['status'], 'error')

    def test_company_channel(self):
        from fastapi.testclient import TestClient
        api = TestClient(self.app.app)
        body = {'site': 'linkedin', 'search_term': 'Acme', 'company_slug': 'acme'}
        self.assertEqual(api.post('/channels', json=body).status_code, 422)
        cid = self.freehire_channel(company_slug='acme')
        client, session = client_with(response(data={'data': [posting('a')], 'meta': {'total': 1}}))
        with patch('jobspy.freehire.FreehireClient', return_value=client):
            self.app._refresh_channel(storage.get_channel(cid))
        params = session.get.call_args.kwargs['params']
        self.assertEqual(params['company_slug'], 'acme')
        self.assertNotIn('q', params)

    def test_on_the_fly_search_and_save(self):
        from fastapi.testclient import TestClient
        api = TestClient(self.app.app)
        client, _ = client_with(response(data={'data': [posting('a')], 'meta': {'total': 1}}))
        with patch.object(self.app, 'FreehireClient', return_value=client):
            res = api.get('/freehire/search', params={'q': 'ML', 'location': 'Italia'})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()['results'][0]['in_db'])
        self.assertEqual(storage.get_all_jobs(), [])
        client, _ = client_with(response(data={'data': posting('a')}))
        with patch.object(self.app, 'FreehireClient', return_value=client), patch.object(self.app, '_kick_analysis'):
            res = api.post('/freehire/save', json={'slug': 'a'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()['created'])
        self.assertEqual(storage.job_source('https://acme.example/jobs/a')['slug'], 'a')
        client, _ = client_with(response(data={'data': CLOSED}))
        with patch.object(self.app, 'FreehireClient', return_value=client):
            self.assertEqual(api.post('/freehire/save', json={'slug': 'closed-1'}).status_code, 409)
        client, _ = client_with(response(404))
        with patch.object(self.app, 'FreehireClient', return_value=client):
            self.assertEqual(api.post('/freehire/save', json={'slug': 'nope'}).status_code, 404)
        client, _ = client_with(response(data={'data': [], 'meta': {'total': 0}}),
                                response(data={'data': [], 'meta': {'total': 0}}))
        with patch.object(self.app, 'FreehireClient', return_value=client):
            self.assertEqual(api.get('/freehire/search', params={'q': 'ML', 'location': 'Xyz'}).status_code, 422)


if __name__ == '__main__':
    unittest.main()
