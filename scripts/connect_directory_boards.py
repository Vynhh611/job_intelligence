"""Reviewed official boards for employers already in the Vietnam directory."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARDS = [
    ('Grab', 'Grab', 'https://www.grab.careers/en/jobs/744000152321499/assistant-manager-self-serve-business-strategy-planning/'),
    ('SmartOSC', 'SmartOSC', 'https://careers.smartrecruiters.com/SmartOSC'),
    ('Sika Vietnam', 'SikaAG', 'https://jobs.smartrecruiters.com/sikaag/744000150837597'),
]


def main():
    config_path = ROOT / 'sources.json'
    registry_path = ROOT / 'data/company_watchlist.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    registry = json.loads(registry_path.read_text(encoding='utf-8'))
    for company, board, evidence in BOARDS:
        employer = next(r for r in registry if r['company'] == company and r['country'] == 'Vietnam')
        if not any(r.get('company_identifier') == board for r in config.get('smartrecruiters', [])):
            config.setdefault('smartrecruiters', []).append({
                'company': company, 'company_identifier': board, 'careers_url': employer['careers_url'],
                'enabled': True, 'discovery_enabled': True, 'public_description_enabled': True,
                'authorized': False, 'ai_authorized': False, 'permission_mode': 'links',
                'access_basis': 'reviewed_public_api_metadata', 'evidence_url': evidence,
                'permission_url': 'https://developers.smartrecruiters.com/docs/posting-api',
                'description_access_basis': 'Public posting API; user requested JD and local CV comparison. Not a contractual license.',
                'reviewed_at': '2026-09-29',
            })
        employer.update({'collector_supported': True, 'board_identifier': board,
                         'integration_status': 'Public API connected: metadata and job descriptions',
                         'verification_method': 'public_api_checked', 'verification_url': evidence})
    for path, value in [(config_path, config), (registry_path, registry)]:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
