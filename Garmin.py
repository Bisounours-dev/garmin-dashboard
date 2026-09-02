# ==========================================================
#  RUN ANALYTICS · Garmin export viewer
#  streamlit run Desktop\Garmin\Footing.py
# ==========================================================
import json
import os
import shutil
import tempfile
import zipfile
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from plotly.subplots import make_subplots

# ----------------------------------------------------------
# 0. DARK MODE AUTOMATIQUE (crée .streamlit/config.toml)
# ----------------------------------------------------------
THEME_TOML = """[theme]
base = "dark"
primaryColor = "#5B8FF9"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#161B26"
textColor = "#E6E9EF"
font = "sans serif"
"""
try:
    _cfg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit")
    _cfg = os.path.join(_cfg_dir, "config.toml")
    _cfg_created = False
    if not os.path.exists(_cfg):
        os.makedirs(_cfg_dir, exist_ok=True)
        with open(_cfg, "w", encoding="utf-8") as _f:
            _f.write(THEME_TOML)
        _cfg_created = True
except Exception:
    _cfg_created = False

# ----------------------------------------------------------
# 1. CONFIG & THEME
# ----------------------------------------------------------
st.set_page_config(
    page_title="Run Analytics · Garmin",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = r"C:/Users/roros/Desktop/Garmin"
DATA_DIR = os.path.join(BASE_DIR, "Data_Garmin")

HR_MAX_DEFAULT = 210          # <<< ta FC max

C = {
    "bg":    "#0E1117",
    "pace":  "#5B8FF9",
    "hr":    "#FF6B6B",
    "dist":  "#36CFC9",
    "eff":   "#FFC53D",
    "load":  "#9F7AEA",
    "ok":    "#4ADE80",
    "warn":  "#FBBF24",
    "bad":   "#F87171",
    "txt":   "#E6E9EF",
    "muted": "#8B93A7",
    "grid":  "rgba(255,255,255,0.06)",
    "card":  "#161B26",
}

FEEL_ORDER = [0, 25, 50, 75, 100]
FEEL_NAME  = {0: "Très faible", 25: "Faible", 50: "Normal", 75: "Fort", 100: "Très fort"}
FEEL_COL   = {0: "#F87171", 25: "#FB923C", 50: "#FBBF24", 75: "#A3E635", 100: "#4ADE80"}
FEEL_EMO   = {0: "😵", 25: "😕", 50: "😐", 75: "🙂", 100: "🤩"}

pio.templates["run"] = go.layout.Template(
    layout=dict(
        font=dict(family="Inter, Segoe UI, system-ui, sans-serif", size=13, color=C["txt"]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[C["pace"], C["hr"], C["dist"], C["eff"], C["load"], C["ok"]],
        title=dict(font=dict(size=17, color=C["txt"]), x=0.01, xanchor="left", y=0.96),
        # ↓↓↓ marges généreuses : plus d'axes coupés
        margin=dict(l=20, r=25, t=75, b=60),
        hoverlabel=dict(bgcolor="#0B0E14", bordercolor="rgba(255,255,255,0.15)",
                        font=dict(size=12, color=C["txt"])),
        xaxis=dict(gridcolor=C["grid"], zeroline=False, linecolor=C["grid"], automargin=True,
                   nticks=8, tickangle=0,
                   tickfont=dict(color=C["muted"], size=11.5),
                   title_font=dict(color=C["muted"], size=12), title_standoff=12),
        yaxis=dict(gridcolor=C["grid"], zeroline=False, linecolor=C["grid"], automargin=True,
                   tickfont=dict(color=C["muted"], size=11.5),
                   title_font=dict(color=C["muted"], size=12), title_standoff=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
    )
)
pio.templates.default = "run"

PLOTLY_CFG = {"displaylogo": False, "responsive": True,
              "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}

st.markdown(f"""
<style>
/* ---- dark mode forcé (secours si config.toml pas encore chargé) ---- */
.stApp, [data-testid="stAppViewContainer"] {{background-color:{C['bg']} !important; color:{C['txt']} !important;}}
[data-testid="stHeader"] {{background:rgba(0,0,0,0) !important;}}
section[data-testid="stSidebar"] {{background-color:{C['card']} !important;}}
section[data-testid="stSidebar"] * {{color:{C['txt']} !important;}}
.stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{color:{C['txt']};}}
[data-testid="stCaptionContainer"] p {{color:{C['muted']} !important;}}

#MainMenu, footer {{visibility:hidden;}}
div[data-testid="stElementToolbar"] {{display:none;}}   /* pas de bouton d'export */
.block-container {{padding-top:2rem; padding-bottom:3rem; max-width:1300px;}}
h1,h2,h3 {{letter-spacing:-.4px;}}
h4 {{margin-top:1.4rem !important;}}

.hero {{background:linear-gradient(120deg, rgba(91,143,249,.18), rgba(159,122,234,.10) 50%, rgba(54,207,201,.14));
  border:1px solid rgba(255,255,255,.07); border-radius:18px; padding:20px 24px; margin-bottom:20px;}}
.hero h1 {{margin:0; font-size:29px;}}
.hero p {{margin:6px 0 0; color:{C['muted']}; font-size:14px;}}

.kpi {{background:{C['card']}; border:1px solid rgba(255,255,255,.06); border-radius:14px;
  padding:13px 15px; height:100%; border-left:3px solid var(--acc); transition:.2s;}}
.kpi:hover {{transform:translateY(-2px); border-color:rgba(255,255,255,.16);}}
.kpi-lab {{font-size:11px; letter-spacing:.5px; text-transform:uppercase; color:{C['muted']};}}
.kpi-val {{font-size:25px; font-weight:700; line-height:1.25; margin-top:2px;}}
.kpi-val small {{font-size:13px; font-weight:500; color:{C['muted']};}}
.kpi-dlt {{font-size:11.5px; margin-top:3px;}}
.up {{color:{C['ok']};}} .down {{color:{C['bad']};}} .flat {{color:{C['muted']};}}

div[data-testid="stTabs"] button {{font-size:14.5px; font-weight:600;}}
div[data-testid="stTabs"] button[aria-selected="true"] {{color:{C['pace']};}}
</style>
""", unsafe_allow_html=True)

if _cfg_created:
    st.toast("🌙 Thème sombre installé (.streamlit/config.toml) — relance l'app une fois.", icon="🌙")


# ----------------------------------------------------------
# 2. HELPERS
# ----------------------------------------------------------
def fmt_pace(p):
    """4.53 min/km -> '4:32'"""
    if p is None or pd.isna(p) or np.isinf(p):
        return "—"
    m, s = int(p), int(round((p - int(p)) * 60))
    if s == 60:
        m, s = m + 1, 0
    return f"{m}:{s:02d}"


def pace_ticks(series, step=0.25):
    s = pd.Series(series).dropna()
    if s.empty:
        return None, None
    vals = np.arange(np.floor(s.min() / step) * step, np.ceil(s.max() / step) * step + step, step)
    return list(vals), [fmt_pace(v) for v in vals]


def num(df, col):
    return pd.to_numeric(df[col], errors="coerce") if col in df.columns else pd.Series(np.nan, index=df.index)


def show(fig, height=430):
    fig.update_layout(height=height)
    st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOTLY_CFG)


def kpi(col, label, value, unit="", delta=None, delta_txt="vs 28 j préc.",
        color=C["pace"], reverse=False):
    """reverse=True -> une baisse est une bonne nouvelle (allure, FC)."""
    if delta is None or pd.isna(delta):
        d_html = '<div class="kpi-dlt flat">— pas de comparatif</div>'
    else:
        good = (delta < 0) if reverse else (delta > 0)
        cls = "up" if good else ("down" if delta != 0 else "flat")
        arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "▬")
        d_html = (f'<div class="kpi-dlt {cls}">{arrow} {abs(delta):.1f}% '
                  f'<span style="color:{C["muted"]}">{delta_txt}</span></div>')
    col.markdown(
        f'<div class="kpi" style="--acc:{color}">'
        f'<div class="kpi-lab">{label}</div>'
        f'<div class="kpi-val">{value}<small> {unit}</small></div>{d_html}</div>',
        unsafe_allow_html=True,
    )


def pct(new, old):
    if old is None or pd.isna(old) or old == 0 or pd.isna(new):
        return None
    return (new - old) / old * 100


# ----------------------------------------------------------
# 3. DONNÉES  (logique d'origine conservée)
# ----------------------------------------------------------
st.sidebar.markdown("### ⚙️ Paramètres")

with st.sidebar.expander("📁 Données Garmin", expanded=not os.path.exists(DATA_DIR)):
    uploaded_file = st.file_uploader("Charger une sauvegarde Garmin (.zip)", type=["zip"])

    if uploaded_file is not None:
        if st.button("📥 Remplacer les données Garmin", use_container_width=True):
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_path = os.path.join(temp_dir, "garmin.zip")

                    with open(zip_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(temp_dir)

                    garmin_root = None
                    for root, dirs, files in os.walk(temp_dir):
                        if "DI_CONNECT" in dirs:
                            garmin_root = root
                            break

                    if garmin_root is None:
                        st.error("❌ Impossible de trouver le dossier DI_CONNECT dans le fichier ZIP.")
                        st.stop()

                    json_found = None
                    for root, dirs, files in os.walk(garmin_root):
                        for file in files:
                            if file.endswith("_summarizedActivities.json"):
                                json_found = os.path.join(root, file)
                                break
                        if json_found is not None:
                            break

                    if json_found is None:
                        st.error("❌ Aucun fichier *_summarizedActivities.json n'a été trouvé dans le ZIP.")
                        st.stop()

                    new_data_dir = os.path.join(temp_dir, "Data_Garmin")
                    shutil.copytree(garmin_root, new_data_dir)

                    if os.path.exists(DATA_DIR):
                        shutil.rmtree(DATA_DIR)

                    shutil.move(new_data_dir, DATA_DIR)

                    st.cache_data.clear()          # force la relecture des nouvelles données
                    st.success("✅ Les données Garmin ont été remplacées.")
                    st.rerun()

            except zipfile.BadZipFile:
                st.error("❌ Le fichier sélectionné n'est pas un ZIP valide.")
            except Exception as e:
                st.error(f"❌ Une erreur est survenue : {e}")

# --- Recherche du fichier JSON (comme avant : le premier trouvé) ---
JSON_FILE = None
if os.path.exists(DATA_DIR):
    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith("_summarizedActivities.json"):
                JSON_FILE = os.path.join(root, file)
                break
        if JSON_FILE is not None:
            break

if JSON_FILE is None:
    st.markdown('<div class="hero"><h1>🏃 Run Analytics</h1>'
                '<p>⚠️ Aucune donnée Garmin trouvée. Charge une sauvegarde ZIP dans la barre latérale.</p></div>',
                unsafe_allow_html=True)
    st.stop()


@st.cache_data(show_spinner="Lecture de l'export Garmin…")
def load_runs(json_path, mtime):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data[0]["summarizedActivitiesExport"])
    df = df[df.get("sportType", "").astype(str).str.upper() == "RUNNING"].copy()
    if df.empty:
        return df

    df["Date"] = pd.to_datetime(num(df, "startTimeLocal"), unit="ms")
    df["Distance (km)"] = num(df, "distance") / 100_000
    df["Temps (min)"] = num(df, "duration") / 60_000
    df["Allure (min/km)"] = df["Temps (min)"] / df["Distance (km)"]
    df["Vitesse (km/h)"] = 60 / df["Allure (min/km)"]
    df["BPM moyen"] = num(df, "avgHr")
    df["BPM max"] = num(df, "maxHr")
    df["Température"] = (num(df, "minTemperature") + num(df, "maxTemperature")) / 2
    df["Indice efficacité"] = df["Vitesse (km/h)"] / df["BPM moyen"] * 100
    df["Allure txt"] = df["Allure (min/km)"].map(fmt_pace)
    df["Effet entraînement"] = df["trainingEffectLabel"].fillna("Non renseigné")

    rpe_map = {0: "Non renseigné", 10: "Très facile", 20: "Facile", 30: "Plutôt facile",
               40: "Modéré", 50: "Assez difficile", 60: "Difficile", 70: "Très difficile",
               80: "Éprouvant", 90: "Maximal", 100: "Échec"}
    df["RPE"] = num(df, "workoutRpe")
    df["Sensation"] = df["RPE"].map(rpe_map).fillna("Non renseigné")
    
    feel = pd.Series(np.nan, index=df.index)
    for c in ("directWorkoutFeel", "workoutFeel", "feel"):
        if c in df.columns:
            feel = feel.fillna(num(df, c))
    df["Feel"] = feel.round(-1).where(feel.isna() | feel.between(0, 100))
    df["Feel"] = (df["Feel"] / 25).round() * 25          # cale sur 0/25/50/75/100
    df["Ressenti"] = df["Feel"].map(FEEL_NAME)

    return df[df["Distance (km)"] > 0.3].sort_values("Date").reset_index(drop=True)


runs = load_runs(JSON_FILE, os.path.getmtime(JSON_FILE))

if runs.empty:
    st.error("Aucune course trouvée dans cet export.")
    st.stop()


# --- Filtres ----------------------------------------------
with st.sidebar:
    period = st.radio("Période", ["30 jours", "3 mois", "Tout"], index=2, horizontal=True)
    dmin = st.slider("Distance minimale (km)", 0.0, 15.0, 1.0, 0.5)
    hrmax = st.number_input("FC max (bpm)", 150, 220, HR_MAX_DEFAULT, 1,
                            help="Base de calcul des zones d'intensité et de la charge.")
    smooth = st.slider("Lissage des tendances (nb séances)", 3, 15, 7, 2)
    st.caption(f"📄 {os.path.basename(JSON_FILE)} · {len(runs)} courses · "
               f"maj {pd.to_datetime(os.path.getmtime(JSON_FILE), unit='s'):%d/%m/%Y}")

days = {"30 jours": 30, "3 mois": 92, "Tout": 100_000}[period]
tmax = runs["Date"].max()
d = runs[(runs["Date"] >= tmax - timedelta(days=days)) &
         (runs["Distance (km)"] >= dmin)].copy()

if d.empty:
    st.warning("Aucune séance ne correspond aux filtres.")
    st.stop()

# --- Zones d'intensité calculées sur la FC max -------------
Z_PCT = [0, 60, 70, 80, 87, 200]           # bornes en % FCmax
Z_NAME = ["Z1 · Récupération", "Z2 · Endurance fondamentale", "Z3 · Endurance active",
          "Z4 · Tempo / Seuil", "Z5 · VMA"]
Z_HEX = ["#38BDF8", C["ok"], C["warn"], "#FB923C", C["bad"]]
bpm_lim = [round(p / 100 * hrmax) for p in Z_PCT]
zlabs = [f"{Z_NAME[i]}  ({bpm_lim[i]}–{bpm_lim[i+1] if i < 4 else hrmax}+ bpm)" if i == 4
         else f"{Z_NAME[i]}  ({bpm_lim[i]}–{bpm_lim[i+1]} bpm)" for i in range(5)]
zcols = dict(zip(zlabs, Z_HEX))

d["%FCmax"] = d["BPM moyen"] / hrmax * 100
d["Zone"] = pd.cut(d["%FCmax"], bins=Z_PCT, labels=zlabs, right=False)

inten = 1 + 4 * np.clip((d["%FCmax"] - 60) / 30, 0, 1)      # intensité 1 → 5
d["Charge"] = d["Temps (min)"] * inten.fillna(2.0)

daily = d.set_index("Date").resample("D").agg({"Distance (km)": "sum", "Charge": "sum"})
d["Semaine"] = d["Date"].dt.to_period("W-SUN").dt.start_time


# ----------------------------------------------------------
# 4. HERO + KPI
# ----------------------------------------------------------
st.markdown(
    f'<div class="hero"><h1>🏃 Run Analytics</h1>'
    f'<p>{len(d)} séances · {d["Distance (km)"].sum():.0f} km · '
    f'{d["Temps (min)"].sum()/60:.0f} h · FC max référence {hrmax} bpm · '
    f'du {d["Date"].min():%d/%m/%Y} au {d["Date"].max():%d/%m/%Y}</p></div>',
    unsafe_allow_html=True,
)

cur = d[d["Date"] >= tmax - timedelta(days=28)]
prev = d[(d["Date"] < tmax - timedelta(days=28)) & (d["Date"] >= tmax - timedelta(days=56))]

r1 = st.columns(3)
kpi(r1[0], "Volume 28 j", f'{cur["Distance (km)"].sum():.0f}', "km",
    pct(cur["Distance (km)"].sum(), prev["Distance (km)"].sum()), color=C["dist"])
kpi(r1[1], "Allure moyenne 28 j",
    fmt_pace(cur["Temps (min)"].sum() / max(cur["Distance (km)"].sum(), 1e-9)), "/km",
    pct(cur["Allure (min/km)"].mean(), prev["Allure (min/km)"].mean()), color=C["pace"], reverse=True)
kpi(r1[2], "FC moyenne 28 j", f'{cur["BPM moyen"].mean():.0f}', "bpm",
    pct(cur["BPM moyen"].mean(), prev["BPM moyen"].mean()), color=C["hr"], reverse=True)

st.write("")
r2 = st.columns(3)
kpi(r2[0], "Indice efficacité", f'{cur["Indice efficacité"].mean():.2f}', "",
    pct(cur["Indice efficacité"].mean(), prev["Indice efficacité"].mean()), color=C["eff"])
kpi(r2[1], "Séances 28 j", f'{len(cur)}', "runs", pct(len(cur), len(prev)), color=C["load"])
kpi(r2[2], "Plus longue sortie 28 j", f'{cur["Distance (km)"].max():.1f}', "km",
    pct(cur["Distance (km)"].max(), prev["Distance (km)"].max() if len(prev) else None),
    color="#94A3B8")

st.write("")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["  📈 Vue d'ensemble  ", "  ⚡ Performance  ",
                                        "  🏋️ Charge & volume  ", "  😊 Ressenti  ",
                                        "  🗂️ Séances  "])


# ==========================================================
# TAB 1 · VUE D'ENSEMBLE
# ==========================================================
with tab1:
    dsz = d["Distance (km)"]
    sizes = 8 + 13 * (dsz - dsz.min()) / max(dsz.max() - dsz.min(), 1e-9)
    cd = np.stack([d["Allure txt"], d["Distance (km)"], d["BPM moyen"],
                   d["Ressenti"], d["Température"].round(0)], axis=-1)

    f = make_subplots(specs=[[{"secondary_y": True}]])
    f.add_trace(go.Scatter(
        x=d["Date"], y=d["Allure (min/km)"], mode="markers", name="Allure (séance)",
        marker=dict(size=sizes, color=C["pace"], opacity=.45,
                    line=dict(width=1, color="rgba(255,255,255,.25)")),
        customdata=cd,
        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>🏃 Allure <b>%{customdata[0]}</b> /km"
                      "<br>📏 %{customdata[1]:.1f} km · ❤️ %{customdata[2]:.0f} bpm"
                      "<br>😊 %{customdata[3]} · 🌡️ %{customdata[4]}°C<extra></extra>"))
    f.add_trace(go.Scatter(
        x=d["Date"], y=d["Allure (min/km)"].rolling(smooth, min_periods=2, center=True).mean(),
        mode="lines", name=f"Tendance allure ({smooth})",
        line=dict(color=C["pace"], width=3.5, shape="spline"), hoverinfo="skip"))
    f.add_trace(go.Scatter(
        x=d["Date"], y=d["BPM moyen"].rolling(smooth, min_periods=2, center=True).mean(),
        mode="lines", name=f"Tendance FC ({smooth})",
        line=dict(color=C["hr"], width=3.5, shape="spline", dash="dot"),
        hoverinfo="skip"), secondary_y=True)

    tv, tt = pace_ticks(d["Allure (min/km)"])
    f.update_yaxes(title_text="Allure (min/km)", autorange="reversed",
                   tickvals=tv, ticktext=tt, secondary_y=False)
    f.update_yaxes(title_text="FC moyenne (bpm)", showgrid=False,
                   automargin=True, tickfont=dict(color=C["muted"], size=11.5),
                   title_font=dict(color=C["muted"], size=12), secondary_y=True)
    f.update_xaxes(title_text="Date", tickformat="%d %b")
    f.update_layout(title="Allure & fréquence cardiaque · <i>objectif : la bleue monte, la rouge descend</i>",
                    hovermode="closest")
    show(f, 480)
    st.caption("💡 Taille des points bleus = distance de la séance. "
               "Une allure qui s'améliore **à FC égale ou plus basse** = vraie progression.")

    # ---- Volume hebdo -------------------------------------
    st.markdown("#### 📅 Volume hebdomadaire")
    wkly = (d.groupby("Semaine")
              .agg(km=("Distance (km)", "sum"), n=("Distance (km)", "size"),
                   mn=("Temps (min)", "sum")).reset_index()
              .set_index("Semaine").asfreq("7D").fillna(0).reset_index())
    wkly["ma4"] = wkly["km"].rolling(4, min_periods=1).mean()

    fv = go.Figure()
    fv.add_bar(x=wkly["Semaine"], y=wkly["km"], name="Volume de la semaine",
               marker=dict(color=C["dist"], opacity=.8, line_width=0),
               text=wkly["km"].map(lambda v: f"{v:.0f}" if v > 0 else ""),
               textposition="outside", textfont=dict(color=C["muted"], size=11),
               customdata=np.stack([wkly["n"], wkly["mn"] / 60], -1),
               hovertemplate="Semaine du %{x|%d/%m}<br><b>%{y:.1f} km</b>"
                             "<br>%{customdata[0]:.0f} séances · %{customdata[1]:.1f} h<extra></extra>")
    fv.add_trace(go.Scatter(x=wkly["Semaine"], y=wkly["ma4"], name="Moyenne 4 semaines",
                            line=dict(color=C["eff"], width=3, shape="spline"), hoverinfo="skip"))
    fv.update_xaxes(title_text="Semaine", tickformat="%d %b", dtick=7 * 86400000)
    fv.update_layout(yaxis_title="km", bargap=.3)
    show(fv, 400)


# ==========================================================
# TAB 2 · PERFORMANCE
# ==========================================================
with tab2:
    e = d.dropna(subset=["Indice efficacité"])
    ma = e["Indice efficacité"].rolling(smooth, min_periods=2, center=True).mean()
    fe = go.Figure()
    fe.add_trace(go.Scatter(x=e["Date"], y=e["Indice efficacité"], mode="markers", name="Séance",
                            marker=dict(size=9, color=e["Distance (km)"], colorscale="Teal",
                                        showscale=True, opacity=.8,
                                        colorbar=dict(title="km", thickness=10, len=.55,
                                                      outlinewidth=0, y=.5)),
                            customdata=np.stack([e["Allure txt"], e["BPM moyen"],
                                                 e["Distance (km)"], d["Ressenti"], d["Température"].round(0)], -1),
                            hovertemplate=(
                                "<b>%{x|%d/%m/%Y}</b><br>"
                                "⚡ %{y:.2f} · 📏 %{customdata[2]:.1f} km<br>"
                                "🏃 %{customdata[0]} /km · ❤️ %{customdata[1]:.0f} bpm<br>"
                                "😊 %{customdata[3]} · 🌡️ %{customdata[4]:.0f}°C"
                                "<extra></extra>"
                            )
                            ))
    fe.add_trace(go.Scatter(x=e["Date"], y=ma, name="Tendance", fill="tonexty",
                            fillcolor="rgba(255,197,61,.08)",
                            line=dict(color=C["eff"], width=3, shape="spline"), hoverinfo="skip"))
    fe.update_xaxes(title_text="Date", tickformat="%d %b")
    fe.update_layout(title="Indice d'efficacité cardiaque (vitesse / FC × 100)", yaxis_title="Indice")
    show(fe, 430)
    st.caption("💡 Plus l'indice monte, plus tu vas vite pour un même coût cardiaque.")

    # ---- Allure × FC -------------------------------------
    st.markdown("#### 🎯 Allure × fréquence cardiaque")
    sc = d.dropna(subset=["BPM moyen", "Allure (min/km)"])
    fs = go.Figure(go.Scatter(
        x=sc["BPM moyen"], y=sc["Allure (min/km)"], mode="markers", name="Séance",
        marker=dict(size=10 + 10 * (sc["Distance (km)"] / sc["Distance (km)"].max()),
                    color=sc["Date"].astype("int64"), colorscale="Plasma", opacity=.85,
                    line=dict(width=.5, color="rgba(255,255,255,.3)"),
                    colorbar=dict(title="Ancien → Récent", thickness=10, len=.55,
                                  outlinewidth=0, tickvals=[], y=.5)),
        customdata=np.stack([sc["Date"].dt.strftime("%d/%m/%Y"), sc["Allure txt"],
                             sc["Distance (km)"]], -1),
        hovertemplate="<b>%{customdata[0]}</b><br>❤️ %{x:.0f} bpm · 🏃 %{customdata[1]} /km"
                      "<br>📏 %{customdata[2]:.1f} km<extra></extra>"))
    mid = sc["Date"].quantile(.5)
    for label, sub, col in [("Début de période", sc[sc["Date"] <= mid], C["muted"]),
                            ("Période récente", sc[sc["Date"] > mid], C["ok"])]:
        if len(sub) > 3:
            a, b = np.polyfit(sub["BPM moyen"], sub["Allure (min/km)"], 1)
            xs = np.linspace(sub["BPM moyen"].min(), sub["BPM moyen"].max(), 20)
            fs.add_trace(go.Scatter(x=xs, y=a * xs + b, mode="lines", name=label,
                                    line=dict(color=col, width=2.5, dash="dash"), hoverinfo="skip"))
    tv, tt = pace_ticks(sc["Allure (min/km)"])
    fs.update_yaxes(autorange="reversed", tickvals=tv, ticktext=tt, title_text="Allure (min/km)")
    fs.update_xaxes(title_text="FC moyenne (bpm)")
    fs.update_layout(title="<i>La droite verte doit passer au-dessus de la grise</i>")
    show(fs, 430)

    # ---- Distributions -----------------------------------
    st.markdown("#### 📐 Répartition des allures")
    
    p = d["Allure (min/km)"].replace([np.inf, -np.inf], np.nan).dropna()

    if len(p) >= 2:
        BIN = 15 / 60                                   # paquets de 15 secondes
        lo = np.floor(p.min() / BIN) * BIN
        hi = np.ceil(p.max() / BIN) * BIN + BIN / 2
        edges = np.arange(lo, hi, BIN)
        
        if len(edges) < 2:
            edges = np.array([lo, lo + BIN])
            
        idx = np.clip(np.digitize(p, edges) - 1, 0, len(edges) - 2)
        counts = np.bincount(idx, minlength=len(edges) - 1)
        kms = np.bincount(idx, weights=d.loc[p.index, "Distance (km)"].values,
                          minlength=len(edges) - 1)
        centers = edges[:-1] + BIN / 2
        ranges = [f"{fmt_pace(edges[i])} – {fmt_pace(edges[i+1])}" for i in range(len(counts))]
        med = p.median()
        pace_txt = np.array([fmt_pace(c) for c in centers])
        
        fh = go.Figure(go.Bar(
            x=centers, y=counts, width=BIN * 0.9,
            marker=dict(color=counts, colorscale=[[0, "#2A4A8C"], [1, C["pace"]]],
                        line_width=0, showscale=False),
            customdata=np.stack([ranges, kms], -1),
            hovertemplate="🏃 Allure <b>%{customdata[0]}</b> /km<br>"
                          "%{y} séance(s) · %{customdata[1]:.1f} km<extra></extra>",
            text=[str(c) if c > 0 else "" for c in counts],
            textposition="outside", textfont=dict(color=C["muted"], size=11),
        ))
        # repère sur l'allure médiane
        fh.add_vline(x=med, line=dict(color=C["eff"], width=2, dash="dash"),
                     annotation_text=f"médiane {fmt_pace(med)}/km",
                     annotation_position="top right",
                     annotation_font=dict(color=C["eff"], size=11))
        tv, tt = pace_ticks(p, .25)                     # étiquettes toutes les 15 s
        fh.update_xaxes(tickvals=tv, ticktext=tt, title_text="Allure (min/km)")
        fh.update_yaxes(title_text="Nb de séances",
                        range=[0, max(counts.max() * 1.18, 1)])
        show(fh, 340)
        st.caption(f"💡 Allure médiane **{fmt_pace(med)}/km** · la plus rapide "
                   f"**{fmt_pace(p.min())}/km** · la plus lente **{fmt_pace(p.max())}/km**.")
                   
    
    st.markdown("#### 📏 Allure selon la distance")
    fd = go.Figure(go.Scatter(
        x=d["Distance (km)"], y=d["Allure (min/km)"], mode="markers",
        marker=dict(size=11, color=d["BPM moyen"], colorscale="Inferno", 
                    reversescale = True, opacity=.85,
                    line=dict(width=.5, color="rgba(255,255,255,.25)"),
                    colorbar=dict(title="bpm", thickness=10, len=.55, outlinewidth=0, y=.5)),
        customdata=np.stack([d["Allure txt"], d["Date"].dt.strftime("%d/%m/%Y")], -1),
        hovertemplate="%{x:.1f} km · %{customdata[0]} /km<br>%{customdata[1]}<extra></extra>"))
    tv, tt = pace_ticks(d["Allure (min/km)"], .25)
    fd.update_yaxes(autorange="reversed", tickvals=tv, ticktext=tt, title_text="Allure (min/km)")
    fd.update_xaxes(title_text="Distance (km)")
    show(fd, 330)


# ==========================================================
# TAB 3 · CHARGE & VOLUME
# ==========================================================
with tab3:

    dl = daily.copy()

    dl["aigue"] = dl["Charge"].rolling(7, min_periods=1).sum()

    dl["chronique"] = dl["Charge"].rolling(28, min_periods=7).sum() / 4

    dl["ratio"] = dl["aigue"] / dl["chronique"].replace(0, np.nan)

 

    # ---------- Verdict du jour ----------

    valid = dl.dropna(subset=["ratio"])

    if len(valid):

        r = valid["ratio"].iloc[-1]

        a, ch = valid["aigue"].iloc[-1], valid["chronique"].iloc[-1]

        if r < 0.8:

            verdict, vc, ico = "Semaine allégée — récupération ou baisse de régime", C["muted"], "😴"

        elif r <= 1.3:

            verdict, vc, ico = "Zone optimale — tu progresses sans te cramer", C["ok"], "✅"

        elif r <= 1.5:

            verdict, vc, ico = "Grosse semaine — prévois une semaine plus light après", C["warn"], "⚠️"

        else:

            verdict, vc, ico = "Surcharge — augmentation trop brutale, risque de blessure", C["bad"], "🚨"

 

        v1, v2, v3 = st.columns([1, 1, 2])

        kpi(v1, "Cette semaine (7 j)", f"{a:.0f}", "UA", None, color=C["load"])

        kpi(v2, "Semaine habituelle", f"{ch:.0f}", "UA", None, color=C["dist"])

        v3.markdown(

            f'<div class="kpi" style="--acc:{vc}"><div class="kpi-lab">Ratio actuel</div>'

            f'<div class="kpi-val" style="color:{vc}">{ico} {r:.2f}</div>'

            f'<div class="kpi-dlt" style="color:{C["muted"]}">{verdict}</div></div>',

            unsafe_allow_html=True)

        st.write("")

 

    # ---------- 1. Les deux charges, MÊME axe ----------

    st.markdown("#### 🏋️ Ta charge : cette semaine vs ton habitude")

    fc = go.Figure()

    fc.add_trace(go.Scatter(x=dl.index, y=dl["aigue"], name="Cette semaine (7 derniers jours)",

                            line=dict(color=C["load"], width=2.5), fill="tozeroy",

                            fillcolor="rgba(159,122,234,.18)",

                            hovertemplate="%{x|%d/%m}<br>Semaine : <b>%{y:.0f} UA</b><extra></extra>"))

    fc.add_trace(go.Scatter(x=dl.index, y=dl["chronique"],

                            name="Semaine habituelle (moyenne sur 28 j)",

                            line=dict(color=C["dist"], width=3, dash="dot"),

                            hovertemplate="Habituel : %{y:.0f} UA<extra></extra>"))

    fc.update_xaxes(title_text="Date", tickformat="%d %b")

    fc.update_yaxes(title_text="Charge (UA ≈ min de footing facile)")

    fc.update_layout(hovermode="x unified",

                     title="<i>Violet au-dessus du pointillé = semaine plus dure que d'habitude</i>")

    show(fc, 380)

 

    # ---------- 2. Le ratio seul, avec zones nommées ----------

    st.markdown("#### 🚦 Rythme de progression")

    fr2 = go.Figure()

    for y0, y1, col, lab in [(0, .8, C["muted"], "Sous-charge"),

                             (.8, 1.3, C["ok"], "Optimal"),

                             (1.3, 1.5, C["warn"], "Attention"),

                             (1.5, 2.5, C["bad"], "Risque de blessure")]:

        fr2.add_hrect(y0=y0, y1=y1, line_width=0, fillcolor=col, opacity=.10,

                      annotation_text=lab, annotation_position="right",

                      annotation_font=dict(color=col, size=11))

    fr2.add_trace(go.Scatter(x=dl.index, y=dl["ratio"], name="Ratio",

                             mode="lines", line=dict(color=C["eff"], width=3),

                             hovertemplate="%{x|%d/%m}<br>Ratio : <b>%{y:.2f}</b><extra></extra>"))

    fr2.add_hline(y=1, line=dict(color="rgba(255,255,255,.25)", width=1))

    fr2.update_xaxes(title_text="Date", tickformat="%d %b")

    fr2.update_yaxes(title_text="Semaine actuelle ÷ semaine habituelle", range=[0, 2.2])

    fr2.update_layout(showlegend=False, margin=dict(l=20, r=120, t=40, b=60))

    show(fr2, 330)

    st.caption(f"💡 **1 UA ≈ 1 minute de footing facile.** Charge = durée × intensité "

               f"(×1 à 126 bpm, ×2,3 à 147, ×3,7 à 168, ×5 au-delà de 189 — base FC max {hrmax}). "

               "Les 4 premières semaines de l'historique ne sont pas fiables : "

               "la « semaine habituelle » a besoin de 28 jours pour se calibrer.")

    # ---- RPE ----------------------------------------------
    if (d["RPE"] > 0).any():
        st.markdown("#### 😊 Ressenti déclaré (RPE)")
        rp = (d[d["RPE"] > 0].groupby("Ressenti")
              .agg(n=("RPE", "size"), rpe=("RPE", "first")).sort_values("rpe"))
        fr = go.Figure(go.Bar(x=rp.index, y=rp["n"],
                              marker=dict(color=rp["rpe"], colorscale="RdYlGn_r",
                                          cmin=0, cmax=100, line_width=0),
                              hovertemplate="<b>%{x}</b> : %{y} séances<extra></extra>"))
        fr.update_layout(yaxis_title="Nb de séances", bargap=.45)
        show(fr, 320)


# ==========================================================
# TAB 4 · RESSENTI
# ==========================================================
with tab4:
    # ---- Socle commun à tous les graphiques de l'onglet ----
    fdf = d.dropna(subset=["Feel", "Indice efficacité"]).copy()
    n_tot, n_ok = len(d), len(fdf)

    if n_tot == 0 or n_ok == 0:
        st.info("😶 Aucune séance avec un ressenti renseigné sur la période sélectionnée."
                "Sur ta montre, note ton ressenti en fin de séance "
                "(*Comment vous sentez-vous ?*) : Garmin l'enregistre dans le champ "
                "`Feel` et cet onglet s'activera automatiquement.")
        st.stop()

    if n_ok < 4:
        st.warning(f"⚠️ Seulement **{n_ok} séance(s)** avec un ressenti sur cette période "
                   "— les tendances ne sont pas encore interprétables. "
                   "Élargis la période dans la barre latérale ou continue à renseigner "
                   "ton ressenti (compte ~15 séances pour des conclusions fiables).")

    rho = (fdf[["Feel", "Indice efficacité"]].corr(method="spearman").iloc[0, 1]
           if n_ok >= 4 and fdf["Feel"].nunique() > 1 else np.nan)

    st.caption(f"😊 {n_ok} séance(s) renseignée(s) sur {n_tot} "
               f"({n_ok/n_tot*100:.0f} %) · du {fdf['Date'].min():%d/%m/%Y} "
               f"au {fdf['Date'].max():%d/%m/%Y}")
    st.write("")

    # ==========================================================
    #  Indice d'efficacité × Ressenti
    # ==========================================================
    st.markdown("#### 🤝 Efficacité cardiaque selon le ressenti")

    fdf = d.dropna(subset=["Feel", "Indice efficacité"]).copy()
    n_tot, n_ok = len(d), len(fdf)

    if n_ok < 4:
        st.info(f"Seulement {n_ok} séance(s) avec un ressenti renseigné — "
                "renseigne le champ *Feel* sur ta montre pour activer cette analyse.")
    else:
        rho = fdf[["Feel", "Indice efficacité"]].corr(method="spearman").iloc[0, 1]
        med_all = fdf["Indice efficacité"].median()
        hi = fdf.loc[fdf["Feel"] >= 75, "Indice efficacité"].median()
        lo = fdf.loc[fdf["Feel"] <= 25, "Indice efficacité"].median()

        # ---- KPI de synthèse ----
        q = st.columns(2)
        lab_rho = ("forte" if abs(rho) >= .5 else "modérée" if abs(rho) >= .3 else "faible")
        kpi(q[0], "Corrélation ressenti ↔ efficacité", f"{rho:+.2f}", f"· {lab_rho}",
            None, color=C["ok"] if rho > .3 else C["warn"])
        if pd.notna(hi) and pd.notna(lo) and lo:
            kpi(q[1], "Écart Fort vs Faible", f"{(hi-lo)/lo*100:+.1f}", "%",
                None, color=C["eff"])
        else:
            kpi(q[1], "Écart Fort vs Faible", "—", "", None, color=C["muted"])
        st.write("")

        xpos = {v: i for i, v in enumerate(FEEL_ORDER)}
        rng = np.random.default_rng(7)                  # jitter stable entre 2 reruns
        fig = go.Figure()
        meds, mx = [], []

        for v in FEEL_ORDER:
            sub = fdf[fdf["Feel"] == v]
            if sub.empty:
                meds.append(np.nan)
                continue
            col = FEEL_COL[v]

            # boîte (distribution)
            fig.add_trace(go.Box(
                y=sub["Indice efficacité"], x0=xpos[v], width=.55,
                boxpoints=False, notched=False, whiskerwidth=.5,
                line=dict(color=col, width=2),
                fillcolor=f"rgba({int(col[1:3],16)},{int(col[3:5],16)},{int(col[5:7],16)},.14)",
                hoveron="boxes", showlegend=False,
                name=f"{FEEL_EMO[v]} {FEEL_NAME[v]}",
                hovertemplate=f"<b>{FEEL_EMO[v]} {FEEL_NAME[v]}</b><br>"
                              "médiane %{median:.2f}<br>Q1 %{q1:.2f} · Q3 %{q3:.2f}"
                              "<extra></extra>"))

            # points individuels
            jit = rng.uniform(-.17, .17, len(sub))
            fig.add_trace(go.Scatter(
                x=xpos[v] + jit, y=sub["Indice efficacité"], mode="markers",
                showlegend=False,
                marker=dict(size=7 + 8 * (sub["Distance (km)"] / max(fdf["Distance (km)"].max(), 1e-9)),
                            color=col, opacity=.8,
                            line=dict(width=.8, color="rgba(255,255,255,.35)")),
                customdata=np.stack([sub["Date"].dt.strftime("%d/%m/%Y"), sub["Allure txt"],
                                     sub["Distance (km)"], sub["BPM moyen"]], -1),
                hovertemplate="<b>%{customdata[0]}</b><br>⚡ %{y:.2f}<br>"
                              "🏃 %{customdata[1]} /km · 📏 %{customdata[2]:.1f} km<br>"
                              "❤️ %{customdata[3]:.0f} bpm<extra></extra>"))

            meds.append(sub["Indice efficacité"].median())
            mx.append(len(sub))

        # ligne des médianes = la tendance
        ok = ~np.isnan(meds)
        fig.add_trace(go.Scatter(
            x=np.arange(5)[ok], y=np.array(meds)[ok], mode="lines+markers",
            name="Médiane", line=dict(color=C["txt"], width=2.5, dash="dot"),
            marker=dict(size=11, symbol="diamond", color=C["txt"],
                        line=dict(width=1.5, color=C["bg"])),
            hovertemplate="médiane %{y:.2f}<extra></extra>"))

        fig.add_hline(y=med_all, line=dict(color="rgba(255,255,255,.22)", width=1),
                      annotation_text=f"médiane globale {med_all:.2f}",
                      annotation_position="bottom right",
                      annotation_font=dict(color=C["muted"], size=10.5))

        counts = fdf["Feel"].value_counts()
        fig.update_xaxes(
            tickvals=list(range(5)), range=[-.6, 4.6], showgrid=False,
            ticktext=[f"{FEEL_EMO[v]}<br>{FEEL_NAME[v]}<br>"
                      f"<span style='font-size:10px;color:{C['muted']}'>"
                      f"n = {int(counts.get(v, 0))}</span>" for v in FEEL_ORDER],
            title_text=None)
        fig.update_yaxes(title_text="Indice d'efficacité (vitesse / FC × 100)")
        fig.update_layout(
            title=f"<i>La ligne pointillée doit monter vers la droite — ρ de Spearman = {rho:+.2f}</i>",
            showlegend=False, margin=dict(l=20, r=30, t=75, b=85))
        show(fig, 470)

    st.divider()

    # ==================================================
    #  C · Profil moyen des séances par ressenti
    # ==================================================
    st.markdown("#### 🧩 Profil moyen des séances selon le ressenti")
    if len(fdf) >= 6:
        specs = [("Distance (km)", "km",  "%.1f", False),
                 ("Allure (min/km)", "/km", None, True),
                 ("BPM moyen", "bpm", "%.0f", False),
                 ("Charge", "UA", "%.0f", False)]

        fp = make_subplots(rows=2, cols=2,
                           vertical_spacing=.30, horizontal_spacing=.10,
                           subplot_titles=[f"{s[0]}" for s in specs])

        for i, (m, unit, f_, is_pace) in enumerate(specs):
            r, c = i // 2 + 1, i % 2 + 1
            g = fdf.groupby("Feel")[m].mean().reindex(FEEL_ORDER)
            vals = g.values.astype(float)

            lab = [fmt_pace(v) if is_pace else ("" if pd.isna(v) else f_ % v)
                   for v in vals]

            fp.add_trace(go.Bar(
                x=[FEEL_EMO[v] for v in FEEL_ORDER], y=vals,
                marker=dict(color=[FEEL_COL[v] for v in FEEL_ORDER],
                            opacity=.85, line_width=0),
                text=lab, textposition="outside",
                textfont=dict(color=C["muted"], size=11.5),
                cliponaxis=False,  
                showlegend=False,
                hovertemplate="%{x} → <b>%{text}</b> " + unit + "<extra></extra>"),
                row=r, col=c)

            # ---- plage Y avec marge pour les étiquettes ----
            vmin, vmax = np.nanmin(vals), np.nanmax(vals)
            if not np.isfinite(vmin):
                continue
            span = max(vmax - vmin, vmax * .05, 1e-6)

            if is_pace:
                # axe inversé : le "haut" du graphique = allure rapide
                fp.update_yaxes(range=[vmax + span * .45, vmin - span * .55],
                                row=r, col=c)
            else:
                base = 0 if vmin / max(vmax, 1e-9) < .35 else vmin - span * .55
                fp.update_yaxes(range=[base, vmax + span * .45], row=r, col=c)

            fp.update_yaxes(title_text=unit, showticklabels=False,
                            title_font=dict(color=C["muted"], size=11),
                            row=r, col=c)

            fp.update_xaxes(tickfont=dict(size=19), showgrid=False, row=r, col=c)

        fp.update_layout(bargap=.35,
                         margin=dict(l=25, r=30, t=70, b=50))
        fp.update_annotations(font=dict(size=13.5, color=C["txt"]), yshift=8)
        show(fp, 600)                                   # 520 → 600

        st.caption("💡 De gauche à droite : 😵 très faible → 🤩 très fort. "
                   "Sur le graphique **Allure**, plus la barre est haute, plus tu cours vite. "
                   "Si tes 😵 correspondent aux séances les plus longues ou intenses, c'est normal. "
                   "Si tes 😵 arrivent sur des footings courts et faciles, regarde du côté de la "
                   "récupération (sommeil, charge cumulée).")


# ==========================================================
# TAB 5 · SÉANCES
# ==========================================================
with tab5:
    tbl = d.sort_values("Date", ascending=False)[[
        "Date", "Distance (km)", "Temps (min)", "Allure txt", "BPM moyen",
        "%FCmax", "Zone", "Indice efficacité", "Température", "Ressenti", "Effet entraînement"]].rename(
        columns={"Allure txt": "Allure /km"})
    tbl["Zone"] = tbl["Zone"].astype(str).str.split("  ").str[0]

    st.dataframe(
        tbl, use_container_width=True, hide_index=True, height=600,
        column_config={
            "Date": st.column_config.DatetimeColumn("Date", format="DD/MM/YYYY HH:mm"),
            "Distance (km)": st.column_config.ProgressColumn(
                "Distance", format="%.1f km", min_value=0,
                max_value=float(tbl["Distance (km)"].max())),
            "Temps (min)": st.column_config.NumberColumn("Durée", format="%.0f min"),
            "BPM moyen": st.column_config.NumberColumn("FC moy", format="%.0f bpm"),
            "%FCmax": st.column_config.NumberColumn("% FCmax", format="%.0f %%"),
            "Indice efficacité": st.column_config.NumberColumn("Indice", format="%.2f"),
            "Température": st.column_config.NumberColumn("Temp.", format="%.0f °C"),
        })