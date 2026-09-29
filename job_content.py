"""Public posting content, separate from discovery and contractual/AI permissions."""
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from intelligence import plain
from storage import load, save, configured_store


def clean(value):
    value = re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>', '', str(value or ''), flags=re.S | re.I)
    value = re.sub(r'</(?:p|li|div|h[1-6])>|<br\s*/?>', '\n', value, flags=re.I)
    return '\n'.join(plain(line) for line in value.splitlines() if plain(line))


def parse_content(provider, item):
    sections = []
    extra = {}
    if provider == 'smartrecruiters':
        labels = {'jobDescription': 'Mô tả công việc', 'qualifications': 'Yêu cầu tuyển dụng',
                  'additionalInformation': 'Quyền lợi & thông tin bổ sung', 'companyDescription': 'Về doanh nghiệp'}
        raw = (item.get('jobAd') or {}).get('sections') or {}
        for key in labels:
            text = clean((raw.get(key) or {}).get('text'))
            if text:
                sections.append({'title': labels[key], 'text': text})
        for target, key in [('experience', 'experienceLevel'), ('department', 'department'), ('employment_type', 'typeOfEmployment')]:
            extra[target] = (item.get(key) or {}).get('label', '')
    elif provider == 'lever':
        sections.append({'title': 'Mô tả công việc', 'text': clean(item.get('description') or item.get('descriptionPlain'))})
        for section in item.get('lists') or []:
            sections.append({'title': plain(section.get('text')) or 'Thông tin bổ sung', 'text': clean(section.get('content'))})
        sections.append({'title': 'Thông tin bổ sung', 'text': clean(item.get('additional') or item.get('additionalPlain'))})
        extra['department'] = (item.get('categories') or {}).get('department', '')
        salary = item.get('salaryRange') or {}
        if salary.get('currency') and salary.get('interval') and salary.get('min') is not None and salary.get('max') is not None:
            extra['salary_text'] = f'{salary["min"]:,}–{salary["max"]:,} {salary["currency"]} / {salary["interval"]}'
    else:
        sections.append({'title': 'Mô tả & yêu cầu công việc', 'text': clean(item.get('descriptionHtml') or item.get('descriptionPlain'))})
        extra['department'] = item.get('department', '')
        compensation = item.get('compensation') or {}
        if compensation.get('scrapeableCompensationSalarySummary'):
            extra['salary_text'] = plain(compensation['scrapeableCompensationSalarySummary'])
    sections = [s for s in sections if s['text']]
    if not sections:
        raise ValueError('No public description')
    return {**extra, 'sections': sections, 'description': '\n\n'.join(s['text'] for s in sections)}


def collect_content(records, config, previous, fetch, now):
    result = dict(previous)
    errors = []
    fields = {'smartrecruiters': 'company_identifier', 'lever': 'site', 'ashby': 'board_name'}
    for provider, field in fields.items():
        for source in config.get(provider, []):
            if not (source.get('enabled', True) and source.get('discovery_enabled') and source.get('public_description_enabled')):
                continue
            board = source[field]
            key = f'{provider}:{board}'
            jobs = [j for j in records if j.get('source_key') == key and j.get('country') == 'Vietnam' and j.get('status') == 'active']
            bulk = None
            try:
                if provider == 'ashby' and jobs:
                    payload = fetch(f'https://api.ashbyhq.com/posting-api/job-board/{quote(board, safe="")}')
                    bulk = {str(j.get('id')): j for j in payload['jobs'] if j.get('isListed') is not False}
                for job in jobs:
                    identity = job['id'].split(':', 3)[-1]
                    if provider == 'smartrecruiters':
                        url = f'https://api.smartrecruiters.com/v1/companies/{quote(board, safe="")}/postings/{quote(identity, safe="")}'
                    elif provider == 'lever':
                        url = f'https://api.lever.co/v0/postings/{quote(board, safe="")}/{quote(identity, safe="")}?mode=json'
                    else:
                        url = f'https://api.ashbyhq.com/posting-api/job-board/{quote(board, safe="")}'
                    try:
                        item = bulk[identity] if bulk is not None else fetch(url)
                        if str(item.get('id')) != identity:
                            raise ValueError('Posting identity mismatch')
                        result[job['id']] = {**parse_content(provider, item), 'fetched_at': now, 'source_url': job['url'], 'api_url': url}
                    except (ValueError, KeyError, requests.RequestException) as error:
                        errors.append({'id': job['id'], 'error': type(error).__name__})
                        if getattr(getattr(error, 'response', None), 'status_code', None) in (401, 403, 429):
                            break
                print(f'{key}: {sum(j["id"] in result for j in jobs)}/{len(jobs)} descriptions', flush=True)
            except (ValueError, KeyError, requests.RequestException) as error:
                errors.append({'source_key': key, 'error': type(error).__name__})
    return result, errors


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--missing-only', action='store_true', help='Bootstrap newly connected postings without refetching existing descriptions')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    store = configured_store()
    records = load(root / 'data/discovered_jobs.json', [], store)
    config = load(root / 'sources.json', {}, store)
    previous = load(root / 'data/job_content.json', {}, store)
    if args.missing_only:
        records = [r for r in records if r['id'] not in previous]
    session = requests.Session()
    session.headers['User-Agent'] = 'JobIntelligenceVietnam/1.0 (+https://github.com/Vynhh611/job_intelligence)'
    def fetch(url):
        time.sleep(.12)
        response = session.get(url, timeout=20, allow_redirects=False)
        response.raise_for_status()
        return response.json()
    now = datetime.now(timezone.utc).isoformat()
    content, errors = collect_content(records, config, previous, fetch, now)
    save(root / 'data/job_content.json', content, store)
    save(root / 'data/content_status.json', {'checked_at': now, 'descriptions': len(content), 'errors': errors}, store)
    print(f'Total descriptions: {len(content)}; errors: {len(errors)}')


if __name__ == '__main__':
    main()
