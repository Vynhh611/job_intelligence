"""Describe observed availability without promising a vacancy remains open."""
from datetime import datetime, timezone


def freshness(job, now=None):
    if job.get('status') == 'closed':
        return 'closed'
    if job.get('missed_successful_checks', 0):
        return 'missing'
    try:
        seen = datetime.fromisoformat(job.get('last_seen', '').replace('Z', '+00:00'))
        if seen.tzinfo is None:
            return 'stale'
        age = ((now or datetime.now(timezone.utc)) - seen).total_seconds()
        return 'recent' if 0 <= age <= 36 * 3600 else 'stale'
    except (ValueError, TypeError):
        return 'stale'


LABELS = {
    'recent': 'Còn được công khai tại nguồn khi kiểm tra gần nhất',
    'missing': 'Không thấy ở lần kiểm tra gần nhất · đang chờ xác nhận',
    'stale': 'Chưa được kiểm tra lại trong 36 giờ · cần xác nhận tại nguồn',
    'closed': 'Không còn thấy tại nguồn sau hai lượt kiểm tra cách nhau ít nhất 6 giờ',
}
