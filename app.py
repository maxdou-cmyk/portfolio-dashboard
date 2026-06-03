"""
Portfolio Dashboard — Streamlit App
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime

st.set_page_config(
    page_title="Portfolio Base 100",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .block-container{padding:1.5rem 2rem 2rem;}
    h1{font-size:1.4rem !important;font-weight:600 !important;}
    h3{font-size:1rem !important;font-weight:500 !important;color:#666 !important;margin-top:1.5rem !important;}
    div[data-testid="stSegmentedControl"] > div{gap:4px;}
</style>
""", unsafe_allow_html=True)

PALETTE = [
    "#378ADD","#E24B4A","#0F6E56","#EF9F27","#533B89","#1D9E75",
    "#A32D2D","#639922","#185FA5","#BA7517","#5DCAA5","#D85A30","#7F77DD",
    "#2196F3","#FF5722","#9C27B0","#4CAF50","#FF9800","#607D8B","#795548"
]

DEFAULT_ETFS = [
    {"ticker":"CW8.PA",   "name":"CW8",   "label":"MSCI World"},
    {"ticker":"PE500.PA", "name":"PE500", "label":"S&P 500 (ESG)"},
    {"ticker":"PAASI.PA", "name":"PAASI", "label":"Émergents Asie"},
    {"ticker":"PUST.PA",  "name":"PUST",  "label":"Nasdaq-100"},
    {"ticker":"PAEEM.PA", "name":"PAEEM", "label":"Émergents Monde (ESG)"},
    {"ticker":"C50.PA",   "name":"C50",   "label":"Euro Stoxx 50"},
    {"ticker":"BNKE.PA",  "name":"BNKE",  "label":"Banques Europe"},
    {"ticker":"GOLD.PA",  "name":"GOLD",  "label":"Or physique"},
    {"ticker":"MMS.PA",   "name":"MMS",   "label":"Small Caps Europe"},
    {"ticker":"RS2K.PA",  "name":"RS2K",  "label":"Russell 2000 (US SC)"},
    {"ticker":"IROB.DE",  "name":"IROB",  "label":"Robotique mondiale"},
    {"ticker":"TNO.PA",   "name":"TNO",   "label":"Tech Europe 600"},
    {"ticker":"SEME.PA",  "name":"SEME",  "label":"Semiconducteurs"},
]

PERIODS = {
    "1S":"1w","1M":"1mo","3M":"3mo","6M":"6mo",
    "YTD":"ytd","1A":"1y","3A":"3y","5A":"5y"
}

# ── Ticker search via Yahoo Finance ────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def search_tickers(query: str) -> list:
    if len(query) < 2:
        return []
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}&lang=fr&region=FR&quotesCount=10"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if not r.ok:
            return []
        quotes = r.json().get("quotes", [])
        return [
            {
                "ticker": q["symbol"],
                "label":  q.get("shortname") or q.get("longname") or q["symbol"],
                "type":   q.get("quoteType", ""),
                "exchange": q.get("exchDisp", ""),
            }
            for q in quotes
            if q.get("symbol")
        ]
    except Exception:
        return []

