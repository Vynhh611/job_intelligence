import time


def payload(provider, url, fetch, page_size=100):
    """Return complete board or fail; partial pages must never close old jobs."""
    if provider == 'lever':
        rows, seen = [], set()
        for offset in range(0, 100000, page_size):
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
    if provider == 'ashby' and result.get('apiVersion') and result.get('error'):
        raise ValueError('Ashby API error')
    for row in result['jobs']:
        if not isinstance(row, dict) or not (row.get('id') or row.get('jobUrl')):
            raise ValueError('Invalid ATS record')
    return result
