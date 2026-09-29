"""Deterministic, traceable job intelligence. No unsupported company allegations."""
import re
import hashlib
import unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from datetime import datetime, timezone
from html import unescape

CATEGORIES = {
    'Healthcare': ['nurse', 'doctor', 'medical', 'điều dưỡng', 'bác sĩ', 'y tế', 'dược'],
    'Education': ['teacher', 'education', 'giáo viên', 'giảng viên', 'giáo dục'],
    'Manufacturing': ['production', 'manufactur', 'quality control', 'sản xuất', 'cơ khí'],
    'Hospitality': ['hotel', 'restaurant', 'hospitality', 'khách sạn', 'nhà hàng'],
    'Human Resources': ['human resources', 'recruiter', 'nhân sự', 'tuyển dụng'],
    'Retail & Sales': ['retail', 'store manager', 'sales', 'bán hàng', 'cửa hàng'],
    'Construction': ['construction', 'civil engineer', 'xây dựng', 'kiến trúc'],
    'Strategy & Consulting': ['strategy','strategic','consult','transformation','corporate development','management consulting','chiến lược','tư vấn'],
    'Revenue & Pricing': ['revenue growth','pricing','commercial excellence','trade investment','category management','monetization','r GM','price analyst','định giá'],
    'Business Development': ['business development','partnership','account manager','key account','sales development','growth manager','phát triển kinh doanh'],
    'Data & Analytics': ['data analyst','analytics','business intelligence','data engineer','data scientist','machine learning','insights','phân tích dữ liệu','數據分析','資料分析'],
    'Finance & Treasury': ['treasury','finance','investment','fx','rates','asset liability','alm','risk analyst','tài chính','ngoại hối'],
    'Operations & Supply Chain': ['operations','operational excellence','supply chain','logistics','procurement','retail operations','vận hành'],
    'Technology & Product': ['software','developer','engineering','product manager','product owner','cloud','cybersecurity'],
    'Marketing & Brand': ['marketing','branding','digital marketing','performance marketing','consumer insights'],
}
SKILLS = {
    'C++': r'\bc\+\+', 'Java': r'\bjava\b', 'JavaScript': r'\bjavascript\b|\btypescript\b',
    'Embedded systems': r'\bembedded\b|\bfirmware\b', 'Linux': r'\blinux\b',
    'Testing': r'\btesting\b|kiểm thử', 'AutoCAD': r'\bautocad\b',
    'Quality assurance': r'\bquality assurance\b|\biso 17025\b|đảm bảo chất lượng',
    'Customer service': r'\bcustomer service\b|chăm sóc khách hàng',
    'Sales': r'\bsales\b|bán hàng', 'Accounting': r'\baccounting\b|kế toán',
    'SQL': r'\bsql\b', 'Python':r'\bpython\b', 'Excel':r'\bexcel\b', 'Power BI':r'\bpower\s?bi\b',
    'Tableau':r'\btableau\b','R':r'\br\s+(?:programming|language|studio)\b|\brstudio\b',
    'Forecasting':r'forecast(?:ing)?|dự báo', 'Pricing':r'pric(?:e|ing)|định giá',
    'Stakeholder management':r'stakeholder', 'Project management':r'project management|quản lý dự án',
    'Financial modelling':r'financial model|mô hình tài chính', 'Strategy':r'strateg(?:y|ic)|chiến lược',
    'Communication':r'communication|giao tiếp', 'English':r'\benglish\b|tiếng anh', 'Mandarin':r'mandarin|chinese|中文|普通话',
    'CRM':r'\bcrm\b|salesforce', 'SAP':r'\bsap\b', 'Experimentation':r'\ba/b test|experiment',
}
COUNTRIES = {
 'Vietnam': ['vietnam','viet nam','việt nam','hanoi','ha noi','hà nội','ho chi minh','hồ chí minh','hcmc','saigon','sài gòn','đà nẵng','da nang','hai phong','hải phòng','bình dương','binh duong','đồng nai','dong nai','bắc ninh','bac ninh','cần thơ','can tho','long an','quảng ninh','quang ninh','hưng yên','hung yen','hải dương','hai duong','thanh hóa','thanh hoa','nghệ an','nghe an','nha trang','khánh hòa','khanh hoa','vũng tàu','vung tau','bình phước','binh phuoc','tây ninh','tay ninh','hue','huế','bắc giang','bac giang'],
 'Singapore':['singapore','singapura'],
 'Taiwan':['taiwan','taipei','taichung','kaohsiung','hsinchu','臺灣','台灣','台北','新竹','台中','高雄','桃園','taoyuan'],
}
def plain(text):
    text=re.sub(r'<[^>]+>',' ',str(text or ''))
    return re.sub(r'\s+',' ',unescape(text)).strip()

