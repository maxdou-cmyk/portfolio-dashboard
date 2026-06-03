"""
Portfolio Dashboard — Streamlit App
Déployable gratuitement sur Streamlit Community Cloud
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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
    h1{font-size:1.4rem !important; font-weight:600 !important;}
    h3{font-size:1rem !important; font-weight:500 !important; color:#666 !important; margin-top:1.5rem !important;}
</style>
""", unsafe_allow_html=True)

# ── Palette de couleurs ────────────────────────────────────────────────────
PALETTE = [
    "#378ADD","#E24B4A","#0F6E56","#EF9F27","#533B89","#1D9E75",
    "#A32D2D","#639922","#185FA5","#BA7517","#5DCAA5","#D85A30","#7F77DD",
    "#2196F3","#FF5722","#9C27B0","#4CAF50","#FF9800","#607D8B","#795548"
]

# ── Portefeuille par défaut (Maxence) ──────────────────────────────────────
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

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    preset = st.selectbox(
        "Portfolio",
        ["Portefeuille Maxence", "Mon portefeuille personnalisé"]
    )

    if preset == "Mon portefeuille personnalisé":
        st.caption(
            "Entrer vos tickers Yahoo Finance, **un par ligne**.\n\n"
            "Format : `TICKER` ou `TICKER | Nom affiché`\n\n"
            "Exemples :\n"
            "```\nCW8.PA\nAAPL | Apple\nBTC-USD | Bitcoin\nSP500.PA | S&P 500\n```"
        )
        user_input = st.text_area("Mes tickers", height=220, key="custom_tickers")
        etf_list = []
        if user_input.strip():
            for i, line in enumerate(user_input.strip().splitlines()):
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split("|")]
                ticker = parts[0].strip()
                label  = parts[1].strip() if len(parts) > 1 else ticker.split(".")[0].upper()
                etf_list.append({
                    "ticker": ticker,
                    "name":   ticker.split(".")[0].upper(),
                    "label":  label,
                    "color":  PALETTE[i % len(PALETTE)]
                })
        if not etf_list:
            st.info("Entrer au moins un ticker pour commencer.")
    else:
        etf_list = [{**e, "color": PALETTE[i % len(PALETTE)]} for i, e in enumerate(DEFAULT_ETFS)]

    st.divider()

    PERIODS = {
        "1 semaine": "1w",  "1 mois": "1mo",  "3 mois": "3mo",
        "6 mois":    "6mo", "YTD":    "ytd",   "1 an":   "1y",
        "3 ans":     "3y",  "5 ans":  "5y",
    }
    period_label = st.select_slider("Période", options=list(PERIODS.keys()), value="1 an")
    period_key   = PERIODS[period_label]

    st.divider()
    st.caption(f"Données : Yahoo Finance  \nMis à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    if st.button("🔄 Rafraîchir les données"):
        st.cache_data.clear()
        st.rerun()

# ── Stop if no tickers ─────────────────────────────────────────────────────
if not etf_list:
    st.stop()

# ── Chargement des données ─────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers_key: str) -> pd.DataFrame:
    tickers = [t.strip() for t in tickers_key.split(",")]
    data = yf.download(tickers, period="5y", auto_adjust=True, progress=False)
    if data.empty:
        return pd.DataFrame()
    if len(tickers) == 1:
        df = pd.DataFrame({tickers[0]: data["Close"]})
    else:
        df = data["Close"].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df

tickers_key = ",".join(e["ticker"] for e in etf_list)
with st.spinner("Téléchargement des données..."):
    prices = load_prices(tickers_key)

if prices.empty:
    st.error("Aucune donnée chargée. Vérifier les tickers.")
    st.stop()

available = [e for e in etf_list if e["ticker"] in prices.columns]
if not available:
    st.error("Aucun ticker valide reconnu par Yahoo Finance.")
    st.stop()

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
st.caption(f"{len(available)} actifs · {date_from} → {today.strftime('%d/%m/%Y')}")

# ── Base-100 chart ─────────────────────────────────────────────────────────
fig = go.Figure()
for e in available:
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
    height=430,
    margin=dict(l=0, r=0, t=10, b=0),
    hovermode="x unified",
    legend=dict(
        orientation="h", y=-0.18,
        font=dict(size=11),
        itemclick="toggle", itemdoubleclick="toggleothers"
    ),
    xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)", zeroline=False),
    yaxis=dict(
        showgrid=True, gridcolor="rgba(128,128,128,0.15)",
        ticksuffix="", tickformat=".0f",
    ),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
