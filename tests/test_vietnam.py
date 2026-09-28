import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services import vietnam_jobs, match_cv, parse_cv, register_source, detect_board
from intelligence import canonical_job_url, enrich
from collectors.transport import payload
from discovery_collector import merge_one


class VietnamTests(unittest.TestCase):
    def test_integrations_require_permission_and_evidence(self):
        from integrations import authorized_feed, explain_job
        from unittest.mock import Mock
        adapter = Mock()
        with self.assertRaises(PermissionError):
            authorized_feed(adapter, 'https://example.com/terms')
        adapter.fetch_jobs.assert_not_called()
        adapter.explain.return_value = [{'summary': 'Phân tích dữ liệu', 'evidence': 'invented'}]
        with self.assertRaises(ValueError):
            explain_job(adapter, {'description': 'Build SQL reports'}, authorized=True)

    def test_smartrecruiters_adapter(self):
        from collectors.smartrecruiters import collect
        responses = [
            {'content': [{'id': 'one', 'name': 'Analyst', 'location': {'country': 'vn', 'city': 'Hanoi'}}], 'totalFound': 1},
            {'applyUrl': 'https://jobs.smartrecruiters.com/demo/one', 'jobAd': {'sections': {'jobDescription': {'text': '<p>Build reports</p>'}}}},
        ]
        result = list(collect({'company_identifier': 'demo', 'company': 'Demo'}, lambda _: responses.pop(0)))
        self.assertEqual(result[0]['description'], 'Build reports')
        self.assertIn('Vietnam', result[0]['location'])

    def test_corrupt_history_is_not_silently_replaced(self):
        from discovery_collector import read_json
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'history.json'
            path.write_text('{invalid')
            with self.assertRaises(ValueError):
                read_json(path, [])
            self.assertEqual(path.read_text(), '{invalid')

    def test_singapore_excluded_from_new_discovery(self):
        from discovery_collector import parse_posts
        self.assertEqual(parse_posts('lever', {'site': 'test', 'company': 'Test'}, [{'id': 'sg', 'text': 'Analyst', 'categories': {'location': 'Singapore'}, 'hostedUrl': 'https://jobs.lever.co/test/sg'}]), [])

    def test_scope_and_query_identifiers(self):
        records = [dict(id=str(i), title='Analyst', country=c, url=f'https://example.com/jobs?id={i}') for i, c in enumerate(['Vietnam', 'Singapore', 'Taiwan', 'Vietnam'])]
        self.assertEqual(len(vietnam_jobs(records)), 2)
        self.assertNotEqual(canonical_job_url(records[0]['url']), canonical_job_url(records[3]['url']))

    def test_cv_evidence_three_categories(self):
        job = enrich({'title': 'Analyst', 'description': 'SQL Python and Excel required.'})
        rows = match_cv('Built reports using SQL. Skills: Python.', job)
        by_skill = {r['Yêu cầu']: r for r in rows}
        self.assertEqual(by_skill['SQL']['Phân loại'], 'Đáp ứng')
        self.assertEqual(by_skill['Python']['Phân loại'], 'Đáp ứng một phần')
        self.assertEqual(by_skill['Excel']['Phân loại'], 'Chưa tìm thấy')
        self.assertIn('Built reports', by_skill['SQL']['Dẫn chứng CV'])

    def test_docx_in_memory(self):
        from docx import Document
        doc = Document()
        doc.add_paragraph('Built SQL reports')
        content = io.BytesIO()
        doc.save(content)
        with patch.object(Path, 'write_text', side_effect=AssertionError('No CV writes allowed')):
            self.assertIn('SQL', parse_cv(content.getvalue(), 'resume.docx'))
        with self.assertRaises(ValueError):
            parse_cv(b'x' * (5 * 1024 * 1024 + 1), 'resume.pdf')

    def test_registry_defaults_disabled_and_preserves(self):
        original = {'lever': [{'company': 'Existing', 'site': 'original', 'authorized': True}]}
        result = register_source(original, 'New', 'https://jobs.lever.co/new')
        self.assertEqual(len(original['lever']), 1)
        self.assertFalse(result['lever'][1]['authorized'])
        with self.assertRaises(ValueError):
            register_source(original, 'New', 'https://jobs.lever.co/new', enabled=True)
        with self.assertRaises(ValueError):
            detect_board('https://jobs.lever.co.evil.example/new')

    def test_complete_pagination(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return [{'id': '1'}, {'id': '2'}] if 'skip=0' in url else [{'id': '3'}]
        self.assertEqual(len(payload('lever', 'https://example.com/?mode=json', fetch, 2)), 3)
        self.assertIn('skip=2', calls[1])
        with self.assertRaises(ValueError):
            payload('greenhouse', 'https://example.com', lambda _: {})
        with self.assertRaises(ValueError):
            payload('lever', 'https://example.com', lambda _: [{'id': '1'}], 1)

    def test_non_vietnam_history_untouched(self):
        previous = {'sg': {'id': 'sg', 'country': 'Singapore', 'source_key': 'lever:test', 'status': 'active'}}
        self.assertEqual(merge_one(previous, [], 'lever:test', 'today'), previous)

    def test_no_unverified_discovery_network(self):
        import discovery_collector as dc
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'sources.json').write_text(json.dumps({'lever': [{'company': 'Test', 'site': 'test', 'enabled': True}]}))
            with patch.object(dc, 'ROOT', root), patch.object(dc, 'DATA', root / 'data'), patch.object(dc, 'get_json', side_effect=AssertionError('Unverified network call')):
                dc.main()
            self.assertEqual(json.loads((root / 'data/discovered_jobs.json').read_text()), [])


class AppSmokeTests(unittest.TestCase):
    def test_all_pages_empty_data(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
        self.assertFalse(list(app.exception))
        for page in ['Việc đã lưu', 'Doanh nghiệp', 'CV của tôi', 'Lộ trình nghề nghiệp', 'Thị trường', 'Phương pháp & riêng tư', 'Quản trị nguồn']:
            app.sidebar.radio[0].set_value(page).run()
            self.assertFalse(list(app.exception), page)

    def test_job_detail_and_save(self):
        from streamlit.testing.v1 import AppTest
        import services
        fixture = enrich({'id': 'test-only', 'title': 'SQL Analyst', 'company': 'Test fixture', 'location': 'Hanoi', 'country': 'Vietnam', 'url': 'https://example.com/job', 'description': 'Develop SQL reports. Requires Python experience.', 'status': 'active'})
        with patch.object(services, 'vietnam_jobs', return_value=[fixture]):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
            self.assertFalse(list(app.exception))
            next(b for b in app.button if b.label == '♡ Lưu việc').click().run()
            self.assertIn('test-only', app.session_state['saved_jobs'])
            next(b for b in app.button if b.label == 'Tìm hiểu công việc →').click().run()
            self.assertFalse(list(app.exception))
            self.assertEqual(app.query_params['job'], ['test-only'])
            app.sidebar.radio[0].set_value('CV của tôi').run()
            self.assertFalse(list(app.exception))
            self.assertNotIn('job', app.query_params)
            self.assertTrue(any('đối chiếu' in title.value for title in app.title))


if __name__ == '__main__':
    unittest.main()

