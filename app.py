"""Vietnam career research interface; business logic lives in services.py."""
import hmac
import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st
from storage import load, save, configured_store, StorageError
from intelligence import new_in_last_days, evidence_snippet, skill_tags
from services import (vietnam_jobs, display, safe_url, dossier, match_cv, parse_cv,
                      register_source, CAREERS, FIELDS)
from ai_explainer import configured as ai_configured, generate, content_hash, current_explanation
from source_discovery import candidates, merge_candidates, add_pending
from salary import disclosed_salary, matches_salary
from employer_directory import filter_employers, source_stage

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
STORE = configured_store()
st.set_page_config(page_title='Job Intelligence Vietnam', page_icon='🌿', layout='wide')
st.markdown('''<style>
.stApp{background:#f5f9f3;color:#183d2b}
.block-container{max-width:1240px;padding-top:2rem;padding-bottom:4rem}
h1,h2,h3{letter-spacing:-.035em} h1{line-height:1.15!important}
[data-testid="stSidebar"]{background:#e8f2e4;border-right:1px solid #d4e3cf}
[data-testid="stMetric"]{background:white;border:1px solid #dce8d7;border-radius:16px;padding:16px}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:16px!important;border-color:#dce8d7!important}
.hero{background:linear-gradient(120deg,#dceecf,#edf5e4 65%,#d7eadb);border:1px solid #cee1c5;border-radius:24px;padding:38px;margin:16px 0 24px}
.hero h1{font-size:2.7rem;max-width:830px;color:#194b31;margin:12px 0}
.hero p{max-width:780px;color:#43624d;font-size:1.05rem}
.eyebrow{font-size:.75rem;font-weight:700;letter-spacing:.16em;color:#376b48}
.pill{display:inline-block;background:#eaf3e5;color:#285a39;border-radius:24px;padding:5px 12px;margin:4px 5px 6px 0;font-size:.8rem}
.job-title{font-size:1.2rem;font-weight:750;color:#224b32;margin:6px 0}.muted{color:#567060;font-size:.88rem}
.salary{color:#24623c;font-weight:700;margin:10px 0}
a{color:#286b47}button{border-radius:10px!important}
@media(max-width:700px){.hero{padding:22px}.hero h1{font-size:1.9rem}.block-container{padding:1rem}}
</style>''', unsafe_allow_html=True)


def read(name, default):
    try:
        path = DATA / name
        return load(path, default, STORE)
    except StorageError as error:
        st.error(str(error))
        st.stop()
    except (OSError, ValueError):
        st.warning(f'Không đọc được dữ liệu {name}. Quản trị viên cần kiểm tra tệp; dữ liệu chưa bị thay đổi.')
        return default


def save_json(path, value):
    try:
        save(path, value, STORE)
    except StorageError as error:
        st.error(str(error))
        st.stop()


