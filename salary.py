"""Conservative normalization of employer-disclosed salary, never estimates."""
import re


def disclosed_salary(job):
    text = str(job.get('salary_text') or '')
    currency = str(job.get('salary_currency') or '').upper()
    period = str(job.get('salary_period') or '').lower()
    low, high = job.get('salary_min'), job.get('salary_max')
    if currency in ('VND', 'USD') and period in ('month', 'year', 'hour'):
        try:
            low, high = float(low), float(high)
            if 0 < low <= high:
                return {'min': low, 'max': high, 'currency': currency, 'period': period, 'evidence': text, 'kind': 'employer_disclosed'}
        except (ValueError, TypeError):
            pass
    period = 'month' if re.search(r'/\s*tháng|mỗi tháng|per month|/\s*month|monthly', text, re.I) else 'year' if re.search(r'/\s*năm|per year|annual|/\s*year', text, re.I) else ''
    currency = 'VND' if re.search(r'\bVND\b|triệu|đồng', text, re.I) else 'USD' if re.search(r'\bUSD\b', text, re.I) else ''
    if currency == 'VND' and re.search(r'\bUSD\b', text, re.I):
        return None
    match = re.search(r'(\d[\d.,]*)\s*(?:triệu)?\s*[-–]\s*(\d[\d.,]*)', text, re.I)
    if not period or not currency or not match:
        return None
    try:
        if 'triệu' in text.lower():
            low, high = (float(v.replace(',', '.')) * 1000000 for v in match.groups())
        else:
            numbers = []
            for value in match.groups():
                if not re.fullmatch(r'\d+|\d{1,3}(?:[,.]\d{3})+', value):
                    return None
                numbers.append(float(value.replace(',', '').replace('.', '')))
            low, high = numbers
        if not 0 < low <= high:
            return None
        return {'min': low, 'max': high, 'currency': currency, 'period': period, 'evidence': text, 'kind': 'employer_disclosed'}
    except ValueError:
        return None


def matches_salary(job, minimum, maximum, currency='VND', period='month'):
    salary = disclosed_salary(job)
    return bool(salary and salary['currency'] == currency and salary['period'] == period and salary['max'] >= minimum and salary['min'] <= maximum)
