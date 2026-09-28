import json
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Job Intelligence Asia", page_icon="💼", layout="wide")
st.title("Job Intelligence Asia")
st.caption("Vietnam · Singapore · Taiwan | Search public company job listings")
file = Path(__file__).parent / "data/jobs.json"
jobs = json.loads(file.read_text(encoding="utf-8")) if file.exists() else []
if not jobs:
    st.info("Website đã hoạt động. Chưa có dữ liệu thật: điền sources.json rồi chạy collector.py hoặc GitHub Actions.")
    st.stop()
df = pd.DataFrame(jobs)
a,b,c = st.columns(3)
a.metric("Collected jobs", len(df))
b.metric("Companies", df.company.nunique())
c.metric("Sources", df.source.nunique())
search = st.text_input("Search title or company", placeholder="Strategy, RGM, Business Development...")
x,y = st.columns(2)
country = x.multiselect("Country", sorted(df.country.dropna().unique().tolist()))
company = y.multiselect("Company", sorted(df.company.dropna().unique().tolist()))
filtered = df.copy()
if search:
    filtered = filtered[filtered.title.str.contains(search, case=False, regex=False, na=False) | filtered.company.str.contains(search, case=False, regex=False, na=False)]
if country:
    filtered = filtered[filtered.country.isin(country)]
if company:
    filtered = filtered[filtered.company.isin(company)]
st.write(f"{len(filtered):,} matching jobs")
for _, j in filtered.head(300).iterrows():
    with st.container(border=True):
        st.subheader(str(j['title']))
        st.write(f"**{j['company']}** · {j['location']} · {j['source']}")
        if str(j.get('url','')).startswith('https://'):
            st.link_button("View original job / Apply", j['url'])
st.download_button("Export filtered CSV", filtered.to_csv(index=False).encode("utf-8-sig"), "job_intelligence.csv", "text/csv")
st.caption("Source coverage depends on configured, authorized public APIs. Country mapping is heuristic and must be reviewed.")
