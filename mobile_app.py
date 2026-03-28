# ─────────────────────────────────────────────────────────────────────────────
#  mobile_app.py  |  아트앤하트 출석부  v4.0
#  Streamlit Cloud + Google Sheets 전용  (SQLite 불필요)
#
#  Google Sheets 시트 구조 (시트 4개):
#    "원생목록"  : 이름 / 수업 / 생년월일 / 등록일 / 탈회일 / 메모
#    "수업일정"  : 이름 / 날짜              ← 클릭한 날짜들 = 계획일수
#    "출석기록"  : 날짜 / 이름 / 상태 / 대체일자 / 환불예정 / 메모
#    "진도현황"  : 이름 / 프로젝트 / 진행단계 / 사진1~5 / 최종수정일
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
import calendar as cal_mod
import base64, io, re

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="아트앤하트 출석부",
    page_icon="🎨",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={"About": "아트앤하트 출석부 v4.0"},
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;800&display=swap');
* { font-family: 'Noto Sans KR', sans-serif !important; box-sizing: border-box; }

[data-testid="stHeader"],[data-testid="stToolbar"],
#MainMenu,[data-testid="stStatusWidget"] { display:none!important; }

[data-testid="stAppViewContainer"] { background:#f0f2f8; }
.block-container { padding:0 .75rem 3rem .75rem!important; max-width:480px!important; margin:0 auto!important; }

/* 앱 헤더 */
.app-hdr {
    background:linear-gradient(135deg,#6366f1,#8b5cf6);
    color:#fff; padding:15px 20px 13px;
    margin:0 -.75rem; display:flex; align-items:center; gap:12px;
}
.app-hdr-title { font-size:18px; font-weight:800; }
.app-hdr-sub   { font-size:11px; opacity:.82; margin-top:2px; }

/* 탭 */
.stTabs [data-baseweb="tab-list"] {
    gap:0; background:#fff; border-bottom:2px solid #e2e8f0;
    position:sticky; top:0; z-index:100; box-shadow:0 1px 4px rgba(0,0,0,.07);
}
.stTabs [data-baseweb="tab"] {
    flex:1; padding:10px 2px; font-size:11px; font-weight:700;
    color:#94a3b8; border-bottom:3px solid transparent; white-space:nowrap;
}
.stTabs [aria-selected="true"] { color:#6366f1; border-bottom-color:#6366f1; background:#f8f7ff; }
.stTabs [data-baseweb="tab-panel"] { padding:12px 0 0 0; }

/* 섹션 헤더 */
.sec { font-size:13px; font-weight:800; color:#374151;
       margin:14px 0 8px; padding-bottom:5px; border-bottom:1.5px solid #e5e7eb; }

/* 카드 */
.card { background:#fff; border-radius:14px; padding:12px 14px;
        margin-bottom:8px; box-shadow:0 1px 4px rgba(0,0,0,.07); }
.s-name  { font-size:15px; font-weight:800; color:#1e293b; }
.s-class { font-size:12px; color:#64748b; margin-top:1px; }
.s-note  { font-size:11px; color:#94a3b8; margin-top:1px; }

/* 상태 배지 */
.badge { display:inline-block; padding:3px 10px; border-radius:20px;
         font-size:11px; font-weight:700; }
.b-ok  { background:#dcfce7; color:#16a34a; }
.b-ng  { background:#fee2e2; color:#dc2626; }
.b-no  { background:#f1f5f9; color:#94a3b8; }

/* 메트릭 */
.mrow  { display:flex; gap:6px; margin:8px 0; }
.mcard { flex:1; background:#fff; border-radius:12px; padding:10px 4px;
         text-align:center; box-shadow:0 1px 3px rgba(0,0,0,.07); }
.mval  { font-size:19px; font-weight:800; }
.mlbl  { font-size:10px; color:#64748b; margin-top:1px; }

/* 달력 */
.cal-hdr  { text-align:center; font-size:15px; font-weight:800; padding:6px 0; }
.cal-day  { text-align:center; font-size:11px; color:#64748b; padding:2px 0; }
.cal-sel  { color:#6366f1; font-weight:800; }

/* 버튼 */
.stButton>button {
    border-radius:12px!important; font-weight:700!important;
    min-height:46px!important; font-size:13px!important;
}
.stButton>button[kind="primary"] {
    background:linear-gradient(135deg,#6366f1,#8b5cf6)!important;
    border:none!important; color:#fff!important;
}

/* 인풋 */
.stTextInput input,.stDateInput input {
    border-radius:10px!important; min-height:44px!important; font-size:14px!important;
}
.stSelectbox>div>div { border-radius:10px!important; min-height:44px!important; font-size:13px!important; }
.stTextArea textarea { font-size:13px!important; border-radius:12px!important; }

/* 달력 버튼 (작게) */
[data-testid="stHorizontalBlock"] .stButton>button {
    padding:2px 0!important; min-height:36px!important; font-size:12px!important;
    border-radius:8px!important;
}
hr { margin:12px 0!important; border-color:#e5e7eb!important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  시트 상수
# ─────────────────────────────────────────────────────────────────────────────
SHEET_STU  = "원생목록"
SHEET_SCH  = "수업일정"
SHEET_ATT  = "출석기록"
SHEET_PRO  = "진도현황"

COLS_STU  = ['이름', '수업', '생년월일', '등록일', '탈회일', '메모']
COLS_SCH  = ['이름', '날짜']
COLS_ATT  = ['날짜', '이름', '상태', '대체일자', '환불예정', '메모']
COLS_PRO  = ['이름', '프로젝트', '진행단계', '사진1', '사진2', '사진3', '사진4', '사진5', '최종수정일']


# ─────────────────────────────────────────────────────────────────────────────
#  Google Sheets 헬퍼 (gspread 직접 사용)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def _gc():
    """gspread 클라이언트 (앱 수명 동안 1회 생성)"""
    import gspread
    from google.oauth2.service_account import Credentials
    creds_dict = dict(st.secrets["connections"]["gsheets"]["credentials"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=[
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ])
    return gspread.authorize(creds)


@st.cache_resource
def _spreadsheet():
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    return _gc().open_by_url(url)


def _fetch_sheet(sheet: str, cols: list) -> pd.DataFrame:
    """Google Sheets에서 직접 읽기 (네트워크 통신 발생)"""
    try:
        ws = _spreadsheet().worksheet(sheet)
        data = ws.get_all_records(default_blank='')
        if not data:
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame(data).fillna('').astype(str)
        for c in cols:
            if c not in df.columns:
                df[c] = ''
        return df[cols]
    except Exception as e:
        st.warning(f"읽기 오류 [{sheet}]: {e}")
        return pd.DataFrame(columns=cols)


def safe_read(sheet: str, cols: list) -> pd.DataFrame:
    """세션 캐시에서 읽기 – 저장 시에만 Google Sheets 통신"""
    key = f'_cache_{sheet}'
    if key not in st.session_state:
        st.session_state[key] = _fetch_sheet(sheet, cols)
    return st.session_state[key]


def safe_write(df: pd.DataFrame, sheet: str) -> bool:
    try:
        ws = _spreadsheet().worksheet(sheet)
        ws.clear()
        ws.update('A1', [df.columns.tolist()] + df.fillna('').astype(str).values.tolist())
        st.session_state.pop(f'_cache_{sheet}', None)  # 해당 시트 캐시 무효화
        return True
    except Exception as e:
        st.error(f"저장 오류: {e}")
        return False


def gs_ok() -> bool:
    try:
        _ = st.secrets["connections"]["gsheets"]["credentials"]
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  유틸
# ─────────────────────────────────────────────────────────────────────────────
def compress_image(img_bytes: bytes) -> str:
    if HAS_PIL:
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        img.thumbnail((240, 240), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=35, optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    return base64.b64encode(img_bytes).decode()


def active_students(df_stu: pd.DataFrame) -> pd.DataFrame:
    return df_stu[df_stu['탈회일'].str.strip() == ''].reset_index(drop=True)


def today_str() -> str:
    return datetime.date.today().strftime('%Y-%m-%d')


def make_months() -> list:
    t = datetime.date.today().replace(day=1)
    out = []
    for i in range(-2, 4):
        m = t.month + i
        y = t.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        mk = f"{y:04d}-{m:02d}"
        if mk not in out:
            out.append(mk)
    return sorted(out)


MONTH_OPTS = make_months()
CUR_MK     = datetime.date.today().strftime('%Y-%m')
CUR_IDX    = MONTH_OPTS.index(CUR_MK) if CUR_MK in MONTH_OPTS else 0
ml = lambda mk: f"{mk[:4]}년 {int(mk[5:])}월"


# ─────────────────────────────────────────────────────────────────────────────
#  앱 헤더
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="app-hdr">
  <div style="font-size:26px">🎨</div>
  <div>
    <div class="app-hdr-title">아트앤하트 출석부</div>
    <div class="app-hdr-sub">{datetime.date.today().strftime('%Y년 %m월 %d일')}</div>
  </div>
</div>
""", unsafe_allow_html=True)

if not gs_ok():
    st.error("""
**Google Sheets 연결 설정이 필요합니다.**

`.streamlit/secrets.toml` 또는 Streamlit Cloud **Settings → Secrets** 에 입력:

```toml
[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/YOUR_ID/edit"
type = "st_gsheets_connection.GsheetsConnection"

[connections.gsheets.credentials]
type = "service_account"
...
```
""")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  비밀번호 인증 (하루 1회)
# ─────────────────────────────────────────────────────────────────────────────
def _is_authenticated() -> bool:
    today = datetime.date.today().isoformat()
    return (st.session_state.get('auth_ok') is True and
            st.session_state.get('auth_date') == today)

if not _is_authenticated():
    st.markdown("""
    <div style="max-width:320px;margin:60px auto 0;text-align:center">
      <div style="font-size:48px;margin-bottom:12px">🔒</div>
      <div style="font-size:18px;font-weight:800;color:#1e293b;margin-bottom:6px">
        아트앤하트 출석부
      </div>
      <div style="font-size:13px;color:#64748b;margin-bottom:28px">
        비밀번호를 입력해주세요
      </div>
    </div>
    """, unsafe_allow_html=True)

    pw_input = st.text_input("비밀번호", type="password",
                             placeholder="비밀번호 6자리 입력")
    if st.button("입장", type="primary", use_container_width=True):
        correct = st.secrets.get("app_password", "")
        if pw_input == correct:
            st.session_state['auth_ok']   = True
            st.session_state['auth_date'] = datetime.date.today().isoformat()
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  세션 상태 초기화
# ─────────────────────────────────────────────────────────────────────────────
_ss_defaults = {
    'att_date':         datetime.date.today(),
    'att_open':         None,   # 펼친 원생 이름
    'att_records':      {},     # {이름: {상태,대체일자,환불예정}}
    'prev_att_date':    '',
    'mgmt_open':        None,
    'show_add':         False,
    'prog_filter':      '오늘 원생',
    'prog_course':      None,
    'prog_open':        None,
}
for k, v in _ss_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
#  달력 컴포넌트 (원생관리 수업일정 선택용)
# ─────────────────────────────────────────────────────────────────────────────
def render_schedule_calendar(name: str, df_sched: pd.DataFrame):
    """날짜 다중 선택 달력 – 선택 날짜 = 계획일수"""
    sched_key  = f"sched_{name}"
    loaded_key = f"sched_loaded_{name}"
    y_key = f"cal_y_{name}"
    m_key = f"cal_m_{name}"

    if not st.session_state.get(loaded_key):
        dates = set(df_sched[df_sched['이름'] == name]['날짜'].tolist())
        st.session_state[sched_key]  = dates
        st.session_state[loaded_key] = True

    if y_key not in st.session_state:
        st.session_state[y_key] = datetime.date.today().year
    if m_key not in st.session_state:
        st.session_state[m_key] = datetime.date.today().month

    year  = st.session_state[y_key]
    month = st.session_state[m_key]

    # ── 월 이동 ──
    c1, c2, c3 = st.columns([1, 2.5, 1])
    with c1:
        if st.button("◀", key=f"prev_{name}"):
            if month == 1:
                st.session_state[y_key] -= 1; st.session_state[m_key] = 12
            else:
                st.session_state[m_key] -= 1
            st.rerun()
    with c2:
        st.markdown(f"<div class='cal-hdr'>{year}년 {month}월</div>", unsafe_allow_html=True)
    with c3:
        if st.button("▶", key=f"next_{name}"):
            if month == 12:
                st.session_state[y_key] += 1; st.session_state[m_key] = 1
            else:
                st.session_state[m_key] += 1
            st.rerun()

    # ── 요일 헤더 ──
    hdr = st.columns(7)
    for i, d in enumerate(['일', '월', '화', '수', '목', '금', '토']):
        color = '#dc2626' if i == 0 else '#2563eb' if i == 6 else '#64748b'
        hdr[i].markdown(f"<div class='cal-day' style='color:{color}'>{d}</div>",
                        unsafe_allow_html=True)

    # ── 날짜 버튼 ──
    selected = st.session_state[sched_key]
    for week in cal_mod.monthcalendar(year, month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                ds = f"{year:04d}-{month:02d}-{day:02d}"
                is_sel = ds in selected
                btn_type = "primary" if is_sel else "secondary"
                if cols[i].button(str(day), key=f"day_{name}_{ds}",
                                  type=btn_type, use_container_width=True):
                    if is_sel:
                        selected.discard(ds)
                    else:
                        selected.add(ds)
                    st.session_state[sched_key] = selected
                    st.rerun()

    # ── 이달/전체 선택 현황 ──
    this_month = f"{year:04d}-{month:02d}"
    m_cnt = sum(1 for d in selected if d.startswith(this_month))
    t_cnt = len(selected)
    st.caption(f"이번 달 선택 **{m_cnt}일** / 전체 선택 **{t_cnt}일** (= 계획일수)")

    return selected


# ═══════════════════════════════════════════════════════════════════════════
#  탭 구성
# ═══════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["✅ 출석체크", "👥 원생관리", "📋 출석기록", "📖 진도현황"])


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 1 | 출석체크
# ═══════════════════════════════════════════════════════════════════════════
with tab1:
    # ── 날짜 선택 (미래 불가) ──
    sel_date = st.date_input(
        "날짜", value=st.session_state['att_date'],
        max_value=datetime.date.today(), key='att_date_input',
    )
    st.session_state['att_date'] = sel_date
    ds = sel_date.strftime('%Y-%m-%d')

    # ── 날짜 바뀌면 기존 기록 로드 ──
    if st.session_state['prev_att_date'] != ds:
        df_att_init = safe_read(SHEET_ATT, COLS_ATT)
        rows_today  = df_att_init[df_att_init['날짜'] == ds]
        recs = {}
        for _, r in rows_today.iterrows():
            recs[r['이름']] = {
                '상태':    r['상태'],
                '대체일자': r['대체일자'],
                '환불예정': r['환불예정'],
                '메모':    r['메모'],
            }
        st.session_state['att_records']  = recs
        st.session_state['prev_att_date'] = ds
        st.session_state['att_open']      = None

    att_records = st.session_state['att_records']

    # ── 오늘 대상자 (수업일정 기준) ──
    df_sch  = safe_read(SHEET_SCH, COLS_SCH)
    df_stu  = safe_read(SHEET_STU, COLS_STU)
    actv    = active_students(df_stu)

    sched_names = set(df_sch[df_sch['날짜'] == ds]['이름'].tolist())
    targets = actv[actv['이름'].isin(sched_names)].reset_index(drop=True)

    if targets.empty:
        st.info(f"**{ds}** 수업 대상자가 없습니다.\n원생관리 탭에서 수업 일정을 설정해주세요.")
    else:
        # ── 전체 출석 ──
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ 전체 출석", use_container_width=True, key="all_ok"):
                for _, s in targets.iterrows():
                    att_records[s['이름']] = {'상태': '출석', '대체일자': '', '환불예정': '', '메모': ''}
                st.session_state['att_records'] = att_records
                st.rerun()
        with c2:
            checked_names = [n for n in targets['이름']
                             if st.session_state.get(f"chk_{n}", False)]
            if st.button(f"선택 출석 ({len(checked_names)}명)", use_container_width=True,
                         key="sel_ok", disabled=not checked_names):
                for n in checked_names:
                    att_records[n] = {'상태': '출석', '대체일자': '', '환불예정': '', '메모': ''}
                st.session_state['att_records'] = att_records
                st.rerun()

        st.markdown(f"<div class='sec'>출석 대상 ({len(targets)}명)</div>",
                    unsafe_allow_html=True)

        for _, s in targets.iterrows():
            name = s['이름']
            cls  = s['수업']
            rec  = att_records.get(name, {})
            stat = rec.get('상태', '미처리')
            is_open = st.session_state['att_open'] == name

            badge_cls = {'출석': 'b-ok', '결석': 'b-ng', '미처리': 'b-no'}.get(stat, 'b-no')
            stat_label = {'출석': '✅ 출석', '결석': '❌ 결석', '미처리': '⬜ 미처리'}.get(stat, stat)

            # ── 행: 체크박스 | 이름버튼 | 상태 ──
            c1, c2, c3 = st.columns([0.7, 3, 1.5])
            with c1:
                st.checkbox("선택", key=f"chk_{name}", label_visibility="collapsed")
            with c2:
                btn_label = f"**{name}**  {cls}"
                if st.button(btn_label, key=f"open_{name}", use_container_width=True):
                    st.session_state['att_open'] = None if is_open else name
                    st.rerun()
            with c3:
                st.markdown(f"<div class='badge {badge_cls}' style='margin-top:8px'>{stat_label}</div>",
                            unsafe_allow_html=True)

            # ── 펼쳐진 상세 ──
            if is_open:
                with st.container():
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✅ 출석", key=f"pr_{name}", type="primary",
                                     use_container_width=True):
                            att_records[name] = {'상태': '출석', '대체일자': '',
                                                 '환불예정': '', '메모': ''}
                            st.session_state['att_records'] = att_records
                            st.session_state['att_open'] = None
                            st.rerun()
                    with col_b:
                        if st.button("❌ 결석", key=f"ab_{name}", use_container_width=True):
                            att_records[name] = {'상태': '결석', '대체일자': '',
                                                 '환불예정': '', '메모': ''}
                            st.session_state['att_records'] = att_records
                            st.rerun()

                    if stat == '결석':
                        makeup_val = rec.get('대체일자', '')
                        try:
                            mv = datetime.date.fromisoformat(makeup_val) if makeup_val else None
                        except ValueError:
                            mv = None
                        makeup = st.date_input("대체일자 (선택)", value=mv,
                                               key=f"mkup_{name}")
                        refund = st.checkbox("환불예정",
                                             value=(rec.get('환불예정') == '예'),
                                             key=f"rfnd_{name}")
                        att_records[name]['대체일자']  = str(makeup) if makeup else ''
                        att_records[name]['환불예정'] = '예' if refund else ''
                        st.session_state['att_records'] = att_records

            st.divider()

        # ── 저장 ──
        has_data = bool(att_records)
        if st.button("💾 저장", type="primary", use_container_width=True,
                     key="att_save", disabled=not has_data):
            df_att2 = safe_read(SHEET_ATT, COLS_ATT)
            for name, rec in att_records.items():
                s_row = actv[actv['이름'] == name]
                cls   = s_row.iloc[0]['수업'] if not s_row.empty else ''
                mask  = (df_att2['날짜'] == ds) & (df_att2['이름'] == name)
                row_d = {'날짜': ds, '이름': name, '상태': rec['상태'],
                         '대체일자': rec.get('대체일자', ''),
                         '환불예정': rec.get('환불예정', ''),
                         '메모': rec.get('메모', '')}
                if mask.any():
                    for col, val in row_d.items():
                        df_att2.loc[mask, col] = val
                else:
                    df_att2 = pd.concat([df_att2, pd.DataFrame([row_d])], ignore_index=True)
            if safe_write(df_att2, SHEET_ATT):
                st.success("✅ 저장 완료!")
                st.session_state['att_records']  = {}
                st.session_state['prev_att_date'] = ''
                st.rerun()

        # ── 요약 ──
        n_ok  = sum(1 for v in att_records.values() if v.get('상태') == '출석')
        n_ng  = sum(1 for v in att_records.values() if v.get('상태') == '결석')
        n_no  = len(targets) - n_ok - n_ng
        st.markdown(f"""
        <div class="mrow">
          <div class="mcard"><div class="mval" style="color:#16a34a">{n_ok}</div><div class="mlbl">출석</div></div>
          <div class="mcard"><div class="mval" style="color:#dc2626">{n_ng}</div><div class="mlbl">결석</div></div>
          <div class="mcard"><div class="mval" style="color:#94a3b8">{n_no}</div><div class="mlbl">미처리</div></div>
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 2 | 원생관리
# ═══════════════════════════════════════════════════════════════════════════
with tab2:
    df_stu2  = safe_read(SHEET_STU, COLS_STU)
    df_sch2  = safe_read(SHEET_SCH, COLS_SCH)
    actv2    = active_students(df_stu2)
    courses2 = sorted(actv2['수업'].dropna().unique().tolist())

    # ── 원생 추가 ──
    if st.session_state['show_add']:
        st.markdown("**+ 신규 원생 추가**")
        c1, c2 = st.columns(2)
        with c1:
            a_name  = st.text_input("이름 *", key="a_name", placeholder="홍길동")
        with c2:
            a_birth = st.text_input("생년월일", key="a_birth", placeholder="YYYY.MM.DD")
        a_class = st.text_input("수업", key="a_class", placeholder="예: 초급반")
        a_note  = st.text_input("메모", key="a_note", placeholder="특이사항")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("추가", type="primary", key="do_add"):
                if a_name.strip():
                    new_row = pd.DataFrame([{
                        '이름': a_name.strip(), '수업': a_class.strip(),
                        '생년월일': a_birth.strip(),
                        '등록일': datetime.date.today().strftime('%Y.%m.%d'),
                        '탈회일': '', '메모': a_note.strip(),
                    }])
                    df_stu2 = pd.concat([df_stu2, new_row], ignore_index=True)
                    if safe_write(df_stu2, SHEET_STU):
                        st.session_state['show_add'] = False
                        st.success(f"'{a_name}' 추가 완료!")
                        st.rerun()
                else:
                    st.error("이름을 입력해주세요.")
        with c2:
            if st.button("취소", key="cancel_add"):
                st.session_state['show_add'] = False
                st.rerun()
        st.divider()
    else:
        if st.button("+ 원생 추가", type="primary", use_container_width=True, key="show_add_btn"):
            st.session_state['show_add'] = True
            st.rerun()

    st.markdown(f"<div class='sec'>원생 ({len(actv2)}명)</div>", unsafe_allow_html=True)

    # 일정 없는 원생 먼저, 일정 있는 원생 아래로
    names_with_sched2 = set(df_sch2['이름'].tolist())
    no_sched2  = actv2[~actv2['이름'].isin(names_with_sched2)]
    has_sched2 = actv2[actv2['이름'].isin(names_with_sched2)]
    actv2_sorted = pd.concat([no_sched2, has_sched2], ignore_index=True)

    for _, s in actv2_sorted.iterrows():
        name    = s['이름']
        cls     = s['수업']
        is_open = st.session_state['mgmt_open'] == name
        has_schedule = name in names_with_sched2

        c1, c2 = st.columns([4, 1])
        with c1:
            note_line = f'<div class="s-note">{s["메모"]}</div>' if s['메모'] else ''
            st.markdown(f"""
            <div class="card" style="margin-bottom:4px">
                <div class="s-name">{name}</div>
                <div class="s-class">{cls or '수업 미정'}</div>
                {note_line}
            </div>""", unsafe_allow_html=True)
        with c2:
            btn_lbl = "닫기" if is_open else ("수정" if has_schedule else "일정")
            if st.button(btn_lbl, key=f"mgmt_{name}"):
                st.session_state['mgmt_open'] = None if is_open else name
                st.rerun()

        if is_open:
            with st.container():
                # 이름 수정 (expander 대신 버튼 토글)
                edit_key = f"edit_open_{name}"
                if st.button("✏️ 정보 수정 열기" if not st.session_state.get(edit_key) else "정보 수정 닫기",
                             key=f"edit_toggle_{name}", use_container_width=True):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                    st.rerun()

                if st.session_state.get(edit_key):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        e_name  = st.text_input("이름", value=name, key=f"en_{name}")
                    with ec2:
                        e_birth = st.text_input("생년월일", value=s['생년월일'],
                                                key=f"eb_{name}", placeholder="YYYY.MM.DD")
                    e_class = st.text_input("수업", value=cls, key=f"ec_{name}")
                    e_note  = st.text_input("메모", value=s['메모'], key=f"eno_{name}")
                    if st.button("정보 저장", key=f"info_save_{name}", type="primary"):
                        idx = df_stu2.index[df_stu2['이름'] == name].tolist()
                        if idx:
                            df_stu2.at[idx[0], '이름']    = e_name.strip()
                            df_stu2.at[idx[0], '수업']    = e_class.strip()
                            df_stu2.at[idx[0], '생년월일'] = e_birth.strip()
                            df_stu2.at[idx[0], '메모']    = e_note.strip()
                            if safe_write(df_stu2, SHEET_STU):
                                st.session_state['mgmt_open'] = None
                                st.session_state[edit_key] = False
                                st.success("저장 완료!")
                                st.rerun()

                # 수업 일정 달력
                st.markdown("<div class='sec'>수업 일정 선택</div>", unsafe_allow_html=True)
                selected_dates = render_schedule_calendar(name, df_sch2)

                if st.button("📅 스케줄 저장", key=f"sched_save_{name}", type="primary",
                             use_container_width=True):
                    df_sch2 = df_sch2[df_sch2['이름'] != name]
                    new_rows = pd.DataFrame([{'이름': name, '날짜': d}
                                             for d in sorted(selected_dates)])
                    df_sch2 = pd.concat([df_sch2, new_rows], ignore_index=True)
                    if safe_write(df_sch2, SHEET_SCH):
                        st.success(f"스케줄 저장 완료! ({len(selected_dates)}일)")
                        st.rerun()

                st.divider()

                # 탈회
                if st.button("⚠️ 탈회 처리", key=f"leave_{name}", use_container_width=True):
                    today_fmt = datetime.date.today().strftime('%Y.%m.%d')
                    idx = df_stu2.index[df_stu2['이름'] == name].tolist()
                    if idx:
                        df_stu2.at[idx[0], '탈회일'] = today_fmt
                        if safe_write(df_stu2, SHEET_STU):
                            st.session_state['mgmt_open'] = None
                            st.warning(f"'{name}' 탈회 처리 ({today_fmt})")
                            st.rerun()

        st.divider()


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 3 | 출석기록
# ═══════════════════════════════════════════════════════════════════════════
with tab3:
    sel_mk3 = st.selectbox("월 선택", MONTH_OPTS, index=CUR_IDX,
                           format_func=ml, key='mk_t3')

    df_stu3  = safe_read(SHEET_STU, COLS_STU)
    df_sch3  = safe_read(SHEET_SCH, COLS_SCH)
    df_att3  = safe_read(SHEET_ATT, COLS_ATT)
    actv3    = active_students(df_stu3)

    month_att3 = df_att3[df_att3['날짜'].str.startswith(sel_mk3)]
    month_sch3 = df_sch3[df_sch3['날짜'].str.startswith(sel_mk3)]

    if actv3.empty:
        st.info("등록된 원생이 없습니다.")
    else:
        st.markdown("<div class='sec'>월별 출석 요약</div>", unsafe_allow_html=True)
        tot_plan = tot_ok = tot_ng = tot_ab = 0

        for _, s in actv3.iterrows():
            name = s['이름']
            plan = len(month_sch3[month_sch3['이름'] == name])
            s_att = month_att3[month_att3['이름'] == name]
            n_ok  = len(s_att[s_att['상태'] == '출석'])
            n_ng  = len(s_att[s_att['상태'] == '결석'])
            n_ab  = max(0, plan - n_ok)
            tot_plan += plan; tot_ok += n_ok; tot_ng += n_ng; tot_ab += max(0, plan - n_ok)

            st.markdown(f"""
            <div class="card" style="margin-bottom:8px">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                <div class="s-name">{name}</div>
                <div class="s-class">{s['수업']}</div>
              </div>
              <div class="mrow" style="margin:0">
                <div class="mcard"><div class="mval" style="font-size:15px;color:#6366f1">{plan}</div><div class="mlbl">계획</div></div>
                <div class="mcard"><div class="mval" style="font-size:15px;color:#16a34a">{n_ok}</div><div class="mlbl">출석</div></div>
                <div class="mcard"><div class="mval" style="font-size:15px;color:#dc2626">{n_ng}</div><div class="mlbl">결석</div></div>
                <div class="mcard"><div class="mval" style="font-size:15px;color:#f59e0b">{n_ab}</div><div class="mlbl">불참</div></div>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:#f0f0ff;border-radius:12px;padding:12px 14px;margin-top:4px">
          <div style="font-size:12px;font-weight:800;color:#6366f1;margin-bottom:6px">전체 합계 ({len(actv3)}명)</div>
          <div class="mrow" style="margin:0">
            <div class="mcard"><div class="mval" style="font-size:15px;color:#6366f1">{tot_plan}</div><div class="mlbl">계획</div></div>
            <div class="mcard"><div class="mval" style="font-size:15px;color:#16a34a">{tot_ok}</div><div class="mlbl">출석</div></div>
            <div class="mcard"><div class="mval" style="font-size:15px;color:#dc2626">{tot_ng}</div><div class="mlbl">결석</div></div>
            <div class="mcard"><div class="mval" style="font-size:15px;color:#f59e0b">{tot_ab}</div><div class="mlbl">불참</div></div>
          </div>
        </div>""", unsafe_allow_html=True)

        st.caption("💡 계획일수 = 원생관리에서 선택한 수업 날짜 수 / 불참 = 계획 − 출석")

        with st.expander("📄 상세 기록"):
            if month_att3.empty:
                st.caption("기록이 없습니다.")
            else:
                ICN = {'출석': '🟢', '결석': '🔴', '미처리': '⚪'}
                for _, r in month_att3.sort_values(['날짜', '이름']).iterrows():
                    line = f"{ICN.get(r['상태'],'⚪')} **{r['날짜']}** | {r['이름']} | **{r['상태']}**"
                    if r.get('대체일자'):
                        line += f" (대체: {r['대체일자']})"
                    if r.get('환불예정') == '예':
                        line += " 💰환불예정"
                    st.markdown(line)


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 4 | 진도현황
# ═══════════════════════════════════════════════════════════════════════════
with tab4:
    df_stu4  = safe_read(SHEET_STU, COLS_STU)
    df_sch4  = safe_read(SHEET_SCH, COLS_SCH)
    df_pro4  = safe_read(SHEET_PRO, COLS_PRO)
    actv4    = active_students(df_stu4)
    courses4 = sorted(actv4['수업'].dropna().replace('', pd.NA).dropna().unique().tolist())

    # ── 필터 버튼 ──
    fc1, fc2, fc3 = st.columns(3)
    filters = ['오늘 원생', '전체 원생', '과정별']
    for col, label in zip([fc1, fc2, fc3], filters):
        is_active = st.session_state['prog_filter'] == label
        style = "background:#6366f1;color:white;border:none;" if is_active else ""
        if col.button(label, key=f"flt_{label}",
                      type="primary" if is_active else "secondary",
                      use_container_width=True):
            st.session_state['prog_filter'] = label
            st.session_state['prog_course'] = None
            st.session_state['prog_open']   = None
            st.rerun()

    # ── 필터 적용 ──
    flt = st.session_state['prog_filter']

    if flt == '오늘 원생':
        today_names = set(df_sch4[df_sch4['날짜'] == today_str()]['이름'].tolist())
        show_stu = actv4[actv4['이름'].isin(today_names)].reset_index(drop=True)
        st.caption(f"오늘({today_str()}) 수업 대상 {len(show_stu)}명")

    elif flt == '전체 원생':
        show_stu = actv4

    else:  # 과정별
        if courses4:
            cur_course = st.session_state.get('prog_course')
            crs_cols = st.columns(min(len(courses4), 3))
            for i, crs in enumerate(courses4):
                is_sel = cur_course == crs
                if crs_cols[i % 3].button(
                    f"{'✓ ' if is_sel else ''}{crs}",
                    key=f"crs_{crs}",
                    type="primary" if is_sel else "secondary",
                    use_container_width=True,
                ):
                    st.session_state['prog_course'] = crs
                    st.session_state['prog_open']   = None
                    st.rerun()
            if cur_course:
                show_stu = actv4[actv4['수업'] == cur_course].reset_index(drop=True)
            else:
                show_stu = pd.DataFrame(columns=COLS_STU)
                st.info("과정을 선택해주세요.")
        else:
            show_stu = actv4
            st.caption("수업 정보가 없습니다. 원생관리에서 수업을 입력해주세요.")

    st.markdown(f"<div class='sec'>원생 ({len(show_stu)}명)</div>", unsafe_allow_html=True)

    for _, s in show_stu.iterrows():
        name    = s['이름']
        cls     = s['수업']
        is_open = st.session_state['prog_open'] == name

        # 진도 미리보기
        pro_row  = df_pro4[df_pro4['이름'] == name]
        cur_proj = str(pro_row.iloc[0]['프로젝트']) if not pro_row.empty else ''
        cur_stg  = str(pro_row.iloc[0]['진행단계']) if not pro_row.empty else ''
        cur_upd  = str(pro_row.iloc[0]['최종수정일']) if not pro_row.empty else ''

        c1, c2 = st.columns([4, 1])
        with c1:
            proj_preview = f'<div class="s-note">{cur_proj[:30]}{"…" if len(cur_proj)>30 else ""}</div>' if cur_proj and cur_proj != 'nan' else ''
            st.markdown(f"""
            <div class="card" style="margin-bottom:4px">
              <div class="s-name">{name}</div>
              <div class="s-class">{cls or ''} {f'· {cur_upd}' if cur_upd and cur_upd!="nan" else ''}</div>
              {proj_preview}
            </div>""", unsafe_allow_html=True)
        with c2:
            if st.button("닫기" if is_open else "편집", key=f"pro_{name}"):
                st.session_state['prog_open'] = None if is_open else name
                # 사진 초기화 (첫 오픈 시)
                if not is_open:
                    photos_key = f"photos_{name}"
                    if photos_key not in st.session_state:
                        photos = []
                        if not pro_row.empty:
                            for i in range(1, 6):
                                v = str(pro_row.iloc[0].get(f'사진{i}', ''))
                                if v and v not in ('', 'nan', 'None'):
                                    photos.append(v)
                        st.session_state[photos_key] = photos
                st.rerun()

        if is_open:
            with st.container():
                # ── 텍스트 입력 ──
                init_proj = '' if (not cur_proj or cur_proj == 'nan') else cur_proj
                init_stg  = '' if (not cur_stg  or cur_stg  == 'nan') else cur_stg

                new_proj = st.text_input(
                    "현재 프로젝트",
                    value=init_proj,
                    placeholder="예: 수채화 정물화",
                    key=f"proj_{name}",
                )
                new_stg = st.text_area(
                    "진행 단계",
                    value=init_stg,
                    placeholder="예: 밑그림 완료, 채색 50% 진행 중\n다음 목표: 배경 채색",
                    key=f"stg_{name}",
                    height=120,
                )

                # ── 사진 ──
                st.markdown("<div class='sec'>사진</div>", unsafe_allow_html=True)
                photos_key  = f"photos_{name}"
                cam_idx_key = f"cam_idx_{name}"
                if cam_idx_key not in st.session_state:
                    st.session_state[cam_idx_key] = 0

                # 기존 사진 썸네일
                photos_list = st.session_state.get(photos_key, [])
                if photos_list:
                    n_cols = min(len(photos_list), 3)
                    p_cols = st.columns(n_cols)
                    to_del = None
                    for j, p_b64 in enumerate(photos_list):
                        with p_cols[j % n_cols]:
                            try:
                                st.image(base64.b64decode(p_b64), use_container_width=True)
                            except Exception:
                                st.caption(f"사진 {j+1}")
                            if st.button("🗑 삭제", key=f"delpho_{name}_{j}"):
                                to_del = j
                    if to_del is not None:
                        photos_list.pop(to_del)
                        st.session_state[photos_key] = photos_list
                        st.rerun()

                # 카메라 (버튼 누를 때만 노출)
                cam_open_key = f"cam_open_{name}"
                if st.session_state.get(cam_open_key):
                    cam_photo = st.camera_input(
                        "촬영 후 자동 추가됩니다",
                        key=f"cam_{name}_{st.session_state[cam_idx_key]}",
                    )
                    if cam_photo is not None:
                        compressed = compress_image(cam_photo.getvalue())
                        st.session_state[photos_key].append(compressed)
                        st.session_state[cam_idx_key] += 1
                        st.session_state[cam_open_key] = False
                        st.rerun()
                    if st.button("카메라 닫기", key=f"cam_close_{name}"):
                        st.session_state[cam_open_key] = False
                        st.rerun()
                else:
                    if st.button("📷 사진 촬영", key=f"cam_btn_{name}",
                                 use_container_width=True):
                        st.session_state[cam_open_key] = True
                        st.rerun()

                st.caption(f"현재 {len(photos_list)}장")

                # ── 저장 ──
                if st.button("💾 저장", type="primary", use_container_width=True,
                             key=f"pro_save_{name}"):
                    today_iso = datetime.date.today().strftime('%Y-%m-%d')
                    photo_vals = {f'사진{i+1}': (photos_list[i] if i < len(photos_list) else '')
                                  for i in range(5)}
                    new_data = {
                        '이름': name, '프로젝트': new_proj, '진행단계': new_stg,
                        **photo_vals, '최종수정일': today_iso,
                    }
                    if pro_row.empty:
                        df_pro4 = pd.concat([df_pro4, pd.DataFrame([new_data])], ignore_index=True)
                    else:
                        for col, val in new_data.items():
                            df_pro4.loc[df_pro4['이름'] == name, col] = val

                    if safe_write(df_pro4, SHEET_PRO):
                        st.success("✅ 저장 완료!")
                        st.session_state['prog_open'] = None
                        st.rerun()

        st.divider()
