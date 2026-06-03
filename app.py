"""Portfolio Dashboard — Streamlit App"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.block-container{padding:1.8rem 2.5rem 3rem;}
h1{font-size:1.55rem !important;font-weight:700 !important;letter-spacing:-.4px;}
h3{font-size:1rem !important;font-weight:600 !important;}
button[data-baseweb="tab"]{font-size:14px !important;font-weight:500 !important;padding:10px 22px !important;}
[data-testid="stMetricValue"]{font-size:1.3rem !important;font-weight:700 !important;}
[data-testid="stMetricLabel"]{font-size:.72rem !important;color:#888 !important;text-transform:uppercase;letter-spacing:.4px;}
div[data-testid="stSegmentedControl"] button{font-size:12px !important;padding:4px 11px !important;}
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

# Preset ticker library for "Mon portefeuille"
PRESET_TICKERS = (
    # ── ETFs Euronext Paris ──────────────────────────────────────────────
    [{"ticker":"CW8.PA",   "label":"CW8 — MSCI World (Amundi)"},
     {"ticker":"PE500.PA", "label":"PE500 — S&P 500 ESG (Amundi PEA)"},
     {"ticker":"PAASI.PA", "label":"PAASI — Émergents Asie (Amundi PEA)"},
     {"ticker":"PUST.PA",  "label":"PUST — Nasdaq-100 (Amundi PEA)"},
     {"ticker":"PAEEM.PA", "label":"PAEEM — Émergents Monde ESG (Amundi)"},
     {"ticker":"C50.PA",   "label":"C50 — Euro Stoxx 50 (Amundi)"},
     {"ticker":"BNKE.PA",  "label":"BNKE — Banques Europe (Amundi)"},
     {"ticker":"GOLD.PA",  "label":"GOLD — Or physique (Amundi ETC)"},
     {"ticker":"MMS.PA",   "label":"MMS — Small Caps Europe (Amundi)"},
     {"ticker":"RS2K.PA",  "label":"RS2K — Russell 2000 US (Amundi)"},
     {"ticker":"TNO.PA",   "label":"TNO — Tech Europe 600 (Amundi)"},
     {"ticker":"SEME.PA",  "label":"SEME — Semiconducteurs (iShares)"},
     {"ticker":"IROB.DE",  "label":"IROB — Robotique mondiale (L&G)"},
    ] +
    # ── ETFs globaux (XETRA / Amsterdam) ─────────────────────────────────
    [{"ticker":"VWCE.DE",  "label":"VWCE — FTSE All-World Acc (Vanguard)"},
     {"ticker":"IWDA.AS",  "label":"IWDA — MSCI World (iShares)"},
     {"ticker":"CSPX.AS",  "label":"CSPX — S&P 500 (iShares)"},
     {"ticker":"EIMI.AS",  "label":"EIMI — EM IMI (iShares)"},
     {"ticker":"IUIT.AS",  "label":"IUIT — US IT (iShares)"},
     {"ticker":"IQQH.DE",  "label":"IQQH — Énergie propre (iShares)"},
     {"ticker":"EXW1.DE",  "label":"EXW1 — MSCI World (iShares XETRA)"},
     {"ticker":"XDWD.DE",  "label":"XDWD — MSCI World (Xtrackers)"},
    ] +
    # ── Actions US ────────────────────────────────────────────────────────
    [{"ticker":"AAPL",  "label":"AAPL — Apple"},
     {"ticker":"MSFT",  "label":"MSFT — Microsoft"},
     {"ticker":"NVDA",  "label":"NVDA — NVIDIA"},
     {"ticker":"GOOGL", "label":"GOOGL — Alphabet (Google)"},
     {"ticker":"AMZN",  "label":"AMZN — Amazon"},
     {"ticker":"META",  "label":"META — Meta"},
     {"ticker":"TSLA",  "label":"TSLA — Tesla"},
     {"ticker":"BRK-B", "label":"BRK-B — Berkshire Hathaway"},
     {"ticker":"JPM",   "label":"JPM — JPMorgan Chase"},
     {"ticker":"V",     "label":"V — Visa"},
     {"ticker":"JNJ",   "label":"JNJ — Johnson & Johnson"},
     {"ticker":"WMT",   "label":"WMT — Walmart"},
     {"ticker":"XOM",   "label":"XOM — ExxonMobil"},
     {"ticker":"NFLX",  "label":"NFLX — Netflix"},
     {"ticker":"AMD",   "label":"AMD — Advanced Micro Devices"},
    ] +
    # ── Actions européennes ───────────────────────────────────────────────
    [{"ticker":"MC.PA",   "label":"MC — LVMH (Paris)"},
     {"ticker":"TTE.PA",  "label":"TTE — TotalEnergies (Paris)"},
     {"ticker":"SAN.PA",  "label":"SAN — Sanofi (Paris)"},
     {"ticker":"AIR.PA",  "label":"AIR — Airbus (Paris)"},
     {"ticker":"BNP.PA",  "label":"BNP — BNP Paribas (Paris)"},
     {"ticker":"SAP.DE",  "label":"SAP — SAP (Frankfurt)"},
     {"ticker":"ASML.AS", "label":"ASML — ASML (Amsterdam)"},
     {"ticker":"NESN.SW", "label":"NESN — Nestlé (Zurich)"},
    ] +
    # ── Crypto ────────────────────────────────────────────────────────────
    [{"ticker":"BTC-USD",  "label":"BTC — Bitcoin"},
     {"ticker":"ETH-USD",  "label":"ETH — Ethereum"},
     {"ticker":"SOL-USD",  "label":"SOL — Solana"},
    ] +
    # ── Indices ───────────────────────────────────────────────────────────
    [{"ticker":"^GSPC",  "label":"^GSPC — S&P 500"},
     {"ticker":"^IXIC",  "label":"^IXIC — NASDAQ Composite"},
     {"ticker":"^DJI",   "label":"^DJI — Dow Jones"},
     {"ticker":"^FCHI",  "label":"^FCHI — CAC 40"},
     {"ticker":"^GDAXI", "label":"^GDAXI — DAX"},
     {"ticker":"^FTSE",  "label":"^FTSE — FTSE 100"},
     {"ticker":"^N225",  "label":"^N225 — Nikkei 225"},
     {"ticker":"^HSI",   "label":"^HSI — Hang Seng"},
    ]
)
PRESET_MAP = {e["label"]: e for e in PRESET_TICKERS}

PERIODS = {"1S":"1w","1M":"1mo","3M":"3mo","6M":"6mo","YTD":"ytd","1A":"1y","3A":"3y","5A":"5y"}

# ── Timezone ───────────────────────────────────────────────────────────────────
now_paris = datetime.now(ZoneInfo("Europe/Paris"))

# ── Helpers ────────────────────────────────────────────────────────────────────
today = pd.Timestamp.today().normalize()

def period_start(key):
    m = {"1w":pd.Timedelta(weeks=1),"1mo":pd.DateOffset(months=1),
         "3mo":pd.DateOffset(months=3),"6mo":pd.DateOffset(months=6),
         "1y":pd.DateOffset(years=1),"3y":pd.DateOffset(years=3),
         "5y":pd.DateOffset(years=5)}
    if key=="ytd": return pd.Timestamp(today.year,1,1)
    return today - m.get(key, pd.DateOffset(years=1))

def pct_ret(series):
    s = series.dropna()
    if len(s)<2: return None
    return (s.iloc[-1]/s.iloc[0]-1)*100

def fmt_pct(x):
    if x is None or (isinstance(x,float) and np.isnan(x)): return "—"
    return f"+{x:.1f}%" if x>=0 else f"{x:.1f}%"

def color_cell(x):
    if x is None or (isinstance(x,float) and np.isnan(x)): return ""
    return "color:#16A34A;font-weight:600" if x>=0 else "color:#DC2626;font-weight:600"

# ── Data ───────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers_key):
    tickers = [t.strip() for t in tickers_key.split(",") if t.strip()]
    if not tickers: return pd.DataFrame()
    try:
        data = yf.download(tickers, period="5y", auto_adjust=True, progress=False)
        if data.empty: return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            ck = next((k for k in data.columns.get_level_values(0).unique()
                       if str(k).lower()=="close"), None)
            if ck is None: return pd.DataFrame()
            df = data[ck].copy()
            if isinstance(df, pd.Series): df = df.to_frame(name=tickers[0])
        else:
            ck = next((k for k in data.columns if str(k).lower()=="close"), None)
            if ck is None: return pd.DataFrame()
            df = pd.DataFrame({tickers[0]: data[ck]})
        if hasattr(df.index,"tz") and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        else:
            df.index = pd.to_datetime(df.index)
        return df.dropna(how="all")
    except Exception:
        return pd.DataFrame()

# ── Session state ──────────────────────────────────────────────────────────────
for k,v in [("vis_default",None),("vis_custom",None),("custom_selection",[])]:
    if k not in st.session_state: st.session_state[k]=v

# ══════════════════════════════════════════════════════════════════════════════
# Dashboard renderer
# ══════════════════════════════════════════════════════════════════════════════
def render_dashboard(etf_list, prices, tab_key):
    available = [e for e in etf_list if e["ticker"] in prices.columns]
    if not available:
        st.error("Aucun ticker valide chargé.")
        return

    # ── Period buttons ─────────────────────────────────────────────────────
    period_label = st.segmented_control(
        "Période", list(PERIODS.keys()), default="1A",
        key=f"period_{tab_key}", label_visibility="collapsed"
    ) or "1A"
    pk = PERIODS[period_label]
    start = period_start(pk)
    sliced = prices.loc[prices.index>=start]

    # ── Metric cards ───────────────────────────────────────────────────────
    rets = {e["name"]: pct_ret(sliced[e["ticker"]].dropna()) for e in available}
    valid = {k:v for k,v in rets.items() if v is not None}
    if valid:
        bk = max(valid, key=valid.get); wk = min(valid, key=valid.get)
        be = next(e for e in available if e["name"]==bk)
        we = next(e for e in available if e["name"]==wk)
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("🏆 Meilleur", be["label"], f"{valid[bk]:+.1f}%")
        c2.metric("📉 Pire",     we["label"], f"{valid[wk]:+.1f}%")
        c3.metric("∅ Moyenne",  f"{np.mean(list(valid.values())):+.1f}%")
        c4.metric("Actifs",     str(len(available)))
    st.markdown("")

    # ── Visibility init ────────────────────────────────────────────────────
    vis_key = f"vis_{tab_key}"
    all_names = [e["name"] for e in available]
    if st.session_state.get(vis_key) is None:
        st.session_state[vis_key] = all_names[:]

    visible_set = set(st.session_state[vis_key]) & set(all_names) or {all_names[0]}
    shown = [e for e in available if e["name"] in visible_set]

    # ── Chart ──────────────────────────────────────────────────────────────
    fig = go.Figure()
    for e in shown:
        s = sliced[e["ticker"]].dropna()
        if len(s)<2: continue
        pct_s = (s/s.iloc[0]*100-100).round(2)
        last  = pct_s.iloc[-1]
        fig.add_trace(go.Scatter(
            x=pct_s.index, y=pct_s.values,
            name=e["label"],
            line=dict(color=e["color"], width=2),
            hovertemplate=(
                f"<b>{e['label']} ({e['name']})</b><br>"
                "%{x|%d/%m/%Y}<br>Performance : <b>%{y:+.1f}%</b><extra></extra>"
            )
        ))
        fig.add_annotation(
            x=pct_s.index[-1], y=last,
            text=f" {last:+.1f}%",
            showarrow=False, xanchor="left",
            font=dict(size=11, color=e["color"], weight=700)
        )
    fig.update_layout(
        height=400, margin=dict(l=0,r=80,t=10,b=0),
        hovermode="x unified",
        legend=dict(orientation="h",y=-0.15,font=dict(size=11),
                    itemclick="toggle",itemdoubleclick="toggleothers"),
        xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", zeroline=False,
                   tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)",
                   tickformat="+.0f", ticksuffix="%",
                   zeroline=True, zerolinecolor="rgba(0,0,0,0.2)", zerolinewidth=1.5),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("💡 Cliquer sur un actif dans la légende pour le masquer · Double-clic pour l'isoler")

    # ── Visibility selector (below chart) ──────────────────────────────────
    ca, cb = st.columns([9,1])
    with cb:
        all_sel = set(st.session_state[vis_key])>=set(all_names)
        if st.button("Tout ✓" if not all_sel else "Tout ✗",
                     key=f"all_{tab_key}", use_container_width=True):
            st.session_state[vis_key] = all_names[:] if not all_sel else [all_names[0]]
            st.rerun()
    with ca:
        sel = st.multiselect(
            "ETFs", all_names, default=st.session_state[vis_key],
            format_func=lambda x: next((f"{e['label']} ({e['name']})"
                                        for e in available if e["name"]==x), x),
            label_visibility="collapsed", key=f"ms_{tab_key}"
        )
        if set(sel)!=set(st.session_state[vis_key]):
            st.session_state[vis_key] = sel or [all_names[0]]
            st.rerun()
    st.markdown("")

    # ── Performance table ──────────────────────────────────────────────────
    with st.expander("📋 Tableau de performances", expanded=True):
        st.caption("Rendement total sur chaque période, trié par performance sur la période sélectionnée. Cliquer sur un en-tête de colonne pour trier.")
        rows = []
        for e in available:
            row = {"Actif": e["label"], "Ticker": e["name"]}
            for lbl,key in PERIODS.items():
                sl = prices.loc[prices.index>=period_start(key), e["ticker"]].dropna()
                row[lbl] = pct_ret(sl)
            rows.append(row)
        df = pd.DataFrame(rows).set_index("Actif")
        df_s = df.sort_values(period_label, ascending=False)
        cols_p = [c for c in PERIODS if c in df_s.columns]
        st.dataframe(
            df_s.style
                .format(fmt_pct, subset=cols_p)
                .map(color_cell, subset=cols_p)
                .set_properties(**{"text-align":"right"})
                .set_properties(subset=["Ticker"],**{"color":"#aaa","font-size":"11px"})
                .highlight_between(subset=[period_label],
                                   props="background-color:rgba(37,99,235,0.06)"),
            width="stretch", height=min(80+len(available)*36, 600)
        )

    # ── Heatmap ────────────────────────────────────────────────────────────
    with st.expander("🗓 Heatmap mensuelle", expanded=False):
        st.caption(
            "ℹ️ Chaque cellule = rendement de l'ETF sur le mois. "
            "Vert = hausse · Rouge = baisse · Intensité = amplitude. "
            "Permet d'identifier les mois de stress ou de sur-performance commune."
        )
        N=18
        ms = pd.date_range(end=today+pd.offsets.MonthBegin(1), periods=N+1, freq="MS")
        ml = [d.strftime("%b %y") for d in ms[:-1]]
        z,txt,ynames=[],[],[]
        for e in available:
            rz,rt=[],[]
            for i in range(N):
                sl=prices.loc[(prices.index>=ms[i])&(prices.index<ms[i+1]),e["ticker"]].dropna()
                v=pct_ret(sl)
                rz.append(v if v is not None else float("nan"))
                rt.append(f"{v:+.1f}%" if v is not None and v>=0 else
                          (f"{v:.1f}%" if v is not None else "—"))
            z.append(rz); txt.append(rt); ynames.append(e["name"])
        fh=go.Figure(go.Heatmap(
            z=z,x=ml,y=ynames,text=txt,texttemplate="%{text}",textfont=dict(size=10),
            colorscale=[[0,"#DC2626"],[0.5,"#f8fafc"],[1,"#16A34A"]],
            zmid=0,zmin=-8,zmax=8,
            hovertemplate="%{y} · %{x} : <b>%{text}</b><extra></extra>",
            showscale=True,colorbar=dict(ticksuffix="%",len=0.7,thickness=10)
        ))
        fh.update_layout(
            height=max(280,len(available)*32+60),margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(tickfont=dict(size=10),side="top"),
            yaxis=dict(tickfont=dict(size=11),autorange="reversed"),
            plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fh, width="stretch")

    # ── Correlation ────────────────────────────────────────────────────────
    with st.expander("🔗 Corrélations — 1 an", expanded=False):
        st.caption(
            "ℹ️ Corrélation Pearson sur les rendements journaliers de la dernière année. "
            "1.0 = actifs qui bougent identiquement · 0 = aucun lien · -1 = mouvement inverse. "
            "Idéalement, ton portefeuille devrait comporter des actifs faiblement corrélés entre eux."
        )
        cs=prices.loc[prices.index>=period_start("1y"),[e["ticker"] for e in available]].dropna()
        if len(cs)>=20:
            lr=np.log(cs/cs.shift(1)).dropna()
            cm=lr.corr().round(2)
            ns=[e["name"] for e in available if e["ticker"] in cm.columns]
            fc=go.Figure(go.Heatmap(
                z=cm.values.tolist(),x=ns,y=ns,
                text=[[f"{v:.2f}" for v in row] for row in cm.values],
                texttemplate="%{text}",textfont=dict(size=11),
                colorscale=[[0,"#DC2626"],[0.5,"#f8fafc"],[1,"#16A34A"]],
                zmid=0,zmin=-1,zmax=1,
                hovertemplate="%{y} / %{x} : <b>%{text}</b><extra></extra>",
                showscale=True,colorbar=dict(len=0.7,thickness=10)
            ))
            fc.update_layout(
                height=max(300,len(ns)*44+60),margin=dict(l=0,r=0,t=10,b=0),
                xaxis=dict(tickfont=dict(size=11),side="top"),
                yaxis=dict(tickfont=dict(size=11),autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fc, width="stretch")
        else:
            st.caption("Données insuffisantes.")

# ── Header ─────────────────────────────────────────────────────────────────────
cr, cb2 = st.columns([9,1])
with cr:
    st.markdown("# 📈 Portfolio Dashboard")
    st.markdown(
        "<p style='color:#64748b;font-size:14px;margin-top:-8px;margin-bottom:4px'>"
        "Compare l'évolution en % de tes actifs sur n'importe quelle période · "
        "Analyse leurs performances mensuelles et leurs corrélations · "
        "Ajoute tes propres tickers dans l'onglet <b>Mon portefeuille</b>."
        "</p>",
        unsafe_allow_html=True
    )
with cb2:
    st.markdown("<div style='margin-top:14px'>", unsafe_allow_html=True)
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
st.caption(f"Données Yahoo Finance · {now_paris.strftime('%d/%m/%Y %H:%M')} (Paris)")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_max, tab_custom = st.tabs(["📊 Portefeuille Maxence", "➕ Mon portefeuille"])

# ── Tab Maxence ────────────────────────────────────────────────────────────────
with tab_max:
    etf_max = [{**e,"color":PALETTE[i%len(PALETTE)]} for i,e in enumerate(DEFAULT_ETFS)]
    with st.spinner("Chargement…"):
        prices_max = load_prices(",".join(e["ticker"] for e in etf_max))
    if prices_max.empty:
        st.error("Impossible de charger les données.")
    else:
        render_dashboard(etf_max, prices_max, "default")

# ── Tab Mon portefeuille ───────────────────────────────────────────────────────
with tab_custom:
    st.caption(
        "Sélectionne tes actifs ci-dessous (ou commence à taper pour filtrer). "
        "Tu peux chercher des ETFs européens, actions US, crypto, indices…"
    )

    # Multiselect = portfolio selector (same layout as Maxence below-chart selector)
    all_labels = list(PRESET_MAP.keys())
    default_sel = st.session_state.get("custom_selection", [])
    # Keep only labels still in the preset map
    default_sel = [l for l in default_sel if l in PRESET_MAP]

    selection = st.multiselect(
        "Mes actifs",
        options=all_labels,
        default=default_sel,
        placeholder="Rechercher : Apple, CW8, Bitcoin, CAC 40…",
        label_visibility="collapsed",
        key="custom_ms_top"
    )
    st.session_state["custom_selection"] = selection

    if not selection:
        st.info(
            "👆 Tape le nom d'un actif pour le trouver et l'ajouter à ton portefeuille.\n\n"
            "Exemples : `MSCI World`, `Apple`, `Bitcoin`, `CAC`, `S&P 500`…"
        )
    else:
        etf_custom = [
            {**PRESET_MAP[lbl],
             "name": PRESET_MAP[lbl]["ticker"].split(".")[0].upper()[:6],
             "color": PALETTE[i%len(PALETTE)]}
            for i, lbl in enumerate(selection)
        ]
        # Reset custom visibility when selection changes
        if set(st.session_state.get("vis_custom") or []) != \
           set(e["name"] for e in etf_custom):
            st.session_state["vis_custom"] = [e["name"] for e in etf_custom]

        with st.spinner("Chargement…"):
            prices_custom = load_prices(",".join(e["ticker"] for e in etf_custom))
        if prices_custom.empty:
            st.error("Impossible de charger les données. Vérifier les symboles.")
        else:
            render_dashboard(etf_custom, prices_custom, "custom")

st.divider()
st.caption("Source : Yahoo Finance · Données auto-ajustées")