def infer_country(location):
    x=(location or '').lower()
    for country,words in COUNTRIES.items():
        if any(w in x for w in words): return country
    return 'Other / Remote / Unknown'

def category_of(title,description=''):
    text=(title+' '+plain(description)[:500]).lower()
    for label, keywords in CATEGORIES.items():
        if any(k in text for k in keywords): return label
    return 'Other'

def skill_tags(description):
    txt=plain(description)
    return [name for name,pattern in SKILLS.items() if re.search(pattern,txt,re.I)]

def signal_report(job):
    """Posting-level review cues, NEVER allegations or a reputation score."""
    description=plain(job.get('description',''))
    text=description.lower()
    signals=[]
    def add(kind,label,reason,evidence):
        signals.append({'type':kind,'label':label,'reason':reason,'evidence':evidence,'scope':'Tin tuyển dụng này; cần xác minh với nhà tuyển dụng'})
    if not description or len(description)<180:
        add('information_gap','JD thiếu chi tiết','Nội dung tin quá ngắn để đánh giá phạm vi công việc, yêu cầu và chế độ.','Mô tả công việc chưa đủ chi tiết')
    if not job.get('salary_min') and not job.get('salary_max') and not job.get('salary_text'):
        add('information_gap','Chưa công bố mức lương','Không có mức lương có thể xác minh trong dữ liệu nguồn.','Salary: Not disclosed')
    if re.search(r'competitive salary|attractive salary|lương cạnh tranh|lương hấp dẫn',text):
        add('clarify','Cách mô tả lương chưa định lượng','Nên hỏi khoảng lương và cấu phần biến đổi.','Competitive / attractive salary')
    if re.search(r'fast.paced|wear many hats|work under pressure|làm việc dưới áp lực|môi trường áp lực',text):
        add('clarify','Cần làm rõ kỳ vọng khối lượng công việc','Cụm từ này không chứng minh văn hóa tiêu cực; nên hỏi giờ làm và nguồn lực.','Fast-paced / pressure wording')
    if re.search(r'weekend[s]?|overtime|saturday|sunday|làm thêm giờ|cuối tuần',text):
        add('clarify','Có đề cập thời gian ngoài giờ','Hỏi tần suất và chính sách bù đắp trước khi ứng tuyển.','Weekend / overtime wording')
    if job.get('country')=='Other / Remote / Unknown':
        add('information_gap','Địa điểm chưa được xác định','Cần xác nhận quốc gia và hình thức làm việc.','Location not mapped')
    return signals

def language_evidence(description):
    text=plain(description)
    patterns={'English':r'\benglish\b|tiếng anh|英文|英語',
              'Mandarin':r'\bmandarin\b|\bchinese\b|中文|普通话|華語|國語|tiếng trung',
              'Vietnamese':r'\bvietnamese\b|tiếng việt|越南語'}
    return [{'language':lang,'evidence':m.group(0)} for lang,pat in patterns.items() if (m:=re.search(pat,text,re.I))]

def visa_evidence(description):
    text=plain(description)
    patterns=[('Not sponsored',r'(?:no|without|not offering|do not offer)\s+(?:visa|work permit)\s+sponsorship|visa sponsorship (?:is )?not available|must (?:already )?have (?:the )?right to work'),
              ('Sponsored',r'visa sponsorship (?:is )?(?:available|provided)|(?:we|company) (?:will |can )?sponsor (?:your |a )?(?:visa|work permit)')]
    for label,pat in patterns:
        if m:=re.search(pat,text,re.I): return {'status':label,'evidence':m.group(0)}
    return {'status':'Unknown','evidence':''}

