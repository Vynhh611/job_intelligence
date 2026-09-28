"""One-shot public ATS endpoint connectivity probe. Stores counts only, never reposts JD content.
A successful response is not a grant to republish employer content.
"""
import json
from pathlib import Path
from datetime import datetime, timezone
import requests
from intelligence import infer_country
ROOT=Path(__file__).resolve().parent
cfg=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
out=[]
for provider,field in [('greenhouse','board_token'),('lever','site'),('ashby','board_name')]:
    for s in cfg.get(provider,[]):
        token=s.get(field,'')
        if not token or not s.get('enabled',True): continue
        if provider=='greenhouse': url=f'https://boards-api.greenhouse.io/v1/boards/{token}/jobs'
        elif provider=='lever': url=f'https://api.lever.co/v0/postings/{token}?mode=json'
        else: url=f'https://api.ashbyhq.com/posting-api/job-board/{token}'
        row={'company':s['company'],'provider':provider,'board':token,'checked_at':datetime.now(timezone.utc).isoformat(),'api_access':'not_checked','VN':0,'SG':0,'TW':0,'total':0,'rights_status':'Requires separate review'}
        try:
            r=requests.get(url,timeout=22,headers={'User-Agent':'JobIntelligenceAsia-SourceProbe/1.0'})
            r.raise_for_status()
            result=r.json()
            jobs=result if provider=='lever' else result.get('jobs',[])
            if not isinstance(jobs,list): raise ValueError('Unexpected JSON format')
            row['api_access']='public_get_ok';row['total']=len(jobs)
            for job in jobs:
                loc=(job.get('categories') or {}).get('location','') if provider=='lever' else ((job.get('location') or {}).get('name','') if provider=='greenhouse' else job.get('location',''))
                c=infer_country(loc)
                if c=='Vietnam': row['VN']+=1
                if c=='Singapore': row['SG']+=1
                if c=='Taiwan': row['TW']+=1
        except (requests.RequestException,ValueError,TypeError) as ex:
            row['api_access']='error: '+str(ex)[:130]
        out.append(row)
        print(f"{s['company']}: {row['api_access']}, VN={row['VN']} SG={row['SG']} TW={row['TW']}")
path=ROOT/'data/source_probe.json'
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Wrote connectivity metadata for {len(out)} candidate boards. No job descriptions collected or published.')
