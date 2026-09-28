"""Multi-source public ATS collector. Add sources only when use is authorized.
Usage: python collector.py --dry-run | python collector.py
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import requests
from intelligence import enrich, infer_country, plain
from collectors.transport import payload
from collectors.smartrecruiters import collect as collect_smartrecruiters
from storage import load, save, configured_store

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
DATA.mkdir(exist_ok=True)
SESSION=requests.Session()
SESSION.headers.update({'User-Agent':'JobIntelligenceAsia/1.0 (public recruitment source monitor)'})
TIMEOUT=25
COUNTRIES={'Vietnam'}
STORE=None

def get_json(url):
    last=None
    for n in range(3):
        try:
            time.sleep(.2)
            r=SESSION.get(url,timeout=TIMEOUT)
            if r.status_code==429 or 500 <= r.status_code < 600:
                r.raise_for_status()
            r.raise_for_status()
            return r.json()
        except (requests.RequestException,ValueError) as exc:
            last=exc
            if n<2: time.sleep(1.5*(n+1))
    raise last

def greenhouse(source):
    token=quote(source['board_token'].strip(),safe='')
    result=payload('greenhouse', f'https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true', get_json)
    for j in result.get('jobs',[]):
        loc=(j.get('location') or {}).get('name','')
        yield {'id':f'greenhouse:{token}:{j["id"]}','title':j.get('title',''),'company':source['company'],
               'location':loc,'url':j.get('absolute_url',''),'description':j.get('content',''),
               'source':'Greenhouse','source_key':f'greenhouse:{token}','source_updated_at':j.get('updated_at','')}

def lever(source):
    site=quote(source['site'].strip(),safe='')
    listings=payload('lever', f'https://api.lever.co/v0/postings/{site}?mode=json', get_json)
    for j in listings:
        cats=j.get('categories') or {}
        desc=' '.join(str(j.get(k) or '') for k in ('descriptionPlain','additionalPlain','description','additional'))
        desc+=' '+' '.join(plain(v.get('content','')) for v in (j.get('lists') or []) if isinstance(v,dict))
        yield {'id':f'lever:{site}:{j["id"]}','title':j.get('text',''),'company':source['company'],
               'location':cats.get('location',''),'url':j.get('hostedUrl',''),'description':desc,
               'source':'Lever','source_key':f'lever:{site}','employment_type':cats.get('commitment') or 'Not specified',
               'source_updated_at':''}

def ashby(source):
    board=quote(source['board_name'].strip(),safe='')
    result=payload('ashby', f'https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true', get_json)
    for j in result.get('jobs',[]):
        if j.get('isListed') is False: continue
        comp=j.get('compensation') or {}
        yield {'id':f'ashby:{board}:{j.get("id") or j.get("jobUrl")}', 'title':j.get('title',''),
               'company':source['company'],'location':j.get('location',''),'url':j.get('jobUrl',''),
               'description':j.get('descriptionPlain') or j.get('descriptionHtml') or '',
               'source':'Ashby','source_key':f'ashby:{board}',
               'salary_text':comp.get('compensationTierSummary') or comp.get('scrapeableCompensationSalarySummary') or '',
               'workplace_type':j.get('workplaceType') or 'Not specified',
               'employment_type':j.get('employmentType') or 'Not specified',
               'source_updated_at':j.get('publishedAt','')}

def smartrecruiters(source):
    yield from collect_smartrecruiters(source, get_json)

COLLECTORS={'greenhouse':greenhouse,'lever':lever,'ashby':ashby,'smartrecruiters':smartrecruiters}
def load_json(path,default):
    return load(path, default, STORE)
def save_json(path,value):
    save(path, value, STORE)

def main():
    global STORE
    STORE=configured_store()
    parser=argparse.ArgumentParser()
    parser.add_argument('--dry-run',action='store_true',help='Report counts without writing snapshots')
    args=parser.parse_args()
    config=load_json(ROOT/'sources.json',{})
    previous={j['id']:j for j in load_json(DATA/'jobs.json',[])}
    history=load_json(DATA/'history.json',[])
    prior_status=load_json(DATA/'run_status.json',{})
    last_good={s['source_key']:s.get('last_success_at') or s.get('checked_at') for s in prior_status.get('sources',[]) if s.get('status')=='ok' or s.get('last_success_at')}
    now=datetime.now(timezone.utc).isoformat()
    updated={}; stats=[]; errors=[]; successes=0
    for name,fn in COLLECTORS.items():
        for source in config.get(name,[]):
            if not source.get('enabled',True): continue
            if not source.get('authorized',False):
                print(f'SKIP {name}/{source.get("company")}: set authorized=true only after confirming terms / permission')
                continue
            key_name={'greenhouse':'board_token','lever':'site','ashby':'board_name','smartrecruiters':'company_identifier'}[name]
            key=source.get(key_name,'')
            if not key or not source.get('company'):
                errors.append(f'Invalid source {name}/{source}: missing {key_name} or company')
                continue
            source_key=f'{name}:{key}'
            try:
                fresh=list(fn(source))
                from urllib.parse import urlsplit
                for record in fresh:
                    link = urlsplit(record.get('url', ''))
                    if not record.get('id') or not record.get('title') or link.scheme != 'https' or not link.hostname or link.username or link.password:
                        raise ValueError('Invalid job record; refusing incomplete board update')
                in_scope=0
                source_updates={}
                for j in fresh:
                    j['country']=infer_country(j['location'])
                    if j['country'] not in COUNTRIES: continue
                    in_scope+=1
                    old=previous.get(j['id'],{})
                    j['first_seen']=old.get('first_seen',now)
                    j['last_seen']=now
                    j['status']='active'
                    j['reopen_count']=old.get('reopen_count',0)+(1 if old.get('status')=='closed' else 0)
                    source_updates[j['id']]=enrich(j)
                updated.update(source_updates)
                successes+=1
                stats.append({'source_key':source_key,'company':source['company'],'provider':name,'fetched':len(fresh),'in_scope':in_scope,'checked_at':now,'last_success_at':now,'status':'ok'})
                print(f'OK {source_key}: fetched={len(fresh)}, VN={in_scope}')
                # Close only after TWO successful consecutive checks where posting is absent.
                observed={j['id'] for j in fresh}
                for jid,old in previous.items():
                    if old.get('country') not in COUNTRIES or old.get('source_key')!=source_key or jid in observed: continue
                    if old.get('status')=='closed': continue
                    updated_old=dict(old)
                    updated_old['missed_successful_checks']=old.get('missed_successful_checks',0)+1
                    if updated_old['missed_successful_checks']>=2:
                        updated_old['status']='closed'
                        updated_old['closed_detected_at']=now
                        history.append({'job_id':jid,'event':'closed_detected','at':now,'source':source_key})
                    updated[jid]=updated_old
                for jid,j in list(updated.items()):
                    if j.get('source_key')==source_key and jid in observed:
                        j['missed_successful_checks']=0
            except (requests.RequestException,ValueError,KeyError,TypeError) as e:
                errors.append(f'{source_key}: {e}')
                stats.append({'source_key':source_key,'company':source.get('company',''),'provider':name,'checked_at':now,'last_success_at':last_good.get(source_key),'status':'error','error':str(e)[:200]})
                print('ERROR',errors[-1])
    merged=dict(previous)
    for jid,job in updated.items():
        old=previous.get(jid)
        if old is None: history.append({'job_id':jid,'event':'first_seen','at':now,'source':job['source_key']})
        elif old.get('status')=='closed' and job.get('status')=='active':
            history.append({'job_id':jid,'event':'reopened','at':now,'source':job['source_key']})
        if old and job != old:
            history.append({'job_id':jid,'event':'snapshot','at':now,'source':job['source_key'],'previous':old})
        merged[jid]=job
    if not args.dry_run:
        # Never overwrite a populated snapshot if all configured sources fail.
        if successes:
            save_json(DATA/'jobs.json',sorted(merged.values(),key=lambda j:(j.get('last_seen',''),j['id']),reverse=True))
            save_json(DATA/'history.json',history)
        save_json(DATA/'run_status.json',{'checked_at':now,'successful_sources':successes,'errors':errors,'sources':stats,'total_records':len(merged)})
    print(f'DONE successes={successes}, records={len(merged)}, errors={len(errors)}')
    if errors: raise SystemExit(1)

if __name__=='__main__': main()
