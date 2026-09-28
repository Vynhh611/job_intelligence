"""Apply this reviewed expansion without changing existing source permissions."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from employer_directory import merge_directory

EXCLUDE = {'GCS Vietnam', 'Trung Nguyên E-Coffee'}
# Candidates inspected on 2026-09-28. Do not promote new scan results automatically.
APPROVED = set('ABB Vietnam|ABBank|Agribank|Amanotes|BIDV|Base.vn|Be Group|Bibica|CJ Foods Vietnam|CMC Corporation|Chubb Life Vietnam|Coca-Cola Vietnam|Coteccons|DKSH Vietnam|DRC|Eurowindow|Ford Vietnam|Gemadept|Giao Hàng Nhanh|HD SAISON|HDBank|Haravan|Highlands Coffee|Home Credit Vietnam|Honda Vietnam|Hoàn Mỹ Medical Group|Hòa Bình Construction|ILA Vietnam|Imexpharm|Indovina Bank|KIDO Group|KIS Vietnam Securities|KienlongBank|KiotViet|Lotte Mart Vietnam|Lộc Trời Group|MBS|MISA|MM Mega Market Vietnam|MSB|Manulife Vietnam|Medlatec|Minh Phú Seafood|Mitsubishi Motors Vietnam|Mondelez Kinh Do|Mường Thanh Group|NashTech|Newtecons|Nutifood|One Mount|Orient Software|Orion Vietnam|PAN Group|Panasonic Vietnam|REE Corporation|Rikkeisoft|Rạng Đông|SJC|SOTRANS|SSI Securities|Saigon Co.op|Saigon Technology|Saigonbank|Saigontourist Group|Sapo|SeABank|Sika Vietnam|SmartOSC|Standard Chartered Vietnam|Toyota Vietnam|Traphaco|Trung Nguyên Legend|Tâm Anh Hospital|VCCorp|VIMC|VISSAN|VNPay|Vedan Vietnam|VietinBank|Vietravel|Vinamilk|Woori Bank Vietnam|Yamaha Motor Vietnam|Zuellig Pharma'.split('|'))
CHOICE = {'HD SAISON': 1, 'Highlands Coffee': 1, 'Honda Vietnam': 1, 'MBS': 2, 'MISA': 1, 'Manulife Vietnam': 3, 'PAN Group': 2, 'REE Corporation': 3, 'SOTRANS': 3, 'Sika Vietnam': 4, 'Vinamilk': 2}


def main():
    report = json.loads((ROOT / 'data/employer_website_checks.json').read_text(encoding='utf-8'))
    search = json.loads((ROOT / 'data/directory_search_references.json').read_text(encoding='utf-8'))
    fresh = []
    for entry in report:
        if entry['company'] in EXCLUDE:
            continue
        row = {k: v for k, v in entry.items() if k not in ('check_note', 'website_title', 'career_link_candidates')}
        if row['company'] in APPROVED:
            row['careers_url'] = entry['career_link_candidates'][CHOICE.get(row['company'], 0)]
            row['verification_method'] = 'official_homepage_link'
        elif row['company'] in search:
            row['careers_url'] = search[row['company']]
            row['source_url'] = row['careers_url']
            row['verification_method'] = 'official_search_reference'
        row['notes'] = 'Mục tham khảo, chưa kết nối dữ liệu việc làm. Trang toàn cầu cần lọc Việt Nam. Không xác nhận mọi vị trí còn tuyển hoặc mọi đơn vị có hồ sơ LinkedIn.'
        fresh.append(row)
    path = ROOT / 'data/company_watchlist.json'
    existing = json.loads(path.read_text(encoding='utf-8'))
    merged = merge_directory(existing, fresh)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    vietnam = [r for r in merged if r['country'] == 'Vietnam']
    print('Vietnam entries:', len(vietnam))
    print('Career links:', sum(bool(r.get('careers_url')) for r in vietnam))


if __name__ == '__main__':
    main()
