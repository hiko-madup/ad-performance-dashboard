import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import glob
import re

st.set_page_config(page_title="Ad Performance", layout="wide", initial_sidebar_state="collapsed")

# ── Design tokens ──────────────────────────────────────────────────────────────
C = {
    "google":  "#4285F4",
    "meta":    "#0082FB",
    "naver":   "#03C75A",
    "accent":  "#2563eb",
    "muted":   "#94a3b8",
    "text":    "#0f172a",
    "sub":     "#64748b",
    "border":  "rgba(0,0,0,0.06)",
    "grid":    "#f1f5f9",
}
CH_COLOR = {"구글": C["google"], "네이버": C["naver"], "메타": C["meta"]}
PALETTE  = ["#2563eb","#0891b2","#059669","#d97706","#7c3aed","#db2777"]
FONT     = "Plus Jakarta Sans"
MONO     = "JetBrains Mono"
PURPOSE_COLORS = {
    "첫구매":    "#2563eb",
    "재구매":    "#0891b2",
    "리타겟팅":  "#059669",
    "플러스가입":"#d97706",
    "신규유저":  "#7c3aed",
    "룩얼라이크":"#db2777",
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html,body,[class*="css"] { font-family:'Plus Jakarta Sans',sans-serif !important; }
p,div,label,input,textarea,a,h1,h2,h3,h4,h5,h6,li,td,th { font-family:'Plus Jakarta Sans',sans-serif !important; }
#MainMenu,footer,.stDeployButton { display:none !important; }
header[data-testid="stHeader"] { display:none !important; }
.stApp,[data-testid="stAppViewContainer"] { background:#f8fafc !important; }
[data-testid="block-container"] { padding:2.5rem 3rem 4rem !important; max-width:1440px !important; }
[data-testid="stSidebar"] { display:none !important; }
[data-testid="stSidebarCollapsedControl"] { display:none !important; }
.stButton>button { background:#0f172a !important; color:#f8fafc !important; border:none !important;
  border-radius:999px !important; font-weight:500 !important; font-size:0.8125rem !important;
  padding:0.5rem 1.25rem !important; transition:all .25s cubic-bezier(.32,.72,0,1) !important; }
.stButton>button:hover { background:#1e293b !important; transform:translateY(-1px) !important; }
.stButton>button:active { transform:scale(.97) !important; }
[data-testid="stRadio"] label { font-size:.875rem !important; }
hr { border-color:#e2e8f0 !important; margin:1.5rem 0 !important; }
/* 탭 스타일 */
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:.25rem !important; border-bottom:2px solid #e2e8f0 !important; background:transparent !important; }
[data-testid="stTabs"] [data-baseweb="tab"] { font-size:.8125rem !important; font-weight:500 !important;
  color:#64748b !important; padding:.5rem 1.25rem !important; border-radius:.5rem .5rem 0 0 !important; background:transparent !important; }
[data-testid="stTabs"] [aria-selected="true"] { color:#2563eb !important; font-weight:600 !important; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background:#2563eb !important; height:2px !important; }
</style>
""", unsafe_allow_html=True)

# ── Data ───────────────────────────────────────────────────────────────────────
DATA_DIR    = Path(__file__).parent / "data"
CHANNEL_DIR = DATA_DIR / "channel"
AF_DIR      = DATA_DIR / "appsflyer"
JOIN_KEYS   = ["일", "캠페인", "그룹", "소재"]
CH_MAP      = {"구글":"googleadwords_int","메타":"Facebook Ads","네이버":"naver_search"}

@st.cache_data(ttl=60)
def load_data():
    ch_files = sorted(glob.glob(str(CHANNEL_DIR / "*_channel.csv")))
    af_files = sorted(glob.glob(str(AF_DIR / "*_appsflyer.csv")))
    ch = pd.concat([pd.read_csv(f) for f in ch_files], ignore_index=True) if ch_files else pd.DataFrame()
    af = pd.concat([pd.read_csv(f) for f in af_files], ignore_index=True) if af_files else pd.DataFrame()
    if ch.empty or af.empty:
        return pd.DataFrame()
    ch["미디어소스"] = ch["채널"].map(CH_MAP)
    af = af.rename(columns={"클릭":"AF클릭","회원가입":"AF회원가입","구매":"AF구매","구매매출":"AF구매매출"})
    df = ch.merge(af[JOIN_KEYS+["미디어소스","AF클릭","AF회원가입","AF구매","AF구매매출"]],
                  on=JOIN_KEYS+["미디어소스"], how="left")
    df["일"] = pd.to_datetime(df["일"])
    df["월"] = df["일"].dt.to_period("M")

    def parse_creative(name):
        parts = str(name).split("_")
        fmt = parts[0] if parts else ""
        ab  = next((p for p in parts if p in ("A","B")), None)
        ver = next((p for p in parts if re.match(r"v\d+$", p)), None)
        return pd.Series({"소재포맷": fmt, "AB": ab, "버전": ver})

    df[["소재포맷","AB","버전"]] = df["소재"].apply(parse_creative)

    # KPI (CLAUDE.md: 비용=채널, 전환=AF)
    df["ROAS"] = (df["AF구매매출"] / df["비용"] * 100).where(df["비용"] > 0)
    df["CPA"]  = (df["비용"] / df["AF구매"]).where(df["AF구매"] > 0)
    df["CTR"]  = (df["클릭"] / df["노출"] * 100).where(df["노출"] > 0)
    df["CVR"]  = (df["AF구매"] / df["클릭"] * 100).where(df["클릭"] > 0)
    df["CPR"]  = (df["비용"] / df["AF회원가입"]).where(df["AF회원가입"] > 0)

    # 숫자형 fillna
    for col in ["AF클릭","AF회원가입","AF구매","AF구매매출"]:
        df[col] = df[col].fillna(0)
    return df

df = load_data()
if df.empty:
    st.error(f"`{DATA_DIR}` 에서 CSV 파일을 찾을 수 없어요.")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.expander("⚙️  필터 · 설정", expanded=False):
    fc1, fc2, fc3, fc4 = st.columns([2, 3, 2, 1])
    with fc1:
        channels = st.multiselect("채널", sorted(df["채널"].unique()), default=sorted(df["채널"].unique()))
    with fc2:
        campaigns = st.multiselect("캠페인", sorted(df["캠페인"].unique()), default=sorted(df["캠페인"].unique()))
    with fc3:
        date_range = st.date_input("기간", value=(df["일"].min(), df["일"].max()))
    with fc4:
        st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
        st.button("새로고침", on_click=load_data.clear)

filt = df[
    df["채널"].isin(channels) &
    df["캠페인"].isin(campaigns) &
    (df["일"] >= pd.Timestamp(date_range[0])) &
    (df["일"] <= pd.Timestamp(date_range[-1]))
]

# ── UI helpers ─────────────────────────────────────────────────────────────────
def base_layout(height=300, margin=None):
    return dict(
        height=height,
        font=dict(family=FONT, color="#374151", size=11),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=margin or dict(l=8, r=8, t=36, b=8),
        showlegend=False,
    )

def section(label):
    st.markdown(
        f"""<div style="font-size:.6875rem;font-weight:600;letter-spacing:.1em;
        text-transform:uppercase;color:#94a3b8;margin:1.5rem 0 .75rem">{label}</div>""",
        unsafe_allow_html=True,
    )

def dod_card(label, now_val, prev_val, fmt_fn, invert=False, accent="#2563eb"):
    """전일 대비 변화 KPI 카드 HTML."""
    if prev_val is not None and prev_val != 0:
        pct   = (now_val - prev_val) / abs(prev_val) * 100
        good  = pct < 0 if invert else pct > 0
        arrow = "▲" if pct > 0 else "▼"
        clr   = "#16a34a" if good else "#dc2626"
        change_html = f"<span style='color:{clr};font-size:.68rem;font-weight:500'>{arrow} {abs(pct):.1f}% vs 어제</span>"
    else:
        change_html = "<span style='color:#94a3b8;font-size:.68rem'>비교 없음</span>"
    return f"""<div style="background:#fff;border-radius:1rem;padding:1.25rem 1.5rem;
      border:1px solid rgba(0,0,0,.06);box-shadow:0 4px 24px -8px rgba(0,0,0,.07)">
      <div style="font-size:.6rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
          color:#94a3b8;margin-bottom:.6rem">{label}</div>
      <div style="font-family:'{MONO}',monospace;font-size:1.6rem;font-weight:600;
          color:#0f172a;letter-spacing:-.02em;line-height:1">{fmt_fn(now_val)}</div>
      <div style="margin-top:.4rem">{change_html}</div>
      <div style="width:2rem;height:2px;background:{accent};border-radius:999px;margin-top:.75rem;opacity:.6"></div>
    </div>"""

def mom_card(label, now_val, prev_val, fmt_fn, invert=False, accent="#2563eb"):
    """전월 대비 변화 KPI 카드 HTML (월간 탭용)."""
    if prev_val is not None and prev_val != 0:
        pct   = (now_val - prev_val) / abs(prev_val) * 100
        good  = pct < 0 if invert else pct > 0
        arrow = "▲" if pct > 0 else "▼"
        clr   = "#16a34a" if good else "#dc2626"
        change_html = f"<span style='color:{clr};font-size:.68rem;font-weight:500'>{arrow} {abs(pct):.1f}% vs 전월</span>"
    else:
        change_html = "<span style='color:#94a3b8;font-size:.68rem'>전월 없음</span>"
    return f"""<div style="background:#fff;border-radius:1rem;padding:1.25rem 1.5rem;
      border:1px solid rgba(0,0,0,.06);box-shadow:0 4px 24px -8px rgba(0,0,0,.07)">
      <div style="font-size:.6rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
          color:#94a3b8;margin-bottom:.6rem">{label}</div>
      <div style="font-family:'{MONO}',monospace;font-size:1.6rem;font-weight:600;
          color:#0f172a;letter-spacing:-.02em;line-height:1">{fmt_fn(now_val)}</div>
      <div style="margin-top:.4rem">{change_html}</div>
      <div style="width:2rem;height:2px;background:{accent};border-radius:999px;margin-top:.75rem;opacity:.6"></div>
    </div>"""

# ── 전체 집계 (헤더용) ─────────────────────────────────────────────────────────
total_cost = filt["비용"].sum()
total_imp  = filt["노출"].sum()
total_clk  = filt["클릭"].sum()
total_pur  = filt["AF구매"].sum()
total_rev  = filt["AF구매매출"].sum()
roas_all   = total_rev / total_cost * 100 if total_cost > 0 else 0
cpa_all    = total_cost / total_pur       if total_pur  > 0 else 0
ctr_all    = total_clk  / total_imp * 100 if total_imp  > 0 else 0
cvr_all    = total_pur  / total_clk * 100 if total_clk  > 0 else 0
days       = (filt["일"].max() - filt["일"].min()).days + 1 if not filt.empty else 0

# ── 헤더 ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:1.5rem">
  <div style="display:inline-flex;align-items:center;gap:.5rem;background:#eff6ff;
      border:1px solid #bfdbfe;border-radius:999px;padding:.25rem .875rem;margin-bottom:.75rem">
    <span style="width:6px;height:6px;border-radius:50%;background:#2563eb;display:inline-block"></span>
    <span style="font-size:.6875rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#1d4ed8">Live Dashboard</span>
  </div>
  <h1 style="font-size:2rem;font-weight:700;color:#0f172a;letter-spacing:-.03em;margin:0;line-height:1.1">광고 성과 대시보드</h1>
  <p style="color:#64748b;font-size:.875rem;margin-top:.4rem">{', '.join(channels)} · {days}일 분석</p>
</div>
""", unsafe_allow_html=True)

# ── 전체 KPI 요약 카드 ────────────────────────────────────────────────────────
def kpi_card(label, val, sub="", acc="#2563eb"):
    return f"""<div style="background:#fff;border-radius:1.25rem;padding:1.5rem 1.75rem;
      border:1px solid {C['border']};box-shadow:0 4px 24px -8px rgba(0,0,0,.07)">
      <div style="font-size:.6875rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
          color:#94a3b8;margin-bottom:.875rem">{label}</div>
      <div style="font-family:'{MONO}',monospace;font-size:1.75rem;font-weight:600;
          color:#0f172a;letter-spacing:-.03em;line-height:1">{val}</div>
      {"<div style='font-size:.75rem;color:#94a3b8;margin-top:.375rem'>"+sub+"</div>" if sub else ""}
      <div style="width:2.5rem;height:3px;background:{acc};border-radius:999px;margin-top:1rem;opacity:.7"></div>
    </div>"""

kc1,kc2,kc3,kc4,kc5,kc6 = st.columns(6)
for col, (lbl, val, sub, acc) in zip(
    [kc1,kc2,kc3,kc4,kc5,kc6],
    [
        ("총 비용",    f"₩{total_cost/1e6:.1f}M",  f"₩{total_cost:,.0f}",    "#2563eb"),
        ("노출",      f"{total_imp/1e6:.2f}M",     f"{total_imp:,.0f}회",     "#0891b2"),
        ("클릭 · CTR", f"{total_clk:,.0f}",        f"CTR {ctr_all:.2f}%",    "#059669"),
        ("구매(AF)",  f"{total_pur:,.0f}",          f"CVR {cvr_all:.2f}%",    "#d97706"),
        ("매출(AF)",  f"₩{total_rev/1e6:.1f}M",    f"₩{total_rev:,.0f}",     "#7c3aed"),
        ("ROAS",     f"{roas_all:.0f}%",           f"CPA ₩{cpa_all:,.0f}",   "#db2777"),
    ]
):
    col.markdown(kpi_card(lbl, val, sub, acc), unsafe_allow_html=True)

st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 3 TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_daily, tab_creative, tab_monthly = st.tabs(["📊  Daily", "🎨  소재·캠페인", "📅  월간"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — DAILY
# ─────────────────────────────────────────────────────────────────────────────
with tab_daily:
    days_sorted = sorted(filt["일"].unique())
    today_df = filt[filt["일"] == days_sorted[-1]] if days_sorted else filt
    yest_df  = filt[filt["일"] == days_sorted[-2]] if len(days_sorted) >= 2 else None

    def agg(d):
        cost = d["비용"].sum()
        rev  = d["AF구매매출"].sum()
        pur  = d["AF구매"].sum()
        return dict(
            비용=cost,
            ROAS=rev / cost * 100 if cost > 0 else 0,
            구매=pur,
            CPA=cost / pur if pur > 0 else 0,
        )

    t = agg(today_df)
    y = agg(yest_df) if yest_df is not None else None

    # ① 전일 대비 변화 카드
    section("① 전일 대비 변화")
    d1, d2, d3, d4 = st.columns(4)
    d1.markdown(dod_card("비용",    t["비용"], y["비용"] if y else None, lambda v: f"₩{v/1e6:.1f}M",  accent="#2563eb"), unsafe_allow_html=True)
    d2.markdown(dod_card("ROAS",   t["ROAS"], y["ROAS"] if y else None, lambda v: f"{v:.0f}%",        accent="#7c3aed"), unsafe_allow_html=True)
    d3.markdown(dod_card("구매(AF)",t["구매"], y["구매"] if y else None, lambda v: f"{v:,.0f}",        accent="#d97706"), unsafe_allow_html=True)
    d4.markdown(dod_card("CPA",    t["CPA"],  y["CPA"]  if y else None, lambda v: f"₩{v:,.0f}", invert=True, accent="#db2777"), unsafe_allow_html=True)

    # 이상 감지 배너
    anomalies = []
    if yest_df is not None:
        for ch_name in today_df["채널"].unique():
            ch_t = today_df[today_df["채널"] == ch_name]
            ch_y = yest_df[yest_df["채널"] == ch_name]
            t_r = ch_t["AF구매매출"].sum() / ch_t["비용"].sum() * 100 if ch_t["비용"].sum() > 0 else 0
            y_r = ch_y["AF구매매출"].sum() / ch_y["비용"].sum() * 100 if ch_y["비용"].sum() > 0 else 0
            if y_r > 0 and (t_r - y_r) / y_r * 100 < -20:
                anomalies.append(f"{ch_name} ROAS 전일 대비 {(t_r-y_r)/y_r*100:.1f}% 하락")

    if not today_df.empty:
        ctr_issues  = today_df[today_df["CTR"] > 30]
        clk_issues  = today_df[today_df["클릭"] > today_df["노출"]]
        cpa_issues  = today_df[(today_df["CPA"] < 100) & today_df["CPA"].notna()]
        if not ctr_issues.empty:  anomalies.append(f"CTR > 30% 소재 {len(ctr_issues)}건")
        if not clk_issues.empty:  anomalies.append(f"클릭 > 노출 오류 {len(clk_issues)}건")
        if not cpa_issues.empty:  anomalies.append(f"CPA < 100원 소재 {len(cpa_issues)}건")

    if anomalies:
        st.markdown(
            f"""<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:.625rem;
            padding:.625rem 1rem;font-size:.75rem;color:#c2410c;margin:.75rem 0">
            ⚠&nbsp;&nbsp;{'  ·  '.join(anomalies)}</div>""",
            unsafe_allow_html=True,
        )

    # ② 채널별 오늘 성과 카드
    section("② 채널별 오늘 성과")
    ch_cols = st.columns(3)
    for i, ch_name in enumerate(["구글", "네이버", "메타"]):
        ch_t = today_df[today_df["채널"] == ch_name]
        ch_y = yest_df[yest_df["채널"] == ch_name] if yest_df is not None else None

        ch_cost = ch_t["비용"].sum()
        ch_roas = ch_t["AF구매매출"].sum() / ch_cost * 100 if ch_cost > 0 else 0
        ch_pur  = ch_t["AF구매"].sum()
        ch_cpa  = ch_cost / ch_pur if ch_pur > 0 else 0

        roas_chg, is_warn = None, False
        if ch_y is not None and ch_y["비용"].sum() > 0:
            y_roas = ch_y["AF구매매출"].sum() / ch_y["비용"].sum() * 100
            if y_roas > 0:
                roas_chg = (ch_roas - y_roas) / y_roas * 100
                is_warn  = roas_chg < -20

        border = "#fecaca" if is_warn else "rgba(0,0,0,.06)"
        badge  = ("<span style='float:right;font-size:.58rem;background:#fee2e2;color:#dc2626;"
                  "padding:.1rem .5rem;border-radius:999px;margin-top:-.1rem'>⚠ 주의</span>") if is_warn else ""
        roas_arrow = ""
        if roas_chg is not None:
            clr = "#16a34a" if roas_chg >= 0 else "#dc2626"
            sym = "▲" if roas_chg >= 0 else "▼"
            roas_arrow = f"<span style='color:{clr};font-size:.6rem;margin-left:.3rem'>{sym}{abs(roas_chg):.1f}%</span>"

        ch_cols[i].markdown(f"""
        <div style="background:#fff;border-radius:1rem;padding:1.1rem 1.25rem;
          border:1px solid {border};box-shadow:0 4px 20px -8px rgba(0,0,0,.07)">
          <div style="display:flex;align-items:center;gap:.4rem;margin-bottom:.75rem">
            <span style="width:8px;height:8px;border-radius:50%;background:{CH_COLOR.get(ch_name,'#94a3b8')};display:inline-block"></span>
            <span style="font-size:.8rem;font-weight:700;color:{CH_COLOR.get(ch_name,'#64748b')}">{ch_name}</span>
            {badge}
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem">
            <div>
              <div style="font-size:.58rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em">비용</div>
              <div style="font-family:'{MONO}',monospace;font-size:.9rem;font-weight:600;color:#0f172a">₩{ch_cost/1e6:.1f}M</div>
            </div>
            <div>
              <div style="font-size:.58rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em">ROAS{roas_arrow}</div>
              <div style="font-family:'{MONO}',monospace;font-size:.9rem;font-weight:600;color:#0f172a">{ch_roas:.0f}%</div>
            </div>
            <div>
              <div style="font-size:.58rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em">구매 (AF)</div>
              <div style="font-family:'{MONO}',monospace;font-size:.9rem;font-weight:600;color:#0f172a">{ch_pur:,.0f}</div>
            </div>
            <div>
              <div style="font-size:.58rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em">CPA</div>
              <div style="font-family:'{MONO}',monospace;font-size:.9rem;font-weight:600;color:#0f172a">₩{ch_cpa:,.0f}</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

    # ③ 채널별 전일 대비 ROAS 변화 바
    section("③ 채널별 전일 대비 ROAS 변화")
    if yest_df is not None:
        dod_rows = []
        for ch_name in sorted(filt["채널"].unique()):
            t_rev  = today_df[today_df["채널"]==ch_name]["AF구매매출"].sum()
            t_cost = today_df[today_df["채널"]==ch_name]["비용"].sum()
            y_rev  = yest_df[yest_df["채널"]==ch_name]["AF구매매출"].sum()
            y_cost = yest_df[yest_df["채널"]==ch_name]["비용"].sum()
            t_r = t_rev / t_cost * 100 if t_cost > 0 else 0
            y_r = y_rev / y_cost * 100 if y_cost > 0 else 0
            chg = (t_r - y_r) / y_r * 100 if y_r > 0 else 0
            dod_rows.append({"채널": ch_name, "변화율": chg})

        dod_ch = pd.DataFrame(dod_rows).sort_values("변화율")
        colors = ["#dc2626" if v < 0 else "#2563eb" for v in dod_ch["변화율"]]

        fig_dod = go.Figure()
        fig_dod.add_trace(go.Bar(
            x=dod_ch["변화율"], y=dod_ch["채널"],
            orientation="h",
            marker=dict(color=colors, cornerradius=5),
            text=[f"{'▲' if v>=0 else '▼'} {abs(v):.1f}%" for v in dod_ch["변화율"]],
            textposition="outside",
            textfont=dict(family=MONO, size=12, color=C["text"]),
            hovertemplate="<b>%{y}</b><br>ROAS 변화: %{x:.1f}%<extra></extra>",
        ))
        fig_dod.update_layout(**base_layout(200), title_text="채널별 ROAS 전일 대비 (%)",
                              title_font=dict(size=13, color=C["sub"]))
        fig_dod.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=C["grid"],
                             tickfont=dict(size=10, color=C["muted"]),
                             zeroline=True, zerolinecolor="#e2e8f0", zerolinewidth=1)
        fig_dod.update_yaxes(tickfont=dict(size=12, color=C["text"]), showgrid=False, zeroline=False)
        st.plotly_chart(fig_dod, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("전일 데이터가 없어 비교할 수 없습니다. 날짜 범위에 2일 이상의 데이터가 필요합니다.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — 소재·캠페인
# ─────────────────────────────────────────────────────────────────────────────
with tab_creative:
    # ① 캠페인 목적별 ROAS 랭킹
    section("① 캠페인 목적별 ROAS")
    camp_roas = (filt.groupby("캠페인목적")
                     .agg(비용=("비용","sum"), 매출=("AF구매매출","sum"))
                     .reset_index())
    camp_roas["ROAS"] = (camp_roas["매출"] / camp_roas["비용"] * 100).where(camp_roas["비용"] > 0)
    camp_roas = camp_roas.dropna(subset=["ROAS"]).sort_values("ROAS")

    fig_camp = go.Figure()
    fig_camp.add_trace(go.Bar(
        x=camp_roas["ROAS"], y=camp_roas["캠페인목적"],
        orientation="h",
        marker=dict(
            color=[PURPOSE_COLORS.get(p, C["accent"]) for p in camp_roas["캠페인목적"]],
            cornerradius=5,
        ),
        text=[f"{v:.0f}%" for v in camp_roas["ROAS"]],
        textposition="outside",
        textfont=dict(family=MONO, size=11, color=C["text"]),
        hovertemplate="<b>%{y}</b><br>ROAS %{x:.1f}%<extra></extra>",
    ))
    fig_camp.update_layout(**base_layout(280), title_text="캠페인 목적별 ROAS (AF 매출 기준)",
                           title_font=dict(size=13, color=C["sub"]))
    fig_camp.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=C["grid"],
                          tickfont=dict(size=10, color=C["muted"]), zeroline=False)
    fig_camp.update_yaxes(tickfont=dict(size=12, color=C["text"]), showgrid=False, zeroline=False)
    st.plotly_chart(fig_camp, use_container_width=True, config={"displayModeBar": False})

    c2_left, c2_right = st.columns(2)

    # ② 소재 포맷별 CTR
    with c2_left:
        section("② 소재 포맷별 CTR")
        fmt_ctr = (filt.groupby("소재포맷")
                       .agg(클릭=("클릭","sum"), 노출=("노출","sum"))
                       .reset_index())
        fmt_ctr["CTR"] = (fmt_ctr["클릭"] / fmt_ctr["노출"] * 100).where(fmt_ctr["노출"] > 0)
        fmt_ctr = fmt_ctr.dropna(subset=["CTR"]).sort_values("CTR")

        fig_fmt = go.Figure()
        fig_fmt.add_trace(go.Bar(
            x=fmt_ctr["CTR"], y=fmt_ctr["소재포맷"],
            orientation="h",
            marker=dict(color=PALETTE[:len(fmt_ctr)], cornerradius=5),
            text=[f"{v:.2f}%" for v in fmt_ctr["CTR"]],
            textposition="outside",
            textfont=dict(family=MONO, size=11, color=C["text"]),
            hovertemplate="<b>%{y}</b><br>CTR %{x:.2f}%<extra></extra>",
        ))
        fig_fmt.update_layout(**base_layout(240, margin=dict(l=8, r=56, t=36, b=8)),
                              title_text="포맷별 CTR",
                              title_font=dict(size=13, color=C["sub"]))
        fig_fmt.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=C["grid"],
                             tickfont=dict(size=10, color=C["muted"]), zeroline=False)
        fig_fmt.update_yaxes(tickfont=dict(size=12, color=C["text"]), showgrid=False, zeroline=False)
        st.plotly_chart(fig_fmt, use_container_width=True, config={"displayModeBar": False})

    # ③ AB 소재 비교
    with c2_right:
        section("③ AB 소재 비교")
        ab_df = filt[filt["AB"].notna()].copy()

        if ab_df.empty:
            st.info("현재 필터에 AB 소재가 없습니다.")
        else:
            def ab_base(name):
                parts = str(name).split("_")
                return "_".join(p for p in parts if p not in ("A","B") and not re.match(r"v\d+$", p))

            ab_df["base"] = ab_df["소재"].apply(ab_base)
            ab_agg = (ab_df.groupby(["base","AB","캠페인","그룹"])
                           .agg(비용=("비용","sum"), 매출=("AF구매매출","sum"))
                           .reset_index())
            ab_agg["ROAS"] = (ab_agg["매출"] / ab_agg["비용"] * 100).where(ab_agg["비용"] > 0)

            # A와 B 둘 다 있는 base만
            valid = ab_agg.groupby("base")["AB"].nunique()
            valid_bases = valid[valid >= 2].index
            ab_pairs = ab_agg[ab_agg["base"].isin(valid_bases)].dropna(subset=["ROAS"])

            if ab_pairs.empty:
                st.info("완전한 A/B 쌍이 없습니다.")
            else:
                fig_ab = go.Figure()
                for base_name in ab_pairs["base"].unique()[:6]:
                    pair = ab_pairs[ab_pairs["base"] == base_name]
                    label = base_name[-18:] if len(base_name) > 18 else base_name
                    for _, row in pair.iterrows():
                        fig_ab.add_trace(go.Bar(
                            x=[label],
                            y=[row["ROAS"]],
                            marker=dict(
                                color="#2563eb" if row["AB"] == "A" else "#059669",
                                cornerradius=4,
                            ),
                            text=[f"{row['AB']}: {row['ROAS']:.0f}%"],
                            textposition="outside",
                            textfont=dict(family=MONO, size=10, color=C["text"]),
                            hovertemplate=f"<b>{label} - {row['AB']}</b><br>ROAS: %{{y:.1f}}%<extra></extra>",
                        ))

                fig_ab.update_layout(**base_layout(240), barmode="group",
                                     title_text="AB 소재 ROAS 비교 (파랑=A, 초록=B)",
                                     title_font=dict(size=13, color=C["sub"]))
                fig_ab.update_xaxes(tickfont=dict(size=10, color=C["text"]), showgrid=False, zeroline=False)
                fig_ab.update_yaxes(ticksuffix="%", showgrid=True, gridcolor=C["grid"],
                                    tickfont=dict(size=10, color=C["muted"]), zeroline=False)
                st.plotly_chart(fig_ab, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — 월간
# ─────────────────────────────────────────────────────────────────────────────
with tab_monthly:
    # 월 선택 (전체 df 기준)
    available_months = sorted(df["월"].unique(), reverse=True)
    month_labels     = [str(m) for m in available_months]
    sel_label        = st.selectbox("월 선택", month_labels, index=0, label_visibility="collapsed")
    sel_month        = pd.Period(sel_label, "M")
    prev_month       = sel_month - 1

    base_filt  = df[df["채널"].isin(channels) & df["캠페인"].isin(campaigns)]
    month_df   = base_filt[base_filt["월"] == sel_month]
    prev_df    = base_filt[base_filt["월"] == prev_month]

    def month_agg(d):
        cost = d["비용"].sum()
        rev  = d["AF구매매출"].sum()
        pur  = d["AF구매"].sum()
        return dict(
            비용=cost,
            ROAS=rev / cost * 100 if cost > 0 else 0,
            구매=pur,
        )

    mk = month_agg(month_df)
    pk = month_agg(prev_df) if not prev_df.empty else None

    # ① 월간 누적 KPI
    section(f"① {sel_label} 월간 누적 KPI")
    m1, m2, m3 = st.columns(3)
    m1.markdown(mom_card("총 비용",  mk["비용"], pk["비용"] if pk else None, lambda v: f"₩{v/1e6:.1f}M",  accent="#2563eb"), unsafe_allow_html=True)
    m2.markdown(mom_card("ROAS",    mk["ROAS"], pk["ROAS"] if pk else None, lambda v: f"{v:.0f}%",        accent="#7c3aed"), unsafe_allow_html=True)
    m3.markdown(mom_card("구매(AF)", mk["구매"], pk["구매"] if pk else None, lambda v: f"{v:,.0f}",        accent="#d97706"), unsafe_allow_html=True)

    if pk:
        st.markdown(f"<div style='font-size:.7rem;color:#94a3b8;margin:.25rem 0 .5rem'>vs {prev_month} 전월 비교</div>", unsafe_allow_html=True)

    # ② 채널별 월간 집계 테이블
    section("② 채널별 월간 집계")
    ch_m = (month_df.groupby("채널")
                    .agg(비용=("비용","sum"), 구매=("AF구매","sum"), 매출=("AF구매매출","sum"))
                    .reset_index())
    ch_m["ROAS"] = (ch_m["매출"] / ch_m["비용"] * 100).where(ch_m["비용"] > 0).round(1)
    ch_m["CPA"]  = (ch_m["비용"] / ch_m["구매"]).where(ch_m["구매"] > 0).round(0)
    ch_m = ch_m.sort_values("비용", ascending=False)

    st.dataframe(
        ch_m[["채널","비용","ROAS","구매","CPA"]],
        use_container_width=True, hide_index=True,
        column_config={
            "비용":  st.column_config.NumberColumn("비용",  format="₩%d"),
            "ROAS": st.column_config.NumberColumn("ROAS",  format="%.1f%%"),
            "CPA":  st.column_config.NumberColumn("CPA",   format="₩%d"),
        },
        height=160,
    )

    # ③ 캠페인 목적별 비용 비중 (100% 누적 가로 바)
    section("③ 캠페인 목적별 비용 비중")
    pur_cost = (month_df.groupby("캠페인목적")["비용"]
                        .sum().reset_index()
                        .sort_values("비용", ascending=False))
    total_m = pur_cost["비용"].sum()
    pur_cost["비중"] = pur_cost["비용"] / total_m * 100 if total_m > 0 else 0

    fig_share = go.Figure()
    for _, row in pur_cost.iterrows():
        fig_share.add_trace(go.Bar(
            x=[row["비중"]],
            y=["비용 비중"],
            orientation="h",
            name=row["캠페인목적"],
            marker=dict(color=PURPOSE_COLORS.get(row["캠페인목적"], C["muted"]), cornerradius=0),
            text=[f"{row['캠페인목적']} {row['비중']:.1f}%"] if row["비중"] > 5 else [""],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(family=FONT, size=11, color="#fff"),
            hovertemplate=f"<b>{row['캠페인목적']}</b><br>₩{row['비용']:,.0f} ({row['비중']:.1f}%)<extra></extra>",
        ))

    fig_share.update_layout(
        **base_layout(110, margin=dict(l=8, r=8, t=36, b=8)),
        barmode="stack",
        title_text="캠페인 목적별 비용 비중 (%)",
        title_font=dict(size=13, color=C["sub"]),
    )
    fig_share.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=C["grid"],
                           tickfont=dict(size=10, color=C["muted"]), zeroline=False, range=[0, 100])
    fig_share.update_yaxes(showgrid=False, zeroline=False, showticklabels=False)
    st.plotly_chart(fig_share, use_container_width=True, config={"displayModeBar": False})

# ── 푸터 ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:3rem;padding-top:1.5rem;border-top:1px solid #e2e8f0;
    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem">
  <span style="font-size:.75rem;color:#cbd5e1">
    {len(filt):,}행 · 채널 {filt['채널'].nunique()}개 · 캠페인 {filt['캠페인'].nunique()}개 · 소재 {filt['소재'].nunique()}개
  </span>
  <span style="font-size:.75rem;color:#cbd5e1;font-family:'{MONO}',monospace">
    AF 매출 기준 · 7일 클릭 Attribution · {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
  </span>
</div>
""", unsafe_allow_html=True)
