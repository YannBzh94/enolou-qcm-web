# -*- coding: utf-8 -*-
"""
ENOLOU QUIZ — v2.1 "Arcade"
Application de quiz interactif multi-joueurs (jusqu'a 40 participants).
Nouveautes v2.1 (Lot 1 / etape 1) : codes de session a 6 chiffres.
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

.eno-lobby{ display:flex; flex-wrap:wrap; gap:10px; }
.eno-chip{ background:#fff; border-radius:999px; padding:8px 14px; font-weight:700; font-size:.85rem;
  border:1px solid rgba(15,23,42,.08); box-shadow:0 4px 12px rgba(15,23,42,.06); animation:pop .35s ease; }
@keyframes pop{ from{transform:scale(.8);opacity:0} to{transform:scale(1);opacity:1} }

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
    """Accepte '123 456', '123-456', 'sess_1758…' (ancien format) et renvoie un identifiant utilisable."""
    if saisie is None:
        return ""
    s = str(saisie).strip()
    if s.lower().startswith("sess_"):          # retrocompatibilite ancien format
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
        if len(set(code)) == 1:                 # 111111, 222222…
            continue
        if code in ("123456", "654321", "000000"):
            continue
        return code
    # repli : premier code libre
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
# 3. MOTEUR AUDIO
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


def calculer_points(q, ratio, elapsed=None, timer_sec=None, bonus_rapidite=False):
    points = int(q.get("points", 10))
    if q.get("type") == "sondage":
        return 0
    base = points * ratio
    if bonus_rapidite and ratio > 0 and timer_sec:
        reste = max(0.0, (timer_sec - (elapsed or 0)) / timer_sec)
        base = base * (0.5 + 0.5 * reste)
    return int(round(base))


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
AVATARS = ["🦊", "🐼", "🦁", "🐨", "🐸", "🦉", "🐙", "🦄", "🐝", "🐧", "🦖", "🐬", "🦋", "🐺", "🦕", "🐳"]


def avatar_de(nom):
    return AVATARS[int(hashlib.md5(nom.encode()).hexdigest(), 16) % len(AVATARS)]


def hero(titre, sous_titre="", pills=None):
    p = "".join(f'<span class="eno-pill">{x}</span>' for x in (pills or []))
    st.markdown(
        f"""<div class="eno-hero"><h1>{titre}</h1><p>{sous_titre}</p>
        <div style="margin-top:10px">{p}</div></div>""",
        unsafe_allow_html=True,
    )


def afficher_code(code, label="Code de session", xl=False):
    """Affiche le code a 6 chiffres sous forme de pavés lisibles à distance."""
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
    pct = int(100 * restant / total) if total else 0
    st.markdown(
        f"""<div class="eno-timer">{'⏱️' if pct > 30 else '🔥'}<div class="eno-bar"><span style="width:{pct}%"></span></div>
        <div style="min-width:52px;text-align:right">{restant}s</div></div>""",
        unsafe_allow_html=True,
    )


def leaderboard(joueurs, limite=10, titre="🏆 Classement"):
    st.markdown(f"#### {titre}")
    if not joueurs:
        st.info("Aucun joueur pour l'instant.")
        return
    medailles = {0: "🥇", 1: "🥈", 2: "🥉"}
    for i, j in enumerate(joueurs[:limite]):
        st.markdown(
            f"""<div class="eno-row">
              <div class="eno-rank">{medailles.get(i, i+1)}</div>
              <div class="eno-avatar">{avatar_de(j.get('name',''))}</div>
              <div class="eno-name">{j.get('name','')}</div>
              <div class="eno-score">{j.get('score',0)} pts</div>
            </div>""",
            unsafe_allow_html=True,
        )


def entete_question(q, index, total, points_affiches=True):
    meta = TYPES_QUESTION.get(q.get("type", "qcm"), TYPES_QUESTION["qcm"])
    pts = f'<span class="eno-badge">🏆 {q.get("points",10)} pts</span>' if points_affiches else ""
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


def afficher_feedback(q, correct, ratio, points_gagnes):
    if q.get("type") == "sondage":
        st.info("📊 Réponse enregistrée — merci !")
    elif correct:
        st.markdown(f"<div class='eno-ok'>🎉 Bonne réponse ! +{points_gagnes} pts</div>", unsafe_allow_html=True)
    elif ratio > 0:
        st.markdown(f"<div class='eno-ok' style='background:linear-gradient(120deg,#f59e0b,#f97316)'>"
                    f"➗ Partiellement juste — +{points_gagnes} pts</div>", unsafe_allow_html=True)
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
            "Participant": j.get("name"), "Score": j.get("score", 0),
            "Score max": j.get("max_points", 0),
            "Réussite %": round(100 * j.get("score", 0) / max(1, j.get("max_points", 1)), 1),
            "Statut": "Terminé" if j.get("finished") else "En cours",
            "Question": "", "Réponse": "", "Correct": "", "Points": "",
        })
        for a in j.get("answers_detail", []):
            lignes.append({
                "Participant": j.get("name"), "Score": "", "Score max": "", "Réussite %": "", "Statut": "",
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

# --- Chargement d'un QCM solo via URL ---
if url_qcm and not st.session_state.qcm_selectionne:
    chemin = os.path.join(DOSSIER_QUIZZES, url_qcm)
    if os.path.exists(chemin):
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
    st.caption("v2.1 — jusqu'à 40 joueurs")
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
        st.markdown(f"Connecté : **{avatar_de(st.session_state.joueur_nom)} {st.session_state.joueur_nom}**")
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

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="eno-card"><h3>🎧 Jouer en solo</h3>'
                    '<p>Entraînez-vous à votre rythme sur un quiz partagé par votre formateur.</p></div>',
                    unsafe_allow_html=True)
        if st.button("Mode solo", use_container_width=True):
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
        st.error("❌ Partie introuvable ou terminée.")
        if st.button("Saisir un autre code"):
            st.query_params.clear()
            st.rerun()
        st.stop()

    quiz_info = sess.get("quiz_info", {})
    mode_sess = sess.get("mode", "battle")
    questions = sess.get("questions", [])
    vol_mus = quiz_info.get("volume_musique", 0.5)
    vol_sfx = quiz_info.get("volume_sons", 0.8)

    # ---------- Inscription ----------
    if not st.session_state.joueur_nom:
        hero(quiz_info.get("titre", "Quiz"), quiz_info.get("description", ""),
             [f"Mode {mode_sess.upper()}", f"{len(questions)} questions", f"Code {sid}"])
        joueurs = charger_tous_joueurs(sid)
        st.markdown(f"**{len(joueurs)}/{MAX_JOUEURS}** joueurs déjà dans le salon.")
        if joueurs:
            st.markdown('<div class="eno-lobby">' + "".join(
                f'<span class="eno-chip">{avatar_de(j["name"])} {j["name"]}</span>' for j in joueurs) + "</div>",
                unsafe_allow_html=True)
        st.markdown("### ✍️ Choisissez votre pseudo")
        nom = st.text_input("Pseudo", placeholder="Ex : Yann Q.", label_visibility="collapsed")
        if st.button("🚀 Entrer dans la partie", type="primary", use_container_width=True):
            nom = nom.strip()
            if not nom:
                st.warning("Merci de saisir un pseudo.")
            elif len(joueurs) >= MAX_JOUEURS and not charger_joueur(sid, nom):
                st.error(f"Salon complet ({MAX_JOUEURS} joueurs).")
            elif charger_joueur(sid, nom):
                st.session_state.joueur_nom = nom  # reconnexion
                st.rerun()
            else:
                ordre = list(range(len(questions)))
                if mode_sess == "examen" and sess.get("melanger", True):
                    random.Random(nom).shuffle(ordre)
                sauver_joueur(sid, {
                    "name": nom, "avatar": avatar_de(nom), "score": 0,
                    "max_points": sum(int(q.get("points", 10)) for q in questions if q.get("type") != "sondage"),
                    "current_idx": 0, "answered": False, "answered_current": False,
                    "last_result": None, "finished": False, "serie": 0, "meilleure_serie": 0,
                    "question_order": ordre, "answers_detail": [], "joined_at": time.time(),
                })
                st.session_state.joueur_nom = nom
                st.balloons()
                st.rerun()
        st.stop()

    nom_joueur = st.session_state.joueur_nom

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

        if statut == "waiting":
            hero("⏳ Salon d'attente", "La partie démarre dès que l'animateur lance le compte à rebours.",
                 [f"{avatar_de(nom_joueur)} {nom_joueur}", f"Code {sid}"])
            joueurs = charger_tous_joueurs(sid)
            st.markdown(f"#### 👥 {len(joueurs)}/{MAX_JOUEURS} joueurs connectés")
            st.markdown('<div class="eno-lobby">' + "".join(
                f'<span class="eno-chip">{avatar_de(j["name"])} {j["name"]}</span>' for j in joueurs) + "</div>",
                unsafe_allow_html=True)
            return

        if statut == "ended":
            joueurs = charger_tous_joueurs(sid)
            rang = next((i + 1 for i, j in enumerate(joueurs) if j["name"] == nom_joueur), "-")
            hero("🏁 Partie terminée !", f"Vous finissez **{rang}e** sur {len(joueurs)} joueurs.",
                 [f"Score : {moi.get('score',0)}/{moi.get('max_points',0)} pts",
                  f"Meilleure série : {moi.get('meilleure_serie',0)} 🔥"])
            leaderboard(joueurs, 10, "🏆 Podium final")
            return

        # =========== MODE BATTLE ===========
        if mode_sess == "battle":
            idx = sess.get("current_global_idx", 0)
            joueurs = charger_tous_joueurs(sid)

            if sess.get("in_transition"):
                reste = max(0, 6 - int(time.time() - sess.get("transition_start_time", time.time())))
                st.markdown(f"### ⏸️ Manche terminée — suite dans {reste}s")
                leaderboard(joueurs, 5, "🏆 Classement en direct")
                if reste == 0 and prendre_verrou(sid, f"adv_{idx}"):
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
            timer_sec = int(q.get("timer_secondes", 30))
            elapsed = int(time.time() - sess.get("question_start_time", time.time()))
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

            chrono(restant, timer_sec)
            entete_question(q, idx + 1, len(questions))
            afficher_medias(q, quiz_info)
            cle = f"b{idx}"

            if not deja:
                rep = widget_reponse(q, cle)
                if st.button("✅ Valider ma réponse", type="primary", use_container_width=True,
                             disabled=rep is None or (isinstance(rep, (list, dict)) and len(rep) == 0)):
                    correct, ratio = evaluer_reponse(q, rep)
                    pts = calculer_points(q, ratio, elapsed, timer_sec, bonus_rapidite=True)
                    serie = moi.get("serie", 0) + 1 if correct else 0
                    if correct and serie >= 3:
                        pts = int(pts * 1.2)
                    moi["score"] += pts
                    moi["serie"] = serie
                    moi["meilleure_serie"] = max(moi.get("meilleure_serie", 0), serie)
                    moi["answered_current"] = True
                    moi["last_result"] = {"correct": correct, "ratio": ratio, "points": pts}
                    moi["answers_detail"].append({"q_num": idx + 1, "consigne": q.get("consigne", ""),
                                                  "type": q.get("type", "qcm"), "reponse": rep,
                                                  "correct": correct, "points": pts})
                    sauver_joueur(sid, moi)
                    st.session_state.declencher_son = "good" if correct else "bad"
                    nettoyer_widgets(cle)
                    st.rerun()
            else:
                r = moi.get("last_result") or {}
                afficher_feedback(q, r.get("correct"), r.get("ratio", 0), r.get("points", 0))
                st.info(f"⏳ {sum(1 for j in joueurs if j.get('answered_current'))}/{len(joueurs)} joueurs ont répondu…")
                leaderboard(joueurs, 5, "🏆 Classement en direct")
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

        q = questions[ordre[i_etu]]
        entete_question(q, i_etu + 1, len(ordre))
        afficher_medias(q, quiz_info)
        cle = f"e{i_etu}"
        if not moi.get("answered"):
            rep = widget_reponse(q, cle)
            if st.button("✅ Valider ma réponse", type="primary", use_container_width=True,
                         disabled=rep is None or (isinstance(rep, (list, dict)) and len(rep) == 0)):
                correct, ratio = evaluer_reponse(q, rep)
                pts = calculer_points(q, ratio)
                moi["score"] += pts
                moi["answered"] = True
                moi["last_result"] = {"correct": correct, "ratio": ratio, "points": pts}
                moi["answers_detail"].append({"q_num": i_etu + 1, "consigne": q.get("consigne", ""),
                                              "type": q.get("type", "qcm"), "reponse": rep,
                                              "correct": correct, "points": pts})
                sauver_joueur(sid, moi)
                st.session_state.declencher_son = "good" if correct else "bad"
                nettoyer_widgets(cle)
                st.rerun()
        else:
            r = moi.get("last_result") or {}
            if sess.get("feedback_immediat", True):
                afficher_feedback(q, r.get("correct"), r.get("ratio", 0), r.get("points", 0))
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
# 10. ESPACE SOLO
# ==========================================================
elif espace == "solo":
    if not st.session_state.qcm_selectionne:
        fichiers = [f for f in os.listdir(DOSSIER_QUIZZES) if f.endswith(".json")]
        hero("🎧 Mode entraînement", "Choisissez un quiz et jouez à votre rythme.")
        if not fichiers:
            st.info("Aucun quiz disponible pour l'instant.")
        cols = st.columns(3)
        for i, f in enumerate(fichiers):
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
        hero(quiz_info.get("titre", "Quiz"), quiz_info.get("description", ""),
             [f"{len(questions)} questions", f"{sum(int(q.get('points',10)) for q in questions)} points en jeu"])
        img = quiz_info.get("image")
        if img and os.path.exists(img):
            st.image(img, use_container_width=True)
        vid = quiz_info.get("video")
        if vid and os.path.exists(vid):
            st.video(vid)
        c1, c2 = st.columns([2, 1])
        with c1:
            if st.button("🎵 Commencer", type="primary", use_container_width=True):
                st.session_state.quiz_started = True
                st.session_state.question_start_time = time.time()
                st.rerun()
        with c2:
            if st.button("← Changer de quiz", use_container_width=True):
                st.session_state.qcm_selectionne = None
                st.query_params.pop("qcm", None)
                st.rerun()
        st.stop()

    idx = st.session_state.current_idx
    if idx >= len(questions):
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
            if st.button("🏠 Autres quiz", use_container_width=True):
                st.session_state.qcm_selectionne = None
                st.session_state.quiz_started = False
                st.query_params.pop("qcm", None)
                st.rerun()
        st.stop()

    q = questions[idx]
    timer_sec = int(q.get("timer_secondes", 30))
    elapsed = int(time.time() - st.session_state.question_start_time)
    restant = max(0, timer_sec - elapsed)
    st.progress(idx / len(questions), text=f"Progression {idx}/{len(questions)} — {st.session_state.score_total} pts")

    a_support = bool(q.get("document_texte") or (q.get("media", {}) or {}).get("image"))
    col_doc, col_q = st.columns([2, 3], gap="large") if a_support else (None, st.container())
    if col_doc is not None:
        with col_doc:
            st.markdown("#### 📄 Support")
            afficher_medias(q, quiz_info)
    with col_q:
        if not st.session_state.answered:
            chrono(restant, timer_sec)
        entete_question(q, idx + 1, len(questions))
        cle = f"s{idx}"
        if not st.session_state.answered:
            rep = widget_reponse(q, cle)
            if st.button("✅ Valider ma réponse", type="primary", use_container_width=True,
                         disabled=rep is None or (isinstance(rep, (list, dict)) and len(rep) == 0)):
                correct, ratio = evaluer_reponse(q, rep)
                pts = calculer_points(q, ratio)
                if elapsed > timer_sec:
                    pts = pts // 2
                st.session_state.score_total += pts
                st.session_state.max_points += int(q.get("points", 10)) if q.get("type") != "sondage" else 0
                st.session_state.answered = True
                st.session_state.last_result = (correct, ratio, pts)
                st.session_state.declencher_son = "good" if correct else "bad"
                nettoyer_widgets(cle)
                st.rerun()
        else:
            correct, ratio, pts = st.session_state.last_result
            afficher_feedback(q, correct, ratio, pts)
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
    hero("🛠️ Espace animateur", "Créez, lancez, pilotez et analysez vos quiz.",
         ["Codes à 6 chiffres", f"Jusqu'à {MAX_JOUEURS} joueurs", "Export Excel"])
    fichiers_existants = [f for f in os.listdir(DOSSIER_QUIZZES) if f.endswith(".json")]
    tab_sess, tab_edit, tab_ecran = st.tabs(["🎮 Sessions en direct", "📝 Éditeur de quiz", "📺 Écran de projection"])

    def galerie(fichiers, prefixe, cle_etat):
        if not fichiers:
            st.info("Aucun quiz disponible.")
            return
        cols = st.columns(3)
        for i, f in enumerate(fichiers):
            data = lire_json(os.path.join(DOSSIER_QUIZZES, f), {}) or {}
            info = data.get("quiz_info", {})
            actif = st.session_state.get(cle_etat) == f
            with cols[i % 3]:
                bord = "2px solid var(--c1)" if actif else "1px solid rgba(15,23,42,.06)"
                st.markdown(
                    f"""<div class="eno-card" style="border:{bord}">
                    <div style="font-weight:800">{'✨ ' if actif else ''}{info.get('titre', f)}</div>
                    <div style="color:#64748b;font-size:.8rem;margin:6px 0;height:32px;overflow:hidden">{info.get('description','—')}</div>
                    <span class="eno-badge">⚡ {len(data.get('questions',[]))} Q</span>
                    <span class="eno-badge">📄 {f}</span></div>""", unsafe_allow_html=True)
                if st.button("Sélectionné ✓" if actif else "Sélectionner", key=f"{prefixe}_{i}",
                             disabled=actif, use_container_width=True):
                    st.session_state[cle_etat] = f
                    st.rerun()

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
                    st.markdown(f"**Mode :** `{sess['mode'].upper()}` — **Statut :** `{sess['status'].upper()}`")

                @st.fragment(run_every=3)
                def pilotage():
                    s = charger_session(sid)
                    if not s:
                        st.warning("Session supprimée.")
                        return
                    joueurs = charger_tous_joueurs(sid)
                    m1, m2, m3 = st.columns(3)
                    m1.metric("👥 Joueurs", f"{len(joueurs)}/{MAX_JOUEURS}")
                    m2.metric("❓ Question",
                              f"{min(s.get('current_global_idx',0)+1, len(s.get('questions',[])))}/{len(s.get('questions',[]))}")
                    m3.metric("✅ Ont répondu", sum(1 for j in joueurs if j.get("answered_current") or j.get("answered")))
                    if joueurs:
                        st.markdown('<div class="eno-lobby">' + "".join(
                            f'<span class="eno-chip">{avatar_de(j["name"])} {j["name"]} · {j.get("score",0)}</span>'
                            for j in joueurs) + "</div>", unsafe_allow_html=True)
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
                        leaderboard(joueurs, 10)
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
                if s["status"] == "waiting":
                    hero("Rejoignez la partie !", "Rendez-vous sur l'application et saisissez le code ci-dessous.",
                         [f"{len(joueurs)}/{MAX_JOUEURS} joueurs"])
                    afficher_code(sid_p, "Code de la partie", xl=True)
                    st.markdown('<div class="eno-lobby">' + "".join(
                        f'<span class="eno-chip" style="font-size:1.1rem">{avatar_de(j["name"])} {j["name"]}</span>'
                        for j in joueurs) + "</div>", unsafe_allow_html=True)
                elif s["status"] == "ended":
                    hero("🏁 Résultats finaux", "Merci à tous les participants !")
                    leaderboard(joueurs, 10, "🏆 Podium")
                elif idx < len(qs):
                    q = qs[idx]
                    total = int(q.get("timer_secondes", 30))
                    restant = max(0, total - int(time.time() - s.get("question_start_time", time.time())))
                    chrono(restant, total)
                    entete_question(q, idx + 1, len(qs))
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
                    leaderboard(joueurs, 5, "🏆 Top 5")
            projection()

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
            with st.expander("🔗 QR code & partage (mode solo)"):
                dom = st.text_input("URL de l'application", value=URL_APP_DEFAUT, key="dom_solo")
                url_solo = f"{dom.strip('/')}/?qcm={choix_edition}"
                buf = BytesIO()
                qrcode.make(url_solo).save(buf, format="PNG")
                st.image(buf.getvalue(), width=180, caption=url_solo)
                if st.button(f"🗑️ Supprimer le quiz « {choix_edition} »"):
                    os.remove(os.path.join(DOSSIER_QUIZZES, choix_edition))
                    supprimer_fichier_github(f"QCM/{choix_edition}")
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
                f'{TYPES_QUESTION.get(q.get("type","qcm"),{}).get("icone","❓")} Q{i+1}</span>'
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
                with st.expander(f"{meta['icone']} Q{i+1} — {q.get('consigne','')[:60]} ({q.get('points',10)} pts)"):
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
                                    "points": int(pts), "tag": q.get("tag", "Général"), "timer_secondes": int(tmr),
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
            "texte": "Saisie libre, comparaison insensible aux accents et majuscules.",
            "curseur": "Estimation numérique avec tolérance : plus on est proche, plus on marque.",
            "sondage": "Aucune bonne réponse, aucun point : pour lancer un débat.",
        }[type_new])
        consigne_n = st.text_area("Consigne", key=f"{pfx}_cons")
        c1, c2, c3 = st.columns(3)
        with c1:
            pts_n = st.number_input("Points", 1, 200, 10, key=f"{pfx}_pts")
        with c2:
            tmr_n = st.number_input("Chrono (s)", 5, 300, 30, key=f"{pfx}_tmr")
        with c3:
            diff_n = st.selectbox("Difficulté", ["Facile", "Moyen", "Difficile"], index=1, key=f"{pfx}_diff")
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
                    "difficulte": diff_n, "points": int(pts_n), "tag": "Général", "timer_secondes": int(tmr_n),
                    "donnees": donnees_n, "explication": expl_n, "document_texte": "",
                    "media": {"image": img_n, "video": vid_n},
                })
                enregistrer_qcm_actuel()
                st.success("Question ajoutée !")
                st.rerun()
            else:
                st.warning("Complétez la consigne et les données de réponse.")
