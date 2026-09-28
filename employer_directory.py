"""Employer directory facts are separate from job records and source rights."""
import unicodedata

from services import safe_url


def search_key(text):
    text = str(text or '').casefold().replace('đ', 'd')
    return ''.join(c for c in unicodedata.normalize('NFD', text) if not unicodedata.combining(c))


def source_stage(row):
    if safe_url(row.get('careers_url')):
        return 'Có liên kết tuyển dụng'
    if row.get('website_check_status') == 'checked':
        return 'Đã đọc website · cần tìm trang tuyển dụng'
    return 'Cần xác minh website và trang tuyển dụng'


def filter_employers(rows, query='', industries=(), stage='Tất cả'):
    terms = search_key(query).split()
    return sorted((r for r in rows
                   if r.get('country') == 'Vietnam'
                   and (not industries or r.get('industry') in industries)
                   and (stage == 'Tất cả' or source_stage(r) == stage)
                   and all(term in search_key(r.get('company', '') + ' ' + r.get('industry', '')) for term in terms)),
                  key=lambda r: (not bool(r.get('careers_url')), search_key(r['company'])))


def merge_directory(existing, fresh):
    """Add research entries without replacing existing identities or permissions."""
    result = list(existing)
    known = {(search_key(r['company']), r['country']) for r in existing}
    for row in fresh:
        key = (search_key(row['company']), row['country'])
        if key not in known:
            result.append(row)
            known.add(key)
    return result