fig.add_hline(y=100, line_dash="dot", line_color="rgba(128,128,128,0.4)", line_width=1)
st.plotly_chart(fig, use_container_width=True)
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
# Sort by selected period descending
df_perf_sorted = df_perf.sort_values(period_label, ascending=False)

def fmt_pct(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "—"
    return f"+{x:.1f}%" if x >= 0 else f"{x:.1f}%"

def color_cell(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return ""
    return "color: #0F6E56; font-weight:500" if x >= 0 else "color: #A32D2D; font-weight:500"

styled_perf = (
    df_perf_sorted
    .style
    .format(fmt_pct)
    .applymap(color_cell)
    .set_properties(**{"text-align": "right"})
    .highlight_between(subset=[period_label], props="background-color: rgba(0,0,0,0.04)")
)
st.dataframe(styled_perf, use_container_width=True, height=min(70 + len(available) * 36, 580))

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
        row.append(round(pct_ret(sl), 2) if pct_ret(sl) is not None else None)
    heat_rows.append(row)
    heat_names.append(e["name"])

z_heat    = [[v if v is not None else float("nan") for v in row] for row in heat_rows]
text_heat = [[f"+{v:.1f}%" if v is not None and v >= 0 else (f"{v:.1f}%" if v is not None else "—")
              for v in row] for row in heat_rows]

fig_heat = go.Figure(go.Heatmap(
    z=z_heat, x=month_labels, y=heat_names,
    text=text_heat, texttemplate="%{text}", textfont=dict(size=10),
    colorscale=[[0,"#A32D2D"],[0.5,"#f5f5f0"],[1,"#0F6E56"]],
    zmid=0, zmin=-8, zmax=8,
    hovertemplate="%{y} · %{x} : <b>%{text}</b><extra></extra>",
    showscale=True,
    colorbar=dict(ticksuffix="%", len=0.6, thickness=12)
))
fig_heat.update_layout(
    height=max(300, len(available) * 34 + 60),
    margin=dict(l=0, r=0, t=10, b=0),
    xaxis=dict(tickfont=dict(size=10), side="top"),
    yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
)
st.plotly_chart(fig_heat, use_container_width=True)

# ── Correlation ────────────────────────────────────────────────────────────
st.markdown("### Matrice de corrélation — 1 an")
st.caption("Corrélation Pearson sur les rendements journaliers. Vert = corrélés · Rouge = décorrélés")

corr_slice = prices.loc[prices.index >= period_start("1y"), [e["ticker"] for e in available]].dropna()
if len(corr_slice) >= 20:
    log_ret = np.log(corr_slice / corr_slice.shift(1)).dropna()
    corr    = log_ret.corr().round(2)
    names   = [e["name"] for e in available if e["ticker"] in corr.columns]
    z_corr  = corr.values.tolist()
    txt_corr= [[f"{v:.2f}" for v in row] for row in z_corr]

    fig_corr = go.Figure(go.Heatmap(
        z=z_corr, x=names, y=names,
        text=txt_corr, texttemplate="%{text}", textfont=dict(size=11),
        colorscale=[[0,"#A32D2D"],[0.5,"#f5f5f0"],[1,"#0F6E56"]],
        zmid=0, zmin=-1, zmax=1,
        hovertemplate="%{y} / %{x} : <b>%{text}</b><extra></extra>",
        showscale=True,
        colorbar=dict(len=0.6, thickness=12)
    ))
    fig_corr.update_layout(
        height=max(320, len(names) * 46 + 60),
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(tickfont=dict(size=11), side="top"),
        yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_corr, use_container_width=True)
else:
    st.caption("Données insuffisantes pour calculer la corrélation.")

# ── Footer ─────────────────────────────────────────────────────────────────
st.divider()
st.caption("Source : Yahoo Finance · Données non-ajustées des dividendes pour certains ETFs")
