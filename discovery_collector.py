"""Link-only job discovery for published employer ATS boards.

This is deliberately separate from collector.py (which uses authorized=true for
full JD reuse). We save only title, company, location, country and original
HTTPS posting URL plus operational timestamps. Never save the response's JD.

Operators must review each board's terms for a public outgoing-link index.
Set discovery_enabled=false for a board where this use is not permitted.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from intelligence import infer_country, visible_jobs
from collectors.transport import payload as fetch_payload
from storage import load, save, configured_store

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
COUNTRIES = {'Vietnam'}
STORE = None
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'JobIntelligenceVietnam-LinkIndex/1.0 (+https://github.com/Vynhh611/job_intelligence)'})


def read_json(path, default):
    # Corrupt historical snapshots must fail closed, never become an empty index.
    return load(path, default, STORE)


def write_json(path, value):
    save(path, value, STORE)


def https_url(value):
    try:
        p = urlparse(str(value or ''))
        return bool(p.netloc) and p.scheme == 'https' and not p.username and not p.password
    except ValueError:
        return False


def get_json(url):
    for attempt in range(3):
        try:
            r = SESSION.get(url, timeout=25)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as error:
            if getattr(getattr(error, 'response', None), 'status_code', None) in (401, 403, 429):
                raise  # Respect access/rate-limit responses; wait until a later scheduled run.
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def endpoint(provider, board):
    token = quote(board, safe='')
    if provider == 'greenhouse':
        # Do not request ?content=true.
        return f'https://boards-api.greenhouse.io/v1/boards/{token}/jobs'
    if provider == 'lever':
        return f'https://api.lever.co/v0/postings/{token}?mode=json'
    if provider == 'ashby':
        # Even if the response contains description fields, we never persist them.
        return f'https://api.ashbyhq.com/posting-api/job-board/{token}'
    if provider == 'smartrecruiters':
        return f'https://api.smartrecruiters.com/v1/companies/{token}/postings?country=vn'
    raise ValueError('Unsupported provider')


def parse_posts(provider, source, payload):
    """Return in-market, HTTPS-linked metadata, excluding unlisted Ashby jobs."""
    rows = payload if provider == 'lever' else payload.get('jobs', [])
    if not isinstance(rows, list):
        raise ValueError('Unexpected API response (jobs is not a list)')
    field = {'greenhouse': 'board_token', 'lever': 'site', 'ashby': 'board_name', 'smartrecruiters': 'company_identifier'}[provider]
    board = str(source[field]).strip()
    result = []
    for item in rows:
        if not isinstance(item, dict) or (provider == 'ashby' and item.get('isListed') is False):
            continue
        if provider == 'greenhouse':
            title, location = item.get('title', ''), (item.get('location') or {}).get('name', '')
            url, source_id = item.get('absolute_url', ''), item.get('id')
        elif provider == 'lever':
            title, location = item.get('text', ''), (item.get('categories') or {}).get('location', '')
            url, source_id = item.get('hostedUrl', ''), item.get('id')
        elif provider == 'ashby':
            title, location = item.get('title', ''), item.get('location', '')
            url, source_id = item.get('jobUrl', ''), item.get('id') or item.get('jobUrl')
        else:
            source_id = item.get('id')
            title = item.get('name', '')
            info = item.get('location') or {}
            if str(info.get('country', '')).lower() not in ('vn', 'vietnam'):
                continue
            location = ', '.join(filter(None, [info.get('city'), info.get('region'), 'Vietnam']))
            url = f'https://jobs.smartrecruiters.com/{quote(board, safe="")}/{quote(str(source_id), safe="")}'
        if not isinstance(location, str):
            location = ''
        if provider == 'lever':
            locations = (item.get('categories') or {}).get('allLocations') or [location]
            if not isinstance(locations, list) or any(not isinstance(v, str) for v in locations):
                raise ValueError('Invalid Lever locations')
            vietnam_locations = [v for v in locations if infer_country(v) == 'Vietnam']
            if vietnam_locations:
                location = ' / '.join(dict.fromkeys(vietnam_locations))
            country = 'Vietnam' if vietnam_locations or str(item.get('country', '')).lower() == 'vn' else infer_country(location)
        else:
            country = infer_country(location)
        if not title or not source_id:
            raise ValueError('Posting missing title or identity; refusing partial snapshot')
        if country not in COUNTRIES or not https_url(url):
            continue
        result.append({
            'id': f'discovery:{provider}:{board}:{source_id}',
            'source_key': f'{provider}:{board}',
            'company': source['company'],
            'title': str(title).strip(),
            'location': location.strip(),
            'country': country,
            'url': url,
            'source': {'greenhouse': 'Greenhouse', 'lever': 'Lever', 'ashby': 'Ashby', 'smartrecruiters': 'SmartRecruiters'}[provider],
            'record_type': 'link_only',
            'source_board_url': source.get('careers_url', ''),
            'source_published_at': item.get('releasedDate', '') if provider == 'smartrecruiters' else item.get('publishedAt', ''),
            'employment_type': ((item.get('typeOfEmployment') or {}).get('label', '') if provider == 'smartrecruiters' else (item.get('categories') or {}).get('commitment', '') if provider == 'lever' else item.get('employmentType', '')),
            'workplace_type': ('Hybrid' if (item.get('location') or {}).get('hybrid') else 'Remote' if (item.get('location') or {}).get('remote') else 'On-site' if (item.get('location') or {}).get('remote') is False else '') if provider == 'smartrecruiters' else item.get('workplaceType', ''),
        })
    return visible_jobs(result)


def merge_one(previous, fresh, source_key, now):
    """Two consecutive successful misses close a link; API errors never reach here."""
    merged = dict(previous)
    seen = set()
    for item in fresh:
        key = item['id']
        old = previous.get(key, {})
        merged[key] = {
            **item,
            'first_seen': old.get('first_seen', now),
            'last_seen': now,
            'last_checked_at': now,
            'status': 'active',
            'missed_successful_checks': 0,
            'reopen_count': int(old.get('reopen_count', 0)) + int(old.get('status') == 'closed'),
        }
        seen.add(key)
    for key, old in previous.items():
        if old.get('country') not in COUNTRIES or old.get('source_key') != source_key or key in seen or old.get('status') == 'closed':
            continue
        # Retries within one collection window must not count as independent misses.
        last_missing = old.get('last_missing_check_at')
        if last_missing:
            elapsed = (datetime.fromisoformat(now) - datetime.fromisoformat(last_missing)).total_seconds()
            if elapsed < 6 * 3600:
                continue
        misses = int(old.get('missed_successful_checks', 0)) + 1
        merged[key] = {**old, 'missed_successful_checks': misses, 'last_checked_at': now,
                       'last_missing_check_at': now,
                       'status': 'closed' if misses >= 2 else old.get('status', 'active')}
        if misses >= 2:
            merged[key]['closed_detected_at'] = now
    return merged


def main():
    global STORE
    STORE = configured_store()
    config = read_json(ROOT / 'sources.json', {})
    read_json(DATA / 'discovery_status.json', {})
    previous = {r['id']: r for r in read_json(DATA / 'discovered_jobs.json', []) if isinstance(r, dict) and r.get('id')}
    merged = dict(previous)
    now = datetime.now(timezone.utc).isoformat()
    stats, errors = [], []
    successful = 0
    for provider, field in (('greenhouse', 'board_token'), ('lever', 'site'), ('ashby', 'board_name'), ('smartrecruiters', 'company_identifier')):
        for source in config.get(provider, []):
            if not source.get('enabled', True) or not source.get('discovery_enabled', False):
                continue
            board = str(source.get(field, '')).strip()
            company = source.get('company', '')
            if not board or not company:
                errors.append(f'{provider}: source missing board identifier/company')
                continue
            source_key = f'{provider}:{board}'
            try:
                payload = fetch_payload(provider, endpoint(provider, board), get_json)
                items = parse_posts(provider, source, payload)
                merged = merge_one(merged, items, source_key, now)
                successful += 1
                counts = {c: sum(j['country'] == c for j in items) for c in sorted(COUNTRIES)}
                stats.append({'company': company, 'source_key': source_key, 'status': 'ok',
                              'in_scope': len(items), **counts, 'checked_at': now})
                print(f'OK {source_key}: {len(items)} link-only records, VN={counts["Vietnam"]}')
            except (requests.RequestException, ValueError, KeyError, TypeError) as e:
                message = f'{source_key}: {type(e).__name__}: {str(e)[:160]}'
                errors.append(message)
                stats.append({'company': company, 'source_key': source_key, 'status': 'error',
                              'error': str(e)[:160], 'checked_at': now})
                print('ERROR', message)
    # Preserve all previous data if every board fails. In fact, failed sources
    # never modify merged, even when some other boards succeed.
    history = read_json(DATA / 'discovery_history.json', [])
    for key, item in merged.items():
        old = previous.get(key)
        # Do not append a full history snapshot just because a polling timestamp advanced.
        ignored = {'last_seen', 'last_checked_at', 'last_missing_check_at'}
        changed = old is None or {k: v for k, v in item.items() if k not in ignored} != {k: v for k, v in old.items() if k not in ignored}
        if changed:
            history.append({'job_id': key, 'at': now, 'event': 'first_seen' if old is None else 'snapshot', 'previous': old})
    write_json(DATA / 'discovery_history.json', history)
    write_json(DATA / 'discovered_jobs.json', sorted(merged.values(), key=lambda j: (j.get('last_seen', ''), j['id']), reverse=True))
    active = [j for j in merged.values() if j.get('status') == 'active' and j.get('country') in COUNTRIES]
    write_json(DATA / 'discovery_status.json', {
        'checked_at': now, 'successful_sources': successful, 'errors': errors,
        'sources': stats, 'active_records': len(active), 'total_records': len(merged),
        'mode': 'link_only', 'full_jd_stored': False,
    })
    print(f'DONE sources={successful}, active_links={len(active)}, errors={len(errors)}; no JD saved')
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
