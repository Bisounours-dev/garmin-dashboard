
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
    page_title="Run Analytics",
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
    st.markdown(
        '<div class="hero"><h1>🏃 Run Analytics</h1>'
        '<p>⚠️ Aucune donnée Garmin trouvée. Chargez une sauvegarde ZIP dans la barre latérale.</p>'
        '<p>Voici le lien pour télécharger vos données depuis le site de Garmin : '
        '<a href="https://www.garmin.com/fr-FR/account/datamanagement/exportdata" '
        'target="_blank">📥 Télécharger mes données Garmin</a></p>'
        "<p>Cliquez simplement sur le bouton : 'DEMANDEZ l'EXPORT DE DONNEES' </p>"
        "<p>Un lien sera disponible dans votre boite mail sous quelques heures en général. Il suffira de le charger dans la barre latéral.</p>"
        '</div>',
        unsafe_allow_html=True
    )
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
    

Hrz_File = None

for root, dirs, files in os.walk(DATA_DIR):
    for fn in files:
        if fn.lower().endswith('heartratezones.json'):
            Hrz_File = os.path.join(root, fn)
            break

    if Hrz_File is not None:
        break


@st.cache_data(show_spinner="Lecture des zones FC Garmin…")
def load_json_file(json_file, mtime):
    """Aplatit un seul fichier JSON en un df Fichier/Champ/Chemin/Valeur."""
    rows = []

    def flat(obj, fichier, chemin=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                flat(v, fichier, f"{chemin}.{k}" if chemin else str(k))

        elif isinstance(obj, list):
            for i, v in enumerate(obj[:100]):
                flat(v, fichier, f"{chemin}[{i}]")

        elif obj is not None and obj != "":
            rows.append({
                "Fichier": fichier,
                "Champ": chemin.split(".")[-1].split("[")[0],
                "Chemin": chemin,
                "Valeur": str(obj)
            })

    if not json_file or not os.path.exists(json_file):
        return pd.DataFrame(
            columns=["Fichier", "Champ", "Chemin", "Valeur"]
        )

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, str):
            raw = json.loads(raw)

        flat(raw, os.path.basename(json_file))

    except Exception:
        pass

    return pd.DataFrame(rows)


hrz = load_json_file(
    Hrz_File,
    os.path.getmtime(Hrz_File) if Hrz_File else 0
)

HR_MAX_GARMIN = int(hrz.loc[hrz["Champ"] == "maxHeartRateUsed", "Valeur"].iloc[0])
HR_MAX = HR_MAX_GARMIN if HR_MAX_GARMIN else HR_MAX_DEFAULT

VO2_FIELD_PRIO = ("vo2maxprecisevalue", "maxmet", "vo2maxvalue", "vo2max")
VO2_DATE_KEYS = ("calendardate", "calendarday", "date", "timestamp", "startdate")
VO2_FILE_HINTS = ("maxmet", "metric", "vo2", "fitnessage")


def _vo2_key(k):
    return str(k).lower().replace("_", "").replace(" ", "")


def _vo2_collect(node, out):
    """Parcourt un JSON quelconque et récupère (date, champ, valeur, sport)."""
    if isinstance(node, dict):
        keys = {_vo2_key(k): k for k in node}
        present = [k for k in VO2_FIELD_PRIO if k in keys]
        if present:
            dk = next((keys[k] for k in VO2_DATE_KEYS if k in keys), None)
            sport = node.get(keys.get("sport")) if "sport" in keys else None
            for nk in present:
                out.append((node.get(dk) if dk else None, nk,
                            node.get(keys[nk]), str(sport or "")))
        for v in node.values():
            _vo2_collect(v, out)
    elif isinstance(node, list):
        for v in node:
            _vo2_collect(v, out)
    return out


