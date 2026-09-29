import unittest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

from collectors.transport import payload
from discovery_collector import parse_posts, endpoint, merge_one
from freshness import freshness
from services import register_source


class PublicIndexTests(unittest.TestCase):
    def test_api_failure_preserves_snapshot_and_reports_failure(self):
        import discovery_collector as dc
        old = [{'id': 'existing', 'country': 'Vietnam', 'source_key': 'smartrecruiters:Example', 'title': 'Engineer', 'status': 'active', 'last_seen': '2026-09-28T00:00:00+00:00'}]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            (root / 'sources.json').write_text(json.dumps({'smartrecruiters': [{'company': 'Example', 'company_identifier': 'Example', 'enabled': True, 'discovery_enabled': True}]}))
            (root / 'data/discovered_jobs.json').write_text(json.dumps(old))
            with patch.object(dc, 'ROOT', root), patch.object(dc, 'DATA', root / 'data'), patch.object(dc, 'configured_store', return_value=None), patch.object(dc, 'get_json', return_value={'error': 'temporary failure'}):
                with self.assertRaises(SystemExit):
                    dc.main()
            self.assertEqual(json.loads((root / 'data/discovered_jobs.json').read_text()), old)
            self.assertEqual(json.loads((root / 'data/discovery_status.json').read_text())['successful_sources'], 0)
            self.assertEqual(json.loads((root / 'data/discovery_history.json').read_text()), [])

    def test_smartrecruiters_all_pages_and_metadata_only(self):
        def row(identity):
            return {'id': str(identity), 'name': 'Engineer', 'location': {'city': 'Da Nang', 'country': 'vn', 'hybrid': True}, 'jobAd': {'sections': {'description': 'PRIVATE JD'}}, 'typeOfEmployment': {'label': 'Full-time'}}
        calls = []
        def fetch(url):
            calls.append(url)
            return {'totalFound': 3, 'content': [row(1), row(2)] if 'offset=0' in url else [row(3)]}
        with patch('collectors.transport.time.sleep'):
            result = payload('smartrecruiters', endpoint('smartrecruiters', 'Example'), fetch, page_size=2)
        jobs = parse_posts('smartrecruiters', {'company': 'Example', 'company_identifier': 'Example'}, result)
        self.assertEqual(len(jobs), 3)
        self.assertIn('country=vn', calls[0])
        self.assertIn('offset=2', calls[1])
        self.assertEqual(jobs[0]['url'], 'https://jobs.smartrecruiters.com/Example/1')
        self.assertEqual(jobs[0]['country'], 'Vietnam')
        self.assertEqual(jobs[0]['workplace_type'], 'Hybrid')
        self.assertNotIn('description', jobs[0])
        self.assertNotIn('jobAd', jobs[0])

    def test_incomplete_changing_or_wrong_country_snapshot_rejected(self):
        base = {'id': '1', 'name': 'Engineer', 'location': {'country': 'vn'}}
        for response in [{'totalFound': 2, 'content': [base]}, {'content': []}, {'totalFound': -1, 'content': []}, {'totalFound': 1, 'content': [{**base, 'location': {'country': 'sg'}}]}]:
            with self.subTest(response=response), self.assertRaises(ValueError):
                payload('smartrecruiters', 'https://example.test/?country=vn', lambda _: response)
        pages = iter([{'totalFound': 2, 'content': [base]}, {'totalFound': 3, 'content': [{**base, 'id': '2'}]}])
        with patch('collectors.transport.time.sleep'), self.assertRaises(ValueError):
            payload('smartrecruiters', 'https://example.test/?country=vn', lambda _: next(pages), page_size=1)

    def test_repeated_smart_page_rejected(self):
        record = {'id': '1', 'name': 'Engineer', 'location': {'country': 'vn'}}
        with patch('collectors.transport.time.sleep'), self.assertRaises(ValueError):
            payload('smartrecruiters', 'https://example.test/?country=vn', lambda _: {'totalFound': 2, 'content': [record]}, page_size=1)

    def test_lever_secondary_vietnam_location_is_included_once(self):
        source = {'company': 'Example', 'site': 'example'}
        row = {'id': 'one', 'text': 'Engineer', 'country': 'sg', 'categories': {'location': 'Singapore', 'allLocations': ['Singapore', 'Ho Chi Minh City, Vietnam', 'Hanoi, Vietnam']}, 'hostedUrl': 'https://jobs.lever.co/example/one'}
        jobs = parse_posts('lever', source, [row])
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['country'], 'Vietnam')
        self.assertNotIn('Singapore', jobs[0]['location'])
        self.assertIn('Hanoi', jobs[0]['location'])

    def test_link_mode_never_enables_full_jd_or_ai(self):
        config = register_source({}, 'Example', 'https://careers.smartrecruiters.com/Example', 'https://developers.smartrecruiters.com/docs/endpoints', True, 'links', True)
        source = config['smartrecruiters'][0]
        self.assertTrue(source['discovery_enabled'])
        self.assertFalse(source['authorized'])
        self.assertFalse(source['ai_authorized'])

    def test_missing_then_closed_then_reopened_and_foreign_history_preserved(self):
        now = '2026-09-29T00:00:00+00:00'
        job = {'id': 'vn', 'source_key': 'smartrecruiters:x', 'country': 'Vietnam'}
        foreign = {'id': 'sg', 'source_key': 'smartrecruiters:x', 'country': 'Singapore', 'status': 'active'}
        first = merge_one({'sg': foreign}, [job], 'smartrecruiters:x', now)
        missing = merge_one(first, [], 'smartrecruiters:x', now)
        self.assertEqual(freshness(missing['vn']), 'missing')
        self.assertEqual(missing['vn']['last_seen'], now)
        closed = merge_one(missing, [], 'smartrecruiters:x', '2026-09-29T06:00:00+00:00')
        self.assertEqual(freshness(closed['vn']), 'closed')
        restored = merge_one(closed, [job], 'smartrecruiters:x', '2026-09-29T12:00:00+00:00')
        self.assertEqual(restored['vn']['reopen_count'], 1)
        self.assertNotIn('last_missing_check_at', restored['vn'])
        self.assertEqual(restored['sg'], foreign)

    def test_stale_or_future_timestamps_are_not_claimed_recent(self):
        now = datetime(2026, 9, 29, tzinfo=timezone.utc)
        self.assertEqual(freshness({'last_seen': '2026-09-28T23:00:00+00:00'}, now), 'recent')
        for seen in ['2026-09-25T00:00:00+00:00', '2026-10-01T00:00:00+00:00', '', 'bad', '2026-09-29T00:00:00']:
            self.assertEqual(freshness({'last_seen': seen}, now), 'stale')
