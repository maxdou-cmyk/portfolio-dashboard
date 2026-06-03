"""Portfolio Dashboard — Streamlit App"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime

st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global */
.block-container{padding:2rem 2.5rem 3rem;}
h1{font-size:1.6rem !important;font-weight:700 !important;letter-spacing:-0.5px;}

/* Tab bar */
button[data-baseweb="tab"]{font-size:14px !important;font-weight:500 !important;padding:10px 20px !important;}

/* Metric cards */
[data-testid="stMetricValue"]{font-size:1.4rem !important;font-weight:700 !important;}
[data-testid="stMetricLabel"]{font-size:0.75rem !important;color:#888 !important;text-transform:uppercase;letter-spacing:.5px;}
[data-testid="stMetricDelta"]{font-size:0.9rem !important;}

/* Segmented control */
div[data-testid="stSegmentedControl"] button{font-size:12px !important;padding:4px 12px !important;}

/* Pill buttons for ETF toggle */
.stButton > button{border-radius:20px !important;font-size:11px !important;padding:3px 10px !important;
  border:0.5px solid rgba(0,0,0,0.15) !important;font-weight:500 !important;}

/* Search result rows */
.ticker-row{display:flex;align-items:center;padding:5px 10px;border-radius:6px;cursor:pointer;
  font-size:13px;border:0.5px solid rgba(0,0,0,0.08);margin:3px 0;background:#fff;}
.ticker-row:hover{background:#f0f4ff;}

/* Sidebar minimal */
section[data-testid="stSidebar"]{min-width:0px !important;}
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
PALETTE = [
    "#2563EB","#DC2626","#16A34A","#D97706","#7C3AED","#0891B2",
    "#BE185D","#65A30D","#9333EA","#EA580C","#0284C7","#B45309","#6366F1",
    "#4F46E5","#DB2777","#15803D","#C2410C","#1D4ED8","#7E22CE","#B91C1C",
]

DEFAULT_ETFS = [
    {"ticker":"CW8.PA",   "name":"CW8",   "label":"MSCI World"},
    {"ticker":"PE500.PA", "name":"PE500", "label":"S&P 500 (ESG)"},
    {"ticker":"PAASI.PA", "name":"PAASI", "label":"Émergents Asie"},
    {"ticker":"PUST.PA",  "name":"PUST",  "label":"Nasdaq-100"},
    {"ticker":"PAEEM.PA", "name":"PAEEM", "label":"Émergents Monde"},
    {"ticker":"C50.PA",   "name":"C50",   "label":"Euro Stoxx 50"},
    {"ticker":"BNKE.PA",  "name":"BNKE",  "label":"Banques Europe"},
    {"ticker":"GOLD.PA",  "name":"GOLD",  "label":"Or physique"},
    {"ticker":"MMS.PA",   "name":"MMS",   "label":"Small Caps Europe"},
    {"ticker":"RS2K.PA",  "name":"RS2K",  "label":"Russell 2000 US"},
    {"ticker":"IROB.DE",  "name":"IROB",  "label":"Robotique mondiale"},
    {"ticker":"TNO.PA",   "name":"TNO",   "label":"Tech Europe 600"},
    {"ticker":"SEME.PA",  "name":"SEME",  "label":"Semiconducteurs"},
]

PERIODS = {"1S":"1w","1M":"1mo","3M":"3mo","6M":"6mo","YTD":"ytd","1A":"1y","3A":"3y","5A":"5y"}

# ── Helpers ────────────────────────────────────────────────────────────────────
today = pd.Timestamp.today().normalize()

def period_start(key: str) -> pd.Timestamp:
    m = {"1w": pd.Timedelta(weeks=1), "1mo": pd.DateOffset(months=1),
         "3mo": pd.DateOffset(months=3), "6mo": pd.DateOffset(months=6),
         "1y": pd.DateOffset(years=1), "3y": pd.DateOffset(years=3),
         "5y": pd.DateOffset(years=5)}
    if key == "ytd": return pd.Timestamp(today.year, 1, 1)
    return today - m.get(key, pd.DateOffset(years=1))

def pct_ret(series: pd.Series):
    s = series.dropna()
    if len(s) < 2: return None
    return (s.iloc[-1] / s.iloc[0] - 1) * 100

def fmt_pct(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "—"
    return f"+{x:.1f}%" if x >= 0 else f"{x:.1f}%"

def color_cell(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return ""
    return "color:#16A34A;font-weight:600" if x >= 0 else "color:#DC2626;font-weight:600"

# ── Data fetching ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def search_tickers(query: str) -> list:
    if len(query) < 2: return []
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}&lang=fr&region=FR&quotesCount=8"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if not r.ok: return []
        return [
            {"ticker": q["symbol"],
             "label":  (q.get("shortname") or q.get("longname") or q["symbol"])[:50],
             "type":   q.get("quoteType", ""),
             "exchange": q.get("exchDisp", "")}
            for q in r.json().get("quotes", []) if q.get("symbol")
        ]
    except Exception:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers_key: str) -> pd.DataFrame:
    tickers = [t.strip() for t in tickers_key.split(",") if t.strip()]
    if not tickers: return pd.DataFrame()
    try:
        data = yf.download(tickers, period="5y", auto_adjust=True, progress=False)
        if data.empty: return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            close_key = next((k for k in data.columns.get_level_values(0).unique()
                              if str(k).lower() == "close"), None)
            if close_key is None: return pd.DataFrame()
            df = data[close_key].copy()
            if isinstance(df, pd.Series): df = df.to_frame(name=tickers[0])
        else:
            close_key = next((k for k in data.columns if str(k).lower() == "close"), None)
            if close_key is None: return pd.DataFrame()
            df = pd.DataFrame({tickers[0]: data[close_key]})
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        else:
            df.index = pd.to_datetime(df.index)
        return df.dropna(how="all")
    except Exception as e:
        return pd.DataFrame()

# ── Session state init ────────────────────────────────────────────────────────
for k, v in [("custom_etfs", []), ("search_q", ""), ("visible_default", None),
              ("visible_custom", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_refresh = st.columns([8, 1])
with col_title:
    st.markdown("# 📈 Portfolio Dashboard")
with col_refresh:
    st.markdown("<div style='margin-top:12px'>", unsafe_allow_html=True)
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.caption(f"Données Yahoo Finance · {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_maxence, tab_custom = st.tabs(["📊 Portefeuille Maxence", "➕ Mon portefeuille"])

# ══════════════════════════════════════════════════════════════════════════════
# Helper: render charts + table given an etf_list + prices + period
# ══════════════════════════════════════════════════════════════════════════════
def render_dashboard(etf_list, prices, tab_key):
    available = [e for e in etf_list if e["ticker"] in prices.columns]
    if not available:
        st.error("Aucun ticker valide. Vérifier les symboles.")
        return

    # ── Period selector ────────────────────────────────────────────────────
    period_label = st.segmented_control(
        "Période", options=list(PERIODS.keys()), default="1A",
        key=f"period_{tab_key}", label_visibility="collapsed"
    ) or "1A"
    period_key = PERIODS[period_label]
    start = period_start(period_key)
    sliced = prices.loc[prices.index >= start]

    # ── Metric cards ───────────────────────────────────────────────────────
    rets = {e["name"]: pct_ret(sliced[e["ticker"]].dropna()) for e in available}
    valid_rets = {k: v for k, v in rets.items() if v is not None}

    if valid_rets:
        best_k  = max(valid_rets, key=valid_rets.get)
        worst_k = min(valid_rets, key=valid_rets.get)
        best_e  = next(e for e in available if e["name"] == best_k)
        worst_e = next(e for e in available if e["name"] == worst_k)
        avg     = np.mean(list(valid_rets.values()))

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("🏆 Meilleur", best_e["label"],
                      delta=f"{valid_rets[best_k]:+.1f}%",
                      delta_color="normal")
        with c2:
            st.metric("📉 Pire", worst_e["label"],
                      delta=f"{valid_rets[worst_k]:+.1f}%",
                      delta_color="normal")
        with c3:
            st.metric("∅ Moyenne", f"{avg:+.1f}%")
        with c4:
            st.metric("📊 Actifs", f"{len(available)}")

    st.markdown("")

    # ── Visibility init ────────────────────────────────────────────────────
    vis_key = f"visible_{tab_key}"
    all_names = [e["name"] for e in available]
    if st.session_state.get(vis_key) is None or \
       not set(st.session_state[vis_key]).issubset(set(all_names)):
        st.session_state[vis_key] = all_names[:]

    # ── Base-100 % chart ───────────────────────────────────────────────────
    visible_set = set(st.session_state[vis_key]) or {all_names[0]}
    shown = [e for e in available if e["name"] in visible_set]

    fig = go.Figure()
    for e in shown:
        s = sliced[e["ticker"]].dropna()
        if len(s) < 2: continue
        pct_series = (s / s.iloc[0] * 100 - 100).round(3)
        last_val   = pct_series.iloc[-1]
        h = e["color"].lstrip("#")
        r_, g_, b_ = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        fill_rgba = f"rgba({r_},{g_},{b_},0.05)"
        fig.add_trace(go.Scatter(
            x=pct_series.index, y=pct_series.values,
            name=f"{e['label']}",
            line=dict(color=e["color"], width=2),
            fill="tozeroy",
            fillcolor=fill_rgba,
            hovertemplate=(
                f"<b>{e['label']} ({e['name']})</b><br>"
                "%{x|%d/%m/%Y}<br>"
                "Performance : <b>%{y:+.2f}%</b><extra></extra>"
            )
        ))
        # End-of-line annotation
        fig.add_annotation(
            x=pct_series.index[-1], y=last_val,
            text=f" {last_val:+.1f}%",
            showarrow=False, xanchor="left",
            font=dict(size=11, color=e["color"], weight=700)
        )

    date_from = sliced.index[0].strftime("%d/%m/%Y") if not sliced.empty else "—"
    fig.update_layout(
        height=400,
        margin=dict(l=0, r=80, t=10, b=0),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15, font=dict(size=11),
                    itemclick="toggle", itemdoubleclick="toggleothers"),
        xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)",
                   zeroline=False, tickfont=dict(size=11)),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(0,0,0,0.05)",
            tickformat="+.0f", ticksuffix="%",
            zeroline=True, zerolinecolor="rgba(0,0,0,0.2)", zerolinewidth=1.5,
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, width="stretch")

    # ── ETF pills selector (below chart) ───────────────────────────────────
    col_pills, col_all = st.columns([9, 1])
    with col_all:
        all_sel = len(st.session_state[vis_key]) == len(available)
        if st.button("Tout ✓" if not all_sel else "Tout ✗",
                     key=f"all_{tab_key}", use_container_width=True):
            st.session_state[vis_key] = all_names[:] if not all_sel else [all_names[0]]
            st.rerun()

    with col_pills:
        selected = st.multiselect(
            "ETFs", options=all_names,
            default=st.session_state[vis_key],
            format_func=lambda x: next((f"{e['label']} ({e['name']})"
                                        for e in available if e["name"] == x), x),
            label_visibility="collapsed",
            key=f"ms_{tab_key}"
        )
        if set(selected) != set(st.session_state[vis_key]):
            st.session_state[vis_key] = selected or [all_names[0]]
            st.rerun()

    st.markdown("")

    # ── Performance table ──────────────────────────────────────────────────
    with st.expander("📋 Tableau de performances", expanded=True):
        rows = []
        for e in available:
            row = {"Actif": f"{e['label']}", "Ticker": e["name"]}
            for lbl, key in PERIODS.items():
                sl = prices.loc[prices.index >= period_start(key), e["ticker"]].dropna()
                row[lbl] = pct_ret(sl)
            rows.append(row)

        df_p = pd.DataFrame(rows).set_index("Actif")
        df_sorted = df_p.sort_values(period_label, ascending=False)
        cols_pct = [c for c in PERIODS.keys() if c in df_sorted.columns]

        st.dataframe(
            df_sorted.style
                .format(fmt_pct, subset=cols_pct)
                .map(color_cell, subset=cols_pct)
                .set_properties(**{"text-align": "right"})
                .set_properties(subset=["Ticker"], **{"color": "#aaa", "font-size": "11px"})
                .highlight_between(subset=[period_label],
                                   props="background-color:rgba(37,99,235,0.06)"),
            width="stretch",
            height=min(80 + len(available) * 36, 600)
        )

    # ── Heatmap ────────────────────────────────────────────────────────────
    with st.expander("🗓 Heatmap mensuelle", expanded=False):
        N = 18
        mstarts = pd.date_range(end=today + pd.offsets.MonthBegin(1), periods=N+1, freq="MS")
        mlabels = [d.strftime("%b %y") for d in mstarts[:-1]]
        z, txt, ynames = [], [], []
        for e in available:
            row_z, row_t = [], []
            for i in range(N):
                sl = prices.loc[(prices.index >= mstarts[i]) &
                                (prices.index < mstarts[i+1]), e["ticker"]].dropna()
                v = pct_ret(sl)
                row_z.append(v if v is not None else float("nan"))
                row_t.append(f"{v:+.1f}%" if v is not None and v >= 0 else
                             (f"{v:.1f}%" if v is not None else "—"))
            z.append(row_z); txt.append(row_t); ynames.append(e["name"])

        fig_h = go.Figure(go.Heatmap(
            z=z, x=mlabels, y=ynames, text=txt,
            texttemplate="%{text}", textfont=dict(size=10),
            colorscale=[[0,"#DC2626"],[0.5,"#f8fafc"],[1,"#16A34A"]],
            zmid=0, zmin=-8, zmax=8,
            hovertemplate="%{y} · %{x} : <b>%{text}</b><extra></extra>",
            showscale=True, colorbar=dict(ticksuffix="%", len=0.7, thickness=10)
        ))
        fig_h.update_layout(
            height=max(280, len(available)*32+60),
            margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(tickfont=dict(size=10), side="top"),
            yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_h, width="stretch")

    # ── Correlation ────────────────────────────────────────────────────────
    with st.expander("🔗 Corrélations — 1 an", expanded=False):
        st.caption("Corrélation Pearson sur rendements journaliers · 🟢 corrélés · 🔴 décorrélés")
        cs = prices.loc[prices.index >= period_start("1y"),
                        [e["ticker"] for e in available]].dropna()
        if len(cs) >= 20:
            lr = np.log(cs / cs.shift(1)).dropna()
            cm = lr.corr().round(2)
            ns = [e["name"] for e in available if e["ticker"] in cm.columns]
            fig_c = go.Figure(go.Heatmap(
                z=cm.values.tolist(), x=ns, y=ns,
                text=[[f"{v:.2f}" for v in row] for row in cm.values],
                texttemplate="%{text}", textfont=dict(size=11),
                colorscale=[[0,"#DC2626"],[0.5,"#f8fafc"],[1,"#16A34A"]],
                zmid=0, zmin=-1, zmax=1,
                hovertemplate="%{y} / %{x} : <b>%{text}</b><extra></extra>",
                showscale=True, colorbar=dict(len=0.7, thickness=10)
            ))
            fig_c.update_layout(
                height=max(300, len(ns)*44+60),
                margin=dict(l=0,r=0,t=10,b=0),
                xaxis=dict(tickfont=dict(size=11), side="top"),
                yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_c, width="stretch")
        else:
            st.caption("Données insuffisantes.")

# ══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Portefeuille Maxence
# ══════════════════════════════════════════════════════════════════════════════
with tab_maxence:
    etf_list_max = [{**e, "color": PALETTE[i % len(PALETTE)]}
                    for i, e in enumerate(DEFAULT_ETFS)]
    tk_key_max = ",".join(e["ticker"] for e in etf_list_max)
    with st.spinner("Chargement…"):
        prices_max = load_prices(tk_key_max)
    if prices_max.empty:
        st.error("Impossible de charger les données.")
    else:
        render_dashboard(etf_list_max, prices_max, "default")

# ══════════════════════════════════════════════════════════════════════════════
# Tab 2 — Mon portefeuille
# ══════════════════════════════════════════════════════════════════════════════
with tab_custom:

    # ── Unified ticker search ──────────────────────────────────────────────
    st.markdown("#### Ajouter des actifs à ton portefeuille")

    c_search, c_clear = st.columns([5, 1])
    with c_search:
        search_q = st.text_input(
            "Recherche", placeholder="🔍  Apple, BTC, CW8, CAC 40…",
            value=st.session_state.search_q,
            label_visibility="collapsed", key="search_input"
        )
        st.session_state.search_q = search_q
    with c_clear:
        st.markdown("<div style='margin-top:4px'>", unsafe_allow_html=True)
        if st.button("Vider liste", use_container_width=True):
            st.session_state.custom_etfs = []
            st.session_state.search_q    = ""
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Search results
    if search_q and len(search_q) >= 2:
        results = search_tickers(search_q)
        if results:
            in_list = {e["ticker"] for e in st.session_state.custom_etfs}
            for r in results:
                already = r["ticker"] in in_list
                r_col, btn_col = st.columns([7, 1])
                with r_col:
                    badge_color = "#16A34A" if already else "#64748b"
                    st.markdown(
                        f"<div style='padding:6px 10px;border-radius:6px;"
                        f"border:0.5px solid #e2e8f0;background:#{'f0fdf4' if already else 'fff'};"
                        f"font-size:13px;line-height:1.4'>"
                        f"<b style='color:{badge_color}'>{r['ticker']}</b> — {r['label']} "
                        f"<span style='color:#94a3b8;font-size:11px'>{r['type']} · {r['exchange']}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with btn_col:
                    if already:
                        if st.button("✕", key=f"rm_{r['ticker']}", help="Retirer"):
                            st.session_state.custom_etfs = [
                                e for e in st.session_state.custom_etfs
                                if e["ticker"] != r["ticker"]
                            ]
                            st.rerun()
                    else:
                        if st.button("＋ Add", key=f"add_{r['ticker']}", help="Ajouter"):
                            i = len(st.session_state.custom_etfs)
                            st.session_state.custom_etfs.append({
                                "ticker": r["ticker"],
                                "name":   r["ticker"].split(".")[0].upper()[:6],
                                "label":  r["label"],
                                "color":  PALETTE[i % len(PALETTE)],
                            })
                            st.rerun()
        else:
            st.caption("Aucun résultat — vérifier l'orthographe ou utiliser le symbole exact (ex : `^FCHI`).")

    # Current ticker list as removable pills
    if st.session_state.custom_etfs:
        st.markdown("**Actifs sélectionnés :**")
        cols = st.columns(min(len(st.session_state.custom_etfs), 5))
        for i, e in enumerate(st.session_state.custom_etfs):
            with cols[i % 5]:
                if st.button(
                    f"✕ {e['name']}",
                    key=f"del_{e['ticker']}_{i}",
                    help=f"Retirer {e['label']}",
                    use_container_width=True
                ):
                    st.session_state.custom_etfs = [
                        t for t in st.session_state.custom_etfs
                        if t["ticker"] != e["ticker"]
                    ]
                    st.session_state.visible_custom = None
                    st.rerun()
        st.divider()

    # ── Render dashboard if any tickers selected ───────────────────────────
    if not st.session_state.custom_etfs:
        st.info(
            "👆 Recherche un actif ci-dessus et clique **＋ Add** pour l'ajouter.\n\n"
            "Tu peux ajouter des ETFs européens (ex: `CW8.PA`), des actions US (ex: `AAPL`), "
            "de la crypto (ex: `BTC-USD`) ou des indices (ex: `^GSPC`)."
        )
    else:
        tk_key_custom = ",".join(e["ticker"] for e in st.session_state.custom_etfs)
        with st.spinner("Chargement…"):
            prices_custom = load_prices(tk_key_custom)
        if prices_custom.empty:
            st.error("Impossible de charger les données. Vérifier les symboles.")
        else:
            render_dashboard(st.session_state.custom_etfs, prices_custom, "custom")

st.divider()
st.caption("Source : Yahoo Finance · Données auto-ajustées des dividendes")