@st.cache_data(show_spinner="Lecture de la VO2max Garmin…")
def load_vo2_profile(data_dir, sig):
    """Série quotidienne de la VO2max course à pied telle que Garmin l'affiche."""
    empty = pd.DataFrame(columns=["Date", "VO2", "Champ"])
    rows, srcs = [], []

    for root, _dirs, files in os.walk(data_dir):
        for fn in files:
            low = fn.lower()
            if not low.endswith(".json") or not any(h in low for h in VO2_FILE_HINTS):
                continue
            try:
                with open(os.path.join(root, fn), "r", encoding="utf-8") as f:
                    blob = json.load(f)
            except Exception:
                continue
            got = _vo2_collect(blob, [])
            if got:
                rows += got
                srcs.append(fn)

    if not rows:
        return empty, []

    v = pd.DataFrame(rows, columns=["raw", "Champ", "Valeur", "Sport"])
    sp = v["Sport"].astype(str).str.upper()
    v = v[sp.str.contains("RUN") | (sp.str.strip() == "")]        # course à pied only
    v["Valeur"] = pd.to_numeric(v["Valeur"], errors="coerce")
    v = v[v["Valeur"] > 0]
    if v.empty:
        return empty, sorted(set(srcs))

    # dates : "2026-09-03", "2026-09-03T07:12:00" ou epoch en ms
    ms = pd.to_numeric(v["raw"], errors="coerce")
    dt = pd.to_datetime(v["raw"].astype(str), errors="coerce", format="ISO8601")
    dt = dt.where(ms.isna(), pd.to_datetime(ms, unit="ms", errors="coerce"))
    v["Date"] = dt.dt.normalize()
    v = v.dropna(subset=["Date"])
    if v.empty:
        return empty, sorted(set(srcs))

    val = v["Valeur"].where(v["Champ"] != "maxmet", v["Valeur"] * 3.5)   # 1 MET = 3,5
    for _ in range(3):                                   # certains exports encodent ×10
        val = val.where(val <= 100, val / 10)
    v["VO2"] = val.round(3)

    v["prio"] = v["Champ"].map({k: i for i, k in enumerate(VO2_FIELD_PRIO)})
    v = (v.sort_values(["Date", "prio"])
          .groupby("Date", as_index=False).first()
          .sort_values("Date"))
    return v[["Date", "VO2", "Champ"]].reset_index(drop=True), sorted(set(srcs))


