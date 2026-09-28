"""One-off bounded website checks for a curated employer research queue.

Reads only robots.txt and homepages; stores factual link evidence, never JDs.
No source permissions or collection configuration are changed.
"""
import csv
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests
from source_discovery import public_url

ROOT = Path(__file__).resolve().parent
AGENT = 'JobIntelligenceVietnam-Directory/1.0'


class Homepage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ''
        self.in_title = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.in_title = self.in_title or tag == 'title'
        if tag == 'a':
            href = dict(attrs).get('href', '')
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def get_page(session, url):
    public_url(url)
    with session.get(url, timeout=(5, 8), allow_redirects=False, stream=True) as response:
        if response.is_redirect:
            # Do not fetch a redirect target until its own robots policy is checked.
            raise ValueError('redirect:' + urljoin(url, response.headers.get('Location', '')))
        response.raise_for_status()
        chunks, total = [], 0
        for part in response.iter_content(16384):
            total += len(part)
            if total > 1500000:
                raise ValueError('page_too_large')
            chunks.append(part)
        return b''.join(chunks).decode('utf-8', errors='replace')


def check(row):
    result = {**row, 'country': 'Vietnam', 'careers_url': None,
              'rights_status': 'unreviewed', 'page_discovery_enabled': False,
              'collector_supported': False, 'platform': 'Not yet identified',
              'integration_status': 'Chưa kết nối · chờ xác minh nguồn',
              'verification_method': 'research_queue',
              'website_check_status': 'unavailable',
              'reference_checked_at': datetime.now(timezone.utc).date().isoformat()}
    url = row['website']
    try:
        with requests.Session() as session:
            session.trust_env = False
            session.headers['User-Agent'] = AGENT
            p = urlsplit(url)
            robots = RobotFileParser()
            robots.parse(get_page(session, f'{p.scheme}://{p.netloc}/robots.txt').splitlines())
            if not robots.can_fetch(AGENT, url):
                result['website_check_status'] = 'robots_denied'
                return result
            delay = robots.crawl_delay(AGENT) or 1
            if delay > 10:
                result['website_check_status'] = 'manual_review'
                return result
            time.sleep(delay)
            parser = Homepage()
            parser.feed(get_page(session, url))
            result.update(website_check_status='checked', website_title=parser.title.strip()[:240], source_url=url)
            links = []
            for href in parser.links:
                candidate = urljoin(url, href)
                parsed = urlsplit(candidate)
                if parsed.scheme != 'https' or parsed.username or parsed.password:
                    continue
                if re.search(r'(?:^|[/.\-_])(careers?|jobs|tuyen-dung|tuyendung|recruitment|recruiting)(?:[/.?\-_]|$)', candidate, re.I):
                    if candidate not in links:
                        links.append(candidate)
            result['career_link_candidates'] = links[:8]
            result['verification_method'] = 'homepage_checked'
    except Exception as error:
        result['check_note'] = str(error)[:300]
    return result


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    rows = list(csv.DictReader((ROOT / 'data/employer_expansion.tsv').open(encoding='utf-8'), delimiter='\t'))
    output = ROOT / 'data/employer_website_checks.json'
    existing = json.loads(output.read_text(encoding='utf-8')) if output.exists() else []
    done = {r['company'] for r in existing}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(check, row): row for row in rows if row['company'] not in done}
        for future in as_completed(futures):
            result = future.result()
            existing.append(result)
            output.write_text(json.dumps(sorted(existing, key=lambda r: r['company']), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(f"{len(existing)}/{len(rows)} {result['company']}: {result['website_check_status']}", flush=True)


if __name__ == '__main__':
    main()
