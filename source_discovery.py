"""Bounded discovery of ATS links on supplied official career pages.

No JD collection, login, redirects, browser automation or automatic activation.
Fetching official pages is opt-in per employer. robots.txt is fail-closed.
"""
import ipaddress
import socket
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
import requests
from services import detect_board, register_source

AGENT = 'JobIntelligenceVietnam-Discovery/1.0'


def public_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Chỉ nhận URL HTTPS công khai, không kèm thông tin đăng nhập.')
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError('Từ chối địa chỉ nội bộ hoặc không công khai.')
    return parsed


def fetch_text(url):
    public_url(url)
    # Refuse redirects, including redirects into private networks. No environment proxies.
    with requests.Session() as session:
        session.trust_env = False
        with session.get(url, headers={'User-Agent': AGENT}, timeout=(8, 20), allow_redirects=False, stream=True) as response:
            if response.is_redirect:
                raise ValueError('Trang chuyển hướng; cập nhật URL đích chính thức trước khi kiểm tra.')
            response.raise_for_status()
            chunks, total = [], 0
            for chunk in response.iter_content(16384):
                total += len(chunk)
                if total > 1000000:
                    raise ValueError('Trang vượt giới hạn 1 MB.')
                chunks.append(chunk)
            return b''.join(chunks).decode(response.encoding or 'utf-8', errors='replace')


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag not in ('a', 'iframe'):
            return
        attrs = dict(attrs)
        url = attrs.get('href') if tag == 'a' else attrs.get('src')
        if url:
            self.urls.append(url)


def candidates(company, url, fetch=fetch_text):
    try:
        provider, board = detect_board(url)
        return [{'company': company, 'provider': provider, 'board': board, 'careers_url': url, 'found_on': url, 'status': 'pending_permission'}]
    except ValueError:
        pass
    parsed = urlsplit(url)
    robots_url = f'{parsed.scheme}://{parsed.netloc}/robots.txt'
    robots = RobotFileParser()
    robots.parse(fetch(robots_url).splitlines())
    if not robots.can_fetch(AGENT, url):
        raise ValueError('robots.txt không cho phép kiểm tra trang này.')
    delay = robots.crawl_delay(AGENT) or 1
    if delay > 10:
        raise ValueError('Nguồn yêu cầu thời gian chờ dài; cần kiểm tra thủ công.')
    time.sleep(delay)
    parser = Links()
    parser.feed(fetch(url))
    result, seen = [], set()
    for link in parser.urls[:500]:
        absolute = urljoin(url, link)
        try:
            provider, board = detect_board(absolute)
        except ValueError:
            continue
        if (provider, board) not in seen:
            seen.add((provider, board))
            result.append({'company': company, 'provider': provider, 'board': board, 'careers_url': absolute,
                           'found_on': url, 'status': 'pending_permission'})
    return result


def merge_candidates(previous, fresh):
    indexed = {(r['provider'], r['board']): dict(r) for r in previous}
    for row in fresh:
        indexed.setdefault((row['provider'], row['board']), row)
    return list(indexed.values())


def add_pending(config, candidate):
    # Never downgrade or overwrite an already-approved source during discovery.
    from services import FIELDS
    if any(s.get(FIELDS[candidate['provider']]) == candidate['board'] for s in config.get(candidate['provider'], [])):
        return config
    return register_source(config, candidate['company'], candidate['careers_url'])


def main():
    import argparse
    from datetime import datetime, timezone
    from storage import ROOT, configured_store, load, save
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='Detect ATS from existing registry URLs without network requests')
    args = parser.parse_args()
    store = configured_store()
    registry = load(ROOT / 'data/company_watchlist.json', [], store)
    pending = load(ROOT / 'data/source_candidates.json', [], store)
    checked = 0
    for employer in registry:
        if employer.get('country') != 'Vietnam':
            continue
        url = employer.get('careers_url', '')
        try:
            if args.offline:
                try:
                    detect_board(url)
                except ValueError:
                    continue
                found = candidates(employer['company'], url)
            else:
                if not employer.get('page_discovery_enabled') or checked >= 10:
                    continue
                checked += 1
                found = candidates(employer['company'], url)
            for item in found:
                item['discovered_at'] = datetime.now(timezone.utc).isoformat()
            pending = merge_candidates(pending, found)
        except (ValueError, OSError, requests.RequestException):
            print('Unable to inspect registered page; source remains disabled:', employer.get('company', ''))
    save(ROOT / 'data/source_candidates.json', pending, store)
    print(f'{len(pending)} pending candidates. No sources activated; no job descriptions collected.')


if __name__ == '__main__':
    main()
