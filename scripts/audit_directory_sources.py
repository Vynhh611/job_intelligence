"""Inspect existing employer career URLs, respecting robots and recording blockers."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from source_discovery import candidates


def inspect(row):
    result = {'company': row['company'], 'careers_url': row.get('careers_url'), 'checked_at': datetime.now(timezone.utc).isoformat()}
    if not result['careers_url']:
        return {**result, 'status': 'missing_careers_url', 'candidates': []}
    try:
        found = candidates(row['company'], result['careers_url'])
        return {**result, 'status': 'ats_found' if found else 'custom_portal_needs_adapter', 'candidates': found}
    except Exception as error:
        return {**result, 'status': 'needs_review', 'reason': str(error)[:300], 'candidates': []}


if __name__ == '__main__':
    registry = json.loads((ROOT / 'data/company_watchlist.json').read_text(encoding='utf-8'))
    rows = list({(r['company'], r.get('careers_url')): r for r in registry if r.get('country') == 'Vietnam'}.values())
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(inspect, rows):
            results.append(result)
            if result['candidates']:
                print(result['company'], [(r['provider'], r['board']) for r in result['candidates']], flush=True)
    (ROOT / 'data/directory_source_audit.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Audited', len(results), 'existing directory entries', flush=True)
