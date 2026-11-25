"""Offline tests for the Concorsi PA and Gare P.IVA areas. Every body, notice and URL here is invented."""
import datetime
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'webapp'), str(ROOT)]
import area_common
import storage
from area_common import AreaStore, SourceError
from gare import evaluate as gare_eval
from gare.sources import build_query, fetch_ted, ted_item, within_budget
from pa import evaluate as pa_eval
from pa.sources import fetch_gazzetta, fetch_inpa, gu_acts, gu_issues, inpa_item


def response(status=200, data=None, text=''):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = data
    r.text = text
    return r


def session_with(*responses, method='post'):
    session = MagicMock()
    getattr(session, method).side_effect = list(responses)
    return session


def item(key, **kw):
    return {'key': key, 'source': 'test', 'title': f'Item {key}', **kw}


GU_INDEX = '''<a href="/gazzetta/concorsi/caricaDettaglio?dataPubblicazioneGazzetta=2099-01-10&numeroGazzetta=4&elenco30giorni=true">n.4</a>
<a href="/gazzetta/concorsi/caricaDettaglio?dataPubblicazioneGazzetta=2099-01-06&numeroGazzetta=3&elenco30giorni=true">n.3</a>'''
GU_ISSUE = '''<html><body>
<span class="rubrica"> AMMINISTRAZIONI CENTRALI</span>
<span class="emettitore">MINISTERO DELLE PROVE</span>
<span class="risultato">
  <a href="/atto/concorsi/caricaDettaglioAtto/originario?atto.codiceRedazionale=99E00001"><span class="data">CONCORSO
    <font>(scad. 20 febbraio 2099)</font></span></a>
  <a href="/atto/concorsi/caricaDettaglioAtto/originario?atto.codiceRedazionale=99E00001">
    Concorso per tre posti di funzionario informatico.  (99E00001) <span class="pagina">Pag. 1</span></a>
</span>
<span class="rubrica"> ENTI LOCALI</span>
<span class="emettitore">COMUNE DI ESEMPIO</span>
<span class="risultato">
  <a href="/atto/x?atto.codiceRedazionale=99E00002"><span class="data">GRADUATORIA</span></a>
  <a href="/atto/x?atto.codiceRedazionale=99E00002">Graduatoria del concorso per un posto di istruttore.  (99E00002)</a>
</span>
</body></html>'''


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = patch.object(storage, '_DB_PATH', str(Path(self.tmp.name) / 'test.db'))
        self.db.start()
        storage.init_db()
        self.store = AreaStore('pa')
        self.store.init_tables()

    def tearDown(self):
        self.db.stop(); self.tmp.cleanup()

    def test_views_verdicts_and_deadlines(self):
        cid = self.store.create_channel({'name': 'c', 'source': 'inpa'})['id']
        new = self.store.upsert_items(cid, [
            item('open', deadline='2099-01-01'), item('nodate'), item('expired', deadline='2000-01-01'),
        ])
        self.assertEqual(new, 3)
        self.assertEqual(self.store.upsert_items(cid, [item('open', deadline='2099-01-01')]), 0)
        feed = {i['key'] for i in self.store.list_items('feed')}
        self.assertEqual(feed, {'open', 'nodate'})
        self.assertEqual([i['key'] for i in self.store.list_items('archived')], ['expired'])
        self.store.set_verdict('open', 'like')
        self.assertEqual([i['key'] for i in self.store.list_items('saved')], ['open'])
        self.assertNotIn('open', {i['key'] for i in self.store.list_items('feed')})
        self.store.set_verdict('open', None)
        self.assertIn('open', {i['key'] for i in self.store.list_items('feed', channel_id=cid)})

    def test_delete_channel_keeps_items_and_verdicts(self):
        cid = self.store.create_channel({'name': 'c', 'source': 'inpa'})['id']
        self.store.upsert_items(cid, [item('a')])
        self.store.set_verdict('a', 'dislike')
        self.store.delete_channel(cid)
        self.assertEqual(self.store.list_channels(), [])
        self.assertEqual([i['key'] for i in self.store.list_items('dismissed')], ['a'])

    def test_areas_do_not_share_tables(self):
        other = AreaStore('gare'); other.init_tables()
        cid = self.store.create_channel({'name': 'c', 'source': 'inpa'})['id']
        self.store.upsert_items(cid, [item('a')])
        self.assertEqual(other.list_items('feed'), [])

    def test_extraction_skips_disliked_and_gives_up_after_failures(self):
        cid = self.store.create_channel({'name': 'c', 'source': 'inpa'})['id']
        self.store.upsert_items(cid, [item('a'), item('b'), item('c')])
        self.store.set_verdict('b', 'dislike')
        for _ in range(area_common.MAX_EXTRACTION_FAILURES):
            self.store.save_extraction_error('c', 'v1', 'boom')
        self.assertEqual([i['key'] for i in self.store.pending_extraction('v1')], ['a'])
        self.store.save_extraction('a', 'v1', {'x': 1})
        self.assertEqual(self.store.pending_extraction('v1'), [])
        self.assertEqual(len(self.store.pending_extraction('v2')), 2)

    def test_profile_defaults_and_overrides(self):
        self.assertEqual(self.store.get_profile({'a': 1, 'b': 2}), {'a': 1, 'b': 2})
        self.store.set_profile({'b': 3})
        self.assertEqual(self.store.get_profile({'a': 1, 'b': 2}), {'a': 1, 'b': 3})


