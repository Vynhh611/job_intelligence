"""Job Intelligence Asia — source-attributed recruitment intelligence portal."""
import io
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, quote

import pandas as pd
import plotly.express as px
import streamlit as st
from intelligence import enrich, signal_report, cv_matches, plain, evidence_snippet, new_in_last_days, visible_jobs

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
st.set_page_config(page_title='Job Intelligence Asia | Career Research',page_icon='🌏',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],div[data-testid="stAppViewContainer"]{font-family:'DM Sans',sans-serif}
h1,h2,h3,h4{font-family:'Manrope',sans-serif!important;letter-spacing:-.035em!important}
.stApp{background:#F6F8FC;color:#12213A}
.block-container{padding-top:1.4rem;max-width:1440px;padding-bottom:4rem}
[data-testid="stSidebar"]{background:#10213C}
[data-testid="stSidebar"] *{color:#E8EEFB!important}
[data-testid="stSidebar"] div[data-baseweb="select"] *{color:#17243b!important}
[data-testid="stSidebar"] input{color:#17243b!important}
[data-testid="stMetric"]{background:#fff;border:1px solid #E3EAF3;border-radius:16px;padding:16px 20px;box-shadow:0 6px 20px rgba(23,47,82,.035)}
[data-testid="stMetricLabel"]{font-size:.85rem}
[data-testid="stMetricValue"]{color:#132E54;font-family:'Manrope',sans-serif;font-weight:800}
[data-testid="stVerticalBlockBorderWrapper"]{border-color:#E1E9F4!important;border-radius:17px!important;background:#fff}
div.stButton>button[kind="primary"],div.stLinkButton>a{background:#1671E8;color:white;border:none;border-radius:10px;font-weight:700}
div.stButton>button{border-radius:10px}
[data-testid="stTabs"] button{font-weight:700}
.hero{padding:32px 34px;background:linear-gradient(112deg,#102443 0%,#174A77 60%,#1267A2 100%);border-radius:22px;color:#fff;margin-bottom:22px;box-shadow:0 13px 35px rgba(15,46,80,.15)}
.hero .eyebrow{font-size:.76rem;letter-spacing:.19em;font-weight:800;color:#8ed7f2}
.hero h1{font-size:2.35rem;color:white!important;margin:6px 0 9px}
.hero p{color:#D5E7F7;max-width:760px;font-size:1rem}
.smallnote{font-size:.78rem;color:#75839B}
.jobtitle{font-size:1.1rem;font-weight:800;color:#183355;margin-bottom:5px}
.jobmeta{color:#62728b;font-size:.87rem}
.pill{display:inline-block;border:1px solid #D8E7F5;background:#F3F8FF;color:#28517C;padding:4px 10px;border-radius:8px;margin:7px 5px 6px 0;font-size:.77rem;font-weight:600}
.section-eyebrow{font-size:.73rem;color:#1671e8;font-weight:800;letter-spacing:.13em}
.market-strip{border:1px solid #dbe5f2;background:#fff;border-radius:12px;padding:12px 18px;margin-bottom:12px}
@media(max-width:700px){.hero{padding:20px}.hero h1{font-size:1.65rem}}

</style>''',unsafe_allow_html=True)

def read(name,default):
    file=DATA/name
    try: return json.loads(file.read_text(encoding='utf-8')) if file.exists() else default
    except (OSError,ValueError): return default

def safe_url(s):
    try:
        p=urlparse(str(s or ''))
        return p.scheme=='https' and bool(p.netloc) and not p.username and not p.password
    except ValueError: return False

def txt(v,default='Not disclosed'):
    v=plain(v)
    return v if v else default

def date_str(s):
    try: return datetime.fromisoformat(str(s).replace('Z','+00:00')).strftime('%d %b %Y')
    except (TypeError,ValueError): return 'Not available'

raw=read('jobs.json',[])
items=[enrich(j) for j in raw if isinstance(j,dict) and j.get('id') and j.get('title')]
profiles=read('company_profiles.json',{})
status=read('run_status.json',{})
history=read('history.json',[])
watchlist=read('company_watchlist.json',[])
probe=read('source_probe.json',[])
sources_config=json.loads((ROOT/'sources.json').read_text(encoding='utf-8')) if (ROOT/'sources.json').exists() else {}
active=visible_jobs([j for j in items if j.get('status','active')=='active'])

def render_detail(job, prefix='detail'):
    st.caption('FROM THE POSTING · Original JD is shown as ingested; extracted fields are rule-based interpretations.')
    left,right=st.columns([1.85,1],gap='large')
    with left:
        st.markdown('#### Role overview & job description')
        st.write(job.get('description') or 'Full job description not available from this source. Please review the original listing.')
        st.markdown('#### Requirements detected in the original posting')
        lines=job.get('requirements_extracted',[])
        if lines:
            for line in lines: st.markdown('• '+line)
        else:st.caption('No requirement sentences confidently extracted; check the full JD.')
        st.markdown('#### Skills · SYSTEM ANALYSIS (keyword evidence)')
        if job.get('skills'):
            for idx,skill in enumerate(job['skills']):
                with st.expander(f'{skill} · Show JD evidence',expanded=False):
                    st.write(evidence_snippet(job.get('description',''),skill) or 'No literal evidence found; classification may have relied on a synonym.')
        else:st.caption('No tracked skills identified. This does not mean no skills are needed.')
    with right:
        with st.container(border=True):
            st.markdown('#### Decision brief')
            st.write('**Published compensation:** '+txt(job.get('salary_text')))
            st.write('**Work arrangement:** '+txt(job.get('workplace_type')))
            st.write('**Visa sponsorship:** '+job.get('visa_sponsorship','Unknown'))
            if job.get('visa_evidence',{}).get('evidence'):st.caption('FROM JD: '+job['visa_evidence']['evidence'])
            st.write('**Languages mentioned:** '+(', '.join(job.get('language_requirements',[])) or 'Unknown'))
            for item in job.get('language_evidence',[]):st.caption('FROM JD: '+item['language']+' — '+item['evidence'])
            st.write('**First detected:** '+date_str(job.get('first_seen')))
            st.write('**Last verified:** '+date_str(job.get('last_seen')))
            st.write('**Reopenings observed:** '+str(job.get('reopen_count',0)))
            st.caption('History reflects this collector, not necessarily the employer’s original publication date.')
            st.markdown('#### Questions before applying')
            for signal in job.get('review_signals',[]):
                st.warning(f"{signal['label']} — {signal['reason']}")
                st.caption('SYSTEM ANALYSIS / VERIFY · '+signal['evidence'])
            if not job.get('review_signals'):st.caption('No tracked cues detected, not an employer endorsement.')
            if safe_url(job.get('url')):st.link_button('Apply at original source ↗',job['url'],use_container_width=True)
            st.caption('Source: '+txt(job.get('source'))+' · Record ID: '+str(job.get('id')))
            st.caption('Share this specific job using the browser URL after opening its detail view.')
            issue_url='https://github.com/Vynhh611/job_intelligence/issues/new?title='+quote('Data correction: '+str(job.get('id',''))) + '&body='+quote('Job ID: '+str(job.get('id',''))+'\nOriginal URL: '+str(job.get('url',''))+'\nWhat should be corrected?\n')
            st.link_button('Report inaccurate listing ↗',issue_url,use_container_width=True)
    st.caption('Evidence labels: FROM JD = employer-provided text; SYSTEM ANALYSIS = rule-based extraction; VERIFY = question for the hiring team. No reputational finding about the employer is implied.')

with st.sidebar:
    st.markdown('### 🌏 JOB INTELLIGENCE')
    st.caption('ASIA · CAREER RESEARCH DESK')
    st.divider()
    st.markdown('**Market coverage**')
    markets=st.multiselect('Country',['Vietnam','Singapore','Taiwan'],default=['Vietnam','Singapore'],label_visibility='collapsed')
    st.markdown('**Live collection**')
    st.write(f'**{len(active):,}** active records')
    st.caption(f'Last collector run: {date_str(status.get("checked_at"))}')
    st.caption(f'Sources checked successfully: {status.get("successful_sources",0)}')
    if status.get('errors'): st.warning(f'{len(status["errors"])} source error(s); see Source health.')
    st.divider()
    st.caption('Listings are source-attributed; completeness, visa and salary details are not guaranteed. No company reputation allegations are generated.')

st.markdown('''<div class="hero"><div class="eyebrow">CAREER DATA · VERIFIED SOURCE TRAIL</div><h1>Discover opportunities. Understand the market.</h1><p>Explore jobs across Vietnam and Singapore, inspect actual job requirements, compare skills and review transparency signals without unsupported company ratings.</p></div>''',unsafe_allow_html=True)

if not active:
    st.info('Website hoạt động. Chưa có tin tuyển dụng đang mở: thêm nguồn đã kiểm tra quyền sử dụng vào sources.json (authorized=true), sau đó chạy Actions → Collect job listings. Có thể xem giao diện và phương pháp bên dưới.')

countries=[j for j in active if j.get('country') in markets]
companies=len({j.get('company','') for j in countries})
new_today=sum(j.get('first_seen','')[:10]==datetime.now(timezone.utc).date().isoformat() for j in countries)
new_week=new_in_last_days(countries)
a,b,c,d=st.columns(4)
a.metric('Active opportunities',f'{len(countries):,}')
b.metric('Hiring companies',f'{companies:,}')
c.metric('Newly discovered (UTC)',f'{new_today:,}')
d.metric('Markets',str(len({j.get('country') for j in countries})))
st.caption('Coverage: '+f'{len(countries):,} observed active jobs from {companies:,} companies · Last collection: '+date_str(status.get('checked_at'))+' · VN '+str(sum(j.get('country')=='Vietnam' for j in countries))+' / SG '+str(sum(j.get('country')=='Singapore' for j in countries))+' / TW '+str(sum(j.get('country')=='Taiwan' for j in countries))+'. Registered sources only; not a national census.')
st.markdown('**MARKET PULSE · OBSERVED SAMPLE**')
p1,p2,p3=st.columns(3)
p1.metric('Newly detected · last 7 days',new_week)
p2.metric('Listings publishing a salary',f'{sum(bool(j.get("salary_text")) for j in countries) / len(countries):.0%}' if countries else '—')
skill_counter=Counter(s for j in countries for s in j.get('skills',[]))
p3.metric('Most mentioned tracked skill',skill_counter.most_common(1)[0][0] if skill_counter else '—')
st.caption('Pulse describes observed listings with exact duplicate application URLs collapsed. Similar company/title/location is only a review candidate, not silently merged. “Most mentioned” is not a growth metric; unreported salary ≠ unpaid role.')
selected_job=next((j for j in items if j.get('id')==st.query_params.get('job')),None)
if selected_job:
    with st.container(border=True):
        st.markdown('### Job dossier · '+selected_job.get('title',''))
        st.caption(txt(selected_job.get('company'))+' · '+txt(selected_job.get('location')))
        if st.button('← Back to all jobs',key='clear-job'):
            del st.query_params['job']
            st.rerun()
        render_detail(selected_job,'focus')


tabs=st.tabs(['🔎 Explore jobs','🏢 Company research','📊 Market intelligence','🧭 Career lab','🛡️ Source health','📄 Privacy & methodology'])
with tabs[0]:
    st.markdown('### Find an opportunity')
    q=st.text_input('Search across job titles, employers, descriptions and skills',placeholder='e.g. Revenue Growth Management, Strategy, SQL, Pricing')
    cats=sorted({j.get('category','Other') for j in countries})
    firms=sorted({j.get('company','') for j in countries})
    x,y,z=st.columns([1.2,1.2,1])
    cat=x.multiselect('Career category',cats)
    firm=y.multiselect('Company',firms)
    mode=z.selectbox('Status',['Active only','Include closed'])
    u,v,w=st.columns(3)
    visa=u.selectbox('Visa information',['Any','Sponsored (explicit)','Not sponsored (explicit)','Unknown'])
    language=v.selectbox('Language evidence',['Any','English','Mandarin','Vietnamese','Not stated'])
    salary_filter=w.checkbox('Salary disclosed only',value=False)

    pool=visible_jobs([j for j in items if j.get('country') in markets]) if mode=='Include closed' else countries
    matches=[]
    for j in pool:
        content=' '.join([j.get('title',''),j.get('company',''),j.get('description',''),' '.join(j.get('skills',[]))]).lower()
        if q and q.lower() not in content: continue
        if cat and j.get('category') not in cat: continue
        if firm and j.get('company') not in firm: continue
        if visa!='Any' and j.get('visa_sponsorship','Unknown') != {'Sponsored (explicit)':'Sponsored','Not sponsored (explicit)':'Not sponsored','Unknown':'Unknown'}[visa]:continue
        if language!='Any' and (language not in j.get('language_requirements',[]) if language!='Not stated' else bool(j.get('language_requirements'))):continue
        if salary_filter and not j.get('salary_text'):continue
        matches.append(j)
    matches.sort(key=lambda j:j.get('last_seen',''),reverse=True)
    st.markdown(f'**{len(matches):,} matching opportunities**')
    if matches:
        download_df=pd.DataFrame([{k:j.get(k,'') for k in ('title','company','country','location','category','source','url','first_seen','last_seen','status')} for j in matches])
        st.download_button('↓ Export results (CSV)',download_df.to_csv(index=False).encode('utf-8-sig'),'job-intelligence-results.csv','text/csv')
    limit=st.select_slider('Show first',options=[10,25,50,100],value=25)
    for j in matches[:limit]:
        with st.container(border=True):
            st.markdown(f'<div class="jobtitle">{__import__("html").escape(txt(j.get("title")))}</div><div class="jobmeta">{__import__("html").escape(txt(j.get("company")))} · {__import__("html").escape(txt(j.get("location")))} · {__import__("html").escape(j.get("country","Unknown"))}</div>',unsafe_allow_html=True)
            st.markdown(' '.join(f'<span class="pill">{__import__("html").escape(t)}</span>' for t in [j.get('category','Other'),j.get('source','Source unknown'),j.get('employment_type','Not specified')]),unsafe_allow_html=True)
            a,b,c=st.columns(3)
            a.caption(f'Salary: {txt(j.get("salary_text"))}')
            b.caption(f'First seen: {date_str(j.get("first_seen"))}')
            c.caption(f'Last verified: {date_str(j.get("last_seen"))}')
            a,b=st.columns([1,1])
            if a.button('Open research dossier →',key='dossier-'+str(j['id'])):
                st.query_params['job']=str(j['id'])
                st.rerun()
            b.caption('Visa: '+j.get('visa_sponsorship','Unknown')+' · Language: '+(', '.join(j.get('language_requirements',[])) or 'Unknown'))
            with st.expander('Quick view · JD and evidence'):
                render_detail(j,'quick')
            if safe_url(j.get('url')): st.link_button('View official posting / Apply ↗',j['url'])
            else: st.caption('Original application URL unavailable or not verified.')
    if not matches: st.info('No matching results. Try selecting all countries, clearing visa/language filters or entering a broader skill. Unknown visa status does not mean sponsorship is unavailable.')
with tabs[1]:
    st.markdown('### Company research')
    st.caption('Evidence-led profile: no invented ratings, unsupported misconduct claims or inferred visa support.')
    known=sorted(set(j.get('company','') for j in countries)|set(profiles)|{c['company'] for c in watchlist if c.get('country') in markets})
    if known:
        selected=st.selectbox('Choose company',known)
        related=[j for j in countries if j.get('company')==selected]
        watched=[c for c in watchlist if c.get('company')==selected and c.get('country') in markets]
        p=profiles.get(selected,{})
        x,y,z=st.columns(3)
        x.metric('Active listings',len(related))
        y.metric('Markets',len({j.get('country') for j in related}))
        z.metric('Available posting sources',len({j.get('source_key') for j in related}))
        st.markdown('#### Employer profile')
        st.write(p.get('overview') or 'No verified company overview has been added yet. Job listings alone do not establish employer size, benefits, management quality or financial position.')
        for field,label in [('industry','Industry'),('headquarters','Headquarters'),('company_size','Company size'),('careers_url','Careers page')]:
            if p.get(field): st.write(f'**{label}:** {p[field]}')
        if safe_url(p.get('website')):st.link_button('Official employer site',p['website'])
        if watched:
            st.markdown('#### Official careers directory')
            for c in watched:
                st.write(f"**{c['country']} · {c['platform']}** — {c['integration_status']}")
                if safe_url(c.get('careers_url')): st.link_button(f"Open {c['country']} careers page ↗",c['careers_url'])
            st.caption('A company in this registry is not counted as an ingested job, a successfully connected API or permission to republish JD text.')
        st.markdown('#### Active openings')
        st.dataframe(pd.DataFrame([{'Role':j['title'],'Market':j.get('country'),'Location':j.get('location'),'Category':j.get('category'),'Original URL':j.get('url')} for j in related]),use_container_width=True,hide_index=True)
        st.markdown('#### What to verify before applying')
        st.write('Confirm: legal employing entity, direct reporting line, total compensation and variable-pay targets, probation terms, actual working location, visa sponsorship, overtime expectations, and whether the same job remains actively open.')
    else:st.info('Employer profiles will populate after collecting eligible jobs or adding verified company_profiles.json entries.')
with tabs[2]:
    st.markdown('### Market intelligence')
    if countries:
        df=pd.DataFrame([{'Country':j.get('country'),'Category':j.get('category'),'Company':j.get('company'),'First seen':j.get('first_seen','')[:10],'Skills':j.get('skills',[])} for j in countries])
        st.caption(f'Analysis sample: n = {len(countries)} observed active postings. Charts are suppressed when n < 20 to avoid over-reading thin coverage.')
        if len(countries)<20:
            st.info('Fewer than 20 observed postings. Showing descriptive records only; distribution charts withheld.')
            st.dataframe(df[['Country','Category','Company','First seen']],hide_index=True,use_container_width=True)
        else:
            left,right=st.columns(2)
            with left:
                fig=px.bar(df.groupby('Country').size().reset_index(name='Openings'),x='Country',y='Openings',title='Observed active openings by market',color='Country')
                fig.update_layout(showlegend=False,margin=dict(l=0,r=0,t=45,b=0),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig,use_container_width=True)
            with right:
                fig=px.bar(df.groupby('Category').size().reset_index(name='Openings').sort_values('Openings'),x='Openings',y='Category',orientation='h',title='Career category distribution')
                fig.update_layout(margin=dict(l=0,r=0,t=45,b=0),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig,use_container_width=True)
        skills=Counter(skill for job in countries for skill in job.get('skills',[]))
        st.markdown('#### Most frequently detected skills')
        if skills and len(countries)>=20:st.dataframe(pd.DataFrame(skills.most_common(20),columns=['Skill','Postings mentioning skill']),hide_index=True,use_container_width=True)
        elif skills:st.caption('Skill frequency breakdown suppressed: sample below 20.')
        else:st.info('No skills detected from the currently available descriptions.')
        daily=df.groupby('First seen').size().reset_index(name='First detected')
        if not daily.empty and len(countries)>=20:
            st.plotly_chart(px.line(daily,x='First seen',y='First detected',markers=True,title='New listings detected by the collector (not employer posting dates)'),use_container_width=True)
        st.caption('Sampling bias: only registered sources and VN/SG/TW location matches. Absence of a listing here is not evidence that an employer is not hiring.')
    else:st.info('Charts will appear when the collector retrieves actual jobs.')
with tabs[3]:
    st.markdown('### Private CV-to-JD skill comparison')
    st.caption('PRIVACY: CV content is handled in memory during this app session. This code does not write CVs to disk, logs, GitHub or an external AI provider. Avoid ID numbers and personal secrets; Streamlit hosting infrastructure still processes the upload. Close/refresh the session to clear the working text.')
    upload=st.file_uploader('Upload a CV (.pdf, .docx, .txt); maximum 5 MB',type=['pdf','docx','txt'])
    cv_text=''
    if upload:
        if upload.size>5*1024*1024:st.error('File exceeds 5 MB.')
        else:
            try:
                if upload.name.lower().endswith('.pdf'):
                    from pypdf import PdfReader
                    cv_text='\n'.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(upload.getvalue())).pages[:12])
                elif upload.name.lower().endswith('.docx'):
                    from docx import Document
                    cv_text='\n'.join(p.text for p in Document(io.BytesIO(upload.getvalue())).paragraphs)
                else:cv_text=upload.getvalue().decode('utf-8')
                st.success(f'Read {len(cv_text):,} characters. This implementation does not persist your CV.')
            except Exception as e:st.error(f'Could not read this file: {type(e).__name__}. Try a text-based PDF or DOCX.')
    if countries and cv_text:
        option=st.selectbox('Compare CV against a current opportunity',range(len(countries)),format_func=lambda i:f'{countries[i]["title"]} — {countries[i]["company"]}')
        result=cv_matches(cv_text,countries[option])
        st.markdown('#### Explainable comparison · no fit score or hiring prediction')
        st.markdown('**Detected in both CV and JD**')
        if result['matched']:
            for skill in result['matched']:
                st.success(skill)
                st.caption('CV evidence: '+evidence_snippet(cv_text,skill)+' · JD evidence: '+evidence_snippet(countries[option]['description'],skill))
        else:st.write('No tracked overlapping keywords found.')
        st.markdown('**Mentioned in JD but not detected in CV text**')
        for skill in result['not_detected']:
            st.warning(skill)
            st.caption('JD evidence: '+evidence_snippet(countries[option]['description'],skill))
        st.caption('Partial matches require manual review: keywords alone cannot distinguish adjacent experience, seniority or actual competence.')
        st.info(result['note'])
    elif not countries:st.info('Select a market with current jobs or add authorized sources to enable comparisons.')
with tabs[4]:
    st.markdown('### Data provenance & source reliability')
    st.write('Greenhouse, Lever and Ashby public posting endpoints are supported. Every entry needs a verified board identifier and an explicit authorized flag in sources.json. No LinkedIn scraping or anti-bot bypass is implemented.')
    st.write(f'**Last run:** {date_str(status.get("checked_at"))} · **Successful sources:** {status.get("successful_sources",0)}')
    st.caption('Registered ATS coverage is skewed toward organizations using Greenhouse, Lever or Ashby; local boards and employers using other systems are not represented unless individually integrated.')
    if status.get('sources'):st.dataframe(pd.DataFrame(status['sources']),use_container_width=True,hide_index=True)
    st.markdown('#### Priority employer coverage')
    watched=[c for c in watchlist if c.get('country') in markets]
    st.caption(f'{len(watched)} targeted company-market pairs (official careers directory, NOT ingested jobs). API candidates remain permission-gated.')
    if watched:
        st.dataframe(pd.DataFrame([{'Market':c['country'],'Company':c['company'],'Industry':c.get('industry'),'Careers':c.get('careers_url'),'Platform':c.get('platform'),'Integration':c.get('integration_status')} for c in watched]),hide_index=True,use_container_width=True,column_config={'Careers':st.column_config.LinkColumn('Official careers URL')})
    if probe:
        st.markdown('#### Candidate board connectivity probe (not publication permission)')
        st.dataframe(pd.DataFrame(probe),hide_index=True,use_container_width=True)
    source_rows=[]
    for provider in ('greenhouse','lever','ashby'):
        for source in sources_config.get(provider,[]):
            source_rows.append({'Company':source.get('company',''),'ATS':provider,'Enabled':source.get('enabled',True),'Authorized':source.get('authorized',False),'Coverage note':source.get('coverage_note','Registered ATS careers page; not representative of all employers')})
    if source_rows:st.dataframe(pd.DataFrame(source_rows),hide_index=True,use_container_width=True)

    if status.get('errors'):
        for err in status['errors']:st.error(err)
    st.markdown('#### How the posting review works')
    st.write('Checks flag missing compensation details, vague salary wording, unclear role detail, mentions of overtime/pressure, and unrecognized location. These are job-posting-level review questions, **not** verified company-wide problems, claims of unlawful behavior or reputation scores.')
    st.write('Closed jobs are marked only after two successive *successful* checks of the same board where an earlier posting is missing. Failed API requests never close jobs. Historical records retain first detection date and source trail.')
    st.write('Country mapping and skill/category tagging are rule-based, explainable approximations. Human review and primary-source verification are required before making decisions.')
    st.markdown('#### Operational links')
    st.link_button('Greenhouse job board documentation','https://developers.greenhouse.io/job-board.html')
    st.link_button('Lever public postings documentation','https://github.com/lever/postings-api')
    st.link_button('Ashby posting API documentation','https://developers.ashbyhq.com/docs/public-job-posting-api')
    st.caption('Sources are public API documentation links, not blanket permission to republish individual postings. Consult applicable terms and data usage rights.')

st.divider()
st.markdown('<span class="smallnote">JOB INTELLIGENCE ASIA · An evidence-oriented career research tool · Data quality and employer claims require source verification · Designed for desktop and mobile</span>',unsafe_allow_html=True)

with tabs[5]:
    st.markdown('### Privacy, provenance & usage terms')
    st.write('This service is an independent research interface, not affiliated with the employers or recruiting platforms shown. Every job links to its original source. Availability, completeness, salaries and sponsorship should be confirmed directly with the employer.')
    st.write('We do not store CV uploads in our job snapshots or GitHub repository, nor transmit them to third-party AI APIs in this version. Uploaded documents are processed transiently by Streamlit infrastructure during the current app session. Avoid sensitive identifiers. No user accounts or behavioral analytics are enabled in this MVP.')
    st.write('Data sources: explicitly configured, authorized ATS boards only. Operators must check API terms, permitted reuse, retention and privacy requirements in each market before publication. Historical job records may contain employer-authored information and are retained in repository snapshots until removed by the operator. Do not include candidate personal data in source files.')
    st.write('For corrections, use the “Report inaccurate listing” link on a dossier. Do not enter personal information into public GitHub issues. Operator contact and formal privacy notices should be completed before public production launch; this page is operational guidance, not a jurisdiction-specific legal compliance certification.')
    st.write('Method: locations and requirements inferred by transparent keyword rules. Salary disclosure rate denominator is observed active listings; the market distribution does not represent all vacancies. Visa and language labels mean an explicit phrase was detected or Unknown, never a guarantee. Duplicate candidate keys are review hints, not indiscriminate record deletion.')