def duplicate_key(job):
    """Conservative candidate key, not proof that distinct listings are identical."""
    def norm(v):
        x=unicodedata.normalize('NFKD',plain(v)).encode('ascii','ignore').decode().lower()
        return re.sub(r'[^a-z0-9]+',' ',x).strip()
    fields=[norm(job.get(x,'')) for x in ('company','title','country','location')]
    if not all(fields): return ''
    return hashlib.sha256('|'.join(fields).encode()).hexdigest()[:16]

def evidence_snippet(description,term,radius=105):
    text=plain(description)
    m=re.search(re.escape(term),text,re.I) if term else None
    if not m:return ''
    return text[max(0,m.start()-radius):min(len(text),m.end()+radius)]

def requirement_lines(description):
    text=plain(description)
    if not text:return []
    sentences=re.split(r'(?<=[.!?。；;])\s+|(?<=:)\s*(?=[A-Z])',text)
    keys=r'\brequir(?:e|ed|ement)|\bqualif|\bexperience|\bproficien|\bachelor|\bdegree|\byears?\b|yêu cầu|kinh nghiệm|必須|資格|經驗|要求'
    return [t.strip()[:350] for t in sentences if re.search(keys,t,re.I)][:12]

def new_in_last_days(jobs,days=7,now=None):
    from datetime import timedelta
    now=now or datetime.now(timezone.utc)
    count=0
    for j in jobs:
        try:
            d=datetime.fromisoformat(str(j.get('first_seen','')).replace('Z','+00:00'))
            if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
            count+= now-timedelta(days=days)<=d<=now
        except (TypeError,ValueError):pass
    return count

def enrich(job):
    job=dict(job)
    job['description']=plain(job.get('description',''))
    job['country']=job.get('country') or infer_country(job.get('location',''))
    job['category']=category_of(job.get('title',''),job['description'])
    job['skills']=skill_tags(job['description'])
    job['review_signals']=signal_report(job)
    job['language_evidence']=language_evidence(job['description'])
    job['language_requirements']=[x['language'] for x in job['language_evidence']]
    job['visa_evidence']=visa_evidence(job['description'])
    job['visa_sponsorship']=job['visa_evidence']['status']
    job['requirements_extracted']=requirement_lines(job['description'])
    job['duplicate_candidate_key']=duplicate_key(job)
    job.setdefault('salary_text','')
    job.setdefault('workplace_type','Not specified')
    job.setdefault('employment_type','Not specified')
    job.setdefault('experience','Not specified')
    return job

def cv_matches(cv_text,job):
    """Explainable text/skill overlap, not a hiring likelihood or personal rating."""
    found=set(skill_tags(cv_text))
    wanted=set(job.get('skills') or [])
    overlap=sorted(found & wanted)
    missing=sorted(wanted-found)
    return {'matched':overlap,'not_detected':missing,'detected_in_cv':sorted(found),'note':'Chỉ so sánh từ khóa trong tài liệu; không đo khả năng được tuyển hay sự phù hợp tổng thể.'}

def canonical_job_url(url):
    """Exact-source URL normalization only; removes tracking query and fragment."""
    try:
        parts=urlsplit(str(url or ''))
        if parts.scheme!='https' or not parts.hostname:return ''
        path=parts.path.rstrip('/') or '/'
        query = urlencode(sorted((k,v) for k,v in parse_qsl(parts.query, keep_blank_values=True)
                                 if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')))
        return urlunsplit(('https',parts.netloc.lower(),path,query,''))
    except ValueError:return ''

def visible_jobs(jobs):
    """Collapse only identical canonical application URLs; preserve same-role candidates."""
    found=set(); visible=[]
    for job in jobs:
        u=canonical_job_url(job.get('url'))
        if u and u in found:continue
        if u:found.add(u)
        visible.append(job)
    return visible
