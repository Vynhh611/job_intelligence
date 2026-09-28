import json
import unittest
from pathlib import Path
from employer_directory import filter_employers, merge_directory, source_stage

ROOT = Path(__file__).resolve().parents[1]


class DirectoryTests(unittest.TestCase):
    def test_merge_preserves_existing_permissions_and_country(self):
        old = [{'company': 'Hòa Phát', 'country': 'Vietnam', 'authorized': True}, {'company': 'Example', 'country': 'Singapore'}]
        fresh = [{'company': 'Hoa Phat', 'country': 'Vietnam', 'authorized': False}, {'company': 'Example', 'country': 'Vietnam'}]
        merged = merge_directory(old, fresh)
        self.assertEqual(len(merged), 3)
        self.assertTrue(merged[0]['authorized'])
        self.assertEqual(old[1]['country'], 'Singapore')

    def test_filter_supports_unaccented_vietnamese_and_source_stage(self):
        rows = [{'company': 'Hòa Phát', 'country': 'Vietnam', 'industry': 'Manufacturing'}, {'company': 'Hòa Phát', 'country': 'Singapore', 'industry': 'Manufacturing'}]
        self.assertEqual(len(filter_employers(rows, 'hoa phat')), 1)
        self.assertEqual(filter_employers(rows, 'hoa', industries=['Banking']), [])
        self.assertEqual(filter_employers(rows, stage='Có liên kết tuyển dụng'), [])
        rows[0]['website_check_status'] = 'checked'
        self.assertEqual(source_stage(rows[0]), 'Đã đọc website · cần tìm trang tuyển dụng')

    def test_expansion_has_provenance_and_does_not_promote_false_matches(self):
        rows = json.loads((ROOT / 'data/company_watchlist.json').read_text(encoding='utf-8'))
        by_name = {r['company']: r for r in rows if r['country'] == 'Vietnam'}
        self.assertGreaterEqual(len(by_name), 200)
        self.assertIsNone(by_name['Fahasa'].get('careers_url'))
        self.assertEqual(by_name['MISA']['careers_url'], 'https://www.misa.vn/tuyen-dung/')
        for row in rows:
            if row.get('verification_method') == 'official_homepage_link':
                self.assertTrue(row.get('source_url'))
                self.assertFalse(row['page_discovery_enabled'])
                self.assertEqual(row['rights_status'], 'unreviewed')

    def test_homepage_company_shortcut(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
        labels = {metric.label for metric in app.metric}
        self.assertIn('Tin việc làm trong hệ thống', labels)
        self.assertIn('Doanh nghiệp / đơn vị trong danh bạ', labels)
        next(b for b in app.button if b.label.startswith('Khám phá danh bạ')).click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.sidebar.radio[0].value, 'Doanh nghiệp')
        next(w for w in app.selectbox if w.label == 'Tình trạng nguồn tham khảo').select('Có liên kết tuyển dụng').run()
        self.assertFalse(app.exception)
        self.assertTrue(app.dataframe[0].value['Trang tuyển dụng'].notna().all())

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
