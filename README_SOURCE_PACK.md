# Job Intelligence Asia — VN-first + 10 Singapore employer source pack (28 Sep 2026)

Only 5 files/folders changed: `app.py`, `sources.json`, `probe_sources.py`, `.github/workflows/probe_sources.yml`, `data/company_watchlist.json` and `data/source_probe.json`.

## What's included
- **20 Vietnam + exactly 10 Singapore employer-market entries** in `data/company_watchlist.json` with source career URLs. These links appear in Company research and Source health even before API integration; NOT counted as jobs.
- **6 ATS candidate boards** with public-facing job board URL identifiers: Airwallex / Notion (Ashby), MongoDB (Greenhouse), Ninja Van / Lalamove / WalkMe (Lever). Their `authorized` flag defaults to `false`: public GET access is NOT a blanket license to republish postings.
- On-demand **Probe candidate job boards** GitHub Action, which tries the documented public endpoints and records only counts and connectivity to `data/source_probe.json`. Probe does not publish JD or make a permission decision.
- All other big-employer career websites (e.g., Vietcombank, FPT Software, Grab, DBS, Sea, Amazon) remain official external directory links, not fictitious Greenhouse tokens.

## Install in the existing repository
1. Back up your existing `sources.json` and nonempty `data/*.json` before replacing anything.
2. Copy the contents of this pack into the ROOT of `Vynhh611/job_intelligence`; replace `app.py`, replace `sources.json` only if yours is still empty; merge previous sources otherwise. Do not wipe `data/jobs.json`, `data/history.json`, or `data/run_status.json`.
3. GitHub Desktop: Commit to main -> Push origin. Streamlit will redeploy.
4. GitHub Actions -> **Probe candidate job boards** -> Run workflow. Look at `data/source_probe.json` / Source health to check which endpoints answer and how many job locations the API reports. API probe may be affected by network/geolocation and job board changes.
5. Review each source's API/website terms and the specific intended storage/display use, obtain permission when needed. Only then edit `authorized:false` to `true` for eligible rows, and run the original **Collect job listings** Action. Documentation and public boards are not automatically authorization to copy and republish full JD.

The collector presently covers only Greenhouse/Lever/Ashby; employer-specific portals require separate connector integration or licensed feeds. The observed counts are sourced from boards registered by you, not a census of national vacancies. This pack does not claim live testing of GET endpoints in the build environment; the on-GitHub probe is the connectivity check.