# ── Data loading ───────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers_key: str) -> pd.DataFrame:
    tickers = [t.strip() for t in tickers_key.split(",") if t.strip()]
    if not tickers:
        return pd.DataFrame()
    try:
        data = yf.download(tickers, period="5y", auto_adjust=True, progress=False)
        if data.empty:
            return pd.DataFrame()

        # Handle yfinance column structure (changes across versions)
        if isinstance(data.columns, pd.MultiIndex):
            # Multi-ticker: columns = (price_type, ticker)
            close_key = next((k for k in data.columns.get_level_values(0).unique()
                              if str(k).lower() == "close"), None)
            if close_key is None:
                return pd.DataFrame()
            df = data[close_key].copy()
            if isinstance(df, pd.Series):
                df = df.to_frame(name=tickers[0])
        else:
            # Single-ticker or flat
            close_key = next((k for k in data.columns if str(k).lower() == "close"), None)
            if close_key is None:
                return pd.DataFrame()
            df = pd.DataFrame({tickers[0]: data[close_key]})

        # Normalise timezone
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        else:
            df.index = pd.to_datetime(df.index)

        return df.dropna(how="all")
    except Exception as e:
        st.warning(f"Erreur lors du téléchargement : {e}")
        return pd.DataFrame()

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    preset = st.selectbox("Portfolio", ["Portefeuille Maxence", "Mon portefeuille"])

    if preset == "Mon portefeuille":

        # ── Ticker search ──────────────────────────────────────────────────
        st.markdown("**Rechercher un ticker**")
        search_query = st.text_input(
            "Recherche", placeholder="Apple, CW8, Bitcoin…", label_visibility="collapsed"
        )
        if search_query:
            results = search_tickers(search_query)
            if results:
                for r in results:
                    st.caption(
                        f"`{r['ticker']}` — {r['label']}  "
                        f"<span style='color:#888;font-size:10px'>{r['type']} · {r['exchange']}</span>",
                        unsafe_allow_html=True
                    )
            else:
                st.caption("_Aucun résultat_")

        st.markdown("**Mes tickers** _(un par ligne)_")
        st.caption(
            "Format : `TICKER` ou `TICKER | Nom`\n\n"
            "Suffixes : `.PA` = Euronext Paris · `.DE` = XETRA · aucun = NYSE/Nasdaq\n\n"
            "Exemples : `CW8.PA`, `AAPL`, `MSFT | Microsoft`, `BTC-USD`"
        )
        user_input = st.text_area("Tickers", height=200, label_visibility="collapsed",
                                   key="custom_tickers_input")

        etf_list = []
        if user_input.strip():
            for i, line in enumerate(user_input.strip().splitlines()):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                ticker = parts[0].strip()
                label  = parts[1].strip() if len(parts) > 1 else ticker.split(".")[0].upper()
                etf_list.append({
                    "ticker": ticker,
                    "name":   ticker.split(".")[0].upper(),
                    "label":  label,
                    "color":  PALETTE[i % len(PALETTE)],
                })
        if not etf_list:
            st.info("Entrer au moins un ticker.")

    else:
        etf_list = [{**e, "color": PALETTE[i % len(PALETTE)]} for i, e in enumerate(DEFAULT_ETFS)]

    st.divider()

    # ── Period — boutons ───────────────────────────────────────────────────
    st.markdown("**Période**")
    period_label = st.segmented_control(
        "Période", options=list(PERIODS.keys()),
        default="1A", label_visibility="collapsed", key="period_ctrl"
    )
    if period_label is None:
        period_label = "1A"
    period_key = PERIODS[period_label]

    st.divider()
    st.caption(f"Données : Yahoo Finance\nMis à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()

# ── Stop if no list ────────────────────────────────────────────────────────
if not etf_list:
    st.stop()

# ── Load prices ────────────────────────────────────────────────────────────
tickers_key = ",".join(e["ticker"] for e in etf_list)

# Reset visible set when portfolio changes
if st.session_state.get("_last_tickers_key") != tickers_key:
    st.session_state["visible_names"] = [e["name"] for e in etf_list]
    st.session_state["_last_tickers_key"] = tickers_key

with st.spinner("Chargement des données…"):
    prices = load_prices(tickers_key)

if prices.empty:
    st.error(
        "Aucune donnée chargée. Vérifier les tickers. "
        "Utiliser la recherche dans la sidebar pour trouver les bons symboles."
    )
    st.stop()

available = [e for e in etf_list if e["ticker"] in prices.columns]
if not available:
    st.error("Aucun ticker reconnu. Vérifier les symboles (ex : CW8.PA, AAPL, BTC-USD).")
    st.stop()

# ── Visibility selector ────────────────────────────────────────────────────
all_names = [e["name"] for e in available]

col_sel, col_btn = st.columns([6, 1])
with col_btn:
    all_visible = set(st.session_state.get("visible_names", all_names)) >= set(all_names)
    if st.button("Tout ✓" if not all_visible else "Tout ✗", use_container_width=True):
        st.session_state["visible_names"] = all_names if not all_visible else [all_names[0]]
        st.rerun()

with col_sel:
    visible_names = st.multiselect(
        "ETFs visibles",
        options=all_names,
        default=st.session_state.get("visible_names", all_names),
        format_func=lambda x: next((e["label"] for e in available if e["name"] == x), x),
        label_visibility="collapsed",
        key="vis_select"
    )
    if visible_names != st.session_state.get("visible_names"):
        st.session_state["visible_names"] = visible_names or [all_names[0]]

visible_set = set(st.session_state.get("visible_names", all_names)) or {all_names[0]}
shown = [e for e in available if e["name"] in visible_set]

# ── Helpers ────────────────────────────────────────────────────────────────
today = pd.Timestamp.today().normalize()

def period_start(key: str) -> pd.Timestamp:
    if key == "1w":  return today - pd.Timedelta(weeks=1)
    if key == "1mo": return today - pd.DateOffset(months=1)
    if key == "3mo": return today - pd.DateOffset(months=3)
    if key == "6mo": return today - pd.DateOffset(months=6)
    if key == "ytd": return pd.Timestamp(today.year, 1, 1)
    if key == "1y":  return today - pd.DateOffset(years=1)
    if key == "3y":  return today - pd.DateOffset(years=3)
    if key == "5y":  return today - pd.DateOffset(years=5)
    return today - pd.DateOffset(years=1)

def pct_ret(series: pd.Series):
    s = series.dropna()
    if len(s) < 2: return None
    return (s.iloc[-1] / s.iloc[0] - 1) * 100

start  = period_start(period_key)
sliced = prices.loc[prices.index >= start]

# ── Header ─────────────────────────────────────────────────────────────────
date_from = sliced.index[0].strftime("%d/%m/%Y") if not sliced.empty else "—"
st.markdown(f"# 📈 Portfolio — Base 100 · {period_label}")
st.caption(f"{len(shown)} actifs affichés sur {len(available)} · {date_from} → {today.strftime('%d/%m/%Y')}")

# ── Base-100 chart ─────────────────────────────────────────────────────────
fig = go.Figure()
for e in shown:
    s = sliced[e["ticker"]].dropna()
    if len(s) < 2:
        continue
    b100 = (s / s.iloc[0] * 100).round(3)
    fig.add_trace(go.Scatter(
        x=b100.index, y=b100.values,
        name=f"{e['label']} ({e['name']})",
        line=dict(color=e["color"], width=1.8),
        hovertemplate=(
            f"<b>{e['label']} ({e['name']})</b><br>"
            "%{x|%d/%m/%Y}<br>"
            "Base 100 : <b>%{y:.2f}</b><extra></extra>"
        )
    ))

fig.update_layout(
    height=430, margin=dict(l=0, r=0, t=10, b=0),
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.18, font=dict(size=11),
                itemclick="toggle", itemdoubleclick="toggleothers"),
    xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)", zeroline=False),
    yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
)
fig.add_hline(y=100, line_dash="dot", line_color="rgba(128,128,128,0.4)", line_width=1)
st.plotly_chart(fig, width="stretch")
st.caption("💡 Cliquer sur un actif dans la légende pour le masquer · Double-clic pour l'isoler")

