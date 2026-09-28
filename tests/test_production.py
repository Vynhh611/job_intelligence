import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ai_explainer import OpenAIExplainer, generate, content_hash, current_explanation
from services import register_source
from source_discovery import candidates, add_pending, public_url, merge_candidates
from storage import local_read, local_write, PostgresStore, ConflictError, StorageError


class DiscoverySecurityTests(unittest.TestCase):
    def test_salary_filters_never_assume_currency_or_period(self):
        from salary import disclosed_salary, matches_salary
        self.assertIsNone(disclosed_salary({'salary_text': '20-30 triệu'}))
        self.assertIsNone(disclosed_salary({'salary_text': '$1000-2000/month'}))
        self.assertIsNone(disclosed_salary({'salary_text': 'USD 1000-2000 / month or 25-50 triệu'}))
        job = {'salary_text': '20–30 triệu/tháng'}
        self.assertEqual(disclosed_salary(job)['min'], 20000000)
        self.assertTrue(matches_salary(job, 25000000, 40000000))
        self.assertFalse(matches_salary(job, 31000000, 40000000))
        self.assertFalse(matches_salary({'salary_text': 'USD 50,000-70,000 per year'}, 4000, 6000, 'USD'))
    def test_robots_denial_no_page_request(self):
        fetch = Mock(return_value='User-agent: *\nDisallow: /')
        with self.assertRaises(ValueError):
            candidates('Employer', 'https://example.com/careers', fetch)
        fetch.assert_called_once_with('https://example.com/robots.txt')

    def test_find_ats_only_does_not_activate(self):
        fetch = Mock(side_effect=['User-agent: *\nAllow: /', '<a href="https://jobs.lever.co/demo">Jobs</a><a href="https://jobs.lever.co/demo/123">Role</a><a href="https://jobs.lever.co.evil.test/demo">Fake</a>'])
        with patch('source_discovery.time.sleep'):
            result = candidates('Demo', 'https://example.com/careers', fetch)
        self.assertEqual(len(result), 1)
        config = add_pending({}, result[0])
        self.assertFalse(config['lever'][0]['authorized'])
        self.assertFalse(config['lever'][0]['enabled'])
        config['lever'][0]['authorized'] = True
        self.assertTrue(add_pending(config, result[0])['lever'][0]['authorized'])
        self.assertEqual(len(merge_candidates(result, result)), 1)

    def test_private_networks_and_credentials_rejected(self):
        with patch('source_discovery.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaises(ValueError):
                public_url('https://internal.example/careers')
        for url in ['http://example.com', 'https://a:b@example.com', 'https://example.com:8080']:
            with self.assertRaises(ValueError):
                public_url(url)

    def test_direct_ats_detection_no_network(self):
        fetch = Mock(side_effect=AssertionError('No fetch expected'))
        result = candidates('Demo', 'https://jobs.lever.co/demo', fetch)
        self.assertEqual(result[0]['board'], 'demo')

    def test_link_permission_does_not_enable_full_jd(self):
        source = register_source({}, 'Demo', 'https://jobs.lever.co/demo', 'https://example.com/permission', True, 'links', True)['lever'][0]
        self.assertTrue(source['discovery_enabled'])
        self.assertFalse(source['authorized'])
        self.assertFalse(source['ai_authorized'])


class AIPrivacyTests(unittest.TestCase):
    def test_no_source_permission_no_api_call(self):
        adapter = Mock()
        with self.assertRaises(PermissionError):
            generate({'description': 'SQL'}, {'authorized': True}, adapter)
        adapter.explain.assert_not_called()

    def test_request_contains_only_jd_no_cv_and_no_response_storage(self):
        response = Mock(status_code=200)
        response.json.return_value = {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps({'items': [{'summary': 'Xây dựng báo cáo SQL', 'evidence': 'Build SQL reports'}]})}]}]}
        with patch.dict(os.environ, {'JOB_AI_ENABLED': 'true', 'OPENAI_MODEL': 'configured-test-model', 'OPENAI_API_KEY': 'test-placeholder'}), patch('ai_explainer.requests.post', return_value=response) as post:
            rows = generate({'description': 'Build SQL reports', 'cv_text': 'PRIVATE CV'}, {'authorized': True, 'ai_authorized': True})
        self.assertEqual(len(rows), 1)
        payload = post.call_args.kwargs['json']
        self.assertFalse(payload['store'])
        self.assertNotIn('PRIVATE CV', json.dumps(payload))
        self.assertEqual(payload['model'], 'configured-test-model')

    def test_incomplete_response_is_not_published(self):
        response = Mock(status_code=200)
        response.json.return_value = {'status': 'incomplete', 'output': []}
        with patch.dict(os.environ, {'JOB_AI_ENABLED': 'true', 'OPENAI_MODEL': 'test', 'OPENAI_API_KEY': 'test'}), patch('ai_explainer.requests.post', return_value=response):
            with self.assertRaises(ValueError):
                OpenAIExplainer().explain('JD')

    def test_changed_jd_hides_old_explanation(self):
        job = {'id': 'one', 'description': 'Old'}
        stored = {'one': {'description_hash': content_hash(job), 'items': []}}
        self.assertTrue(current_explanation(job, stored))
        self.assertFalse(current_explanation({**job, 'description': 'New'}, stored))


class StorageTests(unittest.TestCase):
    def test_atomic_json_and_invalid_json_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'snapshot.json'
            local_write(path, [{'country': 'Việt Nam'}])
            self.assertEqual(local_read(path, []), [{'country': 'Việt Nam'}])
            self.assertEqual(list(Path(folder).glob('*.tmp')), [])
            path.write_text('{invalid')
            with self.assertRaises(ValueError):
                local_read(path, [])

    def test_postgres_conflict_prevents_overwrite(self):
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        connection.execute.return_value.fetchone.return_value = (2, {'existing': True})
        store = PostgresStore('test-only')
        store.revisions['sources.json'] = 1
        with patch.object(store, 'connect', return_value=connection):
            with self.assertRaises(ConflictError):
                store.write('sources.json', {'replacement': True})
        self.assertFalse(any('UPDATE ' in str(call) for call in connection.execute.call_args_list))

    def test_postgres_errors_do_not_expose_credentials(self):
        with patch('psycopg.connect', side_effect=RuntimeError('password=DO_NOT_EXPOSE')):
            with self.assertRaises(StorageError) as error:
                PostgresStore('postgresql://test').connect()
        self.assertNotIn('DO_NOT_EXPOSE', str(error.exception))

    def test_postgres_write_preserves_previous_revision(self):
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        connection.execute.return_value.fetchone.return_value = (3, {'old': True})
        store = PostgresStore('test-only')
        store.revisions['sources.json'] = 3
        with patch.object(store, 'connect', return_value=connection):
            store.write('sources.json', {'new': True})
        self.assertEqual(store.revisions['sources.json'], 4)
        self.assertTrue(any('ji_document_history' in str(call) for call in connection.execute.call_args_list))


class AdminUITests(unittest.TestCase):
    def test_authorized_admin_loads_all_forms(self):
        from streamlit.testing.v1 import AppTest
        with patch.dict(os.environ, {'JOB_ADMIN_PASSWORD': 'test-only', 'DATABASE_URL': ''}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
            app.sidebar.radio[0].set_value('Quản trị nguồn').run()
            next(w for w in app.text_input if w.label == 'Mật khẩu quản trị').set_value('test-only').run()
            self.assertFalse(list(app.exception))
            self.assertTrue(any(w.label == 'Chọn nguồn để chỉnh sửa' for w in app.selectbox))


if __name__ == '__main__':
    unittest.main()
