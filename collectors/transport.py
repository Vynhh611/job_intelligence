import time


def payload(provider, url, fetch, page_size=100):
    """Return complete board or fail; partial pages must never close old jobs."""
    started = time.monotonic()
    if provider == 'smartrecruiters':
        rows, seen, expected_total = [], set(), None
        for offset in range(0, 100000, page_size):
            if time.monotonic() - started > 120:
                raise ValueError('Board scan time limit reached; snapshot not applied')
            page = fetch(f'{url}&limit={page_size}&offset={offset}')
            if not isinstance(page, dict) or not isinstance(page.get('content'), list) or type(page.get('totalFound')) is not int:
                raise ValueError('Invalid SmartRecruiters response')
            total = page['totalFound']
            if total < 0 or (expected_total is not None and total != expected_total):
                raise ValueError('SmartRecruiters total changed during pagination; retry next run')
            expected_total = total
            batch = page['content']
            if len(batch) != min(page_size, max(0, total - offset)):
                raise ValueError('Incomplete SmartRecruiters page')
            for row in batch:
                if not isinstance(row, dict) or not str(row.get('id', '')).isdigit() or not isinstance(row.get('name'), str) or not row['name'].strip():
                    raise ValueError('Invalid SmartRecruiters record')
                if row['id'] in seen:
                    raise ValueError('Repeated SmartRecruiters pagination record')
                location = row.get('location')
                if not isinstance(location, dict) or str(location.get('country', '')).lower() not in ('vn', 'vietnam'):
                    raise ValueError('SmartRecruiters Vietnam filter returned unexpected country')
                seen.add(row['id'])
            rows.extend(batch)
            if len(rows) == total:
                return {'jobs': rows}
            time.sleep(.2)
        raise ValueError('SmartRecruiters pagination safety limit reached')
    if provider == 'lever':
        rows, seen = [], set()
        for offset in range(0, 100000, page_size):
            if time.monotonic() - started > 120:
                raise ValueError('Board scan time limit reached; snapshot not applied')
            page = fetch(f'{url}&skip={offset}&limit={page_size}')
            if not isinstance(page, list):
                raise ValueError('Invalid Lever response')
            for row in page:
                if not isinstance(row, dict) or not row.get('id'):
                    raise ValueError('Invalid Lever record')
                if row['id'] in seen:
                    raise ValueError('Repeated pagination record; refusing incomplete snapshot')
                seen.add(row['id'])
            rows.extend(page)
            if len(page) < page_size:
                return rows
            time.sleep(.2)
        raise ValueError('Pagination safety limit reached')
    result = fetch(url)
    if not isinstance(result, dict) or not isinstance(result.get('jobs'), list):
        raise ValueError('Missing jobs array; refusing to mark jobs closed')
    if result.get('error') or result.get('errors'):
        raise ValueError('ATS API returned an error; snapshot not applied')
    for row in result['jobs']:
        if not isinstance(row, dict) or not (row.get('id') or row.get('jobUrl')):
            raise ValueError('Invalid ATS record')
    return result
