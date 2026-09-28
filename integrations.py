"""Disabled-by-default contracts for licensed feeds and grounded JD explainers.

These interfaces intentionally do not invent vendor endpoints or credentials.
Wire a licensed vendor SDK only after reviewing the data use agreement.
CV content is never accepted by the explainer integration.
"""
from typing import Protocol
from services import safe_url, vietnam_jobs


class LicensedFeed(Protocol):
    def fetch_jobs(self) -> list[dict]:
        """Return source IDs, employer, title, location, country, URL and allowed JD."""
        ...


class JobExplainer(Protocol):
    def explain(self, description: str, language: str) -> list[dict]:
        """Return [{summary: Vietnamese text, evidence: exact JD substring}]."""
        ...


def authorized_feed(adapter: LicensedFeed, permission_url: str, authorized=False):
    if not authorized or not safe_url(permission_url):
        raise PermissionError('Licensed feed permission must be recorded before collection')
    records = adapter.fetch_jobs()
    if not isinstance(records, list):
        raise ValueError('Feed must return a complete list or raise an error')
    return vietnam_jobs(records)


def explain_job(adapter: JobExplainer, job: dict, authorized=False):
    if not authorized:
        raise PermissionError('JD processing by the external provider is not enabled')
    description = str(job.get('description') or '')
    if not description:
        return []
    result = adapter.explain(description=description, language='vi')
    if not isinstance(result, list):
        raise ValueError('Invalid explanation response')
    for item in result:
        if not isinstance(item, dict) or not item.get('summary') or not item.get('evidence') or item['evidence'] not in description:
            raise ValueError('Explanation lacks exact supporting JD evidence')
    return result