class PaSourceTests(unittest.TestCase):
    def notice(self, nid, sedi, **kw):
        return {'id': nid, 'titolo': f'Concorso {nid}', 'sedi': sedi, 'entiRiferimento': ['Ente di prova'],
                'dataScadenza': '2099-03-01T23:59:00Z', 'dataPubblicazione': '2099-01-02T00:00:00Z', **kw}

    def test_inpa_item_fields(self):
        it = inpa_item(self.notice(7, ['Veneto', 'Verona'], numPosti=2, figuraRicercata='Analista'))
        self.assertEqual(it['key'], 'inpa-7')
        self.assertEqual(it['title'], 'Concorso 7 – Analista')
        self.assertEqual(it['deadline'], '2099-03-01')
        self.assertEqual(it['buyer'], 'Ente di prova')
        self.assertTrue(it['body'].startswith('Posti: 2'))

    def test_inpa_place_filter(self):
        page = {'content': [self.notice(1, ['Veneto', 'Verona']), self.notice(2, ['Lazio', 'Roma']),
                            self.notice(3, ['Veneto'])], 'last': True}
        items = fetch_inpa({'query': 'informatic', 'location': 'Verona'}, session_with(response(data=page)))
        self.assertEqual([i['key'] for i in items], ['inpa-1', 'inpa-3'])

    def test_inpa_error_raises(self):
        with self.assertRaises(SourceError):
            fetch_inpa({'query': 'x'}, session_with(response(503)))

    def test_gu_index_and_acts(self):
        self.assertEqual(gu_issues(GU_INDEX), [('2099-01-10', '4'), ('2099-01-06', '3')])
        acts = gu_acts(GU_ISSUE, '2099-01-10')
        self.assertEqual([a['key'] for a in acts], ['gu-99E00001', 'gu-99E00002'])
        first = acts[0]
        self.assertEqual(first['deadline'], '2099-02-20')
        self.assertEqual(first['kind'], 'Concorso')
        self.assertEqual(first['buyer'], 'Ministero Delle Prove')
        self.assertEqual(first['title'], 'Concorso per tre posti di funzionario informatico.')
        self.assertIsNone(acts[1]['deadline'])

    def test_gu_empty_index_is_an_error(self):
        with self.assertRaises(SourceError):
            gu_issues('<html>nothing</html>')

    def test_gu_not_found_page_is_an_error(self):
        session = session_with(response(text='<title>Gazzetta Ufficiale - Pagina non trovata</title>'), method='get')
        with self.assertRaises(SourceError):
            fetch_gazzetta({'query': ''}, session)

    def test_gu_query_and_place(self):
        session = session_with(response(text=GU_INDEX), response(text=GU_ISSUE), response(text=GU_ISSUE),
                               method='get')
        with patch('pa.sources.time.sleep'):
            items = fetch_gazzetta({'query': 'informatic', 'location': 'Verona'}, session)
        # central administrations count everywhere; the same act in two issues is one key
        self.assertEqual({i['key'] for i in items}, {'gu-99E00001'})


class PaEvaluateTests(unittest.TestCase):
    profile = {'titoli': ['LM-32'], 'livello_max': 'magistrale', 'aree': ['informatica'], 'eta': 30}

    def facts(self, **kw):
        base = {'livello_richiesto': 'triennale', 'classi_laurea': [], 'eta_max': None, 'contratto': None,
                'posti': None, 'area_profilo': 'informatica'}
        return {**base, **kw}

    def test_decisions(self):
        decide = pa_eval.decide
        self.assertEqual(decide(None, self.profile), (None, []))
        self.assertEqual(decide(self.facts(), self.profile)[0], 'adatto')
        self.assertEqual(decide(self.facts(livello_richiesto='dottorato'), self.profile)[0], 'non_adatto')
        self.assertEqual(decide(self.facts(classi_laurea=['LM-18']), self.profile)[0], 'non_adatto')
        self.assertEqual(decide(self.facts(classi_laurea=['LM 32']), self.profile)[0], 'adatto')
        self.assertEqual(decide(self.facts(eta_max=29), self.profile)[0], 'non_adatto')
        self.assertEqual(decide(self.facts(livello_richiesto=None), self.profile)[0], 'da_valutare')
        self.assertEqual(decide(self.facts(area_profilo='sanitaria'), self.profile)[0], 'non_adatto')

    def test_normalize_drops_unknown_values(self):
        out = pa_eval.normalize({'livello_richiesto': 'master', 'classi_laurea': ['lm-32', 'boh'],
                                 'eta_max': '35', 'posti': 3, 'area_profilo': 'informatica', 'evidenza': 'x'})
        self.assertIsNone(out['livello_richiesto'])
        self.assertEqual(out['classi_laurea'], ['LM-32'])
        self.assertIsNone(out['eta_max'])
        self.assertEqual(out['posti'], 3)
        self.assertEqual(out['evidenza'], {})


