# -*- coding: utf-8 -*-
"""
ENOLOU QUIZ — v2.3 "Arcade"
Application de quiz interactif multi-joueurs (jusqu'a 40 participants).

Historique :
  v2.0 — refonte design, multi-types, robustesse multi-joueurs, mobile iOS/Android
  v2.1 — Lot 1 : codes de session a 6 chiffres
  v2.2 — Lot 2 : question bonus / double points, chrono synchronise serveur,
                 nuage de mots (sondages + reponses libres), avatars personnalisables,
                 reactions emoji en direct
         + bouton retour accueil sur tous les sous-menus
         + publication selective des quiz pour le mode entrainement
  v2.3 — Lot 3 : import / export Excel des questions (creation en masse)
"""

import os
import re
import json
import random
import time
import hashlib
import unicodedata
import tempfile
import base64
from io import BytesIO
from collections import Counter

import qrcode
import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ==========================================================
# 0. CONFIGURATION GENERALE
# ==========================================================
st.set_page_config(
    page_title="Enolou Quiz",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DOSSIER_QUIZZES = "QCM"
DOSSIER_SESSIONS = "SESSIONS"
FICHIER_PUBLICATION = os.path.join(DOSSIER_QUIZZES, "_publication.json")
MAX_JOUEURS = 40
URL_APP_DEFAUT = "https://yannbzh94-enolou-qcm-web-app-ngwrt8.streamlit.app/"

for d in (DOSSIER_QUIZZES, DOSSIER_SESSIONS):
    os.makedirs(d, exist_ok=True)

# ==========================================================
# 1. DESIGN SYSTEM (CSS)
# ==========================================================
PALETTES = {
    "Nebula": ["#6366f1", "#a855f7", "#ec4899"],
    "Sunset": ["#f97316", "#ef4444", "#d946ef"],
    "Ocean": ["#0ea5e9", "#06b6d4", "#3b82f6"],
    "Forest": ["#10b981", "#22c55e", "#84cc16"],
    "Midnight": ["#1e293b", "#4338ca", "#7c3aed"],
}

TILE_COLORS = ["#ef4444", "#3b82f6", "#f59e0b", "#10b981", "#8b5cf6", "#ec4899", "#14b8a6", "#f43f5e"]
TILE_SHAPES = ["▲", "◆", "●", "■", "★", "⬟", "✦", "❤"]

AVATARS = ["🦊", "🐼", "🦁", "🐨", "🐸", "🦉", "🐙", "🦄", "🐝", "🐧", "🦖", "🐬", "🦋", "🐺", "🦕", "🐳",
           "🐢", "🦔", "🐝", "🦓", "🦒", "🐉", "🦩", "🐅"]
REACTIONS = ["👏", "🔥", "😂", "😱", "🤔", "💪", "🎉", "😅"]


def injecter_design(palette="Nebula"):
    c1, c2, c3 = PALETTES.get(palette, PALETTES["Nebula"])
    tiles_css = "\n".join(
        f"""div[class*="st-key-tile_{i}_"] button {{
            background: linear-gradient(145deg, {c} 0%, {c}cc 100%) !important;
            color:#fff !important; border:none !important;
        }}"""
        for i, c in enumerate(TILE_COLORS)
    )
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;800&family=Inter:wght@400;600;800&display=swap');

#MainMenu, footer, header {visibility: hidden;}
[data-testid="stAudio"], audio { display:none !important; }

:root { --c1: __C1__; --c2: __C2__; --c3: __C3__; --ink:#0b1020; --muted:#64748b; --card:#ffffff; }

.stApp {
  background:
    radial-gradient(1100px 600px at 8% -10%, color-mix(in srgb, var(--c1) 28%, transparent) 0%, transparent 60%),
    radial-gradient(900px 600px at 95% 0%, color-mix(in srgb, var(--c3) 24%, transparent) 0%, transparent 55%),
    linear-gradient(180deg,#f7f8fc 0%, #eef1f9 100%);
  background-attachment: fixed;
}
html, body, [class*="css"] { font-family:'Inter',system-ui,-apple-system,sans-serif; }
h1,h2,h3 { font-family:'Baloo 2','Inter',sans-serif !important; color:var(--ink) !important; letter-spacing:-.02em; }

.eno-card{ background:var(--card); border-radius:20px; padding:22px 24px;
  box-shadow:0 10px 30px rgba(15,23,42,.08); border:1px solid rgba(15,23,42,.06); margin-bottom:16px; }
.eno-hero{ background:linear-gradient(120deg,var(--c1),var(--c2) 55%,var(--c3));
  color:#fff; border-radius:24px; padding:26px 28px; margin-bottom:18px;
  box-shadow:0 18px 40px color-mix(in srgb, var(--c2) 35%, transparent); }
.eno-hero h1{ color:#fff !important; margin:0 0 6px 0; font-size:2rem; }
.eno-hero p{ margin:0; opacity:.92; font-size:.95rem; }

.eno-pill{ display:inline-block; padding:4px 12px; border-radius:999px; font-size:.72rem;
  font-weight:700; background:rgba(255,255,255,.22); color:#fff; margin-right:6px; backdrop-filter:blur(6px); }
.eno-badge{ display:inline-block; padding:4px 10px; border-radius:999px; font-size:.7rem; font-weight:800;
  background:color-mix(in srgb,var(--c1) 14%, #fff); color:var(--c1); border:1px solid color-mix(in srgb,var(--c1) 30%,#fff); }
.eno-badge-or{ background:linear-gradient(120deg,#f59e0b,#f97316); color:#fff; border:none; }

/* ---- Code de session a 6 chiffres ---- */
.eno-code-wrap{ text-align:center; margin:10px 0 4px 0; }
.eno-code-label{ font-size:.8rem; font-weight:700; color:var(--muted); letter-spacing:.14em; text-transform:uppercase; }
.eno-code{ display:inline-flex; gap:8px; margin-top:8px; }
.eno-digit{
  width:52px; height:66px; border-radius:14px; display:grid; place-items:center;
  font-family:'Baloo 2',sans-serif; font-size:2.2rem; font-weight:800; color:#fff;
  background:linear-gradient(145deg,var(--c1),var(--c2));
  box-shadow:0 10px 22px color-mix(in srgb,var(--c2) 32%, transparent);
}
.eno-code-xl .eno-digit{ width:92px; height:120px; font-size:4rem; border-radius:20px; }

.stButton > button{ border-radius:14px !important; font-weight:700 !important; padding:.65rem 1rem !important;
  border:1px solid rgba(15,23,42,.10) !important;
  transition:transform .15s ease, box-shadow .15s ease, filter .15s ease; min-height:48px; }
.stButton > button:hover{ transform:translateY(-2px); box-shadow:0 10px 22px rgba(15,23,42,.14); }
.stButton > button[kind="primary"]{ background:linear-gradient(120deg,var(--c1),var(--c2)) !important; border:none !important; color:#fff !important; }

/* ---- Bouton retour accueil ---- */
div[class*="st-key-home_"] button{
  background:#fff !important; color:var(--c1) !important; font-weight:800 !important;
  border:1px solid color-mix(in srgb,var(--c1) 26%, #fff) !important; min-height:42px !important;
}

/* ---- Avatars selectionnables ---- */
div[class*="st-key-av_"] button{ min-height:56px !important; font-size:1.7rem !important; border-radius:16px !important; padding:0 !important; }
div[class*="st-key-avon_"] button{ min-height:56px !important; font-size:1.7rem !important; border-radius:16px !important; padding:0 !important;
  background:linear-gradient(120deg,var(--c1),var(--c2)) !important; border:none !important; }

/* ---- Reactions ---- */
div[class*="st-key-react_"] button{ min-height:46px !important; font-size:1.4rem !important; border-radius:14px !important; padding:0 !important; }
.eno-reacts{ display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }
.eno-react{ background:#fff; border-radius:999px; padding:6px 12px; font-size:1rem; font-weight:700;
  border:1px solid rgba(15,23,42,.08); animation:pop .35s ease; }

__TILES__
div[class*="st-key-tile_"] button{ min-height:92px !important; font-size:1.05rem !important; font-weight:800 !important;
  border-radius:18px !important; box-shadow:0 8px 20px rgba(15,23,42,.16) !important;
  white-space:normal !important; line-height:1.25 !important; }
div[class*="st-key-tile_"] button p{ font-size:1.05rem !important; font-weight:800 !important; }

.eno-timer{ display:flex; align-items:center; gap:12px; font-weight:800; color:var(--ink);
  background:#fff; border-radius:16px; padding:10px 16px; border:1px solid rgba(15,23,42,.08);
  box-shadow:0 6px 18px rgba(15,23,42,.06); }
.eno-bar{ height:12px; border-radius:99px; background:#e2e8f0; overflow:hidden; flex:1; }
.eno-bar > span{ display:block; height:100%; border-radius:99px; background:linear-gradient(90deg,var(--c1),var(--c3)); transition:width .8s linear; }

.eno-row{ display:flex; align-items:center; gap:12px; background:#fff; border-radius:14px;
  padding:10px 14px; margin-bottom:8px; border:1px solid rgba(15,23,42,.06); box-shadow:0 4px 12px rgba(15,23,42,.05); }
.eno-rank{ width:34px; height:34px; border-radius:12px; display:grid; place-items:center; font-weight:900; color:#fff;
  background:linear-gradient(120deg,var(--c1),var(--c2)); flex:none; }
.eno-name{ font-weight:700; flex:1; }
.eno-score{ font-weight:900; color:var(--c1); }
.eno-avatar{ width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#eef2ff;font-size:1.1rem;flex:none;}
.eno-delta{ font-size:.78rem; font-weight:800; padding:2px 8px; border-radius:999px; }
.eno-up{ background:#dcfce7; color:#15803d; }
.eno-down{ background:#fee2e2; color:#b91c1c; }
.eno-flat{ background:#f1f5f9; color:#64748b; }

.eno-lobby{ display:flex; flex-wrap:wrap; gap:10px; }
.eno-chip{ background:#fff; border-radius:999px; padding:8px 14px; font-weight:700; font-size:.85rem;
  border:1px solid rgba(15,23,42,.08); box-shadow:0 4px 12px rgba(15,23,42,.06); animation:pop .35s ease; }
@keyframes pop{ from{transform:scale(.8);opacity:0} to{transform:scale(1);opacity:1} }

/* ---- Podium anime ---- */
.eno-podium{ display:flex; align-items:flex-end; justify-content:center; gap:14px; margin:18px 0 8px 0; }
.eno-pod{ width:120px; border-radius:18px 18px 0 0; background:linear-gradient(180deg,var(--c1),var(--c2));
  color:#fff; text-align:center; padding:12px 8px 10px 8px; animation:grow .7s cubic-bezier(.2,.9,.3,1.2); transform-origin:bottom; }
.eno-pod .a{ font-size:2rem; }
.eno-pod .n{ font-weight:800; font-size:.9rem; margin-top:4px; word-break:break-word; }
.eno-pod .s{ font-weight:900; font-size:1.1rem; }
.eno-pod1{ height:170px; } .eno-pod2{ height:132px; } .eno-pod3{ height:110px; }
@keyframes grow{ from{transform:scaleY(.15);opacity:.2} to{transform:scaleY(1);opacity:1} }

/* ---- Nuage de mots ---- */
.eno-cloud{ background:#fff; border-radius:18px; padding:20px; text-align:center; line-height:2.1;
  border:1px solid rgba(15,23,42,.06); box-shadow:0 6px 18px rgba(15,23,42,.05); }
.eno-word{ display:inline-block; margin:4px 10px; font-weight:800; font-family:'Baloo 2',sans-serif; animation:pop .4s ease; }

.eno-ok, .eno-ko{ border-radius:18px; padding:18px; color:#fff; font-weight:800; font-size:1.1rem; text-align:center; }
.eno-ok{ background:linear-gradient(120deg,#10b981,#22c55e); }
.eno-ko{ background:linear-gradient(120deg,#ef4444,#f43f5e); }

[data-baseweb="input"] input, [data-baseweb="select"] > div, .stTextArea textarea{
  border-radius:12px !important; font-size:16px !important; }
[data-testid="stMetricValue"]{ font-family:'Baloo 2',sans-serif; }

.stTabs [data-baseweb="tab-list"]{ gap:6px; }
.stTabs [data-baseweb="tab"]{ border-radius:12px 12px 0 0; padding:8px 16px; font-weight:700; background:rgba(255,255,255,.6); }
.stTabs [aria-selected="true"]{ background:#fff !important; color:var(--c1) !important; }

@media (max-width: 820px){
  .block-container{ padding:0.6rem 0.7rem 5rem 0.7rem !important; }
  .eno-hero{ padding:18px; border-radius:18px; }
  .eno-hero h1{ font-size:1.45rem; }
  .eno-card{ padding:16px; border-radius:16px; }
  div[class*="st-key-tile_"] button{ min-height:76px !important; }
  h1{ font-size:1.5rem !important; } h2{ font-size:1.2rem !important; }
  .eno-digit{ width:40px; height:54px; font-size:1.7rem; }
  .eno-code-xl .eno-digit{ width:48px; height:66px; font-size:2.1rem; }
  .eno-pod{ width:88px; } .eno-pod1{ height:140px; } .eno-pod2{ height:108px; } .eno-pod3{ height:90px; }
  [data-testid="stHorizontalBlock"]{ flex-wrap:wrap !important; gap:.4rem !important; }
  [data-testid="column"]{ min-width:46% !important; }
}
@supports (-webkit-touch-callout: none){ .stApp{ -webkit-text-size-adjust:100%; } }
</style>
"""
    css = css.replace("__C1__", c1).replace("__C2__", c2).replace("__C3__", c3).replace("__TILES__", tiles_css)
    st.markdown(css, unsafe_allow_html=True)
    st.markdown(
        """<meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="theme-color" content="#6366f1">
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover">""",
        unsafe_allow_html=True,
    )


# ==========================================================
# 2. STOCKAGE MULTI-JOUEURS + CODES DE SESSION A 6 CHIFFRES
#    SESSIONS/<code>/session.json
#    SESSIONS/<code>/players/<slug>.json  (1 fichier par joueur)
# ==========================================================
def slug(txt):
    return hashlib.md5(txt.strip().lower().encode("utf-8")).hexdigest()[:12]


def normaliser_code(saisie):
    """Accepte '123 456', '123-456', 'sess_1758…' (ancien format)."""
    if saisie is None:
        return ""
    s = str(saisie).strip()
    if s.lower().startswith("sess_"):
        return s
    chiffres = re.sub(r"\D", "", s)
    return chiffres if len(chiffres) == 6 else ""


def code_valide(code):
    return bool(re.fullmatch(r"\d{6}", str(code))) or str(code).lower().startswith("sess_")


def generer_code_session(essais=200):
    """Code a 6 chiffres, unique, sans 0 en tete et sans sequence triviale."""
    existants = set(lister_sessions())
    for _ in range(essais):
        code = str(random.randint(100000, 999999))
        if code in existants:
            continue
        if len(set(code)) == 1:
            continue
        if code in ("123456", "654321", "000000"):
            continue
        return code
    for c in range(100000, 1000000):
        if str(c) not in existants:
            return str(c)
    return f"sess_{int(time.time())}"


def ecrire_json_atomique(chemin, data):
    try:
        dossier = os.path.dirname(chemin) or "."
        os.makedirs(dossier, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=dossier, delete=False, encoding="utf-8") as tf:
            json.dump(data, tf, ensure_ascii=False, indent=2)
            tmp = tf.name
        os.replace(tmp, chemin)
        return True
    except Exception as e:
        print(f"[ecriture] {e}")
        return False


def lire_json(chemin, defaut=None):
    for _ in range(3):
        try:
            with open(chemin, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return defaut
        except Exception:
            time.sleep(0.05)
    return defaut


def dossier_session(sid):
    return os.path.join(DOSSIER_SESSIONS, str(sid))


def chemin_session(sid):
    return os.path.join(dossier_session(sid), "session.json")


def dossier_joueurs(sid):
    return os.path.join(dossier_session(sid), "players")


def charger_session(sid):
    if not sid or not code_valide(sid):
        return None
    return lire_json(chemin_session(sid))


def sauver_session(sid, data):
    return ecrire_json_atomique(chemin_session(sid), data)


def charger_joueur(sid, nom):
    return lire_json(os.path.join(dossier_joueurs(sid), f"{slug(nom)}.json"))


def sauver_joueur(sid, data):
    return ecrire_json_atomique(os.path.join(dossier_joueurs(sid), f"{slug(data['name'])}.json"), data)


def charger_tous_joueurs(sid):
    d = dossier_joueurs(sid)
    joueurs = []
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith(".json"):
                j = lire_json(os.path.join(d, f))
                if j:
                    joueurs.append(j)
    return sorted(joueurs, key=lambda x: (-x.get("score", 0), x.get("name", "")))


def prendre_verrou(sid, cle, ttl=10):
    """Verrou atomique : une seule instance fait avancer la manche."""
    path = os.path.join(dossier_session(sid), f".lock_{cle}")
    try:
        if os.path.exists(path) and time.time() - os.path.getmtime(path) > ttl:
            os.remove(path)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(time.time()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except Exception:
        return False


def lister_sessions():
    out = []
    if os.path.isdir(DOSSIER_SESSIONS):
        for d in os.listdir(DOSSIER_SESSIONS):
            if os.path.isfile(chemin_session(d)):
                out.append(d)
    return sorted(out, key=lambda s: os.path.getmtime(chemin_session(s)), reverse=True)


def supprimer_session(sid):
    import shutil
    try:
        shutil.rmtree(dossier_session(sid))
    except Exception as e:
        print(f"[suppression] {e}")


# ==========================================================
# 2 bis. PUBLICATION DES QUIZ POUR LE MODE ENTRAINEMENT
#    QCM/_publication.json  ->  {"fichier.json": true/false, ...}
#    Par defaut un quiz n'est PAS publie (choix volontairement restrictif).
# ==========================================================
def lister_fichiers_quiz():
    """Tous les quiz de la bibliotheque (le fichier de publication est exclu)."""
    if not os.path.isdir(DOSSIER_QUIZZES):
        return []
    return sorted(f for f in os.listdir(DOSSIER_QUIZZES)
                  if f.endswith(".json") and not f.startswith("_"))


def charger_publication():
    data = lire_json(FICHIER_PUBLICATION, {}) or {}
    return data if isinstance(data, dict) else {}


def sauver_publication(mapping):
    contenu = json.dumps(mapping, ensure_ascii=False, indent=2)
    ecrire_json_atomique(FICHIER_PUBLICATION, mapping)
    sauvegarder_fichier_github("QCM/_publication.json", contenu)


def est_publie(fichier):
    return bool(charger_publication().get(fichier, False))


def definir_publication(fichier, publie):
    mapping = charger_publication()
    mapping[fichier] = bool(publie)
    sauver_publication(mapping)


def lister_quiz_publies():
    mapping = charger_publication()
    return [f for f in lister_fichiers_quiz() if mapping.get(f, False)]


# ---------- Synchronisation GitHub ----------
def sauvegarder_fichier_github(chemin_relatif, contenu_str):
    try:
        if "GITHUB_TOKEN" in st.secrets:
            token = st.secrets["GITHUB_TOKEN"]
            url = f"https://api.github.com/repos/YannBzh94/enolou-qcm-web/contents/{chemin_relatif}"
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
            resp = requests.get(url, headers=headers)
            sha = resp.json().get("sha") if resp.status_code == 200 else None
            payload = {
                "message": f"MAJ {chemin_relatif} via Enolou Quiz",
                "content": base64.b64encode(contenu_str.encode("utf-8")).decode("utf-8"),
                "branch": "main",
            }
            if sha:
                payload["sha"] = sha
            return requests.put(url, headers=headers, json=payload).status_code in (200, 201)
    except Exception as e:
        print(f"[github] {e}")
    return False


def supprimer_fichier_github(chemin_relatif):
    try:
        if "GITHUB_TOKEN" in st.secrets:
            token = st.secrets["GITHUB_TOKEN"]
            url = f"https://api.github.com/repos/YannBzh94/enolou-qcm-web/contents/{chemin_relatif}"
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                requests.delete(url, headers=headers,
                                json={"message": f"Suppression {chemin_relatif}", "sha": r.json().get("sha"), "branch": "main"})
    except Exception as e:
        print(f"[github] {e}")


# ==========================================================
# 3. MOTEUR AUDIO (musique de fond + effets + tic-tac synchronise)
# ==========================================================
def fichier_en_base64(chemin):
    if chemin and os.path.exists(chemin):
        try:
            ext = chemin.strip().lower().split(".")[-1]
            mime = {"mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg",
                    "m4a": "audio/mp4", "aac": "audio/aac"}.get(ext, "audio/mpeg")
            with open(chemin, "rb") as f:
                return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"
        except Exception as e:
            print(f"[audio] {e}")
    return ""


def rendre_moteur_audio(musique_path, vol_musique, son_declenche=None, son_path=None, vol_sons=0.8):
    b64_music = fichier_en_base64(musique_path) if musique_path else ""
    b64_sfx = fichier_en_base64(son_path) if (son_declenche and son_path) else ""
    sfx_script = ""
    if b64_sfx:
        sfx_script = f"""const sfx=new Audio("{b64_sfx}");sfx.volume={float(vol_sons)};sfx.play().catch(e=>0);"""
    html = f"""
    <audio id="eno-bg" loop style="display:none;"></audio>
    <script>
      const a=document.getElementById('eno-bg'); const src="{b64_music}";
      if(a&&src){{ if(a.src!==src){{a.src=src;a.play().catch(e=>0);}} a.volume={float(vol_musique)};
        if(a.paused){{a.play().catch(e=>0);}} }} else if(a){{ a.pause(); }}
      {sfx_script}
    </script>"""
    components.html(html, height=0, width=0)


# ==========================================================
# 4. TYPES DE QUESTIONS & MOTEUR DE NOTATION
# ==========================================================
TYPES_QUESTION = {
    "qcm":        {"label": "QCM / Choix multiple", "icone": "🔘"},
    "vrai_faux":  {"label": "Vrai ou Faux",         "icone": "⚖️"},
    "classement": {"label": "Classement (ordonner)", "icone": "🔢"},
    "association":{"label": "Association (relier)",  "icone": "🔗"},
    "texte":      {"label": "Réponse libre (saisie)", "icone": "⌨️"},
    "curseur":    {"label": "Estimation (curseur)",   "icone": "🎚️"},
    "sondage":    {"label": "Sondage (sans points)",  "icone": "📊"},
}

MOTS_VIDES = {
    "le", "la", "les", "un", "une", "des", "de", "du", "au", "aux", "et", "ou", "a", "en",
    "pour", "par", "sur", "dans", "avec", "sans", "que", "qui", "est", "sont", "ce", "cet",
    "cette", "ces", "il", "elle", "on", "nous", "vous", "ils", "elles", "se", "sa", "son",
    "ses", "plus", "moins", "the", "of", "to", "and",
}


def normaliser(txt):
    txt = unicodedata.normalize("NFKD", str(txt).strip().lower())
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", txt).strip()


def evaluer_reponse(q, reponse):
    """Retourne (est_correct, ratio 0..1). Le ratio permet le credit partiel."""
    t = q.get("type", "qcm")
    d = q.get("donnees", {})

    if t == "sondage":
        return True, 0.0

    if t == "qcm":
        correctes = set(d.get("reponses_correctes", []))
        if not correctes:
            return False, 0.0
        rep = set(reponse if isinstance(reponse, list) else [reponse])
        if len(correctes) == 1:
            ok = rep == correctes
            return ok, 1.0 if ok else 0.0
        bonnes = len(rep & correctes)
        fausses = len(rep - correctes)
        ratio = max(0.0, (bonnes - fausses) / len(correctes))
        return rep == correctes, round(ratio, 3)

    if t == "vrai_faux":
        attendu = bool(d.get("reponse", True))
        ok = bool(reponse) == attendu
        return ok, 1.0 if ok else 0.0

    if t == "classement":
        attendu = d.get("elements", [])
        prop = list(reponse or [])
        if len(prop) != len(attendu) or not attendu:
            return False, 0.0
        n = len(attendu)
        pos = {v: i for i, v in enumerate(attendu)}
        paires_ok = paires_tot = 0
        for i in range(n):
            for j in range(i + 1, n):
                paires_tot += 1
                if pos.get(prop[i], -1) < pos.get(prop[j], 99):
                    paires_ok += 1
        ratio = paires_ok / paires_tot if paires_tot else 0.0
        return prop == attendu, round(ratio, 3)

    if t == "association":
        paires = d.get("paires", [])
        if not paires:
            return False, 0.0
        rep = reponse or {}
        bonnes = sum(1 for g, dr in paires if normaliser(rep.get(g, "")) == normaliser(dr))
        return bonnes == len(paires), round(bonnes / len(paires), 3)

    if t == "texte":
        acceptees = d.get("reponses_acceptees", [])
        rn = normaliser(reponse)
        ok = any(rn == normaliser(a) for a in acceptees)
        if not ok and d.get("tolerance_partielle", True):
            ok = any(rn and (rn in normaliser(a) or normaliser(a) in rn) for a in acceptees)
        return ok, 1.0 if ok else 0.0

    if t == "curseur":
        cible = float(d.get("valeur", 0))
        tol = float(d.get("tolerance", 0)) or max(1.0, abs(cible) * 0.1)
        ecart = abs(float(reponse) - cible)
        if ecart == 0:
            return True, 1.0
        if ecart <= tol:
            return True, round(1.0 - 0.5 * (ecart / tol), 3)
        return False, 0.0

    return False, 0.0


def multiplicateur_question(q, index=None, total=None, bonus_finale=False):
    """Double points : soit la question est marquee, soit c'est la derniere et le bonus finale est actif."""
    if q.get("double_points"):
        return 2
    if bonus_finale and index is not None and total and index == total - 1:
        return 2
    return 1


def calculer_points(q, ratio, elapsed=None, timer_sec=None, bonus_rapidite=False, multiplicateur=1):
    points = int(q.get("points", 10))
    if q.get("type") == "sondage":
        return 0
    base = points * ratio
    if bonus_rapidite and ratio > 0 and timer_sec:
        reste = max(0.0, (timer_sec - (elapsed or 0)) / timer_sec)
        base = base * (0.5 + 0.5 * reste)
    return int(round(base * max(1, int(multiplicateur))))


def points_max_session(questions, bonus_finale=False):
    total = 0
    n = len(questions)
    for i, q in enumerate(questions):
        if q.get("type") == "sondage":
            continue
        total += int(q.get("points", 10)) * multiplicateur_question(q, i, n, bonus_finale)
    return total


def texte_reponse(rep):
    if isinstance(rep, list):
        return " > ".join(str(x) for x in rep)
    if isinstance(rep, dict):
        return " | ".join(f"{k}→{v}" for k, v in rep.items())
    if isinstance(rep, bool):
        return "VRAI" if rep else "FAUX"
    return str(rep)


# ==========================================================
# 5. COMPOSANTS D'INTERFACE
# ==========================================================
def avatar_de(nom):
    """Avatar deduit du pseudo (valeur de repli)."""
    return AVATARS[int(hashlib.md5(nom.encode()).hexdigest(), 16) % len(AVATARS)]


def avatar_joueur(j):
    """Avatar reellement choisi par le joueur, sinon celui deduit du pseudo."""
    if isinstance(j, dict):
        return j.get("avatar") or avatar_de(j.get("name", ""))
    return avatar_de(str(j))


def hero(titre, sous_titre="", pills=None):
    p = "".join(f'<span class="eno-pill">{x}</span>' for x in (pills or []))
    st.markdown(
        f"""<div class="eno-hero"><h1>{titre}</h1><p>{sous_titre}</p>
        <div style="margin-top:10px">{p}</div></div>""",
        unsafe_allow_html=True,
    )


def bouton_accueil(cle, libelle="🏠 Accueil", reinitialiser_joueur=False):
    """Bouton de retour a l'ecran d'accueil, disponible sur tous les sous-menus."""
    if st.button(libelle, key=f"home_{cle}", use_container_width=True):
        st.session_state.espace = "accueil"
        st.session_state.qcm_selectionne = None
        st.session_state.quiz_started = False
        st.session_state.answered = False
        st.session_state.last_result = None
        st.session_state.current_idx = 0
        st.session_state.score_total = 0
        st.session_state.max_points = 0
        if reinitialiser_joueur:
            st.session_state.joueur_nom = ""
        for p in ("qcm", "session", "reorder"):
            st.query_params.pop(p, None)
        st.rerun()


def barre_navigation(cle, reinitialiser_joueur=False, extra_label=None, extra_cle=None):
    """Barre superieure : retour accueil (+ bouton secondaire optionnel)."""
    if extra_label:
        c1, c2, _ = st.columns([1, 1, 2])
        with c1:
            bouton_accueil(cle, reinitialiser_joueur=reinitialiser_joueur)
        with c2:
            clique = st.button(extra_label, key=f"extra_{extra_cle or cle}", use_container_width=True)
        return clique
    c1, _ = st.columns([1, 3])
    with c1:
        bouton_accueil(cle, reinitialiser_joueur=reinitialiser_joueur)
    return False


def afficher_code(code, label="Code de session", xl=False):
    code = str(code)
    if code.lower().startswith("sess_"):
        st.markdown(f"**{label} :** `{code}`")
        return
    digits = "".join(f'<div class="eno-digit">{c}</div>' for c in code)
    st.markdown(
        f"""<div class="eno-code-wrap {'eno-code-xl' if xl else ''}">
        <div class="eno-code-label">{label}</div>
        <div class="eno-code">{digits}</div></div>""",
        unsafe_allow_html=True,
    )


def chrono(restant, total):
    """Chrono statique (rafraichi par le fragment)."""
    pct = int(100 * restant / total) if total else 0
    st.markdown(
        f"""<div class="eno-timer">{'⏱️' if pct > 30 else '🔥'}<div class="eno-bar"><span style="width:{pct}%"></span></div>
        <div style="min-width:52px;text-align:right">{restant}s</div></div>""",
        unsafe_allow_html=True,
    )


def chrono_synchro(fin_timestamp, total, sonore=True, hauteur=74):
    """
    Chrono synchronise sur l'horloge SERVEUR : tous les joueurs voient la meme valeur.
    Le decompte s'anime cote navigateur (1 img/s) a partir de l'ecart serveur/client,
    sans attendre le rafraichissement du fragment.
    Bip discret (WebAudio) sur les 5 dernieres secondes.
    """
    maintenant = time.time()
    restant_serveur = max(0, int(round(fin_timestamp - maintenant)))
    total = max(1, int(total))
    pct = int(100 * restant_serveur / total)
    bip = "true" if sonore else "false"
    html = f"""
<style>
 body{{margin:0;background:transparent;font-family:Inter,system-ui,sans-serif}}
 .t{{display:flex;align-items:center;gap:12px;font-weight:800;color:#0b1020;background:#fff;
    border-radius:16px;padding:10px 16px;border:1px solid rgba(15,23,42,.08);box-shadow:0 6px 18px rgba(15,23,42,.06)}}
 .b{{height:12px;border-radius:99px;background:#e2e8f0;overflow:hidden;flex:1}}
 .b>span{{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#6366f1,#ec4899);
    transition:width .95s linear}}
 .v{{min-width:52px;text-align:right;font-variant-numeric:tabular-nums}}
 .urgent .v{{color:#dc2626}}
 .urgent .b>span{{background:linear-gradient(90deg,#f97316,#ef4444)}}
</style>
<div class="t" id="w"><span id="ic">⏱️</span><div class="b"><span id="bar" style="width:{pct}%"></span></div>
<div class="v" id="v">{restant_serveur}s</div></div>
<script>
 let r={restant_serveur}; const total={total}, sonore={bip};
 const v=document.getElementById('v'), bar=document.getElementById('bar'),
       w=document.getElementById('w'), ic=document.getElementById('ic');
 let ctx=null;
 function bip(){{
   if(!sonore) return;
   try{{
     ctx = ctx || new (window.AudioContext||window.webkitAudioContext)();
     const o=ctx.createOscillator(), g=ctx.createGain();
     o.frequency.value = r<=1 ? 880 : 620; o.type='sine';
     g.gain.setValueAtTime(0.06, ctx.currentTime);
     g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime+0.18);
     o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime+0.18);
   }}catch(e){{}}
 }}
 function rendu(){{
   v.textContent = r + 's';
   bar.style.width = Math.max(0, Math.round(100*r/total)) + '%';
   const urgent = r <= Math.max(5, total*0.25);
   w.classList.toggle('urgent', urgent);
   ic.textContent = urgent ? '🔥' : '⏱️';
 }}
 rendu();
 const id=setInterval(()=>{{
   if(r<=0){{ clearInterval(id); return; }}
   r--; rendu(); if(r<=5 && r>=0) bip();
 }}, 1000);
</script>"""
    components.html(html, height=hauteur)


def leaderboard(joueurs, limite=10, titre="🏆 Classement", rangs_precedents=None):
    """Classement ; si rangs_precedents est fourni, affiche le gain/perte de places."""
    st.markdown(f"#### {titre}")
    if not joueurs:
        st.info("Aucun joueur pour l'instant.")
        return
    medailles = {0: "🥇", 1: "🥈", 2: "🥉"}
    lignes = []
    for i, j in enumerate(joueurs[:limite]):
        delta_html = ""
        if rangs_precedents:
            av = rangs_precedents.get(j.get("name"))
            if av:
                d = av - (i + 1)
                if d > 0:
                    delta_html = f'<span class="eno-delta eno-up">▲ {d}</span>'
                elif d < 0:
                    delta_html = f'<span class="eno-delta eno-down">▼ {abs(d)}</span>'
                else:
                    delta_html = '<span class="eno-delta eno-flat">=</span>'
        lignes.append(
            f"""<div class="eno-row">
              <div class="eno-rank">{medailles.get(i, i+1)}</div>
              <div class="eno-avatar">{avatar_joueur(j)}</div>
              <div class="eno-name">{j.get('name','')}</div>
              {delta_html}
              <div class="eno-score">{j.get('score',0)} pts</div>
            </div>"""
        )
    st.markdown("".join(lignes), unsafe_allow_html=True)


def podium_anime(joueurs, titre="🏆 Podium"):
    """Podium 3 marches, anime a l'affichage."""
    if not joueurs:
        return
    st.markdown(f"#### {titre}")
    top = joueurs[:3]
    ordre_visuel = []
    if len(top) > 1:
        ordre_visuel.append((top[1], 2, "eno-pod2"))
    if top:
        ordre_visuel.insert(1 if len(ordre_visuel) else 0, (top[0], 1, "eno-pod1"))
    if len(top) > 2:
        ordre_visuel.append((top[2], 3, "eno-pod3"))
    blocs = "".join(
        f"""<div class="eno-pod {cls}">
              <div class="a">{avatar_joueur(j)}</div>
              <div class="n">{j.get('name','')}</div>
              <div class="s">{j.get('score',0)} pts</div>
              <div style="opacity:.85;font-size:.8rem;margin-top:4px">{"🥇" if r==1 else ("🥈" if r==2 else "🥉")}</div>
            </div>"""
        for j, r, cls in ordre_visuel
    )
    st.markdown(f'<div class="eno-podium">{blocs}</div>', unsafe_allow_html=True)


def nuage_de_mots(reponses, titre="☁️ Nuage de réponses", max_mots=28):
    """
    Nuage de mots pour les sondages et les reponses libres.
    Les options de sondage sont comptees telles quelles ; le texte libre est decoupe en mots.
    """
    compteur = Counter()
    for r in reponses:
        if r is None:
            continue
        if isinstance(r, list):
            for x in r:
                if str(x).strip():
                    compteur[str(x).strip()] += 1
        else:
            s = str(r).strip()
            if not s:
                continue
            if len(s.split()) <= 3:
                compteur[s] += 1
            else:
                for m in normaliser(s).split():
                    if len(m) > 2 and m not in MOTS_VIDES:
                        compteur[m] += 1
    if not compteur:
        st.info("Aucune réponse à afficher pour l'instant.")
        return
    st.markdown(f"#### {titre}")
    items = compteur.most_common(max_mots)
    vmax = items[0][1]
    vmin = items[-1][1]
    mots_html = []
    for i, (mot, n) in enumerate(items):
        ratio = 1.0 if vmax == vmin else (n - vmin) / (vmax - vmin)
        taille = round(0.95 + 2.05 * ratio, 2)
        couleur = TILE_COLORS[i % len(TILE_COLORS)]
        opacite = round(0.62 + 0.38 * ratio, 2)
        mots_html.append(
            f'<span class="eno-word" style="font-size:{taille}rem;color:{couleur};opacity:{opacite}" '
            f'title="{n} réponse(s)">{mot}</span>'
        )
    st.markdown(f'<div class="eno-cloud">{"".join(mots_html)}</div>', unsafe_allow_html=True)
    st.caption(f"{sum(compteur.values())} réponse(s) · {len(compteur)} terme(s) distinct(s)")


def collecter_reponses(joueurs, q_num):
    """Recupere toutes les reponses des joueurs pour une question donnee (numero 1-based)."""
    out = []
    for j in joueurs:
        for a in j.get("answers_detail", []):
            if a.get("q_num") == q_num:
                out.append(a.get("reponse"))
    return out


def afficher_reactions(joueurs, fenetre=25):
    """Affiche les reactions emoji recentes envoyees par les joueurs."""
    maintenant = time.time()
    recentes = []
    for j in joueurs:
        r = j.get("reaction") or {}
        if r.get("emoji") and maintenant - float(r.get("ts", 0)) <= fenetre:
            recentes.append((r["ts"], avatar_joueur(j), j.get("name", ""), r["emoji"]))
    if not recentes:
        return
    recentes.sort(reverse=True)
    chips = "".join(
        f'<span class="eno-react">{emoji} <span style="opacity:.6;font-size:.8rem">{av} {nom}</span></span>'
        for _, av, nom, emoji in recentes[:12]
    )
    st.markdown(f'<div class="eno-reacts">{chips}</div>', unsafe_allow_html=True)


def barre_reactions(sid, moi, cle):
    """Boutons de reaction emoji pour un joueur."""
    st.caption("Réagir :")
    cols = st.columns(len(REACTIONS))
    for i, emo in enumerate(REACTIONS):
        with cols[i]:
            if st.button(emo, key=f"react_{cle}_{i}", use_container_width=True):
                moi["reaction"] = {"emoji": emo, "ts": time.time()}
                sauver_joueur(sid, moi)
                st.rerun()


def selecteur_avatar(cle="insc"):
    """Grille d'avatars selectionnables ; renvoie l'avatar retenu."""
    st.session_state.setdefault("avatar_choisi", random.choice(AVATARS))
    st.markdown("##### 🎭 Choisissez votre avatar")
    par_ligne = 8
    for debut in range(0, len(AVATARS), par_ligne):
        ligne = AVATARS[debut:debut + par_ligne]
        cols = st.columns(par_ligne)
        for i, emo in enumerate(ligne):
            idx = debut + i
            actif = st.session_state.avatar_choisi == emo
            with cols[i]:
                prefixe = "avon" if actif else "av"
                if st.button(emo, key=f"{prefixe}_{cle}_{idx}", use_container_width=True):
                    st.session_state.avatar_choisi = emo
                    st.rerun()
    st.markdown(f"Avatar retenu : **{st.session_state.avatar_choisi}**")
    return st.session_state.avatar_choisi


def entete_question(q, index, total, points_affiches=True, multiplicateur=1):
    meta = TYPES_QUESTION.get(q.get("type", "qcm"), TYPES_QUESTION["qcm"])
    pts_base = int(q.get("points", 10))
    pts = ""
    if points_affiches and q.get("type") != "sondage":
        if multiplicateur > 1:
            pts = (f'<span class="eno-badge">🏆 {pts_base} pts</span>'
                   f'<span class="eno-badge eno-badge-or">✖️ {multiplicateur} — {pts_base*multiplicateur} pts en jeu !</span>')
        else:
            pts = f'<span class="eno-badge">🏆 {pts_base} pts</span>'
    st.markdown(
        f"""<div class="eno-card" style="padding:14px 18px">
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <span class="eno-badge">Question {index}/{total}</span>
            <span class="eno-badge">{meta['icone']} {meta['label']}</span>{pts}
          </div>
          <div style="font-size:1.35rem;font-weight:800;margin-top:12px;line-height:1.35">{q.get('consigne','')}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def afficher_medias(q, quiz_info=None):
    media = q.get("media", {}) or {}
    if q.get("document_texte"):
        st.info(q["document_texte"])
    img = media.get("image") or ""
    vid = media.get("video") or ""
    if img and os.path.exists(img):
        st.image(img, use_container_width=True)
    if vid and os.path.exists(vid):
        st.video(vid)


def widget_reponse(q, cle, desactive=False):
    """Affiche le widget adapte au type et renvoie la reponse courante (ou None)."""
    t = q.get("type", "qcm")
    d = q.get("donnees", {})

    if t in ("qcm", "sondage"):
        options = d.get("options", [])
        multi = t == "qcm" and len(d.get("reponses_correctes", [])) > 1
        sel_key = f"sel_{cle}"
        st.session_state.setdefault(sel_key, [])
        if multi:
            st.caption("🔷 Plusieurs bonnes réponses possibles — touchez toutes les tuiles correctes.")
        cols = st.columns(2)
        for i, opt in enumerate(options):
            actif = opt in st.session_state[sel_key]
            with cols[i % 2]:
                libelle = f"{TILE_SHAPES[i % len(TILE_SHAPES)]}  {opt}" + ("  ✅" if actif else "")
                if st.button(libelle, key=f"tile_{i}_{cle}", use_container_width=True, disabled=desactive):
                    if multi:
                        st.session_state[sel_key].remove(opt) if actif else st.session_state[sel_key].append(opt)
                    else:
                        st.session_state[sel_key] = [] if actif else [opt]
                    st.rerun()
        sel = st.session_state[sel_key]
        if not sel:
            return None
        return sel if multi else sel[0]

    if t == "vrai_faux":
        sel_key = f"vf_{cle}"
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅  VRAI", key=f"tile_3_{cle}_v", use_container_width=True, disabled=desactive):
                st.session_state[sel_key] = True
                st.rerun()
        with c2:
            if st.button("❌  FAUX", key=f"tile_0_{cle}_f", use_container_width=True, disabled=desactive):
                st.session_state[sel_key] = False
                st.rerun()
        if sel_key in st.session_state:
            st.success(f"Votre choix : **{'VRAI' if st.session_state[sel_key] else 'FAUX'}**")
        return st.session_state.get(sel_key)

    if t == "classement":
        elements = d.get("elements", [])
        melange = list(elements)
        random.Random(q.get("id", 0) * 7 + 13).shuffle(melange)
        ordre_key = f"ord_{cle}"
        st.session_state.setdefault(ordre_key, [])
        st.caption(f"🔢 {d.get('consigne_ordre','Touchez les éléments dans le bon ordre (1er → dernier).')}")
        restants = [e for e in melange if e not in st.session_state[ordre_key]]
        cols = st.columns(2)
        for i, e in enumerate(restants):
            with cols[i % 2]:
                if st.button(e, key=f"tile_{(i+2) % len(TILE_COLORS)}_{cle}_{i}", use_container_width=True, disabled=desactive):
                    st.session_state[ordre_key].append(e)
                    st.rerun()
        if st.session_state[ordre_key]:
            st.markdown("".join(
                f'<div class="eno-row"><div class="eno-rank">{i+1}</div><div class="eno-name">{e}</div></div>'
                for i, e in enumerate(st.session_state[ordre_key])), unsafe_allow_html=True)
            if not desactive and st.button("↩️ Recommencer le classement", key=f"reset_{cle}", use_container_width=True):
                st.session_state[ordre_key] = []
                st.rerun()
        return st.session_state[ordre_key] if len(st.session_state[ordre_key]) == len(elements) else None

    if t == "association":
        paires = d.get("paires", [])
        droites = [p[1] for p in paires]
        random.Random(q.get("id", 0) * 3 + 5).shuffle(droites)
        st.caption("🔗 Associez chaque élément de gauche à sa correspondance.")
        rep = {}
        for i, (g, _) in enumerate(paires):
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown(f"<div class='eno-row'><div class='eno-name'>{g}</div></div>", unsafe_allow_html=True)
            with c2:
                choix = st.selectbox("↔", ["— choisir —"] + droites, key=f"assoc_{cle}_{i}",
                                     disabled=desactive, label_visibility="collapsed")
            if choix != "— choisir —":
                rep[g] = choix
        return rep if len(rep) == len(paires) else None

    if t == "texte":
        val = st.text_input("✍️ Votre réponse", key=f"txt_{cle}", disabled=desactive, placeholder="Tapez votre réponse…")
        return val.strip() if val and val.strip() else None

    if t == "curseur":
        mini, maxi = float(d.get("min", 0)), float(d.get("max", 100))
        val = st.slider(d.get("unite", "Votre estimation"), mini, maxi, (mini + maxi) / 2,
                        step=float(d.get("pas", 1)), key=f"cur_{cle}", disabled=desactive)
        return float(val)

    return None


def nettoyer_widgets(cle):
    for p in ("sel_", "vf_", "ord_", "txt_", "cur_"):
        st.session_state.pop(f"{p}{cle}", None)


def afficher_feedback(q, correct, ratio, points_gagnes, multiplicateur=1):
    suffixe = f" (×{multiplicateur} 🔥)" if multiplicateur > 1 else ""
    if q.get("type") == "sondage":
        st.info("📊 Réponse enregistrée — merci !")
    elif correct:
        st.markdown(f"<div class='eno-ok'>🎉 Bonne réponse ! +{points_gagnes} pts{suffixe}</div>", unsafe_allow_html=True)
    elif ratio > 0:
        st.markdown(f"<div class='eno-ok' style='background:linear-gradient(120deg,#f59e0b,#f97316)'>"
                    f"➗ Partiellement juste — +{points_gagnes} pts{suffixe}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='eno-ko'>❌ Raté cette fois !</div>", unsafe_allow_html=True)
    if q.get("explication"):
        st.caption(f"💡 {q['explication']}")
    if q.get("type") == "classement" and not correct:
        st.caption("Ordre attendu : " + " > ".join(q.get("donnees", {}).get("elements", [])))


# ==========================================================
# 6. EXPORT DES RESULTATS
# ==========================================================
def generer_csv_session(sid):
    lignes = []
    for j in charger_tous_joueurs(sid):
        lignes.append({
            "Participant": j.get("name"), "Avatar": avatar_joueur(j), "Score": j.get("score", 0),
            "Score max": j.get("max_points", 0),
            "Réussite %": round(100 * j.get("score", 0) / max(1, j.get("max_points", 1)), 1),
            "Statut": "Terminé" if j.get("finished") else "En cours",
            "Question": "", "Réponse": "", "Correct": "", "Points": "",
        })
        for a in j.get("answers_detail", []):
            lignes.append({
                "Participant": j.get("name"), "Avatar": "", "Score": "", "Score max": "", "Réussite %": "", "Statut": "",
                "Question": f"Q{a.get('q_num')} — {a.get('consigne','')}",
                "Réponse": texte_reponse(a.get("reponse")),
                "Correct": "Oui" if a.get("correct") else "Non",
                "Points": a.get("points"),
            })
    df = pd.DataFrame(lignes) if lignes else pd.DataFrame(columns=["Participant"])
    return df.to_csv(index=False, sep=";").encode("utf-8-sig")


def enregistrer_qcm_actuel():
    donnees = {
        "quiz_info": {
            "titre": st.session_state.edit_titre,
            "description": st.session_state.edit_desc,
            "image": st.session_state.edit_quiz_image,
            "document_appui": st.session_state.edit_document_appui,
            "video": st.session_state.edit_quiz_video,
            "musique": st.session_state.edit_musique,
            "son_good": st.session_state.edit_son_good,
            "son_bad": st.session_state.edit_son_bad,
            "volume_musique": st.session_state.edit_vol_musique,
            "volume_sons": st.session_state.edit_vol_sons,
        },
        "questions": st.session_state.edit_questions,
    }
    contenu = json.dumps(donnees, ensure_ascii=False, indent=2)
    nom = st.session_state.edit_nom_fichier
    if not nom.endswith(".json"):
        nom += ".json"
    with open(os.path.join(DOSSIER_QUIZZES, nom), "w", encoding="utf-8") as f:
        f.write(contenu)
    sauvegarder_fichier_github(f"QCM/{nom}", contenu)


# ==========================================================
# 6 bis. IMPORT / EXPORT EXCEL DES QUESTIONS  (v2.3 — Lot 3)
#
#   Un classeur = un quiz.
#     Feuille "Questions"  -> une ligne par question
#     Feuille "Quiz"       -> metadonnees (titre, description, medias, sons)
#     Feuille "Aide"       -> mode d'emploi + syntaxe par type
#
#   Colonne "Donnees" : syntaxe compacte, une seule cellule, selon le type.
#     qcm / sondage : options separees par "|", bonne(s) reponse(s) prefixee(s) par "*"
#                     ex : *Paris | Lyon | Nice | Brest
#     vrai_faux     : VRAI  ou  FAUX
#     classement    : elements dans le BON ordre, separes par ">"
#                     ex : 1900 > 1950 > 2000 > 2020
#     association   : paires "gauche = droite", separees par "|"
#                     ex : ACPR = Superviseur | EBA = Autorite europeenne
#     texte         : reponses acceptees separees par "|"
#     curseur       : min ; max ; valeur ; tolerance ; pas ; unite
#                     ex : 0 ; 200 ; 100 ; 20 ; 1 ; Nombre de vehicules
# ==========================================================
COLONNES_EXCEL = [
    "N°", "Type", "Consigne", "Donnees", "Points", "Double points",
    "Chrono (s)", "Difficulte", "Explication", "Image", "Video", "Texte d'appui",
]

SEP_OPTIONS = "|"
SEP_ORDRE = ">"
SEP_PAIRE = "="
SEP_CURSEUR = ";"

ALIAS_TYPES = {
    "qcm": "qcm", "choix multiple": "qcm", "choix": "qcm", "multiple": "qcm", "mcq": "qcm",
    "vrai_faux": "vrai_faux", "vrai faux": "vrai_faux", "vrai/faux": "vrai_faux",
    "vf": "vrai_faux", "vrai ou faux": "vrai_faux", "boolean": "vrai_faux",
    "classement": "classement", "ordre": "classement", "ordonner": "classement", "ranking": "classement",
    "association": "association", "associer": "association", "relier": "association",
    "appariement": "association", "matching": "association",
    "texte": "texte", "reponse libre": "texte", "libre": "texte", "saisie": "texte", "open": "texte",
    "curseur": "curseur", "estimation": "curseur", "slider": "curseur", "numerique": "curseur",
    "sondage": "sondage", "poll": "sondage", "opinion": "sondage",
}


def _vrai(valeur):
    """Interprete une cellule comme un booleen (tolerant : oui/non, x, 1/0, vrai/faux…)."""
    if valeur is None:
        return False
    if isinstance(valeur, bool):
        return valeur
    if isinstance(valeur, (int, float)):
        return float(valeur) != 0
    return normaliser(valeur) in {"oui", "o", "x", "vrai", "true", "1", "yes", "y"}


def _texte(valeur):
    """Cellule -> chaine propre (les cellules vides pandas deviennent '')."""
    if valeur is None:
        return ""
    s = str(valeur)
    if s.strip().lower() in ("nan", "none", "nat"):
        return ""
    return s.strip()


def _entier(valeur, defaut):
    try:
        return int(float(str(valeur).replace(",", ".").strip()))
    except (TypeError, ValueError):
        return defaut


def _reel(valeur, defaut):
    try:
        return float(str(valeur).replace(",", ".").strip())
    except (TypeError, ValueError):
        return defaut


def resoudre_type(valeur):
    """Accepte le code exact, le libelle affiche ou un synonyme courant."""
    brut = _texte(valeur)
    if not brut:
        return None
    if brut in TYPES_QUESTION:
        return brut
    n = normaliser(brut)
    if n in ALIAS_TYPES:
        return ALIAS_TYPES[n]
    for code, meta in TYPES_QUESTION.items():
        if n == normaliser(meta["label"]) or n.startswith(normaliser(code)):
            return code
    return None


# ---------------------------------------------------------
# Serialisation : question JSON -> cellule "Donnees"
# ---------------------------------------------------------
def donnees_vers_cellule(q):
    t = q.get("type", "qcm")
    d = q.get("donnees", {}) or {}

    if t in ("qcm", "sondage"):
        correctes = set(d.get("reponses_correctes", []))
        return f" {SEP_OPTIONS} ".join(
            ("*" if o in correctes else "") + str(o) for o in d.get("options", []))

    if t == "vrai_faux":
        return "VRAI" if d.get("reponse", True) else "FAUX"

    if t == "classement":
        return f" {SEP_ORDRE} ".join(str(e) for e in d.get("elements", []))

    if t == "association":
        return f" {SEP_OPTIONS} ".join(f"{a} {SEP_PAIRE} {b}" for a, b in d.get("paires", []))

    if t == "texte":
        return f" {SEP_OPTIONS} ".join(str(a) for a in d.get("reponses_acceptees", []))

    if t == "curseur":
        return f" {SEP_CURSEUR} ".join(str(x) for x in [
            d.get("min", 0), d.get("max", 100), d.get("valeur", 50),
            d.get("tolerance", 5), d.get("pas", 1), d.get("unite", "Votre estimation")])

    return ""


# ---------------------------------------------------------
# Deserialisation : cellule "Donnees" -> dict JSON
# Retourne (donnees, liste_d_erreurs)
# ---------------------------------------------------------
def cellule_vers_donnees(type_q, cellule, q_existante=None):
    brut = _texte(cellule)
    erreurs = []

    if type_q in ("qcm", "sondage"):
        options, correctes = [], []
        for morceau in brut.split(SEP_OPTIONS):
            m = morceau.strip()
            if not m:
                continue
            if m.startswith("*"):
                m = m[1:].strip()
                if m:
                    correctes.append(m)
            if m:
                options.append(m)
        if len(options) < 2:
            erreurs.append("au moins 2 options attendues, séparées par « | »")
        if type_q == "qcm":
            if not correctes:
                erreurs.append("aucune bonne réponse : préfixez-la par « * »")
            return {"options": options, "reponses_correctes": correctes}, erreurs
        return {"options": options}, erreurs

    if type_q == "vrai_faux":
        n = normaliser(brut)
        if n in ("vrai", "v", "true", "oui", "1", "x"):
            return {"reponse": True}, erreurs
        if n in ("faux", "f", "false", "non", "0"):
            return {"reponse": False}, erreurs
        erreurs.append("attendu « VRAI » ou « FAUX »")
        return {"reponse": True}, erreurs

    if type_q == "classement":
        els = [e.strip() for e in brut.split(SEP_ORDRE) if e.strip()]
        if len(els) < 2:
            erreurs.append("au moins 2 éléments attendus, séparés par « > », dans le bon ordre")
        cons = (q_existante or {}).get("donnees", {}).get("consigne_ordre", "Classez du plus petit au plus grand")
        return {"elements": els, "consigne_ordre": cons}, erreurs

    if type_q == "association":
        paires = []
        for morceau in brut.split(SEP_OPTIONS):
            if SEP_PAIRE not in morceau:
                continue
            g, dte = morceau.split(SEP_PAIRE, 1)
            if g.strip() and dte.strip():
                paires.append([g.strip(), dte.strip()])
        if len(paires) < 2:
            erreurs.append("au moins 2 paires attendues, au format « gauche = droite », séparées par « | »")
        return {"paires": paires}, erreurs

    if type_q == "texte":
        acc = [a.strip() for a in brut.split(SEP_OPTIONS) if a.strip()]
        if not acc:
            erreurs.append("au moins une réponse acceptée attendue")
        tol = (q_existante or {}).get("donnees", {}).get("tolerance_partielle", True)
        return {"reponses_acceptees": acc, "tolerance_partielle": tol}, erreurs

    if type_q == "curseur":
        parts = [p.strip() for p in brut.split(SEP_CURSEUR)]
        while len(parts) < 6:
            parts.append("")
        mini = _reel(parts[0], 0.0)
        maxi = _reel(parts[1], 100.0)
        valeur = _reel(parts[2], (mini + maxi) / 2)
        tolerance = _reel(parts[3], max(1.0, abs(maxi - mini) * 0.05))
        pas = _reel(parts[4], 1.0)
        unite = parts[5] or "Votre estimation"
        if maxi <= mini:
            erreurs.append("le maximum doit être supérieur au minimum (format : min ; max ; valeur ; tolérance ; pas ; unité)")
        elif not (mini <= valeur <= maxi):
            erreurs.append("la valeur exacte doit être comprise entre le minimum et le maximum")
        return {"min": mini, "max": maxi, "valeur": valeur,
                "tolerance": tolerance, "pas": pas, "unite": unite}, erreurs

    erreurs.append(f"type « {type_q} » inconnu")
    return {}, erreurs


# ---------------------------------------------------------
# EXPORT : quiz -> classeur Excel
# ---------------------------------------------------------
def exporter_quiz_excel(quiz_info, questions, nom_fichier=""):
    """Construit le classeur Excel du quiz et renvoie les octets."""
    lignes = []
    for i, q in enumerate(questions):
        lignes.append({
            "N°": i + 1,
            "Type": q.get("type", "qcm"),
            "Consigne": q.get("consigne", ""),
            "Donnees": donnees_vers_cellule(q),
            "Points": int(q.get("points", 10)),
            "Double points": "OUI" if q.get("double_points") else "",
            "Chrono (s)": int(q.get("timer_secondes", 30)),
            "Difficulte": q.get("difficulte", "Moyen"),
            "Explication": q.get("explication", ""),
            "Image": (q.get("media", {}) or {}).get("image", ""),
            "Video": (q.get("media", {}) or {}).get("video", ""),
            "Texte d'appui": q.get("document_texte", ""),
        })
    df_q = pd.DataFrame(lignes, columns=COLONNES_EXCEL)

    df_meta = pd.DataFrame(
        [{"Paramètre": k, "Valeur": v} for k, v in [
            ("Nom du fichier JSON", nom_fichier),
            ("Titre", quiz_info.get("titre", "")),
            ("Description", quiz_info.get("description", "")),
            ("Image", quiz_info.get("image", "")),
            ("Document d'appui", quiz_info.get("document_appui", "")),
            ("Vidéo", quiz_info.get("video", "")),
            ("Musique de fond", quiz_info.get("musique", "")),
            ("Son bonne réponse", quiz_info.get("son_good", "")),
            ("Son mauvaise réponse", quiz_info.get("son_bad", "")),
            ("Volume musique", quiz_info.get("volume_musique", 0.5)),
            ("Volume effets", quiz_info.get("volume_sons", 0.8)),
        ]])

    aide = [
        ("Principe", "Une ligne = une question. Ne modifiez pas les intitulés de colonnes."),
        ("Colonne Type", "Valeurs acceptées : " + ", ".join(TYPES_QUESTION.keys())),
        ("Colonne Donnees", "Syntaxe compacte, voir les exemples ci-dessous selon le type."),
        ("", ""),
        ("qcm", "Options séparées par « | ». Préfixez d'une « * » chaque bonne réponse."),
        ("  exemple", "*Paris | Lyon | Nice | Brest"),
        ("  plusieurs bonnes", "*ACPR | *EBA | Ministère | Préfecture"),
        ("vrai_faux", "VRAI ou FAUX"),
        ("classement", "Éléments dans le BON ordre, séparés par « > »"),
        ("  exemple", "1900 > 1950 > 2000 > 2020"),
        ("association", "Paires « gauche = droite », séparées par « | »"),
        ("  exemple", "ACPR = Superviseur | EBA = Autorité européenne | GAFI = LCB-FT"),
        ("texte", "Réponses acceptées séparées par « | » (accents et majuscules ignorés)"),
        ("  exemple", "Crédit-bail | Leasing | Location avec option d'achat"),
        ("curseur", "min ; max ; valeur exacte ; tolérance ; pas ; libellé"),
        ("  exemple", "0 ; 200 ; 100 ; 20 ; 1 ; Nombre de véhicules"),
        ("sondage", "Options séparées par « | », sans « * » : aucune bonne réponse, aucun point"),
        ("  exemple", "Dynamique | Technique | Trop rapide | Clair"),
        ("", ""),
        ("Double points", "Écrivez OUI pour une question bonus (points ×2)"),
        ("Points / Chrono", "Nombres entiers. Valeurs par défaut : 10 points, 30 secondes."),
        ("Difficulte", "Facile, Moyen ou Difficile"),
        ("Import", "L'import remplace l'intégralité des questions du quiz sélectionné."),
    ]
    df_aide = pd.DataFrame(aide, columns=["Rubrique", "Explication"])

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_q.to_excel(writer, sheet_name="Questions", index=False)
        df_meta.to_excel(writer, sheet_name="Quiz", index=False)
        df_aide.to_excel(writer, sheet_name="Aide", index=False)
        largeurs = {"Questions": {"A": 6, "B": 14, "C": 52, "D": 58, "E": 9, "F": 14,
                                  "G": 11, "H": 12, "I": 42, "J": 22, "K": 22, "L": 34},
                    "Quiz": {"A": 26, "B": 52},
                    "Aide": {"A": 22, "B": 86}}
        for feuille, cols in largeurs.items():
            ws = writer.sheets[feuille]
            for col, w in cols.items():
                ws.column_dimensions[col].width = w
            ws.freeze_panes = "A2"
    return buf.getvalue()


def modele_excel_vierge():
    """Classeur d'exemple couvrant les 7 types, pret a completer."""
    exemples = [
        {"id": 1, "type": "qcm", "consigne": "Quel organisme supervise les établissements de crédit en France ?",
         "points": 10, "timer_secondes": 20, "difficulte": "Facile",
         "donnees": {"options": ["ACPR", "AMF", "INSEE", "URSSAF"], "reponses_correctes": ["ACPR"]},
         "explication": "L'ACPR est l'autorité de contrôle prudentiel et de résolution.", "media": {}},
        {"id": 2, "type": "qcm", "consigne": "Lesquels relèvent de la LCB-FT ? (plusieurs réponses)",
         "points": 15, "timer_secondes": 30, "difficulte": "Moyen",
         "donnees": {"options": ["Connaissance client", "Gel des avoirs", "Politique tarifaire", "Déclaration de soupçon"],
                     "reponses_correctes": ["Connaissance client", "Gel des avoirs", "Déclaration de soupçon"]},
         "explication": "", "media": {}},
        {"id": 3, "type": "vrai_faux", "consigne": "Le crédit-bail transfère la propriété dès la signature.",
         "points": 10, "timer_secondes": 15, "difficulte": "Facile",
         "donnees": {"reponse": False}, "explication": "La propriété reste au bailleur jusqu'à la levée d'option.",
         "media": {}},
        {"id": 4, "type": "classement", "consigne": "Classez ces étapes du plus tôt au plus tard.",
         "points": 15, "timer_secondes": 45, "difficulte": "Moyen",
         "donnees": {"elements": ["Demande de financement", "Analyse crédit", "Accord", "Mise en place"],
                     "consigne_ordre": "Du plus tôt au plus tard"}, "explication": "", "media": {}},
        {"id": 5, "type": "association", "consigne": "Associez chaque sigle à sa définition.",
         "points": 12, "timer_secondes": 60, "difficulte": "Moyen",
         "donnees": {"paires": [["ACPR", "Superviseur français"], ["EBA", "Autorité bancaire européenne"],
                                ["GAFI", "Normes anti-blanchiment"]]}, "explication": "", "media": {}},
        {"id": 6, "type": "texte", "consigne": "Comment nomme-t-on la location avec option d'achat ?",
         "points": 10, "timer_secondes": 30, "difficulte": "Moyen",
         "donnees": {"reponses_acceptees": ["Crédit-bail", "Leasing", "LOA"], "tolerance_partielle": True},
         "explication": "", "media": {}},
        {"id": 7, "type": "curseur", "consigne": "Estimez la durée moyenne d'un contrat, en mois.",
         "points": 10, "timer_secondes": 25, "difficulte": "Difficile",
         "donnees": {"min": 12, "max": 72, "valeur": 48, "tolerance": 6, "pas": 1, "unite": "Durée en mois"},
         "explication": "", "media": {}},
        {"id": 8, "type": "sondage", "consigne": "Quel mot décrit le mieux cette séance ?",
         "points": 0, "timer_secondes": 30, "difficulte": "Facile",
         "donnees": {"options": ["Dynamique", "Technique", "Trop rapide", "Clair"]},
         "explication": "", "media": {}},
        {"id": 9, "type": "qcm", "consigne": "Question finale à points doublés : quel est le rôle du KYC ?",
         "points": 20, "timer_secondes": 30, "difficulte": "Difficile", "double_points": True,
         "donnees": {"options": ["Connaître son client", "Fixer les taux", "Gérer la trésorerie", "Recruter"],
                     "reponses_correctes": ["Connaître son client"]}, "explication": "", "media": {}},
    ]
    info = {"titre": "Modèle Enolou Quiz", "description": "Exemple couvrant les 7 types de questions",
            "volume_musique": 0.5, "volume_sons": 0.8}
    return exporter_quiz_excel(info, exemples, "mon_nouveau_quiz.json")


# ---------------------------------------------------------
# IMPORT : classeur Excel -> (questions, quiz_info, rapport)
# ---------------------------------------------------------
def importer_quiz_excel(fichier):
    """
    Lit un classeur et renvoie (questions, quiz_info, rapport).
    `rapport` = {"erreurs": [...], "avertissements": [...], "lues": n, "retenues": n}
    Les lignes invalides sont ecartees : l'import n'est propose que si aucune erreur.
    """
    rapport = {"erreurs": [], "avertissements": [], "lues": 0, "retenues": 0}
    try:
        feuilles = pd.read_excel(fichier, sheet_name=None, dtype=object, engine="openpyxl")
    except Exception as e:
        rapport["erreurs"].append(f"Fichier illisible : {e}")
        return [], {}, rapport

    # --- Feuille Questions ---
    nom_feuille = next((n for n in feuilles if normaliser(n) == "questions"), None)
    if nom_feuille is None:
        nom_feuille = list(feuilles)[0]
        rapport["avertissements"].append(
            f"Aucune feuille « Questions » : la feuille « {nom_feuille} » a été utilisée.")
    df = feuilles[nom_feuille]

    colonnes = {normaliser(c): c for c in df.columns}

    def col(*noms):
        for n in noms:
            if normaliser(n) in colonnes:
                return colonnes[normaliser(n)]
        return None

    c_type = col("Type")
    c_cons = col("Consigne", "Question", "Énoncé", "Enonce")
    c_don = col("Donnees", "Données", "Reponses", "Réponses")
    if not (c_type and c_cons and c_don):
        manquantes = [n for n, c in (("Type", c_type), ("Consigne", c_cons), ("Donnees", c_don)) if not c]
        rapport["erreurs"].append("Colonne(s) obligatoire(s) absente(s) : " + ", ".join(manquantes))
        return [], {}, rapport

    c_pts, c_dbl = col("Points"), col("Double points", "Bonus")
    c_tmr = col("Chrono (s)", "Chrono", "Timer", "Temps")
    c_diff, c_expl = col("Difficulte", "Difficulté"), col("Explication")
    c_img, c_vid = col("Image"), col("Video", "Vidéo")
    c_doc = col("Texte d'appui", "Texte d appui", "Support")

    questions = []
    for pos, (_, ligne) in enumerate(df.iterrows()):
        num_excel = pos + 2  # +1 en-tete, +1 index 1-based
        type_brut, consigne = ligne.get(c_type), _texte(ligne.get(c_cons))
        if not _texte(type_brut) and not consigne:
            continue  # ligne vide : ignoree silencieusement
        rapport["lues"] += 1

        type_q = resoudre_type(type_brut)
        if not type_q:
            rapport["erreurs"].append(
                f"Ligne {num_excel} : type « {_texte(type_brut)} » non reconnu "
                f"(attendu : {', '.join(TYPES_QUESTION.keys())}).")
            continue
        if not consigne:
            rapport["erreurs"].append(f"Ligne {num_excel} : consigne vide.")
            continue

        donnees, erreurs = cellule_vers_donnees(type_q, ligne.get(c_don))
        if erreurs:
            for e in erreurs:
                rapport["erreurs"].append(f"Ligne {num_excel} ({type_q}) : {e}.")
            continue

        pts = _entier(ligne.get(c_pts) if c_pts else None, 0 if type_q == "sondage" else 10)
        pts = max(0, min(200, pts))
        tmr = _entier(ligne.get(c_tmr) if c_tmr else None, 30)
        if not (5 <= tmr <= 300):
            rapport["avertissements"].append(
                f"Ligne {num_excel} : chrono {tmr}s hors bornes, ramené dans l'intervalle 5–300 s.")
            tmr = max(5, min(300, tmr))
        diff = _texte(ligne.get(c_diff)) if c_diff else ""
        if normaliser(diff) not in ("facile", "moyen", "difficile"):
            diff = "Moyen"
        else:
            diff = {"facile": "Facile", "moyen": "Moyen", "difficile": "Difficile"}[normaliser(diff)]

        questions.append({
            "id": len(questions) + 1,
            "consigne": consigne,
            "type": type_q,
            "difficulte": diff,
            "points": pts,
            "double_points": _vrai(ligne.get(c_dbl)) if c_dbl else False,
            "tag": "Général",
            "timer_secondes": tmr,
            "donnees": donnees,
            "explication": _texte(ligne.get(c_expl)) if c_expl else "",
            "document_texte": _texte(ligne.get(c_doc)) if c_doc else "",
            "media": {"image": _texte(ligne.get(c_img)) if c_img else "",
                      "video": _texte(ligne.get(c_vid)) if c_vid else ""},
        })

    rapport["retenues"] = len(questions)
    if rapport["lues"] == 0:
        rapport["erreurs"].append("Aucune question trouvée dans le classeur.")

    # --- Feuille Quiz (metadonnees, facultative) ---
    quiz_info = {}
    nom_meta = next((n for n in feuilles if normaliser(n) == "quiz"), None)
    if nom_meta:
        correspondance = {
            "titre": "titre", "description": "description", "image": "image",
            "document d appui": "document_appui", "video": "video", "musique de fond": "musique",
            "son bonne reponse": "son_good", "son mauvaise reponse": "son_bad",
            "volume musique": "volume_musique", "volume effets": "volume_sons",
            "nom du fichier json": "_nom_fichier",
        }
        dfm = feuilles[nom_meta]
        if dfm.shape[1] >= 2:
            for _, l in dfm.iterrows():
                cle = correspondance.get(normaliser(l.iloc[0]))
                if not cle:
                    continue
                val = l.iloc[1]
                if cle in ("volume_musique", "volume_sons"):
                    quiz_info[cle] = max(0.0, min(1.0, _reel(val, 0.5)))
                else:
                    quiz_info[cle] = _texte(val)
    return questions, quiz_info, rapport


# ==========================================================
# 7. ETAT APPLICATIF & NAVIGATION
# ==========================================================
ETATS_DEFAUT = {
    "palette": "Nebula",
    "qcm_selectionne": None,
    "banque": {"quiz_info": {}, "questions": []},
    "current_idx": 0,
    "score_total": 0,
    "max_points": 0,
    "quiz_started": False,
    "answered": False,
    "last_result": None,
    "question_start_time": time.time(),
    "declencher_son": None,
    "joueur_nom": "",
    "avatar_choisi": None,
    "rangs_precedents": {},
    "edit_nom_fichier": "nouveau_qcm.json",
    "edit_titre": "",
    "edit_desc": "",
    "edit_quiz_image": "",
    "edit_document_appui": "",
    "edit_quiz_video": "",
    "edit_musique": "",
    "edit_son_good": "",
    "edit_son_bad": "",
    "edit_vol_musique": 0.5,
    "edit_vol_sons": 0.8,
    "edit_questions": [],
    "dernier_choix_edition": None,
    "selected_collec_qcm": "",
    "selected_edit_qcm": "",
    "espace": None,
}
for k, v in ETATS_DEFAUT.items():
    st.session_state.setdefault(k, v)

injecter_design(st.session_state.palette)

query_params = st.query_params
url_qcm = query_params.get("qcm")
url_session = normaliser_code(query_params.get("session"))

# --- Reordonnancement drag & drop (editeur) ---
if "reorder" in query_params and st.session_state.get("edit_questions"):
    try:
        idx_new = [int(x) for x in query_params["reorder"].split(",")]
        if len(idx_new) == len(st.session_state.edit_questions):
            st.session_state.edit_questions = [st.session_state.edit_questions[i] for i in idx_new]
            for i, q in enumerate(st.session_state.edit_questions):
                q["id"] = i + 1
            enregistrer_qcm_actuel()
            st.query_params.pop("reorder", None)
            st.rerun()
    except Exception as e:
        print(f"[reorder] {e}")

# --- Chargement d'un QCM solo via URL (uniquement si le quiz est publie) ---
if url_qcm and not st.session_state.qcm_selectionne:
    chemin = os.path.join(DOSSIER_QUIZZES, url_qcm)
    if os.path.exists(chemin) and est_publie(url_qcm):
        banque = lire_json(chemin, {})
        st.session_state.banque = banque if isinstance(banque, dict) else {"quiz_info": {}, "questions": banque}
        st.session_state.qcm_selectionne = url_qcm
        st.session_state.current_idx = 0
        st.session_state.score_total = 0
        st.session_state.max_points = 0
        st.session_state.quiz_started = False
        st.session_state.answered = False

if st.session_state.espace is None:
    st.session_state.espace = "session" if url_session else ("solo" if url_qcm else "accueil")

ESPACES = {"accueil": "🏠 Accueil", "session": "🎮 Rejoindre", "solo": "🎧 Solo", "prof": "🛠️ Animateur"}

with st.sidebar:
    st.markdown("### 🚀 Enolou Quiz")
    st.caption("v2.3 — jusqu'à 40 joueurs")
    nouveau = st.radio("Espace", list(ESPACES.values()), index=list(ESPACES).index(st.session_state.espace))
    cle_nouveau = [k for k, v in ESPACES.items() if v == nouveau][0]
    if cle_nouveau != st.session_state.espace:
        st.session_state.espace = cle_nouveau
        st.rerun()
    st.markdown("---")
    pal = st.selectbox("🎨 Thème de couleurs", list(PALETTES), index=list(PALETTES).index(st.session_state.palette))
    if pal != st.session_state.palette:
        st.session_state.palette = pal
        st.rerun()
    if st.session_state.joueur_nom:
        av = st.session_state.avatar_choisi or avatar_de(st.session_state.joueur_nom)
        st.markdown(f"Connecté : **{av} {st.session_state.joueur_nom}**")
        if st.button("Se déconnecter", use_container_width=True):
            st.session_state.joueur_nom = ""
            st.rerun()

espace = st.session_state.espace


# ==========================================================
# 8. ACCUEIL
# ==========================================================
if espace == "accueil":
    hero("Enolou Quiz", "Des quiz vivants, colorés et jouables à 40 — sur mobile comme sur grand écran.",
         ["🎮 Battle temps réel", "📝 Mode examen", "🔢 7 types de questions", "📱 iOS & Android"])

    st.markdown('<div class="eno-card"><h3>🎮 Rejoindre une partie</h3>'
                '<p>Saisissez le code à 6 chiffres affiché par l\'animateur.</p></div>', unsafe_allow_html=True)
    c_code, c_go = st.columns([3, 1])
    with c_code:
        code_rapide = st.text_input("Code à 6 chiffres", max_chars=11, placeholder="• • •   • • •",
                                    label_visibility="collapsed", key="code_accueil")
    with c_go:
        if st.button("Entrer ▶", type="primary", use_container_width=True):
            c = normaliser_code(code_rapide)
            if not c:
                st.warning("Le code doit comporter 6 chiffres.")
            elif not charger_session(c):
                st.error("Aucune partie ne correspond à ce code.")
            else:
                st.query_params["session"] = c
                st.session_state.espace = "session"
                st.rerun()

    nb_publies = len(lister_quiz_publies())
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="eno-card"><h3>🎧 Mode entraînement</h3>'
                    f'<p>Révisez à votre rythme sur les quiz ouverts par votre formateur.</p>'
                    f'<span class="eno-badge">📚 {nb_publies} quiz disponible(s)</span></div>',
                    unsafe_allow_html=True)
        if st.button("S'entraîner", use_container_width=True):
            st.session_state.espace = "solo"
            st.rerun()
    with c2:
        st.markdown('<div class="eno-card"><h3>🛠️ Espace animateur</h3>'
                    '<p>Créez vos quiz, lancez une session, projetez le classement en direct.</p></div>',
                    unsafe_allow_html=True)
        if st.button("Ouvrir l'espace animateur", use_container_width=True):
            st.session_state.espace = "prof"
            st.rerun()

    ouvertes = [(s, charger_session(s)) for s in lister_sessions()[:6]]
    ouvertes = [(s, d) for s, d in ouvertes if d and d.get("status") in ("waiting", "started")]
    if ouvertes:
        st.markdown("#### 🔴 Parties ouvertes")
        for sid, s in ouvertes:
            nb = len(charger_tous_joueurs(sid))
            st.markdown(
                f"""<div class="eno-row"><div class="eno-avatar">{'🟢' if s.get('status')=='waiting' else '🔴'}</div>
                <div class="eno-name">{s.get('quiz_info',{}).get('titre','Quiz')} — code <b>{sid}</b></div>
                <div class="eno-score">{nb}/{MAX_JOUEURS} 👥</div></div>""", unsafe_allow_html=True)


# ==========================================================
# 9. ESPACE JOUEUR — SESSION COLLECTIVE
# ==========================================================
elif espace == "session":
    if not url_session:
        barre_navigation("sess_saisie", reinitialiser_joueur=True)
        hero("🎮 Rejoindre une partie", "Saisissez le code à 6 chiffres affiché par l'animateur, ou scannez son QR code.")
        code = st.text_input("Code de session", max_chars=11, placeholder="• • •   • • •")
        if st.button("Entrer dans le salon", type="primary", use_container_width=True):
            c = normaliser_code(code)
            if not c:
                st.warning("Le code doit comporter 6 chiffres.")
            elif not charger_session(c):
                st.error("Aucune partie ne correspond à ce code. Vérifiez auprès de l'animateur.")
            else:
                st.query_params["session"] = c
                st.rerun()
        st.stop()

    sid = url_session
    sess = charger_session(sid)
    if not sess:
        barre_navigation("sess_introuvable", reinitialiser_joueur=True)
        st.error("❌ Partie introuvable ou terminée.")
        if st.button("Saisir un autre code"):
            st.query_params.clear()
            st.rerun()
        st.stop()

    quiz_info = sess.get("quiz_info", {})
    mode_sess = sess.get("mode", "battle")
    questions = sess.get("questions", [])
    bonus_finale = sess.get("bonus_finale", False)
    vol_mus = quiz_info.get("volume_musique", 0.5)
    vol_sfx = quiz_info.get("volume_sons", 0.8)

    # ---------- Inscription ----------
    if not st.session_state.joueur_nom:
        barre_navigation("sess_inscription", reinitialiser_joueur=True)
        hero(quiz_info.get("titre", "Quiz"), quiz_info.get("description", ""),
             [f"Mode {mode_sess.upper()}", f"{len(questions)} questions", f"Code {sid}"])
        joueurs = charger_tous_joueurs(sid)
        st.markdown(f"**{len(joueurs)}/{MAX_JOUEURS}** joueurs déjà dans le salon.")
        if joueurs:
            st.markdown('<div class="eno-lobby">' + "".join(
                f'<span class="eno-chip">{avatar_joueur(j)} {j["name"]}</span>' for j in joueurs) + "</div>",
                unsafe_allow_html=True)
        st.markdown("### ✍️ Choisissez votre pseudo")
        nom = st.text_input("Pseudo", placeholder="Ex : Yann Q.", label_visibility="collapsed")
        avatar_retenu = selecteur_avatar("insc")
        if st.button("🚀 Entrer dans la partie", type="primary", use_container_width=True):
            nom = nom.strip()
            if not nom:
                st.warning("Merci de saisir un pseudo.")
            elif len(joueurs) >= MAX_JOUEURS and not charger_joueur(sid, nom):
                st.error(f"Salon complet ({MAX_JOUEURS} joueurs).")
            elif charger_joueur(sid, nom):
                existant = charger_joueur(sid, nom)
                existant["avatar"] = avatar_retenu
                sauver_joueur(sid, existant)
                st.session_state.joueur_nom = nom  # reconnexion
                st.rerun()
            else:
                ordre = list(range(len(questions)))
                if mode_sess == "examen" and sess.get("melanger", True):
                    random.Random(nom).shuffle(ordre)
                sauver_joueur(sid, {
                    "name": nom, "avatar": avatar_retenu, "score": 0,
                    "max_points": points_max_session(questions, bonus_finale),
                    "current_idx": 0, "answered": False, "answered_current": False,
                    "last_result": None, "finished": False, "serie": 0, "meilleure_serie": 0,
                    "question_order": ordre, "answers_detail": [], "reaction": {},
                    "joined_at": time.time(),
                })
                st.session_state.joueur_nom = nom
                st.balloons()
                st.rerun()
        st.stop()

    nom_joueur = st.session_state.joueur_nom
    barre_navigation("sess_jeu", reinitialiser_joueur=True)

    son = st.session_state.get("declencher_son")
    son_path = quiz_info.get("son_good") if son == "good" else quiz_info.get("son_bad")
    if sess.get("status") == "started":
        rendre_moteur_audio(quiz_info.get("musique"), vol_mus, son, son_path, vol_sfx)
        st.session_state.declencher_son = None

    @st.fragment(run_every=2)
    def ecran_joueur():
        sess = charger_session(sid)
        if not sess:
            st.error("Partie supprimée par l'animateur.")
            return
        moi = charger_joueur(sid, nom_joueur)
        if not moi:
            st.warning("Votre inscription a été réinitialisée.")
            return
        statut = sess.get("status", "waiting")
        questions = sess.get("questions", [])
        mode_sess = sess.get("mode", "battle")
        bonus_finale = sess.get("bonus_finale", False)

        if statut == "waiting":
            hero("⏳ Salon d'attente", "La partie démarre dès que l'animateur lance le compte à rebours.",
                 [f"{avatar_joueur(moi)} {nom_joueur}", f"Code {sid}"])
            joueurs = charger_tous_joueurs(sid)
            st.markdown(f"#### 👥 {len(joueurs)}/{MAX_JOUEURS} joueurs connectés")
            st.markdown('<div class="eno-lobby">' + "".join(
                f'<span class="eno-chip">{avatar_joueur(j)} {j["name"]}</span>' for j in joueurs) + "</div>",
                unsafe_allow_html=True)
            barre_reactions(sid, moi, "lobby")
            afficher_reactions(joueurs)
            return

        if statut == "ended":
            joueurs = charger_tous_joueurs(sid)
            rang = next((i + 1 for i, j in enumerate(joueurs) if j["name"] == nom_joueur), "-")
            hero("🏁 Partie terminée !", f"Vous finissez **{rang}e** sur {len(joueurs)} joueurs.",
                 [f"Score : {moi.get('score',0)}/{moi.get('max_points',0)} pts",
                  f"Meilleure série : {moi.get('meilleure_serie',0)} 🔥"])
            podium_anime(joueurs)
            leaderboard(joueurs, 10, "🏆 Classement final")
            return

        # =========== MODE BATTLE ===========
        if mode_sess == "battle":
            idx = sess.get("current_global_idx", 0)
            joueurs = charger_tous_joueurs(sid)

            if sess.get("in_transition"):
                reste = max(0, 6 - int(time.time() - sess.get("transition_start_time", time.time())))
                st.markdown(f"### ⏸️ Manche terminée — suite dans {reste}s")
                podium_anime(joueurs, "🏆 Podium provisoire")
                leaderboard(joueurs, 8, "Classement en direct", st.session_state.get("rangs_precedents"))
                q_prec = questions[idx] if idx < len(questions) else None
                if q_prec and q_prec.get("type") in ("sondage", "texte"):
                    nuage_de_mots(collecter_reponses(joueurs, idx + 1),
                                  "☁️ Ce que le groupe a répondu")
                barre_reactions(sid, moi, f"trans{idx}")
                afficher_reactions(joueurs)
                if reste == 0 and prendre_verrou(sid, f"adv_{idx}"):
                    st.session_state.rangs_precedents = {j["name"]: i + 1 for i, j in enumerate(joueurs)}
                    s = charger_session(sid)
                    s["current_global_idx"] = idx + 1
                    s["in_transition"] = False
                    if s["current_global_idx"] >= len(questions):
                        s["status"] = "ended"
                    else:
                        s["question_start_time"] = time.time()
                    sauver_session(sid, s)
                    for j in charger_tous_joueurs(sid):
                        j["answered_current"] = False
                        j["last_result"] = None
                        sauver_joueur(sid, j)
                    st.rerun()
                return

            if idx >= len(questions):
                if prendre_verrou(sid, "fin"):
                    s = charger_session(sid)
                    s["status"] = "ended"
                    sauver_session(sid, s)
                st.rerun()
                return

            q = questions[idx]
            mult = multiplicateur_question(q, idx, len(questions), bonus_finale)
            timer_sec = int(q.get("timer_secondes", 30))
            debut = sess.get("question_start_time", time.time())
            elapsed = int(time.time() - debut)
            restant = max(0, timer_sec - elapsed)
            deja = moi.get("answered_current", False)
            tous_repondu = bool(joueurs) and all(j.get("answered_current") for j in joueurs)

            if (restant == 0 or tous_repondu) and prendre_verrou(sid, f"trans_{idx}"):
                s = charger_session(sid)
                s["in_transition"] = True
                s["transition_start_time"] = time.time()
                sauver_session(sid, s)
                st.rerun()
                return

            if mult > 1:
                st.markdown(
                    '<div class="eno-ok" style="background:linear-gradient(120deg,#f59e0b,#f97316);padding:12px">'
                    '⭐ Question bonus — points doublés !</div>', unsafe_allow_html=True)
            chrono_synchro(debut + timer_sec, timer_sec, sonore=not deja)
            entete_question(q, idx + 1, len(questions), multiplicateur=mult)
            afficher_medias(q, quiz_info)
            cle = f"b{idx}"

            if not deja:
                rep = widget_reponse(q, cle)
                if st.button("✅ Valider ma réponse", type="primary", use_container_width=True,
                             disabled=rep is None or (isinstance(rep, (list, dict)) and len(rep) == 0)):
                    correct, ratio = evaluer_reponse(q, rep)
                    pts = calculer_points(q, ratio, elapsed, timer_sec, bonus_rapidite=True, multiplicateur=mult)
                    # Un sondage ne fait ni gagner ni perdre la série en cours.
                    if q.get("type") == "sondage":
                        serie = moi.get("serie", 0)
                    else:
                        serie = moi.get("serie", 0) + 1 if correct else 0
                    if correct and q.get("type") != "sondage" and serie >= 3:
                        pts = int(pts * 1.2)
                    moi["score"] += pts
                    moi["serie"] = serie
                    moi["meilleure_serie"] = max(moi.get("meilleure_serie", 0), serie)
                    moi["answered_current"] = True
                    moi["last_result"] = {"correct": correct, "ratio": ratio, "points": pts, "mult": mult}
                    moi["answers_detail"].append({"q_num": idx + 1, "consigne": q.get("consigne", ""),
                                                  "type": q.get("type", "qcm"), "reponse": rep,
                                                  "correct": correct, "points": pts})
                    sauver_joueur(sid, moi)
                    st.session_state.declencher_son = "good" if correct else "bad"
                    nettoyer_widgets(cle)
                    st.rerun()
            else:
                r = moi.get("last_result") or {}
                afficher_feedback(q, r.get("correct"), r.get("ratio", 0), r.get("points", 0), r.get("mult", 1))
                st.info(f"⏳ {sum(1 for j in joueurs if j.get('answered_current'))}/{len(joueurs)} joueurs ont répondu…")
                barre_reactions(sid, moi, f"q{idx}")
                afficher_reactions(joueurs)
                leaderboard(joueurs, 5, "🏆 Classement en direct", st.session_state.get("rangs_precedents"))
            return

        # =========== MODE EXAMEN ===========
        ordre = moi.get("question_order", list(range(len(questions))))
        i_etu = moi.get("current_idx", 0)
        if i_etu >= len(ordre):
            moi["finished"] = True
            sauver_joueur(sid, moi)
            st.balloons()
            hero("✅ Évaluation terminée", "Vos réponses ont été transmises à l'animateur.",
                 [f"Score : {moi['score']}/{moi['max_points']} pts"])
            return

        reel = ordre[i_etu]
        q = questions[reel]
        mult = multiplicateur_question(q, reel, len(questions), bonus_finale)
        if mult > 1:
            st.markdown('<div class="eno-ok" style="background:linear-gradient(120deg,#f59e0b,#f97316);padding:12px">'
                        '⭐ Question bonus — points doublés !</div>', unsafe_allow_html=True)
        entete_question(q, i_etu + 1, len(ordre), multiplicateur=mult)
        afficher_medias(q, quiz_info)
        cle = f"e{i_etu}"
        if not moi.get("answered"):
            rep = widget_reponse(q, cle)
            if st.button("✅ Valider ma réponse", type="primary", use_container_width=True,
                         disabled=rep is None or (isinstance(rep, (list, dict)) and len(rep) == 0)):
                correct, ratio = evaluer_reponse(q, rep)
                pts = calculer_points(q, ratio, multiplicateur=mult)
                moi["score"] += pts
                moi["answered"] = True
                moi["last_result"] = {"correct": correct, "ratio": ratio, "points": pts, "mult": mult}
                moi["answers_detail"].append({"q_num": reel + 1, "consigne": q.get("consigne", ""),
                                              "type": q.get("type", "qcm"), "reponse": rep,
                                              "correct": correct, "points": pts})
                sauver_joueur(sid, moi)
                st.session_state.declencher_son = "good" if correct else "bad"
                nettoyer_widgets(cle)
                st.rerun()
        else:
            r = moi.get("last_result") or {}
            if sess.get("feedback_immediat", True):
                afficher_feedback(q, r.get("correct"), r.get("ratio", 0), r.get("points", 0), r.get("mult", 1))
            else:
                st.success("Réponse enregistrée ✅")
            if st.button("Question suivante ➡️", type="primary", use_container_width=True):
                moi["current_idx"] += 1
                moi["answered"] = False
                moi["last_result"] = None
                sauver_joueur(sid, moi)
                st.rerun()

    ecran_joueur()


# ==========================================================
# 10. ESPACE SOLO / MODE ENTRAINEMENT
#     Seuls les quiz explicitement publies par l'animateur sont accessibles.
# ==========================================================
elif espace == "solo":
    if not st.session_state.qcm_selectionne:
        barre_navigation("solo_galerie")
        publies = lister_quiz_publies()
        hero("🎧 Mode entraînement", "Révisez à votre rythme sur les quiz ouverts par votre formateur.",
             [f"📚 {len(publies)} quiz disponible(s)"])
        if url_qcm and url_qcm not in publies:
            st.warning("🔒 Ce quiz n'est pas ouvert à l'entraînement. Demandez à votre formateur de le publier.")
        if not publies:
            st.info("Aucun quiz n'est ouvert à l'entraînement pour le moment.")
        cols = st.columns(3)
        for i, f in enumerate(publies):
            data = lire_json(os.path.join(DOSSIER_QUIZZES, f), {}) or {}
            info = data.get("quiz_info", {})
            with cols[i % 3]:
                st.markdown(
                    f"""<div class="eno-card"><div style="font-size:1.05rem;font-weight:800">🎓 {info.get('titre', f)}</div>
                    <div style="color:#64748b;font-size:.85rem;margin:6px 0">{info.get('description','Quiz interactif')}</div>
                    <span class="eno-badge">⚡ {len(data.get('questions',[]))} questions</span></div>""",
                    unsafe_allow_html=True)
                if st.button("Jouer", key=f"play_{i}", type="primary", use_container_width=True):
                    st.session_state.banque = data
                    st.session_state.qcm_selectionne = f
                    st.session_state.current_idx = 0
                    st.session_state.score_total = 0
                    st.session_state.max_points = 0
                    st.session_state.quiz_started = False
                    st.session_state.answered = False
                    st.rerun()
        st.stop()

    quiz_info = st.session_state.banque.get("quiz_info", {})
    questions = st.session_state.banque.get("questions", [])
    son = st.session_state.get("declencher_son")
    son_path = quiz_info.get("son_good") if son == "good" else quiz_info.get("son_bad")
    if st.session_state.quiz_started:
        rendre_moteur_audio(quiz_info.get("musique"), quiz_info.get("volume_musique", 0.5),
                            son, son_path, quiz_info.get("volume_sons", 0.8))
        st.session_state.declencher_son = None

    if not st.session_state.quiz_started:
        retour_galerie = barre_navigation("solo_intro", extra_label="← Autres quiz", extra_cle="solo_intro")
        if retour_galerie:
            st.session_state.qcm_selectionne = None
            st.query_params.pop("qcm", None)
            st.rerun()
        hero(quiz_info.get("titre", "Quiz"), quiz_info.get("description", ""),
             [f"{len(questions)} questions", f"{points_max_session(questions)} points en jeu"])
        img = quiz_info.get("image")
        if img and os.path.exists(img):
            st.image(img, use_container_width=True)
        vid = quiz_info.get("video")
        if vid and os.path.exists(vid):
            st.video(vid)
        if st.button("🎵 Commencer", type="primary", use_container_width=True):
            st.session_state.quiz_started = True
            st.session_state.question_start_time = time.time()
            st.rerun()
        st.stop()

    idx = st.session_state.current_idx
    if idx >= len(questions):
        barre_navigation("solo_fin")
        pct = round(100 * st.session_state.score_total / max(1, st.session_state.max_points))
        st.balloons()
        hero("🎉 Évaluation terminée !",
             f"Score final : **{st.session_state.score_total} / {st.session_state.max_points}** ({pct}%)",
             ["🏆 Bravo !" if pct >= 70 else "💪 Encore un effort !"])
        st.progress(pct / 100)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔁 Rejouer", type="primary", use_container_width=True):
                for k in ("current_idx", "score_total", "max_points"):
                    st.session_state[k] = 0
                st.session_state.quiz_started = False
                st.session_state.answered = False
                st.rerun()
        with c2:
            if st.button("📚 Autres quiz", use_container_width=True):
                st.session_state.qcm_selectionne = None
                st.session_state.quiz_started = False
                st.query_params.pop("qcm", None)
                st.rerun()
        st.stop()

    barre_navigation("solo_jeu")
    q = questions[idx]
    mult = multiplicateur_question(q)
    timer_sec = int(q.get("timer_secondes", 30))
    debut = st.session_state.question_start_time
    elapsed = int(time.time() - debut)
    st.progress(idx / len(questions), text=f"Progression {idx}/{len(questions)} — {st.session_state.score_total} pts")

    a_support = bool(q.get("document_texte") or (q.get("media", {}) or {}).get("image"))
    col_doc, col_q = st.columns([2, 3], gap="large") if a_support else (None, st.container())
    if col_doc is not None:
        with col_doc:
            st.markdown("#### 📄 Support")
            afficher_medias(q, quiz_info)
    with col_q:
        if not st.session_state.answered:
            chrono_synchro(debut + timer_sec, timer_sec, sonore=True)
        if mult > 1:
            st.markdown('<div class="eno-ok" style="background:linear-gradient(120deg,#f59e0b,#f97316);padding:12px">'
                        '⭐ Question bonus — points doublés !</div>', unsafe_allow_html=True)
        entete_question(q, idx + 1, len(questions), multiplicateur=mult)
        cle = f"s{idx}"
        if not st.session_state.answered:
            rep = widget_reponse(q, cle)
            if st.button("✅ Valider ma réponse", type="primary", use_container_width=True,
                         disabled=rep is None or (isinstance(rep, (list, dict)) and len(rep) == 0)):
                correct, ratio = evaluer_reponse(q, rep)
                pts = calculer_points(q, ratio, multiplicateur=mult)
                if elapsed > timer_sec:
                    pts = pts // 2
                st.session_state.score_total += pts
                if q.get("type") != "sondage":
                    st.session_state.max_points += int(q.get("points", 10)) * mult
                st.session_state.answered = True
                st.session_state.last_result = (correct, ratio, pts, mult)
                st.session_state.declencher_son = "good" if correct else "bad"
                nettoyer_widgets(cle)
                st.rerun()
        else:
            correct, ratio, pts, mult_prec = st.session_state.last_result
            afficher_feedback(q, correct, ratio, pts, mult_prec)
            if st.button("Question suivante ➡️", type="primary", use_container_width=True):
                st.session_state.current_idx += 1
                st.session_state.answered = False
                st.session_state.last_result = None
                st.session_state.question_start_time = time.time()
                st.rerun()


# ==========================================================
# 11. ESPACE ANIMATEUR
# ==========================================================
elif espace == "prof":
    barre_navigation("prof")
    hero("🛠️ Espace animateur", "Créez, lancez, pilotez et analysez vos quiz.",
         ["Codes à 6 chiffres", f"Jusqu'à {MAX_JOUEURS} joueurs", "Publication entraînement", "Export Excel"])
    fichiers_existants = lister_fichiers_quiz()
    tab_sess, tab_edit, tab_excel, tab_pub, tab_ecran = st.tabs(
        ["🎮 Sessions en direct", "📝 Éditeur de quiz", "📊 Import / Export Excel",
         "📚 Mode entraînement", "📺 Écran de projection"])

    def galerie(fichiers, prefixe, cle_etat):
        if not fichiers:
            st.info("Aucun quiz disponible.")
            return
        mapping = charger_publication()
        cols = st.columns(3)
        for i, f in enumerate(fichiers):
            data = lire_json(os.path.join(DOSSIER_QUIZZES, f), {}) or {}
            info = data.get("quiz_info", {})
            actif = st.session_state.get(cle_etat) == f
            pub = mapping.get(f, False)
            with cols[i % 3]:
                bord = "2px solid var(--c1)" if actif else "1px solid rgba(15,23,42,.06)"
                badge_pub = ('<span class="eno-badge">🌐 Entraînement</span>' if pub
                             else '<span class="eno-badge">🔒 Privé</span>')
                st.markdown(
                    f"""<div class="eno-card" style="border:{bord}">
                    <div style="font-weight:800">{'✨ ' if actif else ''}{info.get('titre', f)}</div>
                    <div style="color:#64748b;font-size:.8rem;margin:6px 0;height:32px;overflow:hidden">{info.get('description','—')}</div>
                    <span class="eno-badge">⚡ {len(data.get('questions',[]))} Q</span>
                    {badge_pub}
                    <span class="eno-badge">📄 {f}</span></div>""", unsafe_allow_html=True)
                if st.button("Sélectionné ✓" if actif else "Sélectionner", key=f"{prefixe}_{i}",
                             disabled=actif, use_container_width=True):
                    st.session_state[cle_etat] = f
                    st.rerun()

    # ================= ONGLET MODE ENTRAINEMENT (PUBLICATION) =================
    with tab_pub:
        st.subheader("📚 Quiz ouverts au mode entraînement")
        st.caption("Cochez les quiz que les étudiants peuvent réviser en autonomie. "
                   "Un quiz non coché reste strictement réservé aux sessions que vous pilotez.")
        if not fichiers_existants:
            st.info("Aucun quiz dans la bibliothèque.")
        else:
            mapping = charger_publication()
            with st.form("form_publication"):
                etats = {}
                for i, f in enumerate(fichiers_existants):
                    data = lire_json(os.path.join(DOSSIER_QUIZZES, f), {}) or {}
                    info = data.get("quiz_info", {})
                    nb_q = len(data.get("questions", []))
                    etats[f] = st.checkbox(
                        f"**{info.get('titre', f)}** — {nb_q} question(s) · `{f}`",
                        value=bool(mapping.get(f, False)), key=f"pub_{i}")
                c1, c2, c3 = st.columns(3)
                with c1:
                    valider = st.form_submit_button("💾 Enregistrer", type="primary", use_container_width=True)
                with c2:
                    tout = st.form_submit_button("✅ Tout ouvrir", use_container_width=True)
                with c3:
                    rien = st.form_submit_button("🔒 Tout fermer", use_container_width=True)
                if valider or tout or rien:
                    if tout:
                        etats = {f: True for f in fichiers_existants}
                    elif rien:
                        etats = {f: False for f in fichiers_existants}
                    sauver_publication(etats)
                    st.success("Publication mise à jour.")
                    st.rerun()

            publies = lister_quiz_publies()
            st.markdown(f"**{len(publies)}/{len(fichiers_existants)}** quiz ouverts à l'entraînement.")
            if publies:
                st.markdown('<div class="eno-lobby">' + "".join(
                    f'<span class="eno-chip">🌐 {f}</span>' for f in publies) + "</div>", unsafe_allow_html=True)

    # ================= ONGLET SESSIONS =================
    with tab_sess:
        st.subheader("🚀 Lancer une session")
        if fichiers_existants:
            if st.session_state.selected_collec_qcm not in fichiers_existants:
                st.session_state.selected_collec_qcm = fichiers_existants[0]
            galerie(fichiers_existants, "sess_mini", "selected_collec_qcm")
            qcm_collectif = st.session_state.selected_collec_qcm

            c1, c2 = st.columns(2)
            with c1:
                mode_label = st.radio("Mode de jeu", [
                    "🎮 Battle — synchronisé, rapidité, podium",
                    "📝 Examen — autonome, export tableur"], key="mode_collec")
                bonus_finale = st.toggle("⭐ Question bonus finale (points doublés)", value=True)
            with c2:
                domaine_app = st.text_input("URL de l'application déployée", value=URL_APP_DEFAUT, key="dom_collec")
                feedback_imm = st.toggle("Feedback immédiat (mode examen)", value=True)
                melanger = st.toggle("Mélanger les questions par joueur (examen)", value=True)

            if st.button("🚀 Créer la session", type="primary", use_container_width=True):
                data = lire_json(os.path.join(DOSSIER_QUIZZES, qcm_collectif), {}) or {}
                sid = generer_code_session()
                os.makedirs(dossier_joueurs(sid), exist_ok=True)
                sauver_session(sid, {
                    "session_id": sid, "code": sid, "qcm_filename": qcm_collectif,
                    "mode": "battle" if "Battle" in mode_label else "examen",
                    "status": "waiting", "current_global_idx": 0, "question_start_time": 0,
                    "in_transition": False, "transition_start_time": 0,
                    "feedback_immediat": feedback_imm, "melanger": melanger,
                    "bonus_finale": bonus_finale,
                    "max_joueurs": MAX_JOUEURS, "cree_le": time.time(),
                    "quiz_info": data.get("quiz_info", {}), "questions": data.get("questions", []),
                })
                st.session_state["sel_session"] = sid
                st.success("Session créée !")
                st.rerun()

        st.markdown("---")
        sessions = lister_sessions()
        if sessions:
            st.subheader("📊 Pilotage")

            def libelle_session(s):
                d = charger_session(s) or {}
                return f"{s} — {d.get('quiz_info',{}).get('titre','Quiz')} ({d.get('status','?')})"

            sid = st.selectbox("Session", sessions, key="sel_session", format_func=libelle_session)
            sess = charger_session(sid)
            if sess:
                url_complete = f"{st.session_state.get('dom_collec', URL_APP_DEFAUT).strip('/')}/?session={sid}"
                cA, cB = st.columns([1, 2])
                with cA:
                    buf = BytesIO()
                    qrcode.make(url_complete).save(buf, format="PNG")
                    st.image(buf.getvalue(), caption="Scannez pour rejoindre", width=190)
                with cB:
                    afficher_code(sid, "Code à communiquer")
                    st.caption("Les joueurs peuvent aussi saisir ce code depuis la page d'accueil.")
                    st.markdown(f"**Lien direct :** [{url_complete}]({url_complete})")
                    st.markdown(f"**Mode :** `{sess['mode'].upper()}` — **Statut :** `{sess['status'].upper()}`"
                                + (" — ⭐ bonus finale actif" if sess.get("bonus_finale") else ""))

                @st.fragment(run_every=3)
                def pilotage():
                    s = charger_session(sid)
                    if not s:
                        st.warning("Session supprimée.")
                        return
                    joueurs = charger_tous_joueurs(sid)
                    qs = s.get("questions", [])
                    idx = s.get("current_global_idx", 0)
                    m1, m2, m3 = st.columns(3)
                    m1.metric("👥 Joueurs", f"{len(joueurs)}/{MAX_JOUEURS}")
                    m2.metric("❓ Question", f"{min(idx+1, len(qs))}/{len(qs)}")
                    m3.metric("✅ Ont répondu", sum(1 for j in joueurs if j.get("answered_current") or j.get("answered")))
                    if joueurs:
                        st.markdown('<div class="eno-lobby">' + "".join(
                            f'<span class="eno-chip">{avatar_joueur(j)} {j["name"]} · {j.get("score",0)}</span>'
                            for j in joueurs) + "</div>", unsafe_allow_html=True)
                        afficher_reactions(joueurs)
                    else:
                        st.info("En attente des joueurs…")
                    b1, b2, b3 = st.columns(3)
                    with b1:
                        if s["status"] == "waiting" and st.button("▶️ Démarrer", type="primary", use_container_width=True):
                            s["status"] = "started"
                            s["current_global_idx"] = 0
                            s["question_start_time"] = time.time()
                            s["in_transition"] = False
                            sauver_session(sid, s)
                            st.rerun()
                    with b2:
                        if s["status"] == "started" and s["mode"] == "battle" and st.button("⏭️ Question suivante", use_container_width=True):
                            s["in_transition"] = True
                            s["transition_start_time"] = time.time() - 6
                            sauver_session(sid, s)
                            st.rerun()
                    with b3:
                        if s["status"] != "ended" and st.button("⏹️ Clôturer", use_container_width=True):
                            s["status"] = "ended"
                            sauver_session(sid, s)
                            st.rerun()
                    if joueurs:
                        if s["status"] == "ended":
                            podium_anime(joueurs)
                        leaderboard(joueurs, 10)
                    # Nuage de mots : sondages et reponses libres
                    q_nuage = [i for i, q in enumerate(qs) if q.get("type") in ("sondage", "texte")]
                    if q_nuage and joueurs:
                        st.markdown("---")
                        choix_n = st.selectbox(
                            "☁️ Nuage de mots — question", q_nuage,
                            format_func=lambda i: f"Q{i+1} — {qs[i].get('consigne','')[:50]}",
                            key=f"nuage_{sid}")
                        nuage_de_mots(collecter_reponses(joueurs, choix_n + 1))
                pilotage()

                st.download_button("📥 Export des résultats (.csv Excel)", data=generer_csv_session(sid),
                                   file_name=f"resultats_{sid}.csv", mime="text/csv", use_container_width=True)
                d1, d2 = st.columns(2)
                with d1:
                    if st.button("🗑️ Supprimer cette session", use_container_width=True):
                        supprimer_session(sid)
                        st.rerun()
                with d2:
                    if st.button("🔥 Purger toutes les sessions", use_container_width=True):
                        for s_ in lister_sessions():
                            supprimer_session(s_)
                        st.rerun()

    # ================= ONGLET ECRAN DE PROJECTION =================
    with tab_ecran:
        st.subheader("📺 Mode vidéoprojecteur")
        sessions = lister_sessions()
        if not sessions:
            st.info("Créez d'abord une session.")
        else:
            sid_p = st.selectbox("Session à projeter", sessions, key="sel_proj")

            @st.fragment(run_every=2)
            def projection():
                s = charger_session(sid_p)
                if not s:
                    return
                joueurs = charger_tous_joueurs(sid_p)
                qs = s.get("questions", [])
                idx = s.get("current_global_idx", 0)
                bonus_finale = s.get("bonus_finale", False)
                if s["status"] == "waiting":
                    hero("Rejoignez la partie !", "Rendez-vous sur l'application et saisissez le code ci-dessous.",
                         [f"{len(joueurs)}/{MAX_JOUEURS} joueurs"])
                    afficher_code(sid_p, "Code de la partie", xl=True)
                    st.markdown('<div class="eno-lobby">' + "".join(
                        f'<span class="eno-chip" style="font-size:1.1rem">{avatar_joueur(j)} {j["name"]}</span>'
                        for j in joueurs) + "</div>", unsafe_allow_html=True)
                    afficher_reactions(joueurs)
                elif s["status"] == "ended":
                    hero("🏁 Résultats finaux", "Merci à tous les participants !")
                    podium_anime(joueurs)
                    leaderboard(joueurs, 10, "🏆 Classement final")
                elif s.get("in_transition"):
                    reste = max(0, 6 - int(time.time() - s.get("transition_start_time", time.time())))
                    hero("⏸️ Fin de la manche", f"Question suivante dans {reste} secondes.")
                    podium_anime(joueurs, "🏆 Podium provisoire")
                    leaderboard(joueurs, 8, "Classement en direct")
                    if idx < len(qs) and qs[idx].get("type") in ("sondage", "texte"):
                        nuage_de_mots(collecter_reponses(joueurs, idx + 1), "☁️ Réponses du groupe")
                    afficher_reactions(joueurs)
                elif idx < len(qs):
                    q = qs[idx]
                    mult = multiplicateur_question(q, idx, len(qs), bonus_finale)
                    total = int(q.get("timer_secondes", 30))
                    debut = s.get("question_start_time", time.time())
                    if mult > 1:
                        st.markdown('<div class="eno-ok" style="background:linear-gradient(120deg,#f59e0b,#f97316)">'
                                    '⭐ QUESTION BONUS — POINTS DOUBLÉS</div>', unsafe_allow_html=True)
                    chrono_synchro(debut + total, total, sonore=True, hauteur=80)
                    entete_question(q, idx + 1, len(qs), multiplicateur=mult)
                    if q.get("type") in ("qcm", "sondage"):
                        opts = q.get("donnees", {}).get("options", [])
                        cols = st.columns(2)
                        for i, o in enumerate(opts):
                            with cols[i % 2]:
                                st.markdown(
                                    f"""<div style="background:{TILE_COLORS[i%len(TILE_COLORS)]};color:#fff;padding:22px;
                                    border-radius:18px;font-weight:800;font-size:1.2rem;margin-bottom:10px">
                                    {TILE_SHAPES[i%len(TILE_SHAPES)]} {o}</div>""", unsafe_allow_html=True)
                    st.metric("Réponses reçues", f"{sum(1 for j in joueurs if j.get('answered_current'))}/{len(joueurs)}")
                    afficher_reactions(joueurs)
                    leaderboard(joueurs, 5, "🏆 Top 5")
            projection()

    # ================= ONGLET IMPORT / EXPORT EXCEL =================
    with tab_excel:
        st.subheader("📊 Créer et modifier vos questions dans Excel")
        st.caption("Exportez un quiz, travaillez confortablement dans le tableur, puis réimportez. "
                   "Idéal pour saisir ou réviser des dizaines de questions d'un coup.")

        st.markdown("##### 1️⃣ Partir d'un modèle")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "📥 Modèle commenté (8 exemples, 7 types)",
                data=modele_excel_vierge(),
                file_name="modele_enolou_quiz.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
        with c2:
            if fichiers_existants:
                quiz_exp = st.selectbox("Exporter un quiz existant", fichiers_existants,
                                        format_func=lambda f: (lire_json(os.path.join(DOSSIER_QUIZZES, f), {}) or {})
                                        .get("quiz_info", {}).get("titre", f),
                                        key="excel_export_src")
                data_exp = lire_json(os.path.join(DOSSIER_QUIZZES, quiz_exp), {}) or {}
                st.download_button(
                    f"📤 Exporter « {quiz_exp} »",
                    data=exporter_quiz_excel(data_exp.get("quiz_info", {}),
                                             data_exp.get("questions", []), quiz_exp),
                    file_name=quiz_exp.replace(".json", "") + ".xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)
            else:
                st.info("Aucun quiz à exporter pour l'instant.")

        with st.expander("📖 Syntaxe de la colonne « Donnees »"):
            st.markdown(
                "| Type | Syntaxe | Exemple |\n|---|---|---|\n"
                "| `qcm` | options séparées par `\\|`, bonne réponse préfixée par `*` | `*Paris \\| Lyon \\| Nice` |\n"
                "| `vrai_faux` | `VRAI` ou `FAUX` | `FAUX` |\n"
                "| `classement` | éléments dans le bon ordre, séparés par `>` | `1900 > 1950 > 2000` |\n"
                "| `association` | paires `gauche = droite` séparées par `\\|` | `ACPR = Superviseur \\| EBA = Europe` |\n"
                "| `texte` | réponses acceptées séparées par `\\|` | `Crédit-bail \\| Leasing \\| LOA` |\n"
                "| `curseur` | `min ; max ; valeur ; tolérance ; pas ; libellé` | `0 ; 200 ; 100 ; 20 ; 1 ; Véhicules` |\n"
                "| `sondage` | options séparées par `\\|`, sans `*` | `Dynamique \\| Technique \\| Clair` |\n")
            st.caption("Colonne « Double points » : écrivez OUI pour une question bonus. "
                       "La feuille « Aide » du classeur reprend ces règles.")

        st.markdown("---")
        st.markdown("##### 2️⃣ Réimporter le classeur")
        fichier_xl = st.file_uploader("Classeur Excel (.xlsx)", type=["xlsx", "xlsm"], key="excel_upload")

        if fichier_xl is not None:
            questions_imp, info_imp, rapport = importer_quiz_excel(fichier_xl)

            m1, m2, m3 = st.columns(3)
            m1.metric("Lignes lues", rapport["lues"])
            m2.metric("Questions valides", rapport["retenues"])
            m3.metric("Erreurs", len(rapport["erreurs"]))

            if rapport["erreurs"]:
                st.error(f"❌ {len(rapport['erreurs'])} erreur(s) — corrigez le classeur puis réimportez. "
                         "Aucune modification n'a été appliquée.")
                with st.expander("Détail des erreurs", expanded=True):
                    for e in rapport["erreurs"][:60]:
                        st.markdown(f"- {e}")
                    if len(rapport["erreurs"]) > 60:
                        st.caption(f"… et {len(rapport['erreurs']) - 60} autre(s).")
            if rapport["avertissements"]:
                with st.expander(f"⚠️ {len(rapport['avertissements'])} avertissement(s)"):
                    for a in rapport["avertissements"]:
                        st.markdown(f"- {a}")

            if questions_imp and not rapport["erreurs"]:
                st.success(f"✅ {len(questions_imp)} question(s) prête(s) à être importée(s).")
                apercu = pd.DataFrame([{
                    "N°": i + 1,
                    "Type": TYPES_QUESTION[q["type"]]["icone"] + " " + q["type"],
                    "Consigne": q["consigne"][:70],
                    "Points": q["points"] * (2 if q.get("double_points") else 1),
                    "Chrono": f"{q['timer_secondes']}s",
                } for i, q in enumerate(questions_imp)])
                st.dataframe(apercu, use_container_width=True, hide_index=True)
                repartition = Counter(q["type"] for q in questions_imp)
                st.caption("Répartition : " + " · ".join(
                    f"{TYPES_QUESTION[t]['icone']} {t} ({n})" for t, n in repartition.most_common())
                    + f" — {points_max_session(questions_imp)} points en jeu.")

                st.markdown("###### 3️⃣ Destination")
                nom_suggere = _texte(info_imp.get("_nom_fichier")) or (
                    re.sub(r"\W+", "_", os.path.splitext(fichier_xl.name)[0]).strip("_").lower() + ".json")
                dest = st.radio("Importer vers",
                                ["✨ Nouveau quiz", "♻️ Remplacer un quiz existant"],
                                horizontal=True, key="excel_dest")
                if dest.startswith("✨"):
                    cible = st.text_input("Nom du fichier JSON", value=nom_suggere, key="excel_nom_cible")
                    if cible and not cible.endswith(".json"):
                        cible += ".json"
                    if cible in fichiers_existants:
                        st.warning(f"⚠️ « {cible} » existe déjà et sera écrasé.")
                else:
                    cible = st.selectbox("Quiz à remplacer", fichiers_existants,
                                         key="excel_cible") if fichiers_existants else None
                    if cible:
                        actuel = lire_json(os.path.join(DOSSIER_QUIZZES, cible), {}) or {}
                        st.warning(f"⚠️ Les {len(actuel.get('questions', []))} question(s) actuelles de "
                                   f"« {cible} » seront intégralement remplacées.")

                titre_defaut = _texte(info_imp.get("titre")) or os.path.splitext(str(cible or "Quiz"))[0]
                confirme = st.checkbox("Je confirme l'import", key="excel_confirme")
                if st.button("💾 Importer dans la bibliothèque", type="primary",
                             use_container_width=True, disabled=not (cible and confirme)):
                    existant = lire_json(os.path.join(DOSSIER_QUIZZES, cible), {}) or {}
                    info_finale = dict(existant.get("quiz_info", {}))
                    for k, v in info_imp.items():
                        if k.startswith("_"):
                            continue
                        if v not in ("", None):
                            info_finale[k] = v
                    info_finale.setdefault("titre", titre_defaut)
                    info_finale.setdefault("description", "")
                    info_finale.setdefault("volume_musique", 0.5)
                    info_finale.setdefault("volume_sons", 0.8)

                    contenu = json.dumps({"quiz_info": info_finale, "questions": questions_imp},
                                         ensure_ascii=False, indent=2)
                    with open(os.path.join(DOSSIER_QUIZZES, cible), "w", encoding="utf-8") as f:
                        f.write(contenu)
                    sauvegarder_fichier_github(f"QCM/{cible}", contenu)
                    st.session_state.selected_edit_qcm = cible
                    st.session_state.dernier_choix_edition = None  # force le rechargement de l'éditeur
                    st.success(f"✅ {len(questions_imp)} question(s) importée(s) dans « {cible} ». "
                               "Le quiz reste privé tant que vous ne l'ouvrez pas au mode entraînement.")
                    st.balloons()
                    st.rerun()

    # ================= ONGLET EDITEUR =================
    with tab_edit:
        st.subheader("📝 Bibliothèque & éditeur")
        options_edition = ["✨ Nouveau quiz"] + fichiers_existants
        if st.session_state.selected_edit_qcm not in options_edition:
            st.session_state.selected_edit_qcm = options_edition[0]
        if st.button("✨ Créer un nouveau quiz", use_container_width=True,
                     type="primary" if st.session_state.selected_edit_qcm == "✨ Nouveau quiz" else "secondary"):
            st.session_state.selected_edit_qcm = "✨ Nouveau quiz"
            st.rerun()
        if fichiers_existants:
            galerie(fichiers_existants, "edit_mini", "selected_edit_qcm")
        choix_edition = st.session_state.selected_edit_qcm

        if choix_edition != st.session_state.dernier_choix_edition:
            st.session_state.dernier_choix_edition = choix_edition
            if choix_edition == "✨ Nouveau quiz":
                st.session_state.update({
                    "edit_nom_fichier": "nouveau_quiz.json", "edit_titre": "Mon nouveau quiz",
                    "edit_desc": "", "edit_quiz_image": "", "edit_document_appui": "", "edit_quiz_video": "",
                    "edit_musique": "", "edit_son_good": "", "edit_son_bad": "",
                    "edit_vol_musique": 0.5, "edit_vol_sons": 0.8, "edit_questions": [],
                })
            else:
                data = lire_json(os.path.join(DOSSIER_QUIZZES, choix_edition), {}) or {}
                info = data.get("quiz_info", {})
                st.session_state.update({
                    "edit_nom_fichier": choix_edition,
                    "edit_titre": info.get("titre", ""), "edit_desc": info.get("description", ""),
                    "edit_quiz_image": info.get("image", ""), "edit_document_appui": info.get("document_appui", ""),
                    "edit_quiz_video": info.get("video", ""), "edit_musique": info.get("musique", ""),
                    "edit_son_good": info.get("son_good", ""), "edit_son_bad": info.get("son_bad", ""),
                    "edit_vol_musique": info.get("volume_musique", 0.5), "edit_vol_sons": info.get("volume_sons", 0.8),
                    "edit_questions": data.get("questions", []),
                })

        suffix = re.sub(r"\W+", "_", choix_edition)

        # --- Publication rapide du quiz en cours d'edition ---
        if choix_edition != "✨ Nouveau quiz":
            pub_actuel = est_publie(choix_edition)
            nouveau_pub = st.checkbox(
                "📚 Ouvrir ce quiz au mode entraînement (accessible aux étudiants en autonomie)",
                value=pub_actuel, key=f"pub_edit_{suffix}")
            if nouveau_pub != pub_actuel:
                definir_publication(choix_edition, nouveau_pub)
                st.success("Quiz ouvert à l'entraînement." if nouveau_pub else "Quiz retiré de l'entraînement.")
                st.rerun()

        with st.expander("⚙️ Paramètres généraux du quiz", expanded=choix_edition == "✨ Nouveau quiz"):
            with st.form(f"form_meta_{suffix}"):
                nom_fichier = st.text_input("Nom du fichier JSON", value=st.session_state.edit_nom_fichier)
                titre_quiz = st.text_input("Titre affiché", value=st.session_state.edit_titre)
                desc_quiz = st.text_area("Description", value=st.session_state.edit_desc)
                c1, c2, c3 = st.columns(3)
                with c1:
                    quiz_image = st.text_input("Image (docs/img.png)", value=st.session_state.edit_quiz_image)
                with c2:
                    document_appui = st.text_input("PDF d'appui", value=st.session_state.edit_document_appui)
                with c3:
                    quiz_video = st.text_input("Vidéo", value=st.session_state.edit_quiz_video)
                c4, c5, c6 = st.columns(3)
                with c4:
                    musique_path = st.text_input("Musique de fond", value=st.session_state.edit_musique)
                with c5:
                    son_good = st.text_input("Son bonne réponse", value=st.session_state.edit_son_good)
                with c6:
                    son_bad = st.text_input("Son mauvaise réponse", value=st.session_state.edit_son_bad)
                c7, c8 = st.columns(2)
                with c7:
                    vol_m = st.slider("Volume musique", 0.0, 1.0, float(st.session_state.edit_vol_musique), 0.05)
                with c8:
                    vol_s = st.slider("Volume effets", 0.0, 1.0, float(st.session_state.edit_vol_sons), 0.05)
                if st.form_submit_button("💾 Enregistrer les paramètres", use_container_width=True):
                    if not nom_fichier.endswith(".json"):
                        nom_fichier += ".json"
                    st.session_state.update({
                        "edit_nom_fichier": nom_fichier, "edit_titre": titre_quiz, "edit_desc": desc_quiz,
                        "edit_quiz_image": quiz_image, "edit_document_appui": document_appui,
                        "edit_quiz_video": quiz_video, "edit_musique": musique_path,
                        "edit_son_good": son_good, "edit_son_bad": son_bad,
                        "edit_vol_musique": vol_m, "edit_vol_sons": vol_s,
                        "selected_edit_qcm": nom_fichier, "dernier_choix_edition": nom_fichier,
                    })
                    enregistrer_qcm_actuel()
                    st.success("Paramètres enregistrés.")
                    st.rerun()

        if choix_edition != "✨ Nouveau quiz":
            with st.expander("🔗 QR code & partage (mode entraînement)"):
                if not est_publie(choix_edition):
                    st.warning("🔒 Ce quiz n'est pas ouvert à l'entraînement : le lien ci-dessous sera refusé "
                               "aux étudiants tant que la case de publication n'est pas cochée.")
                dom = st.text_input("URL de l'application", value=URL_APP_DEFAUT, key="dom_solo")
                url_solo = f"{dom.strip('/')}/?qcm={choix_edition}"
                buf = BytesIO()
                qrcode.make(url_solo).save(buf, format="PNG")
                st.image(buf.getvalue(), width=180, caption=url_solo)
                if st.button(f"🗑️ Supprimer le quiz « {choix_edition} »"):
                    os.remove(os.path.join(DOSSIER_QUIZZES, choix_edition))
                    supprimer_fichier_github(f"QCM/{choix_edition}")
                    mapping = charger_publication()
                    mapping.pop(choix_edition, None)
                    sauver_publication(mapping)
                    st.session_state.selected_edit_qcm = "✨ Nouveau quiz"
                    st.session_state.dernier_choix_edition = None
                    st.rerun()

        def champs_donnees(type_q, pfx, d=None):
            d = d or {}
            if type_q in ("qcm", "sondage"):
                opts_txt = st.text_area("Options (une par ligne)", value="\n".join(d.get("options", [])),
                                        key=f"{pfx}_opts", height=120)
                opts = [o.strip() for o in opts_txt.split("\n") if o.strip()]
                if type_q == "qcm":
                    bonnes = st.multiselect("Bonnes réponses", options=opts,
                                            default=[r for r in d.get("reponses_correctes", []) if r in opts],
                                            key=f"{pfx}_bonnes")
                    return ({"options": opts, "reponses_correctes": bonnes}, bool(opts and bonnes))
                return ({"options": opts}, bool(opts))
            if type_q == "vrai_faux":
                rep = st.radio("Bonne réponse", ["VRAI", "FAUX"],
                               index=0 if d.get("reponse", True) else 1, key=f"{pfx}_vf", horizontal=True)
                return ({"reponse": rep == "VRAI"}, True)
            if type_q == "classement":
                txt = st.text_area("Éléments dans le BON ordre (un par ligne, du 1er au dernier)",
                                   value="\n".join(d.get("elements", [])), key=f"{pfx}_ordre", height=140)
                els = [e.strip() for e in txt.split("\n") if e.strip()]
                cons = st.text_input("Consigne d'ordre",
                                     value=d.get("consigne_ordre", "Classez du plus petit au plus grand"),
                                     key=f"{pfx}_cons_ordre")
                return ({"elements": els, "consigne_ordre": cons}, len(els) >= 2)
            if type_q == "association":
                st.caption("Une paire par ligne, au format : `Gauche | Droite`")
                txt = st.text_area("Paires", value="\n".join(f"{a} | {b}" for a, b in d.get("paires", [])),
                                   key=f"{pfx}_paires", height=140)
                paires = [[p.split("|")[0].strip(), p.split("|")[1].strip()]
                          for p in txt.split("\n") if "|" in p and len(p.split("|")) == 2]
                return ({"paires": paires}, len(paires) >= 2)
            if type_q == "texte":
                txt = st.text_area("Réponses acceptées (une par ligne)",
                                   value="\n".join(d.get("reponses_acceptees", [])), key=f"{pfx}_acc", height=100)
                acc = [a.strip() for a in txt.split("\n") if a.strip()]
                tol = st.toggle("Accepter les réponses partielles", value=d.get("tolerance_partielle", True), key=f"{pfx}_tol")
                return ({"reponses_acceptees": acc, "tolerance_partielle": tol}, bool(acc))
            if type_q == "curseur":
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    mini = st.number_input("Min", value=float(d.get("min", 0)), key=f"{pfx}_min")
                with c2:
                    maxi = st.number_input("Max", value=float(d.get("max", 100)), key=f"{pfx}_max")
                with c3:
                    val = st.number_input("Valeur exacte", value=float(d.get("valeur", 50)), key=f"{pfx}_val")
                with c4:
                    tol = st.number_input("Tolérance ±", value=float(d.get("tolerance", 5)), key=f"{pfx}_tolc")
                pas = st.number_input("Pas", value=float(d.get("pas", 1)), key=f"{pfx}_pas")
                unite = st.text_input("Libellé / unité", value=d.get("unite", "Votre estimation"), key=f"{pfx}_unite")
                return ({"min": mini, "max": maxi, "valeur": val, "tolerance": tol, "pas": pas, "unite": unite}, maxi > mini)
            return ({}, False)

        st.markdown("---")
        st.subheader("📋 Questions du quiz")

        if st.session_state.edit_questions:
            st.caption("💡 Glissez-déposez pour réordonner.")
            items = "".join(
                f'<div class="drag-item" draggable="true" data-index="{i}">'
                f'<span style="font-weight:800;color:#6366f1;margin-right:10px">☰ '
                f'{TYPES_QUESTION.get(q.get("type","qcm"),{}).get("icone","❓")} Q{i+1}'
                f'{" ⭐" if q.get("double_points") else ""}</span>'
                f'{(q.get("consigne","")[:60]).replace(chr(34), "&quot;")}…</div>'
                for i, q in enumerate(st.session_state.edit_questions))
            dnd = """
<style>
 body{background:transparent;margin:0}
 .drag-container{display:flex;flex-direction:column;gap:6px;font-family:Inter,sans-serif;max-height:340px;overflow-y:auto;padding-right:8px}
 .drag-item{background:#fff;padding:11px 14px;border-radius:12px;cursor:grab;border:1px solid #e2e8f0;user-select:none;display:flex;align-items:center}
 .drag-item:hover{background:#f1f5f9}
 .drag-item.dragging{opacity:.4;background:#e2e8f0}
</style>
<div class="drag-container" id="dc">__ITEMS__</div>
<script>
 const c=document.getElementById('dc');
 c.querySelectorAll('.drag-item').forEach(it=>{
  it.addEventListener('dragstart',function(){setTimeout(()=>this.classList.add('dragging'),0)});
  it.addEventListener('dragend',function(){this.classList.remove('dragging');upd()});
  it.addEventListener('dragover',function(e){e.preventDefault();
    const a=after(c,e.clientY),cur=document.querySelector('.dragging');
    if(a==null){c.appendChild(cur)}else{c.insertBefore(cur,a)}});
 });
 function after(c,y){return [...c.querySelectorAll('.drag-item:not(.dragging)')].reduce((cl,ch)=>{
   const b=ch.getBoundingClientRect(),o=y-b.top-b.height/2;
   return (o<0&&o>cl.offset)?{offset:o,element:ch}:cl;},{offset:-Infinity}).element;}
 function upd(){const o=[...c.querySelectorAll('.drag-item')].map(i=>i.getAttribute('data-index'));
   const u=window.parent.location.href.split('?')[0];
   const p=new URLSearchParams(window.parent.location.search); p.set('reorder',o.join(','));
   window.parent.location.href=u+'?'+p.toString();}
</script>"""
            components.html(dnd.replace("__ITEMS__", items), height=370)

            for i, q in enumerate(st.session_state.edit_questions):
                meta = TYPES_QUESTION.get(q.get("type", "qcm"), TYPES_QUESTION["qcm"])
                etoile = " ⭐" if q.get("double_points") else ""
                with st.expander(f"{meta['icone']} Q{i+1}{etoile} — {q.get('consigne','')[:60]} ({q.get('points',10)} pts)"):
                    pfx = f"m_{suffix}_{i}"
                    type_q = st.selectbox("Type", list(TYPES_QUESTION),
                                          format_func=lambda k: f"{TYPES_QUESTION[k]['icone']} {TYPES_QUESTION[k]['label']}",
                                          index=list(TYPES_QUESTION).index(q.get("type", "qcm")), key=f"{pfx}_type")
                    consigne = st.text_area("Consigne", value=q.get("consigne", ""), key=f"{pfx}_cons")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        pts = st.number_input("Points", 1, 200, int(q.get("points", 10)), key=f"{pfx}_pts")
                    with c2:
                        tmr = st.number_input("Chrono (s)", 5, 300, int(q.get("timer_secondes", 30)), key=f"{pfx}_tmr")
                    with c3:
                        diff = st.selectbox("Difficulté", ["Facile", "Moyen", "Difficile"],
                                            index=["Facile", "Moyen", "Difficile"].index(q.get("difficulte", "Moyen")),
                                            key=f"{pfx}_diff")
                    dbl = st.toggle("⭐ Question à points doublés", value=bool(q.get("double_points", False)),
                                    key=f"{pfx}_dbl")
                    donnees, valide = champs_donnees(type_q, pfx, q.get("donnees", {}) if type_q == q.get("type") else {})
                    expl = st.text_area("Explication affichée après la réponse", value=q.get("explication", ""), key=f"{pfx}_exp")
                    c4, c5 = st.columns(2)
                    with c4:
                        img = st.text_input("Image", value=(q.get("media", {}) or {}).get("image", ""), key=f"{pfx}_img")
                    with c5:
                        vid = st.text_input("Vidéo", value=(q.get("media", {}) or {}).get("video", ""), key=f"{pfx}_vid")
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("💾 Mettre à jour", key=f"{pfx}_save", use_container_width=True, type="primary"):
                            if consigne and valide:
                                st.session_state.edit_questions[i] = {
                                    "id": i + 1, "consigne": consigne, "type": type_q, "difficulte": diff,
                                    "points": int(pts), "double_points": bool(dbl),
                                    "tag": q.get("tag", "Général"), "timer_secondes": int(tmr),
                                    "donnees": donnees, "explication": expl,
                                    "document_texte": q.get("document_texte", ""),
                                    "media": {"image": img, "video": vid},
                                }
                                enregistrer_qcm_actuel()
                                st.success("Question mise à jour.")
                                st.rerun()
                            else:
                                st.warning("Consigne ou données de réponse incomplètes.")
                    with b2:
                        if st.button("❌ Supprimer", key=f"{pfx}_del", use_container_width=True):
                            st.session_state.edit_questions.pop(i)
                            for k, qq in enumerate(st.session_state.edit_questions):
                                qq["id"] = k + 1
                            enregistrer_qcm_actuel()
                            st.rerun()
        else:
            st.info("Ce quiz ne contient encore aucune question.")

        st.markdown("---")
        st.subheader("➕ Ajouter une question")
        pfx = f"add_{suffix}"
        type_new = st.selectbox("Type de question", list(TYPES_QUESTION),
                                format_func=lambda k: f"{TYPES_QUESTION[k]['icone']} {TYPES_QUESTION[k]['label']}",
                                key=f"{pfx}_type")
        st.caption({
            "qcm": "Une ou plusieurs bonnes réponses. Crédit partiel automatique en choix multiple.",
            "vrai_faux": "Duel express en deux tuiles — idéal pour rythmer une session.",
            "classement": "Les joueurs touchent les éléments dans l'ordre. Notation par paires bien ordonnées.",
            "association": "Relier deux colonnes. Crédit partiel proportionnel aux bonnes paires.",
            "texte": "Saisie libre, comparaison insensible aux accents et majuscules. Alimente le nuage de mots.",
            "curseur": "Estimation numérique avec tolérance : plus on est proche, plus on marque.",
            "sondage": "Aucune bonne réponse, aucun point : pour lancer un débat. Alimente le nuage de mots.",
        }[type_new])
        consigne_n = st.text_area("Consigne", key=f"{pfx}_cons")
        c1, c2, c3 = st.columns(3)
        with c1:
            pts_n = st.number_input("Points", 1, 200, 10, key=f"{pfx}_pts")
        with c2:
            tmr_n = st.number_input("Chrono (s)", 5, 300, 30, key=f"{pfx}_tmr")
        with c3:
            diff_n = st.selectbox("Difficulté", ["Facile", "Moyen", "Difficile"], index=1, key=f"{pfx}_diff")
        dbl_n = st.toggle("⭐ Question à points doublés", value=False, key=f"{pfx}_dbl")
        donnees_n, valide_n = champs_donnees(type_new, pfx)
        expl_n = st.text_area("Explication", key=f"{pfx}_exp")
        c4, c5 = st.columns(2)
        with c4:
            img_n = st.text_input("Image (optionnel)", key=f"{pfx}_img")
        with c5:
            vid_n = st.text_input("Vidéo (optionnel)", key=f"{pfx}_vid")
        if st.button("➕ Ajouter au quiz", type="primary", use_container_width=True, key=f"{pfx}_btn"):
            if consigne_n and valide_n:
                st.session_state.edit_questions.append({
                    "id": len(st.session_state.edit_questions) + 1, "consigne": consigne_n, "type": type_new,
                    "difficulte": diff_n, "points": int(pts_n), "double_points": bool(dbl_n),
                    "tag": "Général", "timer_secondes": int(tmr_n),
                    "donnees": donnees_n, "explication": expl_n, "document_texte": "",
                    "media": {"image": img_n, "video": vid_n},
                })
                enregistrer_qcm_actuel()
                st.success("Question ajoutée !")
                st.rerun()
            else:
                st.warning("Complétez la consigne et les données de réponse.")
