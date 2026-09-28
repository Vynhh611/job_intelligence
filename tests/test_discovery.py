import unittest
from discovery_collector import parse_posts, merge_one, endpoint

SRC={'company':'Example Employer','board_token':'board','site':'board','board_name':'board'}
NOW='2026-09-28T00:00:00+00:00'
class DiscoveryTests(unittest.TestCase):
    def test_greenhouse_no_description(self):
        x=parse_posts('greenhouse',SRC,{'jobs':[{'id':1,'title':'Data Analyst','location':{'name':'Hanoi, Vietnam'},'absolute_url':'https://boards.greenhouse.io/example/jobs/1','content':'secret JD'}]})
        self.assertEqual(len(x),1)
        self.assertEqual(x[0]['country'],'Vietnam')
        self.assertNotIn('description',x[0]);self.assertNotIn('content',x[0])
        self.assertNotIn('content=true',endpoint('greenhouse','board'))
    def test_lever_country_filter_and_url(self):
        jobs=[{'id':'x','text':'Analyst','categories':{'location':'Singapore'},'hostedUrl':'https://jobs.lever.co/example/x','descriptionPlain':'full JD'},
              {'id':'y','text':'Analyst','categories':{'location':'Berlin'},'hostedUrl':'https://jobs.lever.co/example/y'}]
        x=parse_posts('lever',SRC,jobs)
        self.assertEqual(len(x),1);self.assertEqual(x[0]['title'],'Analyst');self.assertNotIn('descriptionPlain',x[0])
    def test_ashby_unlisted_excluded(self):
        jobs=[{'id':'one','title':'PM','location':'Singapore','jobUrl':'https://jobs.ashbyhq.com/e/1','isListed':False},
              {'id':'two','title':'PM','location':'Singapore','jobUrl':'https://jobs.ashbyhq.com/e/2','isListed':True,'descriptionPlain':'do not persist'}]
        x=parse_posts('ashby',SRC,{'jobs':jobs})
        self.assertEqual(len(x),1);self.assertTrue(x[0]['id'].endswith('two'));self.assertNotIn('descriptionPlain',x[0])
    def test_bad_urls_rejected(self):
        x=parse_posts('lever',SRC,[{'id':'x','text':'Analyst','categories':{'location':'Singapore'},'hostedUrl':'javascript:alert(1)'}])
        self.assertEqual(x,[])
    def test_tw_excluded_initial_scope(self):
        x=parse_posts('lever',SRC,[{'id':'x','text':'Analyst','categories':{'location':'Taipei, Taiwan'},'hostedUrl':'https://jobs.lever.co/e/x'}])
        self.assertEqual(x,[])
    def test_two_misses_and_reopening(self):
        new={'id':'discovery:lever:board:x','source_key':'lever:board','title':'Analyst','company':'Example Employer','location':'Singapore','country':'Singapore','url':'https://jobs.lever.co/e/x','source':'Lever','record_type':'link_only'}
        a=merge_one({},[new],'lever:board',NOW)
        b=merge_one(a,[],'lever:board',NOW)
        self.assertEqual(b[new['id']]['status'],'active')
        c=merge_one(b,[],'lever:board',NOW)
        self.assertEqual(c[new['id']]['status'],'closed')
        d=merge_one(c,[new],'lever:board',NOW)
        self.assertEqual(d[new['id']]['reopen_count'],1)
        self.assertEqual(d[new['id']]['status'],'active')
    def test_other_source_preserved(self):
        prev={'foreign':{'id':'foreign','source_key':'ashby:other','status':'active'}}
        x=merge_one(prev,[],'lever:board',NOW)
        self.assertEqual(x,prev)
if __name__=='__main__':unittest.main()
