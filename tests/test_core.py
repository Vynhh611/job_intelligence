import unittest
from intelligence import infer_country,skill_tags,signal_report,enrich,cv_matches
from collector import load_json
from pathlib import Path
class CoreTests(unittest.TestCase):
    def test_countries(self):
        self.assertEqual(infer_country('Taipei, Taiwan'),'Taiwan')
        self.assertEqual(infer_country('Hà Nội'),'Vietnam')
        self.assertEqual(infer_country('Singapore'),'Singapore')
        self.assertEqual(infer_country('Remote'),'Other / Remote / Unknown')
    def test_skill_tags(self):
        self.assertIn('SQL',skill_tags('Excellent SQL and Python skills'))
    def test_review_not_allegation(self):
        s=signal_report({'description':'','country':'Vietnam'})
        self.assertTrue(s)
        self.assertTrue(all(v['scope'].startswith('Tin tuyển dụng') for v in s))
    def test_enrichment(self):
        j=enrich({'id':'x','title':'Pricing Analyst','description':'SQL and forecasting','location':'Singapore'})
        self.assertEqual(j['country'],'Singapore')
        self.assertEqual(j['category'],'Revenue & Pricing')
    def test_cv(self):
        r=cv_matches('SQL and Python',{'skills':['SQL','Tableau']})
        self.assertEqual(r['matched'],['SQL'])
        self.assertEqual(r['not_detected'],['Tableau'])
    def test_data_files(self):
        p=Path(__file__).resolve().parents[1]
        self.assertIsInstance(load_json(p/'data/jobs.json',[]),list)
if __name__=='__main__':unittest.main()
