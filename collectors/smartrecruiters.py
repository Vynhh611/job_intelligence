"""Official Posting API adapter. Requires registry permission like other ATS."""
from urllib.parse import quote
from intelligence import plain


def collect(source, fetch):
    board = quote(source['company_identifier'], safe='')
    base = f'https://api.smartrecruiters.com/v1/companies/{board}/postings'
    seen = set()
    for offset in range(0, 100000, 100):
        result = fetch(f'{base}?limit=100&offset={offset}')
        if not isinstance(result, dict) or not isinstance(result.get('content'), list) or not isinstance(result.get('totalFound'), int):
            raise ValueError('Invalid SmartRecruiters page')
        rows = result['content']
        if not rows and offset < result['totalFound']:
            raise ValueError('Incomplete SmartRecruiters page')
        for row in rows:
            identity = str(row['id'])
            if identity in seen:
                raise ValueError('Repeated SmartRecruiters page')
            seen.add(identity)
            location = row.get('location') or {}
            # Still visit all pages; only Vietnam details need storage/processing.
            if str(location.get('country', '')).lower() not in ('vn', 'vietnam'):
                continue
            detail = fetch(f'{base}/{quote(identity, safe="")}')
            sections = (detail.get('jobAd') or {}).get('sections') or {}
            description = '\n'.join(plain(v.get('text', '')) for v in sections.values() if isinstance(v, dict))
            yield {'id': f'smartrecruiters:{board}:{identity}', 'title': row.get('name', ''),
                   'company': source['company'], 'location': (location.get('city') or '') + ', Vietnam',
                   'url': detail.get('applyUrl') or '', 'description': description,
                   'source': 'SmartRecruiters', 'source_key': f'smartrecruiters:{board}',
                   'employment_type': (detail.get('typeOfEmployment') or {}).get('label', ''),
                   'experience': (detail.get('experienceLevel') or {}).get('label', ''),
                   'source_updated_at': detail.get('releasedDate', '')}
        if offset + len(rows) >= result['totalFound']:
            return
    raise ValueError('SmartRecruiters pagination limit reached')
