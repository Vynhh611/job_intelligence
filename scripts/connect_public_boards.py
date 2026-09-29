"""Apply a reviewed, metadata-only initial set of public employer boards."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BOARDS = {
    'lever': [('Ninja Van', 'ninjavan'), ('Lalamove', 'lalamove'), ('cargo-partner', 'cargo-partner'), ('Ataccama', 'ataccama')],
    'ashby': [('Airwallex', 'airwallex')],
    'smartrecruiters': [('Bosch Vietnam', 'BoschGroup'), ('Accor Vietnam', 'AccorHotel'), ('KMS Technology', 'KMSTechnology1'), ('SGS Vietnam', 'SGS'), ('Eurofins Vietnam', 'Eurofins'), ('Renesas Electronics Vietnam', 'RenesasElectronics')],
}
DOCS = {
    'lever': 'https://github.com/lever/postings-api',
    'ashby': 'https://developers.ashbyhq.com/docs/public-job-posting-api',
    'smartrecruiters': 'https://developers.smartrecruiters.com/docs/endpoints',
}
FIELDS = {'lever': 'site', 'ashby': 'board_name', 'smartrecruiters': 'company_identifier'}
PREFIX = {'lever': 'https://jobs.lever.co/', 'ashby': 'https://jobs.ashbyhq.com/', 'smartrecruiters': 'https://careers.smartrecruiters.com/'}


def main():
    path = ROOT / 'sources.json'
    config = json.loads(path.read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc).isoformat()
    for provider, boards in BOARDS.items():
        entries = config.setdefault(provider, [])
        for company, board in boards:
            old = next((s for s in entries if s.get(FIELDS[provider]) == board), None)
            if old and old.get('authorized'):
                continue  # Never downgrade a separately licensed full-JD source.
            if old and old.get('access_basis') == 'reviewed_public_api_metadata':
                continue  # Preserve later operator edits, including a disabled source.
            item = {**(old or {}), 'company': company, FIELDS[provider]: board,
                    'careers_url': PREFIX[provider] + board,
                    'enabled': True, 'authorized': False, 'ai_authorized': False,
                    'discovery_enabled': True, 'permission_mode': 'links',
                    'permission_url': DOCS[provider], 'permission_checked_at': now,
                    'access_basis': 'reviewed_public_api_metadata',
                    'coverage_note': 'Vietnam only. Reviewed documented public postings endpoint for a factual title/location/outgoing-link index. API documentation is not an employer contract or blanket republication license. No full JD, applicant data, login or AI processing.'}
            if old is None:
                entries.append(item)
            else:
                entries[entries.index(old)] = item
    config['_instructions'] = 'authorized=true is reserved for separately confirmed full-JD reuse. discovery_enabled=true enables only a reviewed public metadata/outgoing-link index; see access_basis and permission_url. Public API documentation is not an employer contract. Never enable internal postings or applicant endpoints.'
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
