# Job Intelligence Asia · Research Platform v3

A multi-country job discovery and evidence-led research website for **Vietnam, Singapore and Taiwan**, built with Streamlit, a source-aware Python collector and GitHub Actions. No fabricated listings, employer reviews or LinkedIn scraping.

## Deploy to the EXISTING GitHub repository (no new repository required)

1. Download ZIP and unzip it. Upload **the contents** of `job-intelligence-asia-pro/` to the ROOT of `Vynhh611/job_intelligence`, **replacing same-name files**. The GitHub browser uploader may reject overwrites; to avoid manual editing, use GitHub Desktop: File → Add local repository (clone existing if needed), copy these files into the cloned repository, Commit → Push. Alternatively edit individual existing files in the GitHub browser and create new files.
2. Ensure `.github/workflows/collect.yml`, `data/jobs.json`, `data/history.json`, `data/run_status.json`, `data/company_profiles.json`, `intelligence.py`, `app.py`, `collector.py`, `requirements.txt`, `sources.json` are present.
3. Streamlit Community Cloud: keep repository, branch `main`, main path `app.py`; it should redeploy after push.
4. Set API sources in `sources.json` once you have **verified** a valid board and its terms. Example syntax below has placeholders, not actual verified companies. `authorized` must be set to true deliberately after checking permission. Do **not** put private keys or passwords in repository files.
5. GitHub Actions → `Collect job listings` → `Run workflow` (branch main). A successful run commits `data/*.json`; daily schedule is around 07:17 Vietnam time, not guaranteed exact.
6. Review Source health tab and check live jobs. If no sources are authorized, the site intentionally displays an empty state instead of fabricated data.

### sources.json format

```json
{
  "greenhouse": [{"company":"Verified Example A","board_token":"verified-board-token","enabled":true,"authorized":true}],
  "lever": [{"company":"Verified Example B","site":"verified-site-name","enabled":true,"authorized":true}],
  "ashby": [{"company":"Verified Example C","board_name":"verified-board-name","enabled":true,"authorized":true}]
}
```

Find the public board identifiers from the official career-page URL, verify the JSON endpoint in a browser, read data-reuse terms, and only then enable collection. One configuration can contain hundreds of boards; the actual number is bounded by provider terms, API limits and the GitHub Actions runtime. Only listings with recognized Vietnam/Singapore/Taiwan locations are ingested; remote/unknown are excluded rather than incorrectly classified.

### Company information

`data/company_profiles.json` is an optional map keyed by exact company name. Add sourced, verified profile facts only:

```json
{"Verified Example A": {"overview":"Description verified from official site.","website":"https://example.com","industry":"Technology","headquarters":"Singapore","careers_url":"https://example.com/careers"}}
```

### V3 release: selected research-first improvements

- **Target audience:** cross-border professionals looking at VN, SG and TW. Countries, explicit visa statements and JD-mentioned English/Mandarin/Vietnamese are first-class filters. Unknown is distinct from no sponsorship.
- **Search-first Market Pulse:** new listings detected within 7 days, salary-disclosure share, most-mentioned tracked skill, coverage counts and last run. These are observations from registered sources, not national totals.
- **Evidence-led dossier:** Open research dossier sets a durable `?job=<source-id>` URL. JD, extracted requirement sentences, skill text snippets, published compensation, visa/language evidence, observed reopen count and questions to ask are displayed in two columns. The Streamlit two-column layout is responsive, but not sticky-positioned across devices.
- **Careful review language:** factual JD, system-extracted observations and unverified follow-up questions are distinguished; no company-wide red-flag or reputation score.
- **Duplicate control:** exact canonical application URLs collapse in the displayed view. Same-title/location/company matches are candidates only, never silently deleted. Snapshots keep source-specific records.
- **Small sample safeguard:** market charts and skill-frequency distributions are suppressed for fewer than 20 observed live postings; sample size and coverage caveat shown.
- **Career Lab evidence:** no misleading fit percentage. Show matched and missing detected skills with supporting text snippets. CV bytes read in memory for that session, not saved or sent to a third-party AI endpoint.
- **Data correction:** per-listing GitHub Issue link, with a warning to avoid personal data in public issues. Empty filters show recovery suggestions.
- **Privacy / methodology:** explicit page and operational notes. Public launch still needs completed operator contact, jurisdiction-specific reviewed notices and permitted content reuse; no behavioral tracking is silently installed.
- **No invented source integrations:** the existing Greenhouse, Lever and Ashby collectors and the original workflow remain. LinkedIn/JobStreet/104 are not automatically scraped. The ZIP ships with no pre-authorized live employer board.

### What works now

- Greenhouse / Lever / Ashby collectors with source IDs, timeouts/retries and per-source health.
- Daily scheduler, source permission gate and first/last-seen history. Closes missing postings only after **two successful** board checks; failed requests never close jobs.
- Professional responsive UI: advanced search, market/category/company filters, original posting, JD & requirements, skill tagging, salary visibility, transparency review cues, company research, analytics and CSV export.
- CV/JD term comparison with PDF/DOCX/TXT input processed in the app session, not saved to data or sent to an AI API. This is not a hiring prediction or automated recruitment decision.
- Empty-state safe (works with no data).

### Important limits / roadmap

V3 does not yet implement: full semantic AI, verified immigration/visa advice, automated alerts/accounts, salary trend modeling, cross-platform inferred deduplication, persisted visitor analytics, licensed platform feeds, or large-scale managed PostgreSQL. Source registry must still be configured. The app uses heuristic extraction and only explicit visa wording. The separate URL per job works after a listing has been collected and uses the site's own domain with `?job=`; no external URL is hardcoded.


This is a deployable **v2 foundation**, not a claim of 1,000 connected companies or completed commercial-scale ingestion. LinkedIn, VietnamWorks, JobStreet and 104 are **not** scraped; add only a legitimate licensed partner feed. Source-based signals are questions for further checking, not objective employer misconduct findings or company-wide ratings. Salary, experience, sponsorship and benefits are displayed only if actually provided; unknown is shown otherwise. The `data/*.json` Git-snapshot persistence is suitable for initial volume but not commercial scale. Before 10,000+ jobs or multiple users, migrate to managed PostgreSQL with normalized job/organization/source tables, reliable scheduling, retention policy and monitoring. AI-assisted multilingual summarization can be introduced only after choosing a data processor, consent/privacy controls, audit and explicit citation back to JD text.

### Local run

```bash
python -m pip install -r requirements.txt
streamlit run app.py
python collector.py --dry-run
python collector.py
python -m unittest discover -s tests -v
```

Read API terms before republishing job descriptions. Do not store applicant personal information without an appropriate privacy process. Public GitHub datasets are readable by anyone; CV uploads never enter the GitHub collector.

### Operational upgrade safety

Before replacing files, copy any populated `sources.json`, `data/jobs.json`, `data/history.json`, `data/run_status.json`, `data/company_profiles.json` to a safe location. This ZIP contains intentionally EMPTY placeholders. Merge existing source configuration and snapshots back instead of overwriting accumulated data. The job processing and collector are kept in separate Python modules from the Streamlit UI to support later FastAPI/PostgreSQL migration.
