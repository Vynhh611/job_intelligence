# Job Intelligence Asia — Link-First Update (VN / Singapore)

This is an **additive update** for the existing `Vynhh611/job_intelligence` Pro V3 repository. It shows *individual vacancy links* before building full JD research dossiers.

## Why the current site shows 0 jobs
The earlier `Probe candidate job boards` workflow saved **counts only** to `data/source_probe.json`. It did not store job titles, locations, original URLs or JD. The full `collector.py` requires `authorized:true`; all six sources have `authorized:false`. A successful Probe does not publish job records.

## What this update changes
- Adds `discovery_collector.py`: calls public published job-listing endpoints (Greenhouse, Lever, Ashby) and stores **title, company, location, country, original HTTPS URL**, source and observed timestamps in `data/discovered_jobs.json` — **no full job descriptions**. Ashby `isListed:false` posts are ignored. Scope: Vietnam and Singapore.
- Adds workflow `.github/workflows/discover_jobs.yml`: run on demand, then once daily around 07:47 Vietnam time.
- Replaces `app.py` with a combined UI showing a prominent "Open jobs · Direct source links" section, filters, links and CSV export. Full JD dossiers remain separate and continue to require `authorized:true` in the original collector.
- Makes previous Probe counts visible if individual links have not been collected yet. Clearly labels counts vs individually linked vacancies.
- Keeps current `sources.json`, full JD code, `data/jobs.json`, `data/history.json`, `data/run_status.json`, `data/source_probe.json` and employer watchlist intact.

## Install — 4 simple steps
1. Open GitHub Desktop's local repository `job_intelligence`; back up existing app.py and any important data if desired.
2. Copy the **contents** of this ZIP into the root of `job_intelligence` (overwrite `app.py`, add the new Python file, workflow, and test). The package intentionally contains **no data snapshots and no sources.json**, so no existing job data is overwritten. Include the hidden `.github` folder.
3. GitHub Desktop: **Commit to main** then **Push origin**.
4. GitHub website → **Actions** → **Discover public job links** → **Run workflow** → main. Wait for it to finish, then check `data/discovered_jobs.json`, and refresh the Streamlit site. The website will read the new data from GitHub after redeployment.

## Scope, usage and accuracy
- This collector is a **link-only directory**, not permission to reproduce employer JD text. It does not override existing `authorized:false` on full-JD collection. Public API connectivity is not a grant of downstream content-reuse rights. Before publishing, review each source's site/API terms for the intended title/link index and disable a source where your use is not allowed using `"discovery_enabled": false` on that row in `sources.json`. The new collector respects this optional switch, defaults to enabled for existing configured sources.
- It does not scrape LinkedIn, bypass anti-bot controls, or copy entire job descriptions. Only HTTPS-linked public postings are indexed.
- These counts fluctuate and can differ from the earlier Probe. The discovered-job file is created only after the **new** workflow runs. One successful missing check does not close a job; two do. Failed API runs never close prior jobs.
- The observed sample is not all vacancies in Vietnam or Singapore. Salary, experience, visas and requirements are **unknown** in the link-only index; click original posting to verify.

## Troubleshooting
- Workflow not visible? Check that `.github/workflows/discover_jobs.yml` was copied and pushed into the root of main.
- Workflow reports success but the site still says 0? Confirm `data/discovered_jobs.json` is nonempty and refresh/reboot Streamlit after the GitHub commit deploys.
- `data/discovered_jobs.json` contains 0? Read the log for API errors, missing direct URLs, market mapping, or `discovery_enabled:false` sources. Note that a board can currently have no matching vacancies.
- Permission denied on commit? Repository → Settings → Actions → General → Workflow permissions → Read and write permissions, subject to branch protection rules.

Official API documentation: Greenhouse https://docs.greenhouse.io/job-board.html ; Lever https://github.com/lever/postings-api ; Ashby https://developers.ashbyhq.com/docs/public-job-posting-api .
