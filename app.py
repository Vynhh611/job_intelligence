from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Job Intelligence', page_icon='💼', layout='wide')
st.title('Job Intelligence')
st.caption('Public job listings · Curated source boards · Apply through the original employer link')

PATH = Path(__file__).resolve().parent / 'data' / 'jobs.csv'
@st.cache_data(ttl=900)
def load_jobs():
    df = pd.read_csv(PATH, dtype=str).fillna('')
    for col in ['job_id','title','company','location','category','source','posted_at','first_seen','last_seen','url','description']:
        if col not in df:
            df[col] = ''
    df['sort_date'] = pd.to_datetime(df['last_seen'], errors='coerce', utc=True)
    return df

df = load_jobs()
with st.sidebar:
    st.header('Find opportunities')
    q = st.text_input('Keyword / title / company / description')
    places = sorted(x for x in df.location.unique() if x)
    location = st.multiselect('Location', places)
    cats = sorted(x for x in df.category.unique() if x)
    category = st.multiselect('Career area', cats)
    companies = sorted(x for x in df.company.unique() if x)
    company = st.multiselect('Company', companies)

if q.strip():
    mask = df[['title','company','location','description']].apply(lambda col: col.str.contains(q.strip(),case=False,regex=False)).any(axis=1)
    df = df[mask]
if location: df = df[df.location.isin(location)]
if category: df = df[df.category.isin(category)]
if company: df = df[df.company.isin(company)]

n1,n2,n3 = st.columns(3)
n1.metric('Matching jobs',len(df))
n2.metric('Companies',df.company.nunique())
n3.metric('Source boards',df.source.nunique())
st.caption('Last successful snapshot: ' + (df.last_seen.max() if len(df) else 'Not available yet'))
st.divider()
if df.empty:
    st.info('No listings yet or no matches. Add verified company board tokens/sites to sources.json, run collector.py, then refresh.')
else:
    df = df.sort_values('sort_date',ascending=False,na_position='last')
    for _,j in df.iterrows():
        with st.container(border=True):
            st.subheader(j.title)
            st.write(f'**{j.company}** · {j.location or "Location not specified"} · {j.category}')
            st.caption(f'Source: {j.source} · First found: {j.first_seen[:10]} · Last checked: {j.last_seen[:10]}')
            if j.description:
                with st.expander('Job details'):
                    st.write(j.description)
            st.link_button('View original posting / Apply ↗',j.url)
    st.download_button('Download filtered CSV', df.drop(columns=['sort_date']).to_csv(index=False).encode('utf-8-sig'),file_name='job-intelligence.csv',mime='text/csv')
st.caption('Note: first_seen is when this aggregator first detected a listing, not the employer publication date. Verify availability on the original site.')