# --- Filtres ----------------------------------------------
with st.sidebar:
    period = st.radio("Période", ["30 jours", "3 mois", "Tout"], index=2, horizontal=True)
    dmin = st.slider("Distance minimale (km)", 0.0, 15.0, 1.0, 0.5)
    hrmax = st.number_input("FC max (bpm)", 140, 230, HR_MAX, 1,
                            help="Base de calcul des zones d'intensité et de la charge.")
    if HR_MAX_GARMIN:
        st.caption(f"✅ Lue dans le profil Garmin : **{HR_MAX} bpm**")
    else:
        st.caption(f"⚠️ Introuvable dans l'export → valeur par défaut **{HR_MAX_DEFAULT} bpm**")

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
    f'<div class="hero"><h1>🏃 Run Analytics  -- Données Running uniquement </h1>'
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

    # ==========================================================
    #  [AJOUT] Heatmap calendrier · 30 jours glissants
    # ==========================================================
    st.markdown("#### 🗓️ Calendrier des 30 derniers jours")

    HM_DAYS = 30
    hm_end = tmax.normalize()
    hm_start = hm_end - timedelta(days=HM_DAYS - 1)

    hm_src = d[(d["Date"] >= hm_start) & (d["Date"] < hm_end + timedelta(days=1))].copy()

    if hm_src.empty:
        st.info("Aucune séance sur les 30 derniers jours avec les filtres actuels.")
    else:
        hm_src["Jour"] = hm_src["Date"].dt.normalize()
        full_idx = pd.date_range(hm_start, hm_end, freq="D")
        hm_day = (hm_src.groupby("Jour")
                        .agg(km=("Distance (km)", "sum"), mn=("Temps (min)", "sum"),
                             n=("Distance (km)", "size"), bpm=("BPM moyen", "mean"))
                        .reindex(full_idx))
        hm_day["pace"] = hm_day["mn"] / hm_day["km"].replace(0, np.nan)


        # ---- grille semaines × jours ----
        wk_of = {day: day - timedelta(days=int(day.weekday())) for day in full_idx}
        weeks = sorted(set(wk_of.values()))
        wmap = {w: i for i, w in enumerate(weeks)}

        nrow = len(weeks)
        z = np.full((nrow, 7), np.nan)
        cells = []                                   # (row, col, jour, km)
        hov = np.full((nrow, 7), "", dtype=object)

        for day in full_idx:
            r, c = wmap[wk_of[day]], int(day.weekday())
            km = hm_day.at[day, "km"]
            if pd.isna(km):
                z[r, c] = 0.0
                hov[r, c] = f"<b>{day:%a %d/%m}</b><br>😴 repos"
                cells.append((r, c, day, np.nan))
            else:
                z[r, c] = float(km)
                row = hm_day.loc[day]
                extra = f" · ❤️ {row['bpm']:.0f} bpm" if pd.notna(row["bpm"]) else ""
                multi = f"<br>{int(row['n'])} séances cumulées" if row["n"] > 1 else ""
                hov[r, c] = (f"<b>{day:%a %d/%m}</b><br>📏 {km:.1f} km · ⏱️ {row['mn']:.0f} min"
                             f"<br>🏃 {fmt_pace(row['pace'])} /km{extra}{multi}")
                cells.append((r, c, day, float(km)))

        zmax = max(float(np.nanmax(z)), 1.0)
        HM_SCALE = [[0.00, "#141C27"], [0.01, "#14343F"], [0.35, "#177F86"],
                    [0.70, "#36CFC9"], [1.00, "#B6F5E9"]]

        fhm = go.Figure(go.Heatmap(
            z=z, x=["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
            y=[f"sem. {w:%d/%m}" for w in weeks],
            customdata=hov, hovertemplate="%{customdata}<extra></extra>", hoverongaps=False,
            colorscale=HM_SCALE, zmin=0, zmax=zmax, xgap=5, ygap=5,
            colorbar=dict(title="km", thickness=11, len=.85, outlinewidth=0,
                          tickfont=dict(size=11))))

        for r, c, day, km in cells:
            xr, yr = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"][c], f"sem. {weeks[r]:%d/%m}"
            if np.isnan(km):
                fhm.add_annotation(x=xr, y=yr, text=f"<span style='font-size:10px'>{day.day}</span>",
                                  showarrow=False, font=dict(color="rgba(230,233,239,.30)", size=10),
                                  yshift=0)
            else:
                txt_col = "#0B1220" if km / zmax > .55 else C["txt"]
                fhm.add_annotation(x=xr, y=yr, showarrow=False,
                                  text=(f"<span style='font-size:9.5px;opacity:.75'>{day.day}</span>"
                                        f"<br><b>{km:.1f}</b>"),
                                  font=dict(color=txt_col, size=12.5), align="center")

        fhm.update_xaxes(side="top", showgrid=False, tickfont=dict(size=12, color=C["muted"]))
        fhm.update_yaxes(autorange="reversed", showgrid=False,
                         tickfont=dict(size=11, color=C["muted"]))
        fhm.update_layout(title="<i>Plus la case est claire, plus la sortie est longue</i>",
                          margin=dict(l=20, r=20, t=80, b=30))
        show(fhm, 95 + 78 * nrow)
    
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
    
    # ==========================================================
        #  [AJOUT] Évolution de la VO2max  (valeur montre + estimations séance)
    # ==========================================================

    st.markdown("#### 🫁 VO2max")

    vprof, vsrc = load_vo2_profile(DATA_DIR, os.path.getmtime(JSON_FILE))
    if len(vprof):
        vp = vprof[(vprof["Date"] >= d["Date"].min().normalize()) &
                   (vprof["Date"] <= tmax.normalize())].copy()
    else:
        vp = vprof.copy()

    # --- estimations brutes séance par séance (champ des activités) ---
    vcol = next((c for c in d.columns if "vo2max" in str(c).lower().replace("_", "")), None)
    vact = pd.DataFrame(columns=["Date", "VO2", "km", "Allure txt"])
    if vcol is not None:
        vser = pd.to_numeric(d[vcol], errors="coerce")
        vser = vser.where(vser > 0)
        for _ in range(3):                               # exports encodés ×10
            if vser.notna().any() and vser.median() > 100:
                vser = vser / 10.0
        vact = (pd.DataFrame({"Date": d["Date"], "VO2": vser, "km": d["Distance (km)"],
                              "Allure txt": d["Allure txt"]})
                .dropna(subset=["VO2"]).sort_values("Date"))

    if vp.empty and vact.empty:
        st.info("Ton export ne contient aucune VO2max exploitable "
                "(ni `MetricsMaxMetData_*.json`, ni champ `vO2MaxValue` dans les activités).")
    else:
        official = not vp.empty
        ref = vp if official else vact
        v_now, v_first = float(ref["VO2"].iloc[-1]), float(ref["VO2"].iloc[0])
        v_lo, v_hi = float(ref["VO2"].min()), float(ref["VO2"].max())
        if not vact.empty:
            v_lo, v_hi = min(v_lo, float(vact["VO2"].min())), max(v_hi, float(vact["VO2"].max()))
        vma = v_now / 3.5                                # VMA ≈ VO2max / 3,5 (km/h)

        q1, q2, q3 = st.columns(3)
        kpi(q1, "VO2max actuelle" if official else "VO2max (estim. séance)",
            f"{v_now:.0f}", "ml/kg/min", pct(v_now, v_first),
            delta_txt="vs début de période", color=C["ok"] if official else C["warn"])
        kpi(q2, "Pic sur la période", f"{float(ref['VO2'].max()):.0f}", "ml/kg/min",
            None, color=C["eff"])
        kpi(q3, "VMA estimée", f"{vma:.1f}", f"km/h · {fmt_pace(60/vma)} /km",
            None, color=C["pace"])
        st.write("")

        fvo = go.Figure()
        if not vact.empty:
            fvo.add_trace(go.Scatter(
                x=vact["Date"], y=vact["VO2"], mode="markers",
                name="Estimation brute de la séance",
                marker=dict(size=7, color=C["muted"], opacity=.55,
                            line=dict(width=.5, color="rgba(255,255,255,.2)")),
                customdata=np.stack([vact["km"], vact["Allure txt"]], -1),
                hovertemplate="<b>%{x|%d/%m/%Y}</b><br>estimation séance "
                              "<b>%{y:.1f}</b> ml/kg/min<br>📏 %{customdata[0]:.1f} km · "
                              "🏃 %{customdata[1]} /km<extra></extra>"))
        if official:
            fvo.add_trace(go.Scatter(
                x=vp["Date"], y=vp["VO2"], mode="lines+markers",
                name="VO2max Garmin (celle de ta montre)",
                line=dict(color=C["ok"], width=3, shape="spline", smoothing=1.2),
                marker=dict(size=6, color=C["ok"],
                            line=dict(width=1, color="rgba(255,255,255,.3)")),
                hovertemplate="<b>%{x|%d/%m/%Y}</b><br>🫁 <b>%{y:.1f}</b> ml/kg/min"
                              "<extra></extra>"))

        pad = max((v_hi - v_lo) * .18, 1.0)
        fvo.update_yaxes(title_text="VO2max (ml/kg/min)", range=[v_lo - pad, v_hi + pad])
        fvo.update_xaxes(title_text="Date", tickformat="%d %b")
        fvo.update_layout(title=f"<i>{v_first:.1f} → {v_now:.1f} ml/kg/min "
                                f"({v_now - v_first:+.1f} sur la période)</i>")
        show(fvo, 400)

        if official:
            st.caption(
                "💡 La **ligne verte** est la VO2max de ton profil Garmin : c'est exactement "
                "le chiffre affiché sur la montre. Les **points gris** "
                "sont l'estimation brute calculée séance par séance : elle est "
                "quasi toujours plus basse, car Garmin lisse et ne retient que les séances "
                "de qualité.")
        else:
            st.warning(
                "⚠️ Aucun fichier `MetricsMaxMetData_*.json` trouvé dans l'export : "
                "seule l'estimation **séance par séance** est affichée, et elle est "
                "typiquement 1 à 3 points **sous** la valeur de ta montre. Vérifie que le "
                "dossier `DI_CONNECT/DI-Connect-Metrics` est bien présent dans le ZIP.")

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

  # ---- Ressenti ------------------------------------------

    if d["Feel"].notna().any():
        st.markdown("#### 😊 Ressenti déclaré")

        cnt = (d.dropna(subset=["Feel"]).groupby("Feel").size().reindex(FEEL_ORDER, fill_value=0))          # ← ordre garanti
        tot = cnt.sum()

        fr = go.Figure(go.Bar(
            x=[f"{FEEL_EMO[v]}<br>{FEEL_NAME[v]}" for v in FEEL_ORDER],
            y=cnt.values,
            marker=dict(color=[FEEL_COL[v] for v in FEEL_ORDER],
                        opacity=.88, line_width=0),
            text=[f"{n}<br><span style='font-size:10px'>{n/tot*100:.0f} %</span>"
                  if n else "" for n in cnt.values],
            textposition="outside", textfont=dict(color=C["muted"], size=12),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>%{y} séance(s)<extra></extra>"))

        fr.update_xaxes(tickfont=dict(size=12), showgrid=False, title_text=None)
        fr.update_yaxes(title_text="Nb de séances",
                        range=[0, max(cnt.max() * 1.28, 1)])
        fr.update_layout(bargap=.45, margin=dict(l=25, r=30, t=50, b=70))
        show(fr, 340)

        moy = (d["Feel"] * 1).mean()
        st.caption(f"💡 Ressenti moyen : **{moy:.0f}/100** · "
                   f"{cnt.loc[[75, 100]].sum()} séance(s) en 🙂/🤩 contre "
                   f"{cnt.loc[[0, 25]].sum()} en 😵/😕.")

    # ==========================================================
    #  [AJOUT] Répartition mensuelle du temps par zone d'intensité
    # ==========================================================
    st.divider()
    st.markdown("#### 🎚️ Où passes-tu ton temps ? · zones d'intensité par mois")

    ZS_SHORT = ["Z1", "Z2", "Z3", "Z4", "Z5"]


    def _z_suffix(c):
        s = "".join(ch for ch in str(c) if ch.isdigit())
        return int(s) if s else -1


    def zone_minutes(df):
        """Minutes par zone (Z1..Z5) pour chaque séance.

        1) champs Garmin `hrTimeInZone_*` s'ils existent → répartition intra-séance (précise)
        2) sinon : toute la durée de la séance est affectée à sa zone de FC moyenne (approx.)
        """
        cols = sorted([c for c in df.columns if str(c).lower().startswith("hrtimeinzone")],
                      key=_z_suffix)
        if len(cols) >= 5:
            raw = df[cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
            tot = raw.sum(axis=1)
            ref = pd.to_numeric(df["Temps (min)"], errors="coerce") * 60.0
            m = (tot > 0) & ref.gt(0)
            if int(m.sum()) >= 3:
                k = float(np.nanmedian((tot[m] / ref[m]).to_numpy()))
                div = 60.0 if 0.5 < k < 2.5 else (60_000.0 if k > 100 else 1.0)   # s / ms / min
                mins = raw / div
                if _z_suffix(cols[0]) == 0 and len(cols) >= 6:      # zone 0 fusionnée dans Z1
                    z = pd.concat([mins[cols[0]] + mins[cols[1]]] +
                                  [mins[c] for c in cols[2:6]], axis=1)
                else:
                    z = mins[cols[:5]].copy()
                z.columns = ZS_SHORT
                return z, "garmin"

        z = pd.DataFrame(0.0, index=df.index, columns=ZS_SHORT)
        lab2short = {lab: ZS_SHORT[i] for i, lab in enumerate(zlabs)}
        for i in df.index:
            sh = lab2short.get(df.at[i, "Zone"])
            t = df.at[i, "Temps (min)"]
            if sh is not None and pd.notna(t):
                z.at[i, sh] = float(t)
        return z, "fcmax"


    zmin, zsrc = zone_minutes(d)
    mois = d["Date"].dt.to_period("M").dt.to_timestamp()

    g = zmin.groupby(mois)[ZS_SHORT].sum()
    tot_m = g.sum(axis=1)
    g, tot_m = g[tot_m > 0], tot_m[tot_m > 0]

    if g.empty:
        st.info("Pas assez de données de fréquence cardiaque pour répartir le temps par zone.")
    else:
        nse = d.groupby(mois).size().reindex(g.index).fillna(0)
        share = g.div(tot_m, axis=0) * 100

        MOIS_FR = {1: "janv.", 2: "févr.", 3: "mars", 4: "avr.", 5: "mai", 6: "juin", 7: "juil.",
                   8: "août", 9: "sept.", 10: "oct.", 11: "nov.", 12: "déc."}
        xlab = [f"{MOIS_FR[m.month]} {m.year}<br>"
                f"<span style='font-size:10px;color:{C['muted']}'>"
                f"{int(nse.loc[m])} séances · {tot_m.loc[m]/60:.1f} h</span>" for m in g.index]

        fz = go.Figure()
        for i, zs in enumerate(ZS_SHORT):
            pc, mn = share[zs].to_numpy(), g[zs].to_numpy()
            fz.add_bar(
                x=xlab, y=pc, name=Z_NAME[i],
                marker=dict(color=Z_HEX[i], opacity=.92, line=dict(width=0)),
                text=[f"{v:.0f} %" if v >= 6 else "" for v in pc],
                textposition="inside", insidetextanchor="middle",
                textfont=dict(color="#0B1220", size=11.5),
                customdata=np.stack([mn, mn / 60], -1),
                hovertemplate=(f"<b>{Z_NAME[i]}</b><br>%{{y:.1f}} % du temps"
                               "<br>%{customdata[0]:.0f} min (%{customdata[1]:.1f} h)<extra></extra>"))

        #fz.add_hline(y=80, line=dict(color="rgba(255,255,255,.45)", width=1.5, dash="dash"),
                     #annotation_text="objectif ≈ 80 % en Z1–Z2-Z3", annotation_position="top right",
         #            annotation_font=dict(color=C["txt"], size=11))
        fz.update_yaxes(title_text="% du temps couru", range=[0, 104],
                        ticksuffix=" %", dtick=20)
        fz.update_xaxes(title_text=None, showgrid=False, tickfont=dict(size=12))
        fz.update_layout(barmode="stack", bargap=.45, hovermode="x unified",
                         #title="<i>Le bas des barres (Z1+Z2+Z3) doit atteindre ~80 % : la base aérobie</i>",
                         margin=dict(l=25, r=30, t=80, b=70))
        show(fz, 470)
        
        st.caption("Temps réel passé dans chaque zone, pas de temps estimé les bornes sont celle de ta montre")


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