def date(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return 'Chưa xác định'


def save_button(job, suffix):
    saved = st.session_state.setdefault('saved_jobs', set())
    if st.button('♥ Đã lưu' if job['id'] in saved else '♡ Lưu việc', key=f'save-{suffix}-{job["id"]}'):
        if job['id'] in saved:
            saved.remove(job['id'])
        else:
            saved.add(job['id'])
        st.rerun()


def match_panel(job):
    if st.session_state.get('cv_text'):
        rows = match_cv(st.session_state.cv_text, job)
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.info('JD chưa đủ dữ liệu kỹ năng để đối chiếu. Hãy đọc bản gốc.')
    else:
        st.caption('Tải CV tại mục CV của tôi để xem dẫn chứng phù hợp.')


raw = read('jobs.json', []) + read('discovered_jobs.json', [])
jobs = vietnam_jobs(raw)
archive = vietnam_jobs(raw, active_only=False)
profiles = read('company_profiles.json', {})
watchlist = [r for r in read('company_watchlist.json', []) if r.get('country') == 'Vietnam']
for job in jobs:
    job['industry'] = profiles.get(job.get('company'), {}).get('industry') or next((r.get('industry') for r in watchlist if r.get('company') == job.get('company')), None)
status = read('run_status.json', {})
discovery_status = read('discovery_status.json', {})
explanations = read('job_explanations.json', {})
try:
    config = load(ROOT / 'sources.json', {}, STORE)
except (StorageError, ValueError, OSError):
    st.error('Không đọc được cấu hình nguồn. Kiểm tra lưu trữ trước khi tiếp tục.')
    st.stop()
updated = max(str(status.get('checked_at', '')), str(discovery_status.get('checked_at', '')))

with st.sidebar:
    st.markdown('### 🌿 JOB INTELLIGENCE\n**VIETNAM**')
    st.caption('Discover jobs. Understand companies. Plan your career.')
    st.divider()
    page = st.radio('Khám phá', ['Tìm việc', 'Việc đã lưu', 'Doanh nghiệp', 'CV của tôi', 'Lộ trình nghề nghiệp', 'Thị trường', 'Phương pháp & riêng tư', 'Quản trị nguồn'], key='navigation', on_change=st.query_params.clear)
    st.divider()
    st.caption('Dành riêng cho cơ hội tại Việt Nam')
    st.caption(f'Cập nhật: {date(updated)} · {len(jobs):,} tin đang quan sát')
    st.caption(f'Danh bạ riêng: {len(watchlist):,} doanh nghiệp / đơn vị')
    st.caption('Dữ liệu từ các nguồn đã đăng ký; không đại diện toàn bộ thị trường Việt Nam.')


def card(job, suffix='list'):
    with st.container(border=True):
        left, right = st.columns([4, 1])
        with left:
            st.markdown(f'<div class="muted">{escape(job.get("company", ""))} · {escape(job.get("location", ""))}</div><div class="job-title">{escape(job["title"])}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="salary">{escape(display(job.get("salary_text")))}</div>', unsafe_allow_html=True)
            st.markdown(''.join(f'<span class="pill">{escape(display(v))}</span>' for v in [job.get('experience'), job.get('employment_type'), job.get('workplace_type')]), unsafe_allow_html=True)
        with right:
            save_button(job, suffix)
        details = dossier(job)
        for line in details['duties'][:2]:
            st.write('• ' + line)
        if job.get('skills'):
            st.caption('Kỹ năng: ' + ' · '.join(job['skills'][:6]))
        if st.session_state.get('cv_text'):
            results = match_cv(st.session_state.cv_text, job)
            st.caption(f'CV: {sum(r["Phân loại"] == "Đáp ứng" for r in results)}/{len(results)} kỹ năng có dẫn chứng áp dụng; cần xác minh mức thành thạo.' if results else 'CV: JD chưa đủ dữ liệu để đối chiếu.')
        st.caption(f'{job.get("source", "Nguồn gốc")} · Phát hiện {date(job.get("first_seen"))} · Kiểm tra {date(job.get("last_seen"))}' + (' · Chỉ có liên kết gốc' if not job.get('description') else ''))
        a, b = st.columns(2)
        if a.button('Tìm hiểu công việc →', key=f'open-{suffix}-{job["id"]}', use_container_width=True):
            st.query_params['job'] = job['id']
            st.rerun()
        if safe_url(job.get('url')):
            b.link_button('Ứng tuyển tại nguồn ↗', job['url'], use_container_width=True)


def detail(job):
    if st.button('← Quay lại danh sách'):
        st.query_params.clear()
        st.rerun()
    st.caption(job.get('company', '') + ' / ' + job.get('location', ''))
    st.title(job['title'])
    if job.get('status') == 'closed':
        st.warning('Tin này không còn được quan sát tại nguồn. Kiểm tra lại với nhà tuyển dụng.')
    left, right = st.columns([1.8, 1], gap='large')
    d = dossier(job)
    with left:
        st.subheader('Tổng quan công việc')
        explanation = current_explanation(job, explanations)
        if explanation:
            st.caption('Diễn giải tiếng Việt bằng AI · Có trích dẫn để đối chiếu, vẫn có thể sai nghĩa. Kiểm tra JD gốc trước khi quyết định.')
            for item in explanation.get('items', []):
                st.write(item['summary'])
                with st.expander('Câu gốc hỗ trợ nội dung này'):
                    st.text(item['evidence'])
        st.caption('Phần trích xuất bên dưới giữ nguyên ngôn ngữ JD. Yêu cầu không được tự bổ sung.')
        st.write(d['overview'] or 'Nguồn chỉ cung cấp liên kết. Mở tin gốc để đọc đầy đủ trách nhiệm và yêu cầu.')
        st.subheader('Công việc hằng ngày')
        for line in d['duties']:
            st.write('• ' + line)
        if not d['duties']:
            st.info('Chưa có đủ dẫn chứng để tách nhiệm vụ, người phối hợp và kết quả cần bàn giao.')
        st.subheader('Yêu cầu tuyển dụng')
        for label, lines in d['requirements'].items():
            if lines:
                st.markdown('**' + label + '**')
                for line in lines:
                    st.write('• ' + line)
        st.caption('“Ưu tiên” chỉ được gắn khi JD có từ ngữ tương ứng. Các nhóm còn lại không tự động có nghĩa là bắt buộc.')
        st.subheader('Kỹ năng & dẫn chứng')
        for skill in job.get('skills', []):
            with st.expander(skill):
                from services import sentences
                from intelligence import SKILLS
                import re
                st.write(next((s for s in sentences(job.get('description')) if re.search(SKILLS[skill], s, re.I)), 'Chưa tìm thấy dẫn chứng.'))
        st.subheader('Đối chiếu với CV của bạn')
        match_panel(job)
        st.subheader('Khả năng phát triển nghề nghiệp')
        st.write('Có thể phát triển chuyên môn sâu, quản lý nhóm hoặc chuyển sang vai trò liên quan. Xem Lộ trình nghề nghiệp để so sánh kỹ năng từ các tin đang có.')
        st.caption('Gợi ý minh họa; không phải cam kết thăng tiến hoặc mức lương.')
        with st.expander('Xem toàn bộ JD đã thu thập'):
            st.text(job.get('description') or 'Chưa lưu JD. Vui lòng xem nguồn gốc.')
    with right:
        with st.container(border=True):
            st.subheader('Thông tin để quyết định')
            st.markdown('**Lương nhà tuyển dụng công bố**')
            st.write(display(job.get('salary_text')))
            salary = disclosed_salary(job)
            if salary:
                st.caption(f"Khoảng đã chuẩn hóa từ nguồn: {salary['min']:,.0f}–{salary['max']:,.0f} {salary['currency']} / {salary['period']}. Chưa tự suy luận gross/net hoặc thưởng.")
            st.caption('Chưa đủ dữ liệu để ước tính mức lương đáng tin cậy.')
            for label, field in [('Địa điểm', 'location'), ('Hình thức làm việc', 'workplace_type'), ('Kinh nghiệm', 'experience'), ('Loại hợp đồng', 'employment_type')]:
                st.write(f'**{label}:** {display(job.get(field))}')
            st.caption(f'Phát hiện: {date(job.get("first_seen"))}\n\nKiểm tra: {date(job.get("last_seen"))}')
            st.link_button('Mở tin gốc / Ứng tuyển ↗', job['url'], use_container_width=True)
            save_button(job, 'detail')
            st.caption('Chia sẻ: sao chép địa chỉ hiện tại trên trình duyệt. Mã liên kết cố định:')
            st.code('?job=' + quote(job['id'], safe=''), language=None)
            st.caption('Nguồn: ' + job.get('source', 'Chưa xác định'))
        with st.container(border=True):
            st.subheader(job.get('company', 'Doanh nghiệp'))
            profile = profiles.get(job.get('company'), {})
            st.write(profile.get('overview') or 'Chưa có hồ sơ doanh nghiệp được xác minh.')
            if safe_url(profile.get('website')):
                st.link_button('Website doanh nghiệp ↗', profile['website'])
            st.markdown('**Những điều nên tìm hiểu thêm**')
            for signal in job.get('review_signals', []):
                st.write('• ' + signal['label'])
                st.caption(signal['reason'] + ' — Dẫn chứng: ' + signal['evidence'])
            st.caption('Thông tin còn thiếu không phải bằng chứng về uy tín hay hành vi của doanh nghiệp.')


job_id = st.query_params.get('job')
if job_id:
    selected = next((j for j in archive if j['id'] == job_id), None)
    if selected:
        detail(selected)
    else:
        st.warning('Không tìm thấy tin tuyển dụng Việt Nam với mã này trong dữ liệu hiện có.')
        if st.button('Về trang tìm việc'):
            st.query_params.clear()
            st.rerun()
    st.stop()

if page in ('Tìm việc', 'Việc đã lưu'):
    st.markdown('''<div class="hero"><div class="eyebrow">CƠ HỘI MỚI · GÓC NHÌN RÕ RÀNG HƠN</div><h1>Tìm công việc phù hợp.<br>Hiểu rõ trước khi ứng tuyển.</h1><p>Khám phá cơ hội tuyển dụng tại Việt Nam, tìm hiểu doanh nghiệp và đối chiếu yêu cầu công việc với CV của bạn.</p></div>''', unsafe_allow_html=True)
    if page == 'Tìm việc':
        a, b, c = st.columns(3)
        a.metric('Tin việc làm trong hệ thống', len(jobs))
        b.metric('Doanh nghiệp / đơn vị trong danh bạ', len(watchlist))
        c.metric('Có liên kết trang tuyển dụng', sum(safe_url(r.get('careers_url')) for r in watchlist))
        st.caption('Số tin việc làm khác số doanh nghiệp. Danh bạ gồm nguồn tham khảo và mục đang xác minh; truy cập trang doanh nghiệp để xem cơ hội ngoài dữ liệu hiện có.')
        st.button(f'Khám phá danh bạ {len(watchlist)} doanh nghiệp →', on_click=lambda: st.session_state.update(navigation='Doanh nghiệp'), type='primary')
    query = st.text_input('Bạn đang tìm công việc gì?', placeholder='Chức danh, doanh nghiệp, lĩnh vực hoặc kỹ năng…')
    if page == 'Tìm việc' and query.strip():
        employer_matches = filter_employers(watchlist, query)
        if employer_matches:
            with st.expander(f'{len(employer_matches)} doanh nghiệp phù hợp trong danh bạ'):
                for row in employer_matches[:8]:
                    url = row.get('careers_url') or row.get('website')
                    st.write(row['company'] + ' · ' + source_stage(row))
                    if safe_url(url):
                        st.link_button('Xem nguồn tham khảo: ' + row['company'] + ' ↗', url)
    filtered = jobs if page == 'Tìm việc' else [j for j in jobs if j['id'] in st.session_state.get('saved_jobs', set())]
    with st.expander('Bộ lọc tìm kiếm', expanded=bool(jobs)):
        cols = st.columns(3)
        selections = {}
        for index, (label, field) in enumerate([('Địa điểm', 'location'), ('Doanh nghiệp', 'company'), ('Chức năng công việc', 'category'), ('Hình thức làm việc', 'workplace_type'), ('Kinh nghiệm', 'experience'), ('Loại hợp đồng', 'employment_type'), ('Ngành doanh nghiệp', 'industry')]):
            selections[field] = cols[index % 3].multiselect(label, sorted({display(j.get(field)) for j in jobs}))
        cols = st.columns(3)
        recency = cols[0].selectbox('Thời điểm phát hiện', ['Tất cả', '7 ngày qua', '30 ngày qua'])
        disclosed = cols[1].checkbox('Chỉ tin công bố lương')
        languages = cols[2].multiselect('Ngôn ngữ được nhắc đến', sorted({s for j in jobs for s in j.get('language_requirements', [])}))
        salary_filter = st.checkbox('Lọc khoảng lương công bố có đơn vị rõ ràng')
        if salary_filter:
            s1, s2, s3 = st.columns(3)
            salary_currency = s1.selectbox('Đơn vị lương', ['VND', 'USD'])
            salary_range = s2.number_input('Từ / tháng', min_value=0, value=0, step=1000)
            salary_ceiling = s3.number_input('Đến / tháng', min_value=0, value=100000000 if salary_currency == 'VND' else 10000, step=1000)
            st.caption('Chỉ lọc lương nhà tuyển dụng công bố có tiền tệ và kỳ trả lương rõ ràng; không quy đổi ngoại tệ hoặc suy đoán lương tháng.')
    filtered = [j for j in filtered if query.casefold() in ' '.join(str(j.get(k, '')) for k in ('title', 'company', 'description', 'category', 'skills')).casefold() and all(not values or display(j.get(field)) in values for field, values in selections.items()) and (not disclosed or j.get('salary_text')) and (not languages or set(languages).issubset(j.get('language_requirements', []))) and (recency == 'Tất cả' or new_in_last_days([j], 7 if recency == '7 ngày qua' else 30))]
    filtered.sort(key=lambda j: j.get('first_seen', ''), reverse=True)
    if salary_filter:
        filtered = [j for j in filtered if matches_salary(j, salary_range, salary_ceiling, salary_currency)]
        if salary_range > salary_ceiling:
            st.warning('Mức lương tối thiểu cần nhỏ hơn hoặc bằng mức tối đa.')
    st.subheader(f'{len(filtered):,} tin tuyển dụng' + (' đã lưu' if page == 'Việc đã lưu' else ' trong dữ liệu hiện có'))
    st.caption('Tin mới phát hiện trước · Việc đã lưu chỉ được giữ trong phiên hiện tại.')
    if not filtered:
        st.info('Chưa có công việc phù hợp trong dữ liệu hiện có. Thử bỏ bộ lọc hoặc khám phá các trang tuyển dụng chính thức tại mục Doanh nghiệp.')
        st.subheader('Khám phá trang tuyển dụng doanh nghiệp')
        st.caption('Liên kết trong danh bạ hiện có; chưa xác nhận số vị trí đang tuyển hoặc quyền thu thập.')
        for employer in watchlist[:6]:
            if safe_url(employer.get('careers_url')):
                st.link_button(employer['company'] + ' ↗', employer['careers_url'])
    else:
        current = st.number_input('Trang', min_value=1, max_value=max(1, (len(filtered) + 11) // 12), step=1)
        for job in filtered[(current - 1) * 12:current * 12]:
            card(job)
        export = pd.DataFrame([{k: j.get(k, '') for k in ('title', 'company', 'location', 'salary_text', 'url', 'first_seen')} for j in filtered])
        # Avoid spreadsheet formula execution in exported employer text.
        export = export.map(lambda x: "'" + x if isinstance(x, str) and x.startswith(('=', '+', '-', '@')) else x)
        st.download_button('Tải danh sách CSV', export.to_csv(index=False).encode('utf-8-sig'), 'viec-lam-vietnam.csv', 'text/csv')

elif page == 'Doanh nghiệp':
    st.title('Hiểu doanh nghiệp trước khi ứng tuyển')
    st.caption('Danh bạ doanh nghiệp, đơn vị và thương hiệu hoạt động tại Việt Nam. Có trong danh bạ không đồng nghĩa đang tuyển hoặc đã cho phép thu thập dữ liệu; các đơn vị cùng tập đoàn có thể được liệt kê riêng.')
    a, b, c = st.columns(3)
    a.metric('Doanh nghiệp / đơn vị trong danh bạ', len(watchlist))
    b.metric('Có liên kết tuyển dụng', sum(safe_url(r.get('careers_url')) for r in watchlist))
    c.metric('Cần tìm trang tuyển dụng', sum(not safe_url(r.get('careers_url')) for r in watchlist))
    search = st.text_input('Tìm trong danh bạ', placeholder='Tên doanh nghiệp hoặc ngành…')
    industries = st.multiselect('Lọc ngành trong danh bạ', sorted({r.get('industry', 'Chưa phân loại') for r in watchlist}))
    stage = st.selectbox('Tình trạng nguồn tham khảo', ['Tất cả', 'Có liên kết tuyển dụng', 'Đã đọc website · cần tìm trang tuyển dụng', 'Cần xác minh website và trang tuyển dụng'])
    directory = filter_employers(watchlist, search, industries, stage)
    st.caption(f'{len(directory)} doanh nghiệp phù hợp · Liên kết tuyển dụng được ưu tiên trước. Website chưa xác minh được ghi rõ trong bảng.')
    if directory:
        st.dataframe(pd.DataFrame([{'Doanh nghiệp': r['company'], 'Ngành': r.get('industry'), 'Tình trạng': source_stage(r), 'Trang tuyển dụng': r.get('careers_url'), 'Website tham khảo': r.get('website')} for r in directory]), hide_index=True, column_config={'Trang tuyển dụng': st.column_config.LinkColumn('Trang tuyển dụng', display_text='Xem tuyển dụng ↗'), 'Website tham khảo': st.column_config.LinkColumn('Website tham khảo', display_text='Xem website ↗')}, width='stretch', height=460)
    else:
        st.info('Chưa có doanh nghiệp phù hợp trong danh bạ. Thử đổi từ khóa hoặc bỏ bộ lọc.')
    st.divider()
    names = sorted(set(j.get('company', '') for j in archive) | set(profiles) | {r['company'] for r in watchlist})
    if names:
        name = st.selectbox('Tìm doanh nghiệp', names)
        profile = profiles.get(name, {})
        registry = next((r for r in watchlist if r['company'] == name), {})
        st.subheader(name)
        if registry:
            st.caption(source_stage(registry))
        if safe_url(registry.get('website')):
            st.link_button('Website tham khảo của doanh nghiệp ↗', registry['website'])
        st.write(profile.get('overview') or 'Chưa có mô tả doanh nghiệp đã xác minh.')
        for label, field in [('Lĩnh vực', 'industry'), ('Trụ sở', 'headquarters'), ('Quy mô', 'size'), ('Công ty mẹ', 'parent_company')]:
            st.write(f'**{label}:** {display(profile.get(field) or registry.get(field))}')
        for label, url in [('Website chính thức', profile.get('website')), ('Trang tuyển dụng', profile.get('careers_url') or registry.get('careers_url')), ('Nguồn xác minh hồ sơ', profile.get('source_url'))]:
            if safe_url(url):
                st.link_button(label + ' ↗', url)
        st.caption('Ngày xác minh hồ sơ: ' + date(profile.get('verified_at')))
        if registry.get('source_url') and safe_url(registry['source_url']):
            st.link_button('Nguồn tham chiếu ↗', registry['source_url'])
            method = {'official_page_review': 'Đã xem trang chính thức', 'official_search_reference': 'Đã đối chiếu kết quả tìm kiếm từ trang chính thức; cần kiểm tra trực tiếp', 'homepage_checked': 'Đã đọc website; chưa xác nhận các vị trí đang tuyển', 'official_homepage_link': 'Liên kết tuyển dụng được dẫn từ website doanh nghiệp; chưa xác nhận các vị trí đang tuyển'}.get(registry.get('verification_method'), 'Cần xác minh nguồn')
            st.caption(method + ' · ' + date(registry.get('reference_checked_at')))
        if safe_url(registry.get('linkedin_url')) and safe_url(registry.get('linkedin_evidence_url')):
            st.link_button('LinkedIn được doanh nghiệp dẫn chiếu ↗', registry['linkedin_url'])
            st.link_button('Bằng chứng liên kết LinkedIn ↗', registry['linkedin_evidence_url'])
        else:
            st.caption('Chưa đối chiếu liên kết LinkedIn cho doanh nghiệp này.')
        if registry.get('rights_status') == 'unreviewed':
            st.caption('Nguồn mới: chưa kết nối tự động, đang chờ xác minh quyền sử dụng dữ liệu.')
        own = [j for j in archive if j.get('company') == name]
        live = [j for j in jobs if j.get('company') == name]
        a, b, c = st.columns(3)
        a.metric('Đang quan sát', len(live))
        b.metric('Đã ghi nhận trong lịch sử', len(own))
        c.metric('Tin có công bố lương', sum(bool(j.get('salary_text')) for j in live))
        st.caption('Đánh giá nhân viên: chưa có dữ liệu được cấp quyền. Không tạo điểm uy tín hoặc lời chứng thực giả.')
        if own:
            st.dataframe(pd.DataFrame([{'Chức danh': j['title'], 'Trạng thái': j.get('status', 'active'), 'Phát hiện': date(j.get('first_seen')), 'Số lần mở lại': j.get('reopen_count', 0)} for j in own]), hide_index=True)
        for job in live[:12]:
            card(job, 'company')

elif page == 'CV của tôi':
    st.title('Biến yêu cầu tuyển dụng thành điều có thể đối chiếu')
    st.info('CV chỉ được đọc trong bộ nhớ của phiên hiện tại. Không ghi tệp, không lưu vào cơ sở dữ liệu, không gửi đến dịch vụ AI bên ngoài.')
    st.caption('PDF/DOCX tối đa 5 MB; PDF tối đa 30 trang. Không hỗ trợ OCR cho bản quét. Kết quả là đối chiếu từ khóa và dẫn chứng, không dự đoán quyết định tuyển dụng.')
    key = st.session_state.get('upload_epoch', 0)
    uploaded = st.file_uploader('Tải CV của bạn', type=['pdf', 'docx'], key=f'cv-upload-{key}')
    if st.button('Xóa CV khỏi phiên'):
        st.session_state.pop('cv_text', None)
        st.session_state.upload_epoch = key + 1
        st.rerun()
    if uploaded:
        try:
            st.session_state.cv_text = parse_cv(uploaded.getvalue(), uploaded.name)
            st.success('CV đã sẵn sàng để đối chiếu trong phiên này.')
        except Exception:
            st.session_state.pop('cv_text', None)
            st.error('Không đọc được CV. Kiểm tra định dạng, giới hạn dung lượng/trang và dùng tệp có văn bản, không mã hóa.')
    st.caption('Đáp ứng: có câu mô tả áp dụng kỹ năng. Đáp ứng một phần: chỉ nhắc tới kỹ năng. Chưa tìm thấy: không có từ khóa trong phần văn bản đọc được. Chưa đánh giá số năm kinh nghiệm, trình độ hoặc tính xác thực.')
    if jobs:
        chosen = st.selectbox('Chọn công việc để đối chiếu', jobs, format_func=lambda j: j['title'] + ' · ' + j['company'])
        match_panel(chosen)
    else:
        st.info('Chưa có JD Việt Nam để đối chiếu. CV sẽ không được đưa vào bộ thu thập dữ liệu.')

elif page == 'Lộ trình nghề nghiệp':
    st.title('Hình dung bước tiếp theo của bạn')
    track = st.selectbox('Nhóm nghề nghiệp', list(CAREERS))
    roles = CAREERS[track]
    st.markdown(' → '.join('**' + r + '**' for r in roles))
    st.caption('Lộ trình minh họa, không phải kết quả thống kê hoặc cam kết thăng tiến. Có thể đi theo nhánh chuyên gia, quản lý hoặc nghề liên quan.')
    a, b = st.columns(2)
    current = a.selectbox('Vai trò hiện tại', roles)
    target = b.selectbox('Vai trò mong muốn', roles, index=min(1, len(roles) - 1))
    current_jobs = [j for j in jobs if current.casefold() in j['title'].casefold()]
    target_jobs = [j for j in jobs if target.casefold() in j['title'].casefold()]
    current_skills = {s for j in current_jobs for s in j.get('skills', [])}
    target_skills = {s for j in target_jobs for s in j.get('skills', [])}
    st.write('**Kỹ năng chung quan sát được:** ' + (', '.join(sorted(current_skills & target_skills)) or 'Chưa đủ dữ liệu'))
    st.write('**Kỹ năng bổ sung ở vai trò đích:** ' + (', '.join(sorted(target_skills - current_skills)) or 'Chưa đủ dữ liệu'))
    st.caption(f'Đối chiếu từ {len(current_jobs)} tin vai trò hiện tại và {len(target_jobs)} tin vai trò đích; đây là khác biệt giữa mẫu tin, không kết luận về năng lực của bạn.')
    for job in target_jobs[:6]:
        card(job, 'career')

elif page == 'Thị trường':
    st.title('Góc nhìn từ những cơ hội đã quan sát')
    period_start = min((j.get('first_seen', '') for j in archive if j.get('first_seen')), default='')
    scope = f'Mẫu {len(jobs)} tin Việt Nam đang quan sát / {len(archive)} tin lịch sử; từ {date(period_start)} đến {date(updated)}. Chỉ các nguồn đã đăng ký, không đại diện toàn quốc.'
    st.caption(scope)
    a, b, c, d = st.columns(4)
    a.metric('Tin đang quan sát', len(jobs))
    b.metric('Mới trong 7 ngày', new_in_last_days(jobs))
    c.metric('Doanh nghiệp', len({j['company'] for j in jobs}))
    d.metric('Công bố lương', f'{sum(bool(j.get("salary_text")) for j in jobs) / len(jobs):.0%}' if jobs else '—')
    if len(jobs) < 20:
        st.info('Mẫu dưới 20 tin: chưa hiển thị biểu đồ phân bố để tránh diễn giải quá mức.')
    else:
        for title, counts in [('Cơ hội theo địa điểm', Counter(j.get('location', 'Chưa rõ') for j in jobs)), ('Chức năng công việc', Counter(j.get('category', 'Khác') for j in jobs)), ('Kỹ năng được nhắc tới', Counter(s for j in jobs for s in j.get('skills', []))), ('Tin phát hiện theo ngày', Counter(j.get('first_seen', '')[:10] for j in archive if j.get('first_seen')))]:
            if counts:
                st.subheader(title)
                st.bar_chart(pd.DataFrame(counts.most_common(15), columns=['Nhóm', 'Số tin']).set_index('Nhóm'), color='#75A66A')
                st.caption(scope + ' Ngày phát hiện không nhất thiết là ngày đăng tuyển.')
    st.write(f'**Tin từng mở lại:** {sum(j.get("reopen_count", 0) > 0 for j in archive)}')

elif page == 'Phương pháp & riêng tư':
    st.title('Rõ nguồn dữ liệu. Rõ giới hạn.')
    st.markdown('''- **Việc làm:** nguồn ATS có quyền sử dụng được xác nhận; tin thiếu hai lần kiểm tra thành công liên tiếp mới được ghi nhận đóng.
- **Phân tích:** trích xuất từ khóa theo quy tắc. Bản diễn giải AI chỉ hiển thị khi quản trị đã tạo từ JD được cấp quyền; nội dung được gắn nhãn và kèm câu gốc để đối chiếu.
- **Lương:** chỉ hiển thị nội dung nguồn công bố. Chưa có bộ dữ liệu được cấp quyền để ước tính thị trường.
- **CV và việc đã lưu:** chỉ tồn tại trong phiên hiện tại; không lưu vào kho mã hoặc gửi đến AI bên ngoài. Xóa CV bằng nút tại CV của tôi.
- **Uy tín doanh nghiệp:** không chấm điểm, không suy diễn hành vi từ dữ liệu thiếu, không tạo đánh giá giả.
- **Phạm vi:** Việt Nam; dữ liệu lịch sử các thị trường khác vẫn được bảo toàn trong kho dữ liệu.
- **Nguồn đối tác:** LinkedIn, VietnamWorks, TopCV, CareerViet, ITviec, Vieclam24h và Glints cần quyền sử dụng/luồng dữ liệu phù hợp trước khi kết nối.''')

elif page == 'Quản trị nguồn':
    st.title('Quản trị doanh nghiệp & sức khỏe nguồn')
    secret = os.environ.get('JOB_ADMIN_PASSWORD', '')
    if not secret:
        try:
            secret = st.secrets.get('JOB_ADMIN_PASSWORD', '')
        except Exception:
            secret = ''
    password = st.text_input('Mật khẩu quản trị', type='password')
    if not secret:
        st.info('Thiết lập JOB_ADMIN_PASSWORD trong biến môi trường hoặc Streamlit Secrets để bật quản trị.')
        st.stop()
    if not hmac.compare_digest(password.encode(), str(secret).encode()):
        st.info('Đăng nhập để quản lý nguồn và xem lỗi thu thập.')
        st.stop()
    st.caption('Lưu trữ dùng chung: PostgreSQL. Website và bộ thu thập cần dùng cùng DATABASE_URL.' if STORE else 'Lưu trữ hiện tại: JSON trên máy chủ. Trên Streamlit Cloud, tải cấu hình và đưa vào GitHub để GitHub Actions sử dụng; ổ đĩa Cloud không bảo đảm lưu lâu dài.')
    rows = [{**s, 'provider': p} for p in FIELDS for s in config.get(p, [])]
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True)
    editing = st.selectbox('Chọn nguồn để chỉnh sửa', [None] + rows, format_func=lambda r: 'Thêm nguồn mới' if r is None else r['company'] + ' · ' + r['provider']) or {}
    provider = editing.get('provider')
    domains = {'greenhouse': 'https://boards.greenhouse.io/', 'lever': 'https://jobs.lever.co/', 'ashby': 'https://jobs.ashbyhq.com/', 'smartrecruiters': 'https://careers.smartrecruiters.com/'}
    edit_url = editing.get('careers_url') or (domains[provider] + editing.get(FIELDS[provider], '') if provider else '')
    with st.form('source-form'):
        st.subheader('Thêm / cập nhật / tắt nguồn ATS')
        company = st.text_input('Tên doanh nghiệp', value=editing.get('company', ''))
        url = st.text_input('URL trang tuyển dụng ATS', value=edit_url, placeholder='https://jobs.lever.co/tên-doanh-nghiệp')
        permission = st.text_input('URL bằng chứng cho phép lưu và công bố dữ liệu', value=editing.get('permission_url', ''))
        permission_mode = st.radio('Phạm vi được cấp quyền', ['full', 'links'], index=1 if editing.get('permission_mode') == 'links' else 0, format_func=lambda v: 'JD đầy đủ và liên kết' if v == 'full' else 'Chỉ thông tin cơ bản và liên kết')
        enabled = st.checkbox('Tôi đã xác minh quyền sử dụng và muốn kích hoạt thu thập', value=bool(editing.get('enabled') and (editing.get('authorized') or editing.get('discovery_enabled'))))
        ai_allowed = st.checkbox('Quyền sử dụng cũng cho phép gửi JD đến OpenAI để diễn giải', value=bool(editing.get('ai_authorized')))
        submitted = st.form_submit_button('Lưu nguồn')
    if submitted:
        try:
            revised = register_source(config, company, url, permission, enabled, permission_mode, ai_allowed)
            backup = ROOT / 'backups' / ('sources-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')
            save_json(backup, config)
            save_json(ROOT / 'sources.json', revised)
            st.success('Đã lưu cấu hình nguồn. Lần chạy bộ thu thập tiếp theo sẽ đọc cấu hình mới.')
            config = revised
        except ValueError as error:
            st.error(str(error))
    st.download_button('Tải cấu hình nguồn cho GitHub', json.dumps(config, ensure_ascii=False, indent=2), 'sources.json', 'application/json')
    with st.form('company-form'):
        st.subheader('Thêm doanh nghiệp vào danh sách cần xác minh')
        employer = st.text_input('Doanh nghiệp')
        careers_url = st.text_input('Trang tuyển dụng chính thức')
        industry = st.text_input('Ngành nghề')
        page_discovery = st.checkbox('Cho phép kiểm tra trang tuyển dụng để tìm liên kết ATS (không thu thập JD)')
        add_company = st.form_submit_button('Lưu doanh nghiệp')
    if add_company:
        if employer.strip() and safe_url(careers_url):
            existing = read('company_watchlist.json', [])
            old = next((r for r in existing if r.get('company') == employer.strip() and r.get('country') == 'Vietnam'), {})
            entry = {**old, 'company': employer.strip(), 'country': 'Vietnam', 'careers_url': careers_url, 'industry': industry, 'page_discovery_enabled': page_discovery, 'integration_status': 'Cần xác minh quyền sử dụng'}
            existing = [r for r in existing if not (r.get('company') == employer.strip() and r.get('country') == 'Vietnam')] + [entry]
            save_json(DATA / 'company_watchlist.json', existing)
            st.success('Đã lưu doanh nghiệp; chưa bật thu thập tự động.')
        else:
            st.error('Cần tên doanh nghiệp và URL HTTPS hợp lệ.')
    st.subheader('Phát hiện nguồn từ danh bạ')
    st.caption('Chỉ dò liên kết ATS trên trang được chọn; kiểm tra robots.txt, không đăng nhập, không vượt hạn chế, không tự bật thu thập.')
    eligible = [r for r in watchlist if r.get('page_discovery_enabled')]
    if eligible:
        scan = st.selectbox('Trang đã cho phép kiểm tra', eligible, format_func=lambda r: r['company'])
        if st.button('Kiểm tra trang này'):
            try:
                pending = read('source_candidates.json', [])
                found = candidates(scan['company'], scan['careers_url'])
                save_json(DATA / 'source_candidates.json', merge_candidates(pending, found))
                st.success(f'Đã tìm thấy {len(found)} liên kết ATS; tất cả vẫn chờ duyệt quyền sử dụng.')
            except Exception:
                st.warning('Không kiểm tra được trang này. Xem lại URL, robots.txt hoặc kiểm tra thủ công; không bật nguồn.')
    else:
        st.info('Chưa có trang được bật kiểm tra tự động. Cập nhật doanh nghiệp trong biểu mẫu phía trên.')
    pending = read('source_candidates.json', [])
    if pending:
        candidate = st.selectbox('Nguồn chờ duyệt', pending, format_func=lambda r: r['company'] + ' · ' + r['provider'] + '/' + r['board'])
        if st.button('Đưa vào danh sách nguồn ở trạng thái tắt'):
            save_json(ROOT / 'sources.json', add_pending(config, candidate))
            st.success('Đã thêm hoặc giữ nguyên nguồn đã có; không thay đổi quyền sử dụng.')
    st.subheader('Diễn giải JD bằng AI')
    st.caption('Chỉ quản trị viên tạo nội dung; chỉ gửi JD được cấp quyền, không gửi CV. Kết quả gắn với phiên bản JD và bị ẩn khi JD thay đổi. Có thể phát sinh phí API.')
    if not ai_configured():
        st.info('Chưa bật AI. Cần OPENAI_API_KEY, OPENAI_MODEL và JOB_AI_ENABLED=true trong cấu hình bảo mật.')
    elif jobs:
        explain_target = st.selectbox('JD cần diễn giải', jobs, format_func=lambda j: j['title'] + ' · ' + j['company'])
        if st.button('Tạo bản diễn giải tiếng Việt'):
            source = next((r for r in rows if r['provider'] + ':' + r.get(FIELDS[r['provider']], '') == explain_target.get('source_key')), {})
            try:
                result = generate(explain_target, source)
                explanations[explain_target['id']] = {'description_hash': content_hash(explain_target), 'items': result, 'created_at': datetime.now(timezone.utc).isoformat()}
                save_json(DATA / 'job_explanations.json', explanations)
                st.success('Đã lưu bản diễn giải có dẫn chứng gốc để người đọc đối chiếu.')
            except (ValueError, PermissionError) as error:
                st.error(str(error))
            except Exception:
                st.error('Không kết nối được dịch vụ AI. Chưa lưu nội dung mới.')
    for label, report in [('JD đầy đủ', status), ('Chỉ mục liên kết', discovery_status)]:
        st.subheader(label)
        st.caption('Lần chạy: ' + date(report.get('checked_at')))
        if report.get('sources'):
            st.dataframe(pd.DataFrame(report['sources']), hide_index=True)
        for error in report.get('errors', []):
            st.error(str(error))
        if not report.get('sources'):
            st.info('Chưa có lần thu thập nguồn được cấp quyền.')
    with st.expander('Kết quả kiểm tra kết nối gần nhất (không xác nhận quyền sử dụng)'):
        st.json(read('source_probe.json', []))
