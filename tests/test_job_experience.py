import unittest
from unittest.mock import Mock
import requests

from locations import location_tags
from job_content import parse_content, collect_content
from services import rank_jobs, vietnam_jobs
from intelligence import enrich


class JobExperienceTests(unittest.TestCase):
    def test_city_aliases_and_multilocation(self):
        for value in ['Hanoi, Vietnam', 'Hanoi, Hanoi, Vietnam', 'Hanoi, Ha Noi, Vietnam', 'Hà Nội, Việt Nam']:
            self.assertEqual(location_tags(value), ['Hà Nội'])
        self.assertEqual(location_tags('Ho Chi Minh City, HCM, Vietnam'), ['TP. Hồ Chí Minh'])
        self.assertEqual(location_tags('Hanoi / Ho Chi Minh City'), ['Hà Nội', 'TP. Hồ Chí Minh'])
        self.assertEqual(location_tags('Ho Chi Minh, Lot 3/21, 19/5A Street, Vietnam'), ['TP. Hồ Chí Minh'])
        job = vietnam_jobs([dict(id='1', title='A', url='https://example.com/a', country='Vietnam', location='Hanoi, Ha Noi, Vietnam')])[0]
        self.assertEqual(job['source_location'], 'Hanoi, Ha Noi, Vietnam')
        self.assertEqual(job['location'], 'Hà Nội')

    def test_sections_are_complete_and_safe_text(self):
        result = parse_content('smartrecruiters', {'jobAd': {'sections': {
            'jobDescription': {'text': '<p>Build software.</p><ul><li>Test products.</li></ul><script>evil()</script>'},
            'qualifications': {'text': '<p>Python required.</p>'},
            'additionalInformation': {'text': '<p>Annual leave.</p>'}}}})
        self.assertEqual(len(result['sections']), 3)
        self.assertIn('Annual leave.', result['description'])
        self.assertNotIn('evil', result['description'])
        self.assertIn('\n', result['sections'][0]['text'])

    def test_fetch_errors_preserve_previous_and_stop_rate_limit(self):
        jobs = [dict(id=f'discovery:lever:test:{i}', source_key='lever:test', country='Vietnam', status='active', url=f'https://jobs.lever.co/test/{i}') for i in range(2)]
        config = {'lever': [dict(site='test', discovery_enabled=True, public_description_enabled=True)]}
        previous = {jobs[0]['id']: {'description': 'Earlier JD', 'fetched_at': 'earlier'}}
        response = requests.Response(); response.status_code = 429
        fetch = Mock(side_effect=requests.HTTPError(response=response))
        result, errors = collect_content(jobs, config, previous, fetch, 'now')
        self.assertEqual(result, previous)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(len(errors), 1)
        config['lever'][0]['public_description_enabled'] = False
        fetch.reset_mock()
        collect_content(jobs, config, previous, fetch, 'now')
        fetch.assert_not_called()

    def test_rank_search_and_unknown(self):
        jobs = [enrich(dict(id='1', title='Data Engineer', company='A', description='Build Python SQL pipelines.')),
                enrich(dict(id='2', title='Sales Executive', company='B', description='Sales and customer service.')),
                enrich(dict(id='3', title='Python vacancy', company='C'))]
        result = rank_jobs('Built Python SQL pipelines.', jobs)
        self.assertEqual(result[0]['job']['id'], '1')
        self.assertGreater(result[0]['score'], result[1]['score'])
        self.assertIsNone(result[-1]['score'])
        self.assertEqual(len(rank_jobs('', jobs, 'sales')), 1)
        self.assertEqual(rank_jobs('SQL', jobs, 'notthere'), [])

    def test_cv_list_search_pagination_and_details(self):
        from streamlit.testing.v1 import AppTest
        from pathlib import Path
        from unittest.mock import patch
        import services
        jobs = [enrich(dict(id=str(i), title=f'Python Engineer {i}', company='Fixture', country='Vietnam', location='Hanoi', url=f'https://example.com/{i}', description='Build Python software.')) for i in range(14)]
        with patch.object(services, 'vietnam_jobs', return_value=jobs):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
            app.session_state['cv_text'] = 'Built Python software.'
            app.sidebar.radio[0].set_value('CV của tôi').run()
            self.assertFalse(list(app.exception))
            self.assertEqual(sum(b.label == 'Tìm hiểu công việc →' for b in app.button), 12)
            app.number_input(key='cv-page').set_value(2).run()
            self.assertEqual(sum(b.label == 'Tìm hiểu công việc →' for b in app.button), 2)
            app.text_input(key='cv-search').set_value('Engineer 13').run()
            self.assertFalse(list(app.exception))
            self.assertEqual(app.number_input(key='cv-page').value, 1)
            self.assertEqual(sum(b.label == 'Tìm hiểu công việc →' for b in app.button), 1)
            next(b for b in app.button if b.label == 'Tìm hiểu công việc →').click().run()
            self.assertFalse(list(app.exception))
            self.assertTrue(any('Mô tả đầy đủ' in s.value for s in app.subheader))


if __name__ == '__main__':
    unittest.main()
