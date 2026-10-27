"""Presentation only: existing API, report values, citations and JSON are untouched."""
import hashlib
import html
import json
import math
import os
from collections import Counter
from datetime import date
from pathlib import Path
import requests
import streamlit as st

API = os.getenv("TENDERPROOF_API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="TenderProof AI | مراجعة المناقصات", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")
STATUS = {"SATISFIED": ("مستوفى", "green"), "CONTRADICTED": ("مخالف", "red"), "MISSING_EVIDENCE": ("دليل ناقص", "purple"), "NEEDS_REVIEW": ("يحتاج مراجعة", "amber")}
TYPES = {"ELIGIBILITY": "الأهلية", "TECHNICAL": "المتطلبات الفنية", "BOQ": "جدول الكميات"}
E = lambda value: html.escape(str(value))
st.markdown('<style>'+Path(__file__).with_name('ui.css').read_text(encoding='utf-8')+'</style>',unsafe_allow_html=True)

def markup(value):
    st.markdown(value,unsafe_allow_html=True)

def section(title,subtitle=""):
    return f"<div class='tp-section'><h3>{E(title)}</h3><span class='tp-muted'>{E(subtitle)}</span></div>"

def badge(status):
    label,color=STATUS[status]
    return f"<span class='tp-badge {color}'>{E(label)}</span>"

def citations(sources,names):
    if not sources:
        return "<div class='tp-no-evidence'>لا توجد مراجع في هذا الجزء من التقرير. لا تضيف الواجهة أدلة أو استنتاجات.</div>"
    return ''.join(f"<div class='tp-citation'><div class='tp-source'><bdi>{E(names.get(c['document_id'],c['document_id']))}</bdi><span>·</span><bdi>{E(c['document_id'])}</bdi><span class='tp-page'>صفحة <bdi>{E(c['pdf_page'])}</bdi></span></div><div class='quote'>{E(c['quote'])}</div></div>" for c in sources)

@st.cache_data(ttl=3,show_spinner=False)
def service_state():
    try:
        response=requests.get(API+'/health',timeout=3)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {'status':'offline','paid_ai_enabled':False}

state=service_state()
ready=state['status']=='ok'
markup(f"<div class='tp-topbar'><div class='tp-brand'><div class='tp-logo'>TP</div><div class='tp-brand-name'>TenderProof <span>AI</span><small>TENDER REVIEW WORKSPACE</small></div></div><span class='tp-api'><i></i>{'الخدمة متصلة' if ready else 'الخدمة غير متاحة'}</span></div>")
mode_slot=st.empty()
intro_slot=st.empty()

def render_intro(result=None):
    if result:
        intro_slot.markdown("<div class='tp-workspace-heading'><div class='tp-kicker'>مساحة العمل / المراجعة</div><h1>نتائج الشروط والأدلة</h1></div>",unsafe_allow_html=True)
    else:
        intro_slot.markdown("<div class='tp-intro'><div><div class='tp-kicker'>مساحة مراجعة المناقصات</div><h1>راجع الشروط. وافحص الدليل.</h1><p>الكراسة ومستندات الشركة في مساحة واحدة، مع مراجع أصلية وقرار قابل للمراجعة.</p></div><div class='tp-intro-meta'>أهلية · متطلبات فنية · كميات<br>اقتباسات مرتبطة بالمستند والصفحة</div></div>",unsafe_allow_html=True)
