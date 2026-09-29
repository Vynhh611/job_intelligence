"""Conservative city aliases; raw source addresses remain available."""
import re
import unicodedata


def folded(value):
    value = unicodedata.normalize('NFKD', str(value or '').lower().replace('đ', 'd'))
    return re.sub(r'\s+', ' ', ''.join(c for c in value if not unicodedata.combining(c))).strip()


ALIASES = {
    'Hà Nội': r'\b(?:ha\s?noi)\b',
    'TP. Hồ Chí Minh': r'\b(?:ho chi minhh?|ho chi min|hcmc|hcm|saigon|sai gon|thu duc)\b',
    'Đà Nẵng': r'\bda nang\b', 'Hải Phòng': r'\bhai\s?phong\b',
    'Cần Thơ': r'\bcan tho\b', 'Huế': r'\bhue\b',
    'Bình Dương': r'\bbinh duong\b', 'Đồng Nai': r'\bdong nai\b',
    'Bắc Ninh': r'\bbac ninh\b', 'Hưng Yên': r'\bhung yen\b',
    'Quảng Ninh': r'\bquang ninh\b', 'Nha Trang': r'\bnha trang\b',
    'Vũng Tàu': r'\bvung tau\b', 'Quy Nhơn': r'\bquy nhon\b',
    'Phú Quốc': r'\bphu quoc\b', 'Đà Lạt': r'\bda lat\b',
    'Thái Nguyên': r'\bthai nguyen\b', 'Sa Pa': r'\bsa\s?pa\b',
    'Cam Lâm': r'\bcam lam\b', 'Cam Ranh': r'\bcam ranh\b',
    'Đồng bằng sông Cửu Long': r'\bmekong delta\b',
}


def location_tags(value):
    tags = []
    for part in re.split(r'\s+/\s+|;|\s+&\s+', str(value or '')):
        normalized = folded(part)
        matched = [city for city, pattern in ALIASES.items() if re.search(pattern, normalized)]
        if not matched:
            components = [p.strip() for p in part.split(',') if folded(p) not in ('vietnam', 'viet nam', 'vn', '')]
            matched = list(dict.fromkeys(components))[:1] or ['Việt Nam — chưa rõ tỉnh/thành']
        tags.extend(matched)
    return list(dict.fromkeys(tags))
