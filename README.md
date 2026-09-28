# Job Intelligence — starter MVP

A Streamlit job aggregator using the public job boards of **Greenhouse** and **Lever**. No fake job listings are included. Read the data-provider terms and honor reasonable request limits. This is not affiliated with Greenhouse or Lever.

## Getting started

1. Install Python 3.11+, then `pip install -r requirements.txt`.
2. Edit `sources.json` with **verified** company boards. Example format (replace placeholders with real values):

```json
{
  "greenhouse": [{"company": "Company A", "token": "VERIFIED_GREENHOUSE_BOARD_TOKEN"}],
  "lever": [{"company": "Company B", "site": "VERIFIED_LEVER_SITE"}]
}
```

Greenhouse board tokens come from URLs like `https://boards.greenhouse.io/BOARD_TOKEN` (some employers use other Greenhouse domains). Lever sites come from `https://jobs.lever.co/SITE`. Not every company uses these services.

3. Run `python collector.py`; on any configured source error it stops without overwriting the existing CSV.
4. Run `streamlit run app.py`.
5. Upload the project to a GitHub repository. Enable GitHub Actions, run **Refresh public job feeds** manually once, and confirm `data/jobs.csv` is populated.
6. At [share.streamlit.io](https://share.streamlit.io), create an app from that repository, branch `main`, entry point `app.py`. Cloud deployments need repository access and the appropriate permissions.

## Notes
- A daily scheduled workflow refreshes the CSV snapshot; GitHub scheduled runs can be delayed, and can be disabled for inactive public repositories. Check Actions for failures.
- The current snapshot represents currently returned published posts, not a permanent job-posting history. `first_seen` is retained for continuing listings, but disappears for closed posts. Add a database when you need longitudinal analytics.
- Lever's API does not guarantee a publication timestamp in this collector; `posted_at` is intentionally empty for Lever. Greenhouse's `updated_at` is **not necessarily** its original posting date.
- Location strings are employer-supplied and are not geocoded in this MVP. Company board tokens/sites must be entered only after verification. The supplied default configuration is empty.
- Do not insert CVs, API secrets or personal information into a public repository. Use Streamlit Secrets / GitHub Secrets for later private functionality.