previous=st.session_state.get('result')
action=saved_action=False
with st.expander('تغيير الملفات أو اختيار سيناريو آخر' if previous else 'رفع الملفات أو اختيار سيناريو للعرض',expanded=not bool(previous)):
    if previous:
        st.caption('افتح هذا القسم للرجوع إلى الملفات أو اختيار سيناريو آخر. تغيير المدخلات يتطلب تحميل التقرير أو تشغيله من جديد.')
    source=st.radio('مصدر المستندات',['رفع ملفات','Demo Mode — مستندات افتراضية'],horizontal=True,key='document_source')
    is_demo=source.startswith('Demo')
    with st.container(key='tp_upload_panel',border=False):
        if not is_demo:
            markup(section('رفع المستندات','PDF فقط · حتى 20 MB للملف'))
            tender_col,company_col=st.columns(2)
            with tender_col:
                tender=st.file_uploader('كراسة الشروط',type=['pdf'],key='tender_pdf',help='ملف واحد حتى 20 MB.')
            with company_col:
                companies=st.file_uploader('مستندات الشركة',type=['pdf'],accept_multiple_files=True,key='company_pdfs',help='حتى 20 ملفًا وإجمالي 50 MB.')
            settings_col,date_col=st.columns([1,2])
            with settings_col:
                with st.popover('إعدادات متقدمة',width='stretch'):
                    mode_label=st.selectbox('طريقة التشغيل',['MOCK — فحص مجاني بدون تحليل AI','AI — تحليل حقيقي عبر OpenAI'],key='upload_mode')
                    mode='AI' if mode_label.startswith('AI') else 'MOCK'
                    complete=st.checkbox('أؤكد أن كل مستندات الشركة المطلوبة ضمن الملفات المرفوعة',value=False,key='upload_complete')
                    synthetic=st.checkbox('استخدام مستندات افتراضية للديمو',value=False,key='upload_synthetic',help='فعّل هذا الخيار فقط مع ملفات الاختبار الافتراضية، وليس مع مستندات شركة حقيقية.')
                    st.caption('الفحص المجاني يختبر رفع الملفات وقراءتها، ولا يصدر أحكام أهلية. خيار المستندات الافتراضية مخصص للديمو فقط.')
                    if mode=='AI':
                        st.caption('تفاصيل جاهزية السيرفر: '+state.get('ai_readiness',{}).get('message','تعذر الاتصال بالخدمة. تأكد من تشغيل التطبيق.'))
            reference=date_col.date_input('تاريخ التقييم',value=date.today(),help='نتحقق من سريان المستندات في هذا التاريخ. عند تجربة السيناريوهات المرفقة استخدم 2026-10-31.')
            confirmed=False
            if mode=='AI':
                if not state.get('paid_ai_enabled'):
                    messages={
                        'DISABLED':'التحليل عبر OpenAI غير مفعّل. لعرض النتائج بدون تكلفة اختر Demo Mode. لتفعيله لاحقًا استخدم START_REAL_AI.bat حسب دليل التشغيل.',
                        'KEY_MISSING':'مفتاح OpenAI غير مُعدّ. راجع دليل التشغيل لإضافته بأمان، أو استخدم Demo Mode بدون تكلفة.',
                        'SECRET_UNREADABLE':'تعذر قراءة مفتاح OpenAI. راجع ملف المفتاح وصلاحياته حسب دليل التشغيل؛ لا ترسل المفتاح في الرسائل.',
                        'MODEL_UNSUPPORTED':'إعداد الموديل لا يتوافق مع ضوابط التشغيل الحالية. راجع تفاصيل الجاهزية في الإعدادات المتقدمة.',
                        'ATTEMPT_USED':'محاولة التحليل المدفوعة المصرح بها استُخدمت بالفعل. لن نعيدها تلقائيًا؛ يمكنك الاستمرار في عرض التقارير المحفوظة.'}
                    st.info(messages.get(state.get('ai_readiness',{}).get('code'),'تعذر تحديد جاهزية التحليل. تأكد من تشغيل التطبيق، ثم راجع الإعدادات المتقدمة.'))
                else:
                    confirmed=st.checkbox('أوافق على إرسال هذه المستندات إلى OpenAI وتكلفة هذا التشغيل',value=False)
            fingerprint=hashlib.sha256(json.dumps({'source':source,'date':str(reference),'mode':mode,'complete':complete,'synthetic':synthetic,
                'tender':hashlib.sha256(tender.getvalue()).hexdigest() if tender else None,
                'companies':[(p.name,hashlib.sha256(p.getvalue()).hexdigest()) for p in companies]},sort_keys=True).encode()).hexdigest()
            action=st.button('بدء المراجعة' if mode=='AI' else 'تشغيل الفحص',type='primary',width='stretch',disabled=not ready or not tender or not companies or (mode=='AI' and not (state.get('paid_ai_enabled') and confirmed)))
        else:
            st.caption('مستندات افتراضية فقط. عرض التقرير المحفوظ لا يشغّل تحليلًا جديدًا.')
            cases={'case_101':'case_101 · تقرير قبول OpenAI سابق','case_202':'case_202 · Replay محلي محفوظ','case_303':'case_303 · Replay محلي محفوظ'}
            chosen=st.selectbox('اختر سيناريو الديمو',list(cases),format_func=cases.get)
            a,b=st.columns([1,2])
            with a:
                with st.popover('إعدادات متقدمة',width='stretch'):
                    synthetic=st.checkbox('تفعيل synthetic-test لفحص MOCK الجديد — ملفات افتراضية فقط',value=False,key='demo_synthetic')
                    action=st.button('فحص MOCK جديد لملفات الديمو',width='stretch',disabled=not ready)
                    st.caption('فحص جديد بدون LLM؛ لا يعيد أحكام التقرير المحفوظ.')
            saved_action=b.button('عرض التقرير المحفوظ',type='primary',width='stretch',disabled=not ready)
            fingerprint=f'demo:{chosen}:{synthetic}'
            st.caption('تاريخ تقارير الديمو: 2026-10-31 · لا توجد استدعاءات مدفوعة في هذا القسم.')

