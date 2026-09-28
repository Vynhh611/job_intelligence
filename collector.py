"""Collect published roles from configured public Greenhouse / Lever job boards.

Configure sources.json with board tokens/sites and company display names.
Does not bypass access controls or scrape HTML pages.
"""
import csv
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / 'data' / 'jobs.csv'
FIELDS = ['job_id','title','company','location','category','source','posted_at','first_seen','last_seen','url','description']
HEADERS = {'User-Agent': 'JobIntelligencePersonalResearch/0.1', 'Accept': 'application/json'}
KEYWORDS = {
    'Strategy & Consulting': r'\b(strategy|strategic|consult|transformation|business design)\b',
    'Revenue & Pricing': r'\b(revenue|pricing|commercial excellence|growth management|rgm)\b',
    'Business Development': r'\b(business development|partnership|account manager|sales|b2b)\b',
    'Data & Analytics': r'\b(data|analytic|business intelligence|research|insight)\b',
    'Operations': r'\b(operation|process improvement|supply chain)\b',
}

def classify(title):
    for group, pattern in KEYWORDS.items():
        if re.search(pattern, title, re.I):
            return group
    return 'Other'

def strip_html(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', value or ''))).strip()[:2500]

def fetch_json(url, params=None):
    response = requests.get(url, params=params, headers=HEADERS, timeout=25)
    response.raise_for_status()
    return response.json()

def greenhouse(entry, now):
    token = entry['token']
    if not re.fullmatch(r'[A-Za-z0-9_-]+', token):
        raise ValueError('Invalid Greenhouse token')
    payload = fetch_json(f'https://boards-api.greenhouse.io/v1/boards/{token}/jobs', {'content':'true'})
    for j in payload.get('jobs', []):
        yield dict(job_id=f'greenhouse:{token}:{j["id"]}', title=j.get('title',''), company=entry['company'],
            location=(j.get('location') or {}).get('name',''), category=classify(j.get('title','')),
            source='Greenhouse', posted_at=j.get('updated_at',''), first_seen=now, last_seen=now,
            url=j.get('absolute_url',''), description=strip_html(j.get('content','')))

def lever(entry, now):
    site = entry['site']
    if not re.fullmatch(r'[A-Za-z0-9_-]+', site):
        raise ValueError('Invalid Lever site')
    # Lever may paginate; skip/limit are documented public Postings API parameters.
    skip = 0
    while True:
        items = fetch_json(f'https://api.lever.co/v0/postings/{site}', {'mode':'json', 'skip':skip, 'limit':100})
        if not isinstance(items, list):
            raise ValueError('Unexpected Lever API response')
        for j in items:
            categories = j.get('categories') or {}
            yield dict(job_id=f'lever:{site}:{j["id"]}', title=j.get('text',''), company=entry['company'],
                location=categories.get('location',''), category=classify(j.get('text','')),
                source='Lever', posted_at='', first_seen=now, last_seen=now,
                url=j.get('hostedUrl',''), description=strip_html(j.get('descriptionPlain','') or j.get('description','')))
        if len(items) < 100:
            break
        skip += len(items)

def previous_rows():
    if not CSV_PATH.exists():
        return {}
    with CSV_PATH.open(newline='', encoding='utf-8-sig') as f:
        return {row['job_id']:row for row in csv.DictReader(f) if row.get('job_id')}

def main():
    config = json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
    old = previous_rows()
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    collected = {}
    failures = []
    configured = 0
    for provider, fn in [('greenhouse',greenhouse), ('lever',lever)]:
        for entry in config.get(provider, []):
            configured += 1
            try:
                for j in fn(entry, now):
                    if not j['url'].startswith('https://'):
                        continue
                    j['first_seen'] = old.get(j['job_id'], {}).get('first_seen') or now
                    collected[j['job_id']] = j
                print(f'OK: {provider} / {entry["company"]}')
            except (requests.RequestException, ValueError, KeyError, TypeError) as ex:
                failures.append(f'{provider}/{entry.get("company", "?")}: {ex}')
    # Do not overwrite a known-good snapshot if the source configuration is empty or ANY API fails.
    if not configured:
        print('No sources configured: existing CSV left untouched.')
        return
    if failures:
        raise RuntimeError('Some sources failed; existing CSV retained. ' + '; '.join(failures))
    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(collected.values(), key=lambda x:(x['company'].lower(),x['title'].lower())))
    print(f'Saved {len(collected)} active published jobs on {now}.')

if __name__ == '__main__':
    main()
