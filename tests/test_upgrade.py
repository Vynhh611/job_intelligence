import unittest
from datetime import datetime, timezone
from intelligence import enrich, evidence_snippet, new_in_last_days, visible_jobs, canonical_job_url, requirement_lines

class UpgradeTests(unittest.TestCase):
    def test_visa_conservative(self):
        yes=enrich({'title':'Analyst','location':'Singapore','description':'We can sponsor a work permit. Fluent English required.'})
        self.assertEqual(yes['visa_sponsorship'],'Sponsored')
        self.assertEqual(yes['language_requirements'],['English'])
        no=enrich({'title':'Analyst','location':'Singapore','description':'Must already have the right to work.'})
        self.assertEqual(no['visa_sponsorship'],'Not sponsored')
        unknown=enrich({'title':'Analyst','location':'Singapore','description':'Great team and benefits.'})
        self.assertEqual(unknown['visa_sponsorship'],'Unknown')
    def test_evidence(self):
        self.assertIn('SQL',evidence_snippet('Must have SQL and Python knowledge','SQL'))
        self.assertTrue(any('3 years' in line for line in requirement_lines('Requires 3 years of experience.')))
    def test_exact_url_dedup_only(self):
        a={'url':'https://a.example/job/123?utm_source=x','title':'Analyst'}
        b={'url':'https://a.example/job/123','title':'Analyst'}
        c={'url':'https://b.example/job/123','title':'Analyst'}
        self.assertEqual(canonical_job_url(a['url']),canonical_job_url(b['url']))
        self.assertEqual(len(visible_jobs([a,b,c])),2)
    def test_last_week(self):
        now=datetime(2026,9,28,tzinfo=timezone.utc)
        self.assertEqual(new_in_last_days([{'first_seen':'2026-09-27T00:00:00+00:00'},{'first_seen':'2026-08-01T00:00:00+00:00'}],now=now),1)
if __name__=='__main__':unittest.main()