if st.session_state.get('result_fingerprint')!=fingerprint:
    st.session_state.pop('result',None)
    st.session_state.pop('selected_requirement',None)

def render_mode(result=None):
    execution=result['execution'] if result else {}
    kind=execution.get('kind')
    if kind=='SAVED_DEMO':label,detail,tone='تقرير محفوظ','ليس تحليلًا جديدًا','saved'
    elif kind=='LIVE_AI':label,detail,tone='Real AI','تحليل OpenAI جديد','live'
    elif kind=='MOCK_PIPELINE':label,detail,tone='MOCK','فحص بدون AI','mock'
    elif is_demo:label,detail,tone='Demo','عرض تقارير محفوظة','saved'
    elif mode=='AI':label,detail,tone='Real AI','غير مفعّل' if not state.get('paid_ai_enabled') else 'بانتظار التشغيل','live'
    else:label,detail,tone='MOCK','فحص بدون AI','mock'
    mode_slot.markdown(f"<div class='tp-mode {tone}' role='status'><span class='tp-dot'></span><bdi>{E(label)}</bdi><small>{E(detail)}</small></div>",unsafe_allow_html=True)
render_mode(st.session_state.get('result'))
render_intro(st.session_state.get('result'))
if action or saved_action:
    st.session_state.pop("result", None)
    with st.status("تحميل التقرير المحفوظ…" if saved_action else "قراءة المستندات والتحقق من الأدلة…", expanded=True) as progress:
        st.caption("عرض نسخة محفوظة دون تحليل جديد." if saved_action else "نقرأ الملفات ونراجع الشروط والأدلة ثم نتحقق من مراجع التقرير.")
        try:
            if is_demo and saved_action:
                response = requests.get(f"{API}/demo/{chosen}", timeout=60)
            elif is_demo:
                response = requests.post(f"{API}/demo/{chosen}/mock", data={"synthetic_test":str(synthetic).lower()}, timeout=180)
            else:
                files = [("tender", (tender.name, tender.getvalue(), "application/pdf"))]
                files += [("companies", (p.name,p.getvalue(),"application/pdf")) for p in companies]
                response = requests.post(API+"/analyze", files=files, data={"mode":mode,"reference_date":str(reference),
                    "synthetic_test":str(synthetic).lower(),"company_documents_complete":str(complete).lower(),"confirm_paid_api":str(confirmed).lower()}, timeout=900)
            if response.ok:
                st.session_state["result"] = response.json()
                st.session_state["result_fingerprint"] = fingerprint
                progress.update(label="تم تحميل التقرير المحفوظ" if saved_action else "اكتمل المسار والتحقق", state="complete", expanded=False)
                st.rerun()
            else:
                try:
                    detail = response.json().get("detail")
                except ValueError:
                    detail = None
                st.error(detail if isinstance(detail,str) else "تعذر إكمال الطلب. تأكد من الملفات وإعدادات السيرفر.")
                progress.update(label="الطلب لم يكتمل — لا يوجد تقرير نجاح", state="error")
        except requests.RequestException:
            progress.update(label="تعذر الاتصال بالـAPI أو انتهت مهلة الانتظار", state="error")
            st.error("تحقق من تشغيل FastAPI. الطلب لا يُعاد تلقائيًا؛ لا تضغط مرة أخرى أثناء تشغيل AI قبل مراجعة حالة السيرفر.")

