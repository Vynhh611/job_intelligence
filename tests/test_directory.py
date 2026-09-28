import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DirectoryTests(unittest.TestCase):
    def test_new_references_do_not_enable_collection(self):
        entries = json.loads((ROOT / 'data/employer_references_20260928.json').read_text(encoding='utf-8'))
        directory = json.loads((ROOT / 'data/company_watchlist.json').read_text(encoding='utf-8'))
        keys = [(r['company'].casefold(), r['country']) for r in directory]
        self.assertEqual(len(keys), len(set(keys)))
        for row in entries:
            self.assertEqual(row['rights_status'], 'unreviewed')
            self.assertFalse(row['page_discovery_enabled'])
            self.assertTrue(row['source_url'].startswith('https://'))
            self.assertIn((row['company'].casefold(), row['country']), keys)
            if row.get('linkedin_url'):
                self.assertTrue(row.get('linkedin_evidence_url'))

    def test_directory_filter_and_empty_results(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
        app.sidebar.radio[0].set_value('Doanh nghiệp').run()
        search = next(w for w in app.text_input if w.label == 'Tìm trong danh bạ')
        search.set_value('Bosch').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value['Doanh nghiệp'].tolist(), ['Bosch Vietnam'])
        search.set_value('no-such-company-12345').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Chưa có doanh nghiệp phù hợp' in w.value for w in app.info))
