"""Template preservation, migration and lossless export with realistic CV structure."""
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'webapp'), str(ROOT)]
import analyzer
import cv_render
import cv_template
import cv_import
import cv_review
import storage
from fastapi.testclient import TestClient
import app
from pypdf import PdfReader
import pdfplumber
from reportlab.pdfgen import canvas

SAMPLE = '''Demo Candidate
Backend Engineer
Verona · demo@example.com
PROFILO
Sviluppatore di servizi Python e FastAPI,
con esperienza in API REST e database relazionali.
ESPERIENZA
Backend Engineer 11/2025 - oggi
Example S.r.l. | Verona, Italia
• Progettazione di API REST in Python.
• Integrazione di servizi esterni e database.
ISTRUZIONE
Laurea in Informatica 10/2018 - 10/2022
Università di esempio | Verona, Italia
COMPETENZE TECNICHE
Linguaggi: Python, SQL
Backend e API: FastAPI, API REST
LINGUE
Italiano: madrelingua
Inglese: B2'''


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = patch.object(storage, '_DB_PATH', str(Path(self.tmp.name) / 'test.db'))
        self.backups = patch.object(storage, '_BACKUP_DIR', str(Path(self.tmp.name) / 'backups'))
        self.db.start(); self.backups.start(); storage.init_db()
        self.client = TestClient(app.app)

    def tearDown(self):
        self.db.stop(); self.backups.stop(); self.tmp.cleanup()

    def test_plain_pdf_lines_become_structured_cv_without_model(self):
        name, header, sections = cv_template.parse(SAMPLE)
        self.assertEqual(name, 'Demo Candidate')
        self.assertEqual(len(sections), 5)
        self.assertIn('FastAPI, con esperienza', sections[0].blocks[0][1])
        for template in ['europass', 'classic']:
            with self.subTest(template=template):
                pdf = PdfReader(io.BytesIO(cv_render.markdown_to_pdf(SAMPLE, template)))
                self.assertEqual(len(pdf.pages), 1)
                text = pdf.pages[0].extract_text()
                for token in ['Demo Candidate', 'demo@example.com', '11/2025', 'Example S.r.l.', 'Università', 'Italiano', 'FastAPI']:
                    self.assertIn(token, text)
                # Embedded fonts, including accented characters; no bitmap-only export.
                fonts = pdf.pages[0]['/Resources']['/Font'].get_object()
                self.assertTrue(any('/FontFile2' in f.get_object()['/FontDescriptor'].get_object()
                                    for f in fonts.values() if '/FontDescriptor' in f.get_object()))

    def test_template_change_does_not_reanalyze_or_change_cv_facts(self):
        cid = storage.create_cv('Base', SAMPLE)
        context = storage.analysis_context()
        with patch.object(app, '_kick_analysis') as kick:
            response = self.client.patch(f'/cvs/{cid}', json={'template': 'classic'})
        self.assertEqual(response.status_code, 200)
        kick.assert_not_called()
        self.assertEqual(storage.get_cv(cid)['template'], 'classic')
        self.assertEqual(storage.get_cv(cid)['markdown'], SAMPLE)
        self.assertEqual(storage.analysis_context(), context)
        self.assertEqual(self.client.patch(f'/cvs/{cid}', json={'template': 'untrusted'}).status_code, 422)

    def test_revisions_and_tailored_cvs_inherit_template(self):
        cid = storage.create_cv('Base', SAMPLE, template='classic')
        res = self.client.post(f'/cvs/{cid}/revision', json={'source_hash': cv_review.source_hash(SAMPLE),
            'patches': [{'before': 'Progettazione di API REST in Python.', 'after': 'Sviluppo di API REST in Python.'}]})
        self.assertEqual(res.status_code, 201, res.text)
        self.assertEqual(res.json()['cv']['template'], 'classic')
        storage.upsert_jobs([{'job_url': 'https://example.com/job', 'title': 'Backend Engineer'}])
        with patch.object(analyzer, 'tailor_cv', return_value={'markdown': SAMPLE, 'changes': []}):
            res = self.client.post('/cvs/tailor', json={'job_url': 'https://example.com/job', 'base_cv_id': cid})
        self.assertEqual(res.status_code, 201, res.text)
        self.assertEqual(res.json()['cv']['template'], 'classic')

    def test_existing_database_gets_template_without_changing_content(self):
        cid = storage.create_cv('Base', SAMPLE)
        with storage._connect() as conn:
            conn.execute('ALTER TABLE cvs DROP COLUMN template')
        storage.init_db(); storage.init_db()
        self.assertEqual(storage.get_cv(cid)['markdown'], SAMPLE)
        self.assertEqual(storage.get_cv(cid)['template'], 'europass')

    def test_long_cv_paginates_without_losing_last_entry_or_stranding_headings(self):
        text = SAMPLE + '\n\n## Progetti\n\n' + '\n\n'.join(f'- Progetto {i}: servizi Python e API REST. ' * 8 for i in range(35)) + '\n\n## Certificazioni\n\nFinal marker XYZ'
        for template in ['classic', 'europass']:
            pdf = PdfReader(io.BytesIO(cv_render.markdown_to_pdf(text, template)))
            self.assertGreater(len(pdf.pages), 1)
            extracted = '\n'.join(page.extract_text() for page in pdf.pages)
            self.assertIn('Final marker XYZ', extracted)
            self.assertIn('Progetto 34', extracted)

    def test_markup_cannot_fetch_remote_assets(self):
        text = '# Demo\n\n## Profilo\n\n<img src="https://example.com/secret">\n\nPython & SQL'
        result = cv_render.check_pdf(text, 'classic')
        self.assertIn('<img', result['text'])
        self.assertIn('Python & SQL', result['text'])

    def test_two_column_import_keeps_main_and_sidebar_separate(self):
        out = io.BytesIO()
        c = canvas.Canvas(out)
        c.drawString(197, 790, 'Demo Candidate')
        for i in range(14):
            c.drawString(197, 670-i*15, f'MAIN {i} Python services backend development')
            c.drawString(32, 670-i*15, f'SIDE {i} Docker Git')
        c.save()
        with pdfplumber.open(io.BytesIO(out.getvalue())) as pdf:
            result = cv_import.page_text(pdf.pages[0])
        self.assertLess(result.index('MAIN 13'), result.index('SIDE 0'))
        self.assertTrue(result.startswith('Demo Candidate'))
        self.assertEqual(result.count('MAIN'), 14)
        self.assertEqual(result.count('SIDE'), 14)

    def test_single_column_import_retains_reading_order(self):
        source = cv_render.markdown_to_pdf(SAMPLE, 'classic')
        with pdfplumber.open(io.BytesIO(source)) as pdf:
            result = cv_import.page_text(pdf.pages[0])
            self.assertEqual(result, pdf.pages[0].extract_text())

    def test_browser_preview_is_real_pdf_raster_and_handles_missing_pages(self):
        cid = storage.create_cv('Base', SAMPLE)
        self.assertEqual(self.client.get(f'/cvs/{cid}/preview').json(), {'pages': 1})
        image = self.client.get(f'/cvs/{cid}/preview/1')
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image.headers['content-type'], 'image/png')
        self.assertTrue(image.content.startswith(b'\x89PNG'))
        self.assertEqual(self.client.get(f'/cvs/{cid}/preview/999').status_code, 404)