result=st.session_state.get('result')
render_mode(result)
render_intro(result)
if result:
    report,execution=result['report'],result['execution']
    kind=execution['kind']
    if kind=='SAVED_DEMO':
        st.info(f"تقرير محفوظ للعرض · {execution['case']} — لم يُجرَ تحليل جديد للملفات في هذه الجلسة.")
    elif kind=='MOCK_PIPELINE':
        st.warning('فحص مجاني جديد (MOCK) — يختبر قراءة الملفات فقط، دون تحليل OpenAI أو إصدار حكم على أهلية الشركة.')
    else:
        st.success('تحليل جديد عبر OpenAI — تم التحقق من مراجع التقرير.')
    if not report['coverage_confirmed']:
        st.warning('اكتمال المستندات غير مؤكد. عدم العثور على دليل لا يثبت وحده غياب مستند مطلوب؛ راجع مجموعة الملفات قبل الاعتماد على النتائج.')
    markup('<div class="tp-section"><div><div class="tp-kicker">نتائج المراجعة</div><h2>ملخص التقرير</h2></div><span class="tp-count">'+str(len(report['findings']))+' نتيجة</span></div>')
    elapsed=f"<span>زمن التنفيذ <bdi>{E(execution['elapsed_seconds'])}</bdi> ثانية</span>" if execution.get('elapsed_seconds') is not None else ''
    markup(f"<div class='tp-report-meta'><span>تاريخ التقييم <b><bdi>{E(report['reference_date'])}</bdi></b></span><span><b>{len(report['documents'])}</b> مستندات</span><span>اكتمال المستندات: <b>{'مؤكد' if report['coverage_confirmed'] else 'غير مؤكد'}</b></span>{elapsed}</div>")
    counts=Counter(f['status'] for f in report['findings'])
    symbols={'SATISFIED':'✓','CONTRADICTED':'×','MISSING_EVIDENCE':'−','NEEDS_REVIEW':'!'}
    markup('<div class="summary">'+''.join(f"<div class='tp-stat {color}'><div><strong>{counts[status]}</strong><span>{label}</span></div><em>{symbols[status]}</em></div>" for status,(label,color) in STATUS.items())+'</div>')
    st.download_button('تنزيل التقرير الأصلي · JSON',data=json.dumps(report,ensure_ascii=False,indent=2),file_name=f"tenderproof-{report['reference_date']}-{kind.lower()}.json",mime='application/json')
    targets={}
    for row in report['eligibility']['requirements']:targets[('ELIGIBILITY',row['requirement_id'])]=row
    for row in report['technical']['technical_requirements']:targets[('TECHNICAL',row['technical_id'])]=row
    for row in report['technical']['boq_items']:targets[('BOQ',row['boq_item_id'])]=row
    names={d['document_id']:d['filename'] for d in report['documents']}
    with st.container(key='tp-filters'):
        search_col,status_col,type_col=st.columns([2,1,1])
        search=search_col.text_input('ابحث في الشروط',placeholder='نص الشرط، رقم البند، أو سبب النتيجة')
        status_filter=status_col.selectbox('الحالة',['الكل',*STATUS],format_func=lambda v:STATUS[v][0] if v in STATUS else v)
        type_filter=type_col.selectbox('نوع الشرط',['الكل',*TYPES],format_func=lambda v:TYPES.get(v,v))
    filtered=[]
    for finding in report['findings']:
        target=targets.get((finding['target_type'],finding['target_id']),{})
        text=target.get('text',target.get('description',''))
        if status_filter!='الكل' and finding['status']!=status_filter:continue
        if type_filter!='الكل' and finding['target_type']!=type_filter:continue
        if search and search.casefold() not in (text+' '+finding['target_id']+' '+finding['explanation']).casefold():continue
        filtered.append((finding,target,text))
    if filtered:
        with st.container(key='tp-results'):
            list_col,inspector_col=st.columns([.37,.63],gap='large')
            with list_col:
                with st.container(key='tp-requirements'):
                    markup(section('قائمة الشروط',f'{len(filtered)} مطابق للفلاتر'))
                    page_count=math.ceil(len(filtered)/4)
                    page_number=st.selectbox('صفحة الشروط',range(page_count),format_func=lambda n:f'الصفحة {n+1} من {page_count}') if page_count>1 else 0
                    visible=filtered[page_number*4:(page_number+1)*4]
                    key_of=lambda item:item[0]['target_type']+':'+item[0]['target_id']
                    visible_keys=[key_of(item) for item in visible]
                    if st.session_state.get('selected_requirement') not in visible_keys:
                        st.session_state['selected_requirement']=visible_keys[0]
                    for index,(finding,target,text) in enumerate(visible):
                        item_key=finding['target_type']+':'+finding['target_id']
                        active=st.session_state['selected_requirement']==item_key
                        with st.container(border=True,key=f'tp_reqitem_{index}'):
                            markup(f"<div class='tp-list-card {'selected' if active else ''}'><div class='tp-list-meta'><bdi class='tp-identifier'>{E(finding['target_id'])}</bdi>{badge(finding['status'])}</div><div class='tp-list-text' dir='auto'>{E(text)}</div><div class='tp-list-foot'><span>{E(TYPES[finding['target_type']])}</span><span>{len(finding['evidence'])} مراجع من الشركة</span></div></div>")
                            def inspect(item_key=item_key):
                                st.session_state['selected_requirement']=item_key
                            st.button(('الدليل المعروض' if active else 'فحص الأدلة')+' · '+finding['target_id'],key='inspect_'+item_key,on_click=inspect,width='stretch',type='primary' if active else 'secondary')
            with inspector_col:
                with st.container(key='tp-evidence-inspector'):
                    finding,target,text=next(item for item in visible if key_of(item)==st.session_state['selected_requirement'])
                    markup(section('عارض الأدلة','النصوص الأصلية كاملة'))
                    review_html=''.join(f"<div class='tp-uncertainty' dir='auto'>{E(reason)}</div>" for reason in finding['uncertainty_reasons'])
                    markup(f"<section class='tp-inspector' aria-label='تفاصيل الشرط والأدلة'><div class='tp-inspector-head'><h3><bdi>{E(finding['target_id'])}</bdi> · {E(TYPES[finding['target_type']])}</h3>{badge(finding['status'])}</div><div class='tp-inspector-grid'><div class='tp-inspector-pane tp-condition-pane'><div class='tp-pane-title'><i></i>الشرط في كراسة الشروط</div><div class='tp-full-text' dir='auto'>{E(text)}</div><div class='tp-subtitle'>مراجع الشرط</div>{citations(target.get('sources',[]),names)}</div><div class='tp-inspector-pane tp-company-pane'><div class='tp-pane-title'><i></i>دليل الشركة</div><div class='tp-full-text' dir='auto'>{E(finding['explanation'])}</div>{review_html}<div class='tp-subtitle'>المستندات المستشهد بها</div>{citations(finding['evidence'],names)}</div></div></section>")
    else:
        st.info('لا توجد شروط مطابقة للفلاتر.' if report['findings'] else 'المسار اكتمل بدون نتائج شروط. في MOCK ده متوقع؛ لا توجد أحكام AI مخفية أو أرقام افتراضية.')
    with st.expander('جدول الكميات · BOQ · '+report['technical']['boq_status'],expanded=False):
        for reason in report['technical']['boq_review_reasons']:st.warning(reason)
        for item in report['technical']['boq_items']:
            q=item['quantity']
            markup(f"<div class='tp-boq-item'><h4><bdi>{E(item['boq_item_id'])}</bdi> · {E(item['description'])}</h4><div class='tp-boq-meta'><span>الكمية الأصلية: <bdi>{E(q['raw_text'])}</bdi></span><span>القيمة: <bdi>{E(q['decimal_value']) if q['decimal_value'] is not None else 'غير مؤكدة'}</bdi></span><span>الوحدة: <bdi>{E(item['unit'] or 'غير محددة')}</bdi></span></div>{''.join('<div class="tp-uncertainty">'+E(reason)+'</div>' for reason in item['review_reasons'])}{citations(q['sources'],names)}</div>")
        if not report['technical']['boq_items']:st.caption('لا توجد أصناف كميات مستخرجة في التقرير.')
    with st.expander(f"ملاحظات القراءة والتحقق الأصلية · {len(report['warnings'])}"):
        st.caption('هذه الملاحظات الأصلية تشرح حدود القراءة والتحقق. راجع أسباب «يحتاج مراجعة» والأدلة قبل اعتماد النتيجة؛ عرض التقرير لا يغيّر أحكامه.')
        for warning in report['warnings']:st.write('• '+warning)
else:
    markup("<div class='tp-empty'><strong>ابدأ من المستندات</strong>ارفع الكراسة ومستندات الشركة، أو اختر الديمو لعرض تقرير محفوظ بعلامة واضحة.</div>")
markup("<div class='tp-footer'><span>TenderProof AI · مساحة مراجعة قائمة على الأدلة</span><span>النتائج للمراجعة البشرية، ولا تؤكد وحدها أهلية التقديم.</span></div>")