# ── Performance table ──────────────────────────────────────────────────────
st.markdown("### Performances comparées")

rows = []
for e in available:
    row = {"Actif": f"{e['label']} ({e['name']})"}
    for lbl, key in PERIODS.items():
        sl = prices.loc[prices.index >= period_start(key), e["ticker"]].dropna()
        row[lbl] = pct_ret(sl)
    rows.append(row)

df_perf = pd.DataFrame(rows).set_index("Actif")
df_perf_sorted = df_perf.sort_values(period_label, ascending=False)

def fmt_pct(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "—"
    return f"+{x:.1f}%" if x >= 0 else f"{x:.1f}%"

def color_cell(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return ""
    return "color:#0F6E56;font-weight:500" if x >= 0 else "color:#A32D2D;font-weight:500"

styled_perf = (
    df_perf_sorted.style
    .format(fmt_pct)
    .map(color_cell)
    .set_properties(**{"text-align": "right"})
    .highlight_between(subset=[period_label], props="background-color:rgba(0,0,0,0.04)")
)
st.dataframe(styled_perf, width="stretch", height=min(70 + len(available) * 36, 580))

# ── Monthly heatmap ────────────────────────────────────────────────────────
st.markdown("### Rendements mensuels — 18 derniers mois")

N = 18
month_starts = pd.date_range(end=today + pd.offsets.MonthBegin(1), periods=N+1, freq="MS")
month_labels = [d.strftime("%b %y") for d in month_starts[:-1]]

heat_rows, heat_names = [], []
for e in available:
    row = []
    for i in range(N):
        s   = month_starts[i]
        end = month_starts[i+1]
        sl  = prices.loc[(prices.index >= s) & (prices.index < end), e["ticker"]].dropna()
        v   = pct_ret(sl)
        row.append(round(v, 2) if v is not None else None)
    heat_rows.append(row)
    heat_names.append(e["name"])

z_heat    = [[v if v is not None else float("nan") for v in row] for row in heat_rows]
text_heat = [
    [f"+{v:.1f}%" if v is not None and v >= 0 else (f"{v:.1f}%" if v is not None else "—") for v in row]
    for row in heat_rows
]

fig_heat = go.Figure(go.Heatmap(
    z=z_heat, x=month_labels, y=heat_names,
    text=text_heat, texttemplate="%{text}", textfont=dict(size=10),
    colorscale=[[0,"#A32D2D"],[0.5,"#f5f5f0"],[1,"#0F6E56"]],
    zmid=0, zmin=-8, zmax=8,
    hovertemplate="%{y} · %{x} : <b>%{text}</b><extra></extra>",
    showscale=True, colorbar=dict(ticksuffix="%", len=0.6, thickness=12)
))
fig_heat.update_layout(
    height=max(300, len(available) * 34 + 60),
    margin=dict(l=0, r=0, t=10, b=0),
    xaxis=dict(tickfont=dict(size=10), side="top"),
    yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
)
st.plotly_chart(fig_heat, width="stretch")

# ── Correlation ────────────────────────────────────────────────────────────
st.markdown("### Matrice de corrélation — 1 an")
st.caption("Corrélation Pearson sur les rendements journaliers · Vert = corrélés · Rouge = décorrélés")

corr_slice = prices.loc[prices.index >= period_start("1y"), [e["ticker"] for e in available]].dropna()
if len(corr_slice) >= 20:
    log_ret     = np.log(corr_slice / corr_slice.shift(1)).dropna()
    corr_matrix = log_ret.corr().round(2)
    names_corr  = [e["name"] for e in available if e["ticker"] in corr_matrix.columns]
    z_corr      = corr_matrix.values.tolist()
    txt_corr    = [[f"{v:.2f}" for v in row] for row in z_corr]

    fig_corr = go.Figure(go.Heatmap(
        z=z_corr, x=names_corr, y=names_corr,
        text=txt_corr, texttemplate="%{text}", textfont=dict(size=11),
        colorscale=[[0,"#A32D2D"],[0.5,"#f5f5f0"],[1,"#0F6E56"]],
        zmid=0, zmin=-1, zmax=1,
        hovertemplate="%{y} / %{x} : <b>%{text}</b><extra></extra>",
        showscale=True, colorbar=dict(len=0.6, thickness=12)
    ))
    fig_corr.update_layout(
        height=max(320, len(names_corr) * 46 + 60),
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(tickfont=dict(size=11), side="top"),
        yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_corr, width="stretch")
else:
    st.caption("Données insuffisantes pour calculer la corrélation.")

st.divider()
st.caption("Source : Yahoo Finance · Données auto-ajustées")