class GareTests(unittest.TestCase):
    notice = {
        'publication-number': '1-2099', 'title-proc': {'eng': 'Software services', 'ita': 'Servizi software'},
        'buyer-name': {'ita': ['Ente appaltante di prova']}, 'publication-date': '2099-01-05+01:00',
        'deadline-receipt-tender-date-lot': ['2099-02-10+01:00', '2099-02-01+01:00'],
        'estimated-value-lot': ['100000.00', '50000.00'], 'estimated-value-cur-lot': ['EUR', 'EUR'],
        'classification-cpv': ['72000000', '72000000', '48000000'], 'notice-type': 'cn-standard',
        'place-of-performance-city-lot': ['Veneto'],
    }

    def test_query(self):
        q = build_query({'cpv': '72000000, 48000000', 'country': 'ITA', 'days': 7, 'query': 'cloud "x"'},
                        today=datetime.date(2099, 1, 10))
        self.assertIn('(classification-cpv=72000000 OR classification-cpv=48000000)', q)
        self.assertIn('FT~"cloud  x"', q)
        self.assertIn('PD>=20990103', q)
        self.assertIn('notice-type IN (cn-standard', q)

    def test_item_lots(self):
        it = ted_item(self.notice)
        self.assertEqual(it['key'], 'ted-1-2099')
        self.assertEqual(it['title'], 'Servizi software')
        self.assertEqual(it['deadline'], '2099-02-01')
        self.assertEqual(it['amount'], 150000.0)
        self.assertEqual(it['currency'], 'EUR')
        self.assertEqual(it['cpv'], '72000000,48000000')

    def test_fetch_and_errors(self):
        ok = response(data={'notices': [self.notice], 'totalNoticeCount': 1})
        self.assertEqual(len(fetch_ted({'results_wanted': 10}, session_with(ok))), 1)
        with self.assertRaises(SourceError):
            fetch_ted({}, session_with(response(400, text='bad query')))
        with self.assertRaises(SourceError):
            fetch_ted({}, session_with(response(data={'timedOut': True})))

    def test_budget(self):
        self.assertTrue(within_budget({'amount': None}, {'max_amount': 10}))
        self.assertTrue(within_budget({'amount': 5}, {'max_amount': 10}))
        self.assertFalse(within_budget({'amount': 50}, {'max_amount': 10}))
        self.assertTrue(within_budget({'amount': 50}, {}))

    def test_decisions(self):
        profile = {'servizi': ['sviluppo-software'], 'fatturato_annuo': 50000, 'certificazioni': ['ISO 9001'],
                   'solo_subappalto_ok': True}
        decide = gare_eval.decide
        base = {'servizi': ['sviluppo-software'], 'fatturato_minimo': 10000, 'certificazioni_richieste': [],
                'subappalto_ammesso': None, 'raggruppamento_ammesso': None}
        self.assertEqual(decide(base, profile)[0], 'adatto')
        self.assertEqual(decide({**base, 'servizi': ['forniture-hardware']}, profile)[0], 'non_adatto')
        self.assertEqual(decide({**base, 'fatturato_minimo': 1e6}, profile)[0], 'non_adatto')
        sub = decide({**base, 'fatturato_minimo': 1e6, 'subappalto_ammesso': True}, profile)
        self.assertEqual(sub[0], 'adatto')
        self.assertIn('solo in subappalto o raggruppamento', sub[1])
        self.assertEqual(decide({**base, 'fatturato_minimo': 1e6, 'subappalto_ammesso': True},
                                {**profile, 'solo_subappalto_ok': False})[0], 'non_adatto')
        self.assertEqual(decide({**base, 'certificazioni_richieste': ['ISO 27001']}, profile)[0], 'da_valutare')
        self.assertEqual(decide({**base, 'certificazioni_richieste': ['iso 9001']}, profile)[0], 'adatto')


class AppAreaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = patch.object(storage, '_DB_PATH', str(Path(self.tmp.name) / 'test.db'))
        self.backups = patch.object(storage, '_BACKUP_DIR', str(Path(self.tmp.name) / 'backups'))
        self.db.start(); self.backups.start()
        storage.init_db()
        import app
        self.app = app
        for area in app._AREAS:
            area.store.init_tables()
        from fastapi.testclient import TestClient
        self.client = TestClient(app.app)

    def tearDown(self):
        self.db.stop(); self.backups.stop(); self.tmp.cleanup()

    def test_channel_items_verdict_profile_api(self):
        fake = MagicMock(return_value=[item('ted-1', deadline='2099-01-01', amount=10.0)])
        with patch.dict(self.app.gare.AREA.fetchers, {'ted': fake}), \
                patch.object(self.app.gare.AREA, 'kick_analysis'):
            r = self.client.post('/gare/channels', json={'name': 'IT', 'cpv': '72000000', 'country': 'ITA'})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()['new_count'], 1)
        items = self.client.get('/gare/items').json()['items']
        self.assertEqual([i['key'] for i in items], ['ted-1'])
        self.assertIsNone(items[0]['decision'])
        self.assertEqual(self.client.get('/pa/items').json()['items'], [])
        self.assertEqual(self.client.post('/gare/verdict', json={'key': 'ted-1', 'verdict': 'like'}).status_code, 200)
        self.assertEqual(self.client.post('/gare/verdict', json={'key': 'nope', 'verdict': 'like'}).status_code, 404)
        self.assertEqual([i['key'] for i in self.client.get('/gare/items?view=saved').json()['items']], ['ted-1'])
        prof = self.client.put('/gare/profile', json={'fatturato_annuo': 1000, 'typo': 1}).json()
        self.assertEqual(prof['fatturato_annuo'], 1000)
        self.assertNotIn('typo', prof)
        self.assertEqual(self.client.post('/pa/channels', json={'name': 'x', 'source': 'nope'}).status_code, 422)
        self.assertEqual(self.client.get('/pa/meta').json()['sources'], ['inpa', 'gazzetta'])

    def test_decision_uses_profile_without_new_extraction(self):
        store = self.app.pa.AREA.store
        cid = store.create_channel({'name': 'c', 'source': 'inpa'})['id']
        store.upsert_items(cid, [item('inpa-1')])
        store.save_extraction('inpa-1', pa_eval.PROMPT_VERSION, {
            'livello_richiesto': 'magistrale', 'classi_laurea': [], 'area_profilo': 'informatica'})
        self.client.put('/pa/profile', json={'livello_max': 'triennale'})
        self.assertEqual(self.client.get('/pa/items').json()['items'][0]['decision'], 'non_adatto')
        self.client.put('/pa/profile', json={'livello_max': 'magistrale'})
        self.assertEqual(self.client.get('/pa/items').json()['items'][0]['decision'], 'adatto')

    def test_failing_area_does_not_stop_the_other(self):
        pa_store, gare_store = self.app.pa.AREA.store, self.app.gare.AREA.store
        pa_store.create_channel({'name': 'p', 'source': 'inpa'})
        gare_store.create_channel({'name': 'g', 'source': 'ted'})
        boom = MagicMock(side_effect=SourceError('down'))
        ok = MagicMock(return_value=[item('ted-9')])
        with patch.dict(self.app.pa.AREA.fetchers, {'inpa': boom}), \
                patch.dict(self.app.gare.AREA.fetchers, {'ted': ok}):
            self.app._refresh_areas('scheduler')
        self.assertEqual([i['key'] for i in gare_store.list_items('feed')], ['ted-9'])
        statuses = {log['site']: log['status'] for log in storage.list_logs() if log['kind'] == 'refresh'}
        self.assertEqual(statuses, {'pa:inpa': 'error', 'gare:ted': 'ok'})

    def test_extraction_with_fake_llm(self):
        store = self.app.pa.AREA.store
        cid = store.create_channel({'name': 'c', 'source': 'inpa'})['id']
        store.upsert_items(cid, [item('inpa-1')])
        llm = {'livello_richiesto': 'triennale', 'area_profilo': 'informatica', 'classi_laurea': ['L-8']}
        with patch('area_common.analyzer.is_configured', return_value=True), \
                patch('pa.llm_json', return_value=llm):
            self.assertEqual(self.app.pa.AREA.analyze_pending('manual'), 1)
        got = self.client.get('/pa/items').json()['items'][0]
        self.assertEqual(got['facts']['classi_laurea'], ['L-8'])
        self.assertEqual(got['decision'], 'adatto')


if __name__ == '__main__':
    unittest.main()
