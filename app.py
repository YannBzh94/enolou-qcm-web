import os
import json
import random
import time
import qrcode
import base64
import requests
from io import BytesIO
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Portail QCM Enolou", page_icon="🎓", layout="wide")

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stAudio"] {
        display: none !important;
    }
    audio {
        display: none !important;
    }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

DOSSIER_QUIZZES = "QCM"
DOSSIER_SESSIONS = "SESSIONS"

if not os.path.exists(DOSSIER_QUIZZES):
    os.makedirs(DOSSIER_QUIZZES)
if not os.path.exists(DOSSIER_SESSIONS):
    os.makedirs(DOSSIER_SESSIONS)

# --- FONCTION DE SYNCHRONISATION AUTOMATIQUE AVEC GITHUB ---
def sauvegarder_fichier_github(chemin_relatif, contenu_str):
    try:
        if "GITHUB_TOKEN" in st.secrets:
            token = st.secrets["GITHUB_TOKEN"]
            owner_repo = "YannBzh94/enolou-qcm-web"
            url = f"https://api.github.com/repos/{owner_repo}/contents/{chemin_relatif}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"
            }
            
            resp = requests.get(url, headers=headers)
            sha = resp.json().get("sha") if resp.status_code == 200 else None
            
            content_base64 = base64.b64encode(contenu_str.encode('utf-8')).decode('utf-8')
            payload = {
                "message": f"Mise à jour automatique de {chemin_relatif} via l'application Enolou",
                "content": content_base64,
                "branch": "main"
            }
            if sha:
                payload["sha"] = sha
                
            put_resp = requests.put(url, headers=headers, json=payload)
            return put_resp.status_code in [200, 201]
    except Exception as e:
        print(f"Erreur synchro GitHub: {e}")
    return False

def supprimer_fichier_github(chemin_relatif):
    try:
        if "GITHUB_TOKEN" in st.secrets:
            token = st.secrets["GITHUB_TOKEN"]
            owner_repo = "YannBzh94/enolou-qcm-web"
            url = f"https://api.github.com/repos/{owner_repo}/contents/{chemin_relatif}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"
            }
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                sha = resp.json().get("sha")
                payload = {
                    "message": f"Suppression de {chemin_relatif} via l'application Enolou",
                    "sha": sha,
                    "branch": "main"
                }
                requests.delete(url, headers=headers, json=payload)
    except Exception as e:
        print(f"Erreur suppression GitHub: {e}")

# --- UTILITAIRE DE SAUVEGARDE GLOBALE DU QCM ---
def enregistrer_qcm_actuel():
    donnees_globales = {
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
            "volume_sons": st.session_state.edit_vol_sons
        },
        "questions": st.session_state.edit_questions
    }
    contenu_json = json.dumps(donnees_globales, ensure_ascii=False, indent=4)
    nom_fich = st.session_state.edit_nom_fichier
    if not nom_fich.endswith(".json"):
        nom_fich += ".json"
    with open(os.path.join(DOSSIER_QUIZZES, nom_fich), "w", encoding="utf-8") as f:
        f.write(contenu_json)
    sauvegarder_fichier_github(f"QCM/{nom_fich}", contenu_json)

# --- MOTEUR AUDIO UNIFIÉ (BASE64 & JS PERSISTANT) ---
def fichier_en_base64(chemin):
    if chemin and os.path.exists(chemin):
        try:
            ext = chemin.strip().lower().split('.')[-1]
            mime_map = {'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'ogg': 'audio/ogg', 'm4a': 'audio/mp4', 'aac': 'audio/aac'}
            mime_type = mime_map.get(ext, 'audio/mpeg')
            with open(chemin, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return f"data:{mime_type};base64,{b64}"
        except Exception as e:
            print(f"Erreur encodage audio: {e}")
    return ""

def rendre_moteur_audio(musique_path, vol_musique, son_declenche=None, son_path=None, vol_sons=0.8):
    b64_music = fichier_en_base64(musique_path) if musique_path else ""
    b64_sfx = fichier_en_base64(son_path) if (son_declenche and son_path) else ""
    
    sfx_script = ""
    if b64_sfx:
        sfx_script = f"""
        const sfx = new Audio("{b64_sfx}");
        sfx.volume = {float(vol_sons)};
        sfx.play().catch(e => console.log("SFX play error:", e));
        """

    audio_html = f"""
    <audio id="persistent-bg-audio" loop style="display:none;"></audio>
    <script>
        const audioEl = document.getElementById('persistent-bg-audio');
        const musicSrc = "{b64_music}";
        
        if (audioEl && musicSrc) {{
            if (audioEl.src !== musicSrc) {{
                audioEl.src = musicSrc;
                audioEl.play().catch(e => console.log("Autoplay bloqué:", e));
            }}
            audioEl.volume = {float(vol_musique)};
            if (audioEl.paused) {{
                audioEl.play().catch(e => console.log("Reprise audio bloquée:", e));
            }}
        }} else if (audioEl && !musicSrc) {{
            audioEl.pause();
        }}

        {sfx_script}
    </script>
    """
    components.html(audio_html, height=0, width=0)

# --- EXPORT TABLEUR COMPATIBLE EXCEL ---
def generer_csv_session(sess_data):
    summary_data = []
    for nom, info in sess_data.get("students", {}).items():
        summary_data.append({
            "Étudiant": nom,
            "Score Total": info.get("score", 0),
            "Score Max": info.get("max_points", 0),
            "Statut": "Terminé" if info.get("finished", False) else "En cours"
        })
        for ans in info.get("answers_detail", []):
            rep_str = ", ".join(ans.get('reponse', [])) if isinstance(ans.get('reponse'), list) else str(ans.get('reponse'))
            summary_data.append({
                "Étudiant": f"   -> Q{ans.get('q_num')}: {ans.get('consigne')}",
                "Score Total": f"Réponse: {rep_str}",
                "Score Max": f"Correct: {'Oui' if ans.get('correct') else 'Non'}",
                "Statut": f"Pts: {ans.get('points')}"
            })
    df = pd.DataFrame(summary_data)
    return df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')

# --- GESTION DES URLS & REORDER DRAG-AND-DROP ---
query_params = st.query_params
url_qcm = query_params.get("qcm")
url_session = query_params.get("session")

if "reorder" in query_params and 'edit_questions' in st.session_state and st.session_state.edit_questions:
    try:
        new_order_indices = [int(x) for x in query_params["reorder"].split(",")]
        if len(new_order_indices) == len(st.session_state.edit_questions):
            st.session_state.edit_questions = [st.session_state.edit_questions[i] for i in new_order_indices]
            for r_idx, rq in enumerate(st.session_state.edit_questions):
                rq["id"] = r_idx + 1
            enregistrer_qcm_actuel()
            st.query_params.pop("reorder", None)
            st.rerun()
    except Exception as e:
        print(f"Erreur reorder D&D: {e}")

if url_qcm and 'qcm_selectionne' not in st.session_state:
    chemin_complet = os.path.join(DOSSIER_QUIZZES, url_qcm)
    if os.path.exists(chemin_complet):
        with open(chemin_complet, 'r', encoding='utf-8') as f:
            banque = json.load(f)
        st.session_state.banque = banque if isinstance(banque, dict) else {"quiz_info": {}, "questions": banque}
        st.session_state.qcm_selectionne = url_qcm
        st.session_state.current_idx = 0
        st.session_state.score_total = 0
        st.session_state.max_points = 0
        st.session_state.quiz_started = False
        st.session_state.answered = False
        st.session_state.last_result = None
        st.session_state.declencher_son = None

default_mode_idx = 1 if url_session else 0

st.sidebar.title("🧭 Navigation")
mode = st.sidebar.radio("Choisissez le mode :", [
    "👨‍🎓 Espace Étudiant (Solo)", 
    "🌐 Espace Collectif (Rejoindre une session)", 
    "👨‍🏫 Espace Professeur"
], index=default_mode_idx)

if 'qcm_selectionne' not in st.session_state:
    st.session_state.qcm_selectionne = None

if 'declencher_son' not in st.session_state:
    st.session_state.declencher_son = None
    st.session_state.chemin_son_actuel = None

# ==========================================
# 👨‍🏫 ESPACE PROFESSEUR
# ==========================================
if mode == "👨‍🏫 Espace Professeur":
    st.title("👨‍🏫 Espace Professeur - Gestion & Sessions Collectives")
    
    tab_gen, tab_sess = st.tabs(["📝 Éditeur & QR Codes Solo", "🌐 Gestion des Sessions Collectives"])
    fichiers_existants = [f for f in os.listdir(DOSSIER_QUIZZES) if f.endswith('.json')]

    with tab_sess:
        st.subheader("Lancer un Quiz en mode Collectif")
        if fichiers_existants:
            qcm_collectif = st.selectbox("Sélectionnez le QCM :", fichiers_existants, key="sel_collec_qcm")
            type_mode_collec = st.radio("Mode de session :", [
                "🎮 Mode Battle (Synchronisé, rapidité, podium & cuillère de bois)", 
                "📝 Mode Examen (Synchro au départ, autonomie & export tableur)"
            ], key="type_mode_collec")

            domaine_app = st.text_input(
                "URL de votre application déployée :", 
                value="https://yannbzh94-enolou-qcm-web-app-ngwrt8.streamlit.app/",
                key="domaine_app_collec"
            )

            if st.button("🚀 Créer une nouvelle session", type="primary"):
                session_id = f"sess_{int(time.time())}"
                chemin_qcm = os.path.join(DOSSIER_QUIZZES, qcm_collectif)
                with open(chemin_qcm, 'r', encoding='utf-8') as f:
                    qcm_data = json.load(f)
                
                mode_interne = "battle" if "Battle" in type_mode_collec else "examen"
                session_data = {
                    "session_id": session_id,
                    "qcm_filename": qcm_collectif,
                    "mode": mode_interne,
                    "status": "waiting",
                    "current_global_idx": 0,
                    "question_start_time": 0,
                    "in_transition": False,
                    "transition_start_time": 0,
                    "quiz_info": qcm_data.get("quiz_info", {}),
                    "questions": qcm_data.get("questions", []),
                    "students": {}
                }
                
                with open(os.path.join(DOSSIER_SESSIONS, f"{session_id}.json"), 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=4)
                
                st.session_state["sel_session_piloter"] = session_id
                st.success(f"Nouvelle session créée avec succès ! (ID: {session_id})")
                st.rerun()

            sessions_existantes = [f.replace('.json', '') for f in os.listdir(DOSSIER_SESSIONS) if f.endswith('.json')]
            if sessions_existantes:
                st.markdown("---")
                st.markdown("### 📊 Suivi / Consultation des Sessions")
                
                if "sel_session_piloter" not in st.session_state or st.session_state["sel_session_piloter"] not in sessions_existantes:
                    st.session_state["sel_session_piloter"] = sessions_existantes[0]
                
                sess_choisie = st.selectbox("Sélectionnez une session à piloter :", sessions_existantes, key="sel_session_piloter")
                
                chemin_sess = os.path.join(DOSSIER_SESSIONS, f"{sess_choisie}.json")
                if os.path.exists(chemin_sess):
                    with open(chemin_sess, 'r', encoding='utf-8') as f:
                        s_data = json.load(f)
                    
                    url_session_complete = f"{domaine_app.strip('/')}/?session={sess_choisie}"
                    st.write(f"**Lien étudiants :** [{url_session_complete}]({url_session_complete})")
                    
                    img_qr = qrcode.make(url_session_complete)
                    buffered = BytesIO()
                    img_qr.save(buffered, format="PNG")
                    st.image(buffered.getvalue(), caption=f"QR Code Session : {s_data['quiz_info'].get('titre', '')}", width=200)

                    st.markdown(f"**Mode :** `{s_data['mode'].upper()}` | **Statut :** `{s_data['status'].upper()}`")
                    
                    etudiants = s_data.get("students", {})
                    st.markdown(f"#### 👥 Étudiants inscrits ({len(etudiants)}) :")
                    if etudiants:
                        st.success(", ".join(etudiants.keys()))
                    else:
                        st.info("En attente d'inscription...")

                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button("🔄 Rafraîchir l'écran"):
                            st.rerun()
                    with col_btn2:
                        if s_data["status"] == "waiting" and st.button("▶️ Démarrer la session", type="primary"):
                            s_data["status"] = "started"
                            s_data["current_global_idx"] = 0
                            s_data["question_start_time"] = time.time()
                            s_data["in_transition"] = False
                            with open(chemin_sess, 'w', encoding='utf-8') as f:
                                json.dump(s_data, f, ensure_ascii=False, indent=4)
                            st.success("Session lancée !")
                            st.rerun()
                    with col_btn3:
                        if s_data["status"] == "started" and st.button("⏹️ Clôturer la session"):
                            s_data["status"] = "ended"
                            with open(chemin_sess, 'w', encoding='utf-8') as f:
                                json.dump(s_data, f, ensure_ascii=False, indent=4)
                            st.rerun()

                    if s_data["status"] in ["started", "ended"]:
                        csv_data = generer_csv_session(s_data)
                        st.download_button(
                            label="📥 Télécharger le rapport des notes (.csv compatible Excel)",
                            data=csv_data,
                            file_name=f"resultats_{sess_choisie}.csv",
                            mime="text/csv"
                        )

                    if s_data["status"] in ["started", "ended"] and s_data["mode"] == "battle":
                        finis = [info for info in etudiants.values() if info.get("finished", False) or info.get("score", 0) >= 0]
                        if finis:
                            finis_tries = sorted(finis, key=lambda x: x["score"], reverse=True)
                            st.markdown("### 🏆 Podium Battle en direct")
                            for idx, f_info in enumerate(finis_tries[:3]):
                                medailles = ["🥇", "🥈", "🥉"]
                                st.markdown(f"**{medailles[idx]} {f_info['name']}** : {f_info['score']} pts")
                            if len(finis_tries) >= 4:
                                dernier = finis_tries[-1]
                                st.markdown(f"**🥄 Cuillère de bois :** {dernier['name']} ({dernier['score']} pts)")

                    st.markdown("---")
                    col_del1, col_del2 = st.columns(2)
                    with col_del1:
                        if st.button(f"🗑️ Supprimer cette session ({sess_choisie})"):
                            os.remove(chemin_sess)
                            st.success(f"Session {sess_choisie} supprimée.")
                            st.rerun()
                    with col_del2:
                        if st.button("🔥 Purger toutes les sessions"):
                            for f_s in os.listdir(DOSSIER_SESSIONS):
                                if f_s.endswith('.json'):
                                    os.remove(os.path.join(DOSSIER_SESSIONS, f_s))
                            st.success("Toutes les sessions ont été purgées.")
                            st.rerun()
        else:
            st.info("Aucun QCM disponible pour lancer une session.")

    with tab_gen:
        st.subheader("Générateur de QR Code Solo & Éditeur")
        if fichiers_existants:
            qcm_pour_qr = st.selectbox("Sélectionnez le QCM (Solo) :", fichiers_existants)
            domaine_app_solo = st.text_input("URL de l'application :", value="https://yannbzh94-enolou-qcm-web-app-ngwrt8.streamlit.app/", key="dom_solo")
            if domaine_app_solo:
                url_complete = f"{domaine_app_solo.strip('/')}/?qcm={qcm_pour_qr}"
                img_qr = qrcode.make(url_complete)
                buffered = BytesIO()
                img_qr.save(buffered, format="PNG")
                st.image(buffered.getvalue(), caption=f"QR Code Solo : {qcm_pour_qr}", width=200)

        choix_edition = st.selectbox("Éditer ou supprimer un QCM :", ["-- Créer un nouveau QCM --"] + fichiers_existants)
        
        if choix_edition != "-- Créer un nouveau QCM --":
            if st.button(f"🗑️ Supprimer définitivement le QCM '{choix_edition}'", type="secondary"):
                chemin_qcm = os.path.join(DOSSIER_QUIZZES, choix_edition)
                if os.path.exists(chemin_qcm):
                    os.remove(chemin_qcm)
                    supprimer_fichier_github(f"QCM/{choix_edition}")
                st.success(f"QCM {choix_edition} supprimé avec succès !")
                if st.session_state.get('qcm_selectionne') == choix_edition:
                    st.session_state.qcm_selectionne = None
                st.rerun()

        keys_defaults = {
            'edit_nom_fichier': "nouveau_qcm.json",
            'edit_titre': "",
            'edit_desc': "",
            'edit_quiz_image': "",
            'edit_document_appui': "",
            'edit_quiz_video': "",
            'edit_musique': "",
            'edit_son_good': "",
            'edit_son_bad': "",
            'edit_vol_musique': 0.5,
            'edit_vol_sons': 0.8,
            'edit_questions': [],
            'dernier_choix_edition': None
        }
        for k, v in keys_defaults.items():
            if k not in st.session_state:
                st.session_state[k] = v

        if choix_edition != st.session_state.dernier_choix_edition:
            st.session_state.dernier_choix_edition = choix_edition
            if choix_edition == "-- Créer un nouveau QCM --":
                st.session_state.edit_nom_fichier = "nouveau_qcm.json"
                st.session_state.edit_titre = "Mon Nouveau Quiz"
                st.session_state.edit_desc = ""
                st.session_state.edit_quiz_image = ""
                st.session_state.edit_document_appui = ""
                st.session_state.edit_quiz_video = ""
                st.session_state.edit_musique = ""
                st.session_state.edit_son_good = ""
                st.session_state.edit_son_bad = ""
                st.session_state.edit_vol_musique = 0.5
                st.session_state.edit_vol_sons = 0.8
                st.session_state.edit_questions = []
            else:
                chemin = os.path.join(DOSSIER_QUIZZES, choix_edition)
                try:
                    with open(chemin, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        info = data.get("quiz_info", {})
                        st.session_state.edit_nom_fichier = choix_edition
                        st.session_state.edit_titre = info.get("titre", "")
                        st.session_state.edit_desc = info.get("description", "")
                        st.session_state.edit_quiz_image = info.get("image", "")
                        st.session_state.edit_document_appui = info.get("document_appui", "")
                        st.session_state.edit_quiz_video = info.get("video", "")
                        st.session_state.edit_musique = info.get("musique", "")
                        st.session_state.edit_son_good = info.get("son_good", "")
                        st.session_state.edit_son_bad = info.get("son_bad", "")
                        st.session_state.edit_vol_musique = info.get("volume_musique", 0.5)
                        st.session_state.edit_vol_sons = info.get("volume_sons", 0.8)
                        st.session_state.edit_questions = data.get("questions", [])
                except Exception:
                    pass

        st.markdown("### 🔊 Réglage des Volumes Audio")
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.session_state.edit_vol_musique = st.slider("Volume musique de fond", 0.0, 1.0, value=float(st.session_state.edit_vol_musique), step=0.05)
        with col_v2:
            st.session_state.edit_vol_sons = st.slider("Volume effets sonores", 0.0, 1.0, value=float(st.session_state.edit_vol_sons), step=0.05)

        with st.form("form_edition_qcm"):
            st.markdown("### ⚙️ Paramètres Généraux du QCM")
            nom_fichier = st.text_input("Nom du fichier JSON :", value=st.session_state.edit_nom_fichier)
            titre_quiz = st.text_input("Titre affiché :", value=st.session_state.edit_titre)
            desc_quiz = st.text_area("Description :", value=st.session_state.edit_desc)
            
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                quiz_image = st.text_input("Image générale (chemin ex: docs/image.png) :", value=st.session_state.edit_quiz_image)
            with col_m2:
                document_appui = st.text_input("PDF d'appui / Doc (chemin ex: docs/cas.pdf) :", value=st.session_state.edit_document_appui)
            with col_m3:
                quiz_video = st.text_input("Vidéo générale (chemin ex: docs/video.mp4) :", value=st.session_state.edit_quiz_video)

            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                musique_path = st.text_input("Musique de fond :", value=st.session_state.edit_musique)
            with col_s2:
                son_good = st.text_input("Son bonne réponse :", value=st.session_state.edit_son_good)
            with col_s3:
                son_bad = st.text_input("Son mauvaise réponse :", value=st.session_state.edit_son_bad)

            submitted_meta = st.form_submit_button("💾 Enregistrer les paramètres généraux")
            if submitted_meta:
                if not nom_fichier.endswith(".json"):
                    nom_fichier += ".json"
                
                st.session_state.edit_nom_fichier = nom_fichier
                st.session_state.edit_titre = titre_quiz
                st.session_state.edit_desc = desc_quiz
                st.session_state.edit_quiz_image = quiz_image
                st.session_state.edit_document_appui = document_appui
                st.session_state.edit_quiz_video = quiz_video
                st.session_state.edit_musique = musique_path
                st.session_state.edit_son_good = son_good
                st.session_state.edit_son_bad = son_bad

                enregistrer_qcm_actuel()
                st.success("Paramètres généraux enregistrés avec succès !")

        st.markdown("---")
        st.subheader("📋 Ré-ordonnancement par Glisser-Déposer (Drag & Drop)")
        
        if st.session_state.edit_questions:
            st.info("💡 Glissez et déposez les questions ci-dessous pour réorganiser leur ordre instantanément.")
            
            # Génération du composant Drag-and-Drop en HTML/JS
            questions_list_html = ""
            for idx, q in enumerate(st.session_state.edit_questions):
                consigne_court = q.get('consigne', f'Question {idx+1}')[:65].replace('"', '&quot;')
                questions_list_html += f'<div class="drag-item" draggable="true" data-index="{idx}"><span style="font-weight:bold; color:#ff4b4b; margin-right:10px;">☰ Q{idx+1}</span> {consigne_court}...</div>'

            drag_drop_html = f"""
            <style>
                .drag-container {{ display: flex; flex-direction: column; gap: 6px; font-family: sans-serif; margin-bottom: 10px; }}
                .drag-item {{ background: #f8f9fa; padding: 10px 14px; border-radius: 6px; cursor: grab; border: 1px solid #ced4da; user-select: none; display: flex; align-items: center; transition: background 0.2s; }}
                .drag-item:hover {{ background: #e9ecef; border-color: #adb5bd; }}
                .drag-item:active {{ cursor: grabbing; }}
                .drag-item.dragging {{ opacity: 0.4; background: #dee2e6; }}
            </style>
            <div class="drag-container" id="dragContainer">
                {questions_list_html}
            </div>
            <script>
                const container = document.getElementById('dragContainer');
                let draggedItem = null;

                container.querySelectorAll('.drag-item').forEach(item => {{
                    item.addEventListener('dragstart', function(e) {{
                        draggedItem = this;
                        setTimeout(() => this.classList.add('dragging'), 0);
                    }});
                    item.addEventListener('dragend', function(e) {{
                        this.classList.remove('dragging');
                        draggedItem = null;
                        updateOrder();
                    }});
                    item.addEventListener('dragover', function(e) {{
                        e.preventDefault();
                        const afterElement = getDragAfterElement(container, e.clientY);
                        const currentItem = document.querySelector('.dragging');
                        if (afterElement == null) {{
                            container.appendChild(currentItem);
                        }} else {{
                            container.insertBefore(currentItem, afterElement);
                        }}
                    }});
                }});

                function getDragAfterElement(container, y) {{
                    const draggableElements = [...container.querySelectorAll('.drag-item:not(.dragging)')];
                    return draggableElements.reduce((closest, child) => {{
                        const box = child.getBoundingClientRect();
                        const offset = y - box.top - box.height / 2;
                        if (offset < 0 && offset > closest.offset) {{
                            return {{ offset: offset, element: child }};
                        }} else {{
                            return closest;
                        }}
                    }}, {{ offset: Number.NEGATIVE_INFINITY }}).element;
                }}

                function updateOrder() {{
                    const items = [...container.querySelectorAll('.drag-item')];
                    const order = items.map(item => item.getAttribute('data-index'));
                    const currentUrl = window.parent.location.href.split('?')[0];
                    const searchParams = new URLSearchParams(window.parent.location.search);
                    searchParams.set('reorder', order.join(','));
                    window.parent.location.href = currentUrl + '?' + searchParams.toString();
                }}
            </script>
            """
            components.html(drag_drop_html, height=min(450, max(120, len(st.session_state.edit_questions) * 45 + 30)))

            st.markdown("---")
            st.subheader("📝 Modification et Édition des Questions")
            for idx, q in enumerate(st.session_state.edit_questions):
                with st.expander(f"Modifier la Question {idx+1} : {q.get('consigne', '')[:50]}... (Points: {q.get('points', 10)})"):
                    with st.form(f"form_mod_q_{idx}"):
                        mod_consigne = st.text_area("Consigne :", value=q.get('consigne', ''), key=f"mod_c_{idx}")
                        col_p1, col_p2 = st.columns(2)
                        with col_p1:
                            mod_points = st.number_input("Points :", min_value=1, value=q.get('points', 10), key=f"mod_pts_{idx}")
                        with col_p2:
                            mod_timer = st.number_input("Chronomètre (sec) :", min_value=5, value=q.get('timer_secondes', 30), key=f"mod_tim_{idx}")
                        
                        options_actuelles = q.get('donnees', {}).get('options', [])
                        mod_options_input = st.text_area("Options (une par ligne) :", value="\n".join(options_actuelles), key=f"mod_opt_{idx}")
                        
                        reponses_actuelles = q.get('donnees', {}).get('reponses_correctes', [])
                        options_temp_list = [o.strip() for o in mod_options_input.split("\n") if o.strip()]
                        def_reps = [r for r in reponses_actuelles if r in options_temp_list]
                        mod_reponses_correctes = st.multiselect(
                            "Réponses correctes (cochez une ou plusieurs options) :", 
                            options=options_temp_list, 
                            default=def_reps, 
                            key=f"mod_rep_{idx}"
                        )
                        
                        mod_explication = st.text_area("Explication :", value=q.get('explication', ''), key=f"mod_exp_{idx}")
                        
                        col_m_img, col_m_vid = st.columns(2)
                        with col_m_img:
                            mod_img = st.text_input("Image question (optionnel) :", value=q.get('media', {}).get('image', ''), key=f"mod_img_{idx}")
                        with col_m_vid:
                            mod_vid = st.text_input("Vidéo question (optionnel) :", value=q.get('media', {}).get('video', ''), key=f"mod_vid_{idx}")

                        submitted_mod = st.form_submit_button("💾 Mettre à jour cette question")
                        if submitted_mod:
                            options_liste = [opt.strip() for opt in mod_options_input.split("\n") if opt.strip()]
                            if mod_consigne and options_liste and mod_reponses_correctes:
                                st.session_state.edit_questions[idx] = {
                                    "id": idx + 1,
                                    "consigne": mod_consigne,
                                    "type": "qcm",
                                    "difficulte": q.get("difficulte", "Moyen"),
                                    "points": mod_points,
                                    "tag": q.get("tag", "Général"),
                                    "timer_secondes": mod_timer,
                                    "donnees": {
                                        "options": options_liste,
                                        "reponses_correctes": mod_reponses_correctes
                                    },
                                    "explication": mod_explication,
                                    "document_texte": q.get("document_texte", ""),
                                    "document_image_a4": q.get("document_image_a4", ""),
                                    "document_appui": q.get("document_appui", ""),
                                    "media": {
                                        "image": mod_img,
                                        "video": mod_vid
                                    }
                                }
                                enregistrer_qcm_actuel()
                                st.success(f"Question {idx+1} mise à jour avec succès !")
                                st.rerun()

                    if st.button(f"❌ Supprimer la question {idx+1}", key=f"del_q_{idx}"):
                        st.session_state.edit_questions.pop(idx)
                        for r_idx, rq in enumerate(st.session_state.edit_questions):
                            rq["id"] = r_idx + 1
                        enregistrer_qcm_actuel()
                        st.success("Question supprimée !")
                        st.rerun()

        st.markdown("---")
        st.subheader("➕ Ajouter une nouvelle question")
        with st.form("form_ajout_question"):
            consigne_q = st.text_area("Consigne :")
            col_ap1, col_ap2 = st.columns(2)
            with col_ap1:
                points_q = st.number_input("Points :", min_value=1, value=10)
            with col_ap2:
                timer_q = st.number_input("Chronomètre (secondes) :", min_value=5, value=30)
            
            options_input = st.text_area("Options (une par ligne) :")
            options_ajout_list = [o.strip() for o in options_input.split("\n") if o.strip()]
            
            add_reponses_correctes = st.multiselect("Réponses correctes (cochez une ou plusieurs options) :", options=options_ajout_list)
            explication_q = st.text_area("Explication :")
            
            col_m_add_img, col_m_add_vid = st.columns(2)
            with col_m_add_img:
                add_img = st.text_input("Image média (optionnel) :", value="")
            with col_m_add_vid:
                add_vid = st.text_input("Vidéo média (optionnel) :", value="")

            submitted_q = st.form_submit_button("➕ Ajouter la question au QCM")
            if submitted_q:
                options_liste = [opt.strip() for opt in options_input.split("\n") if opt.strip()]
                if consigne_q and options_liste and add_reponses_correctes:
                    nouv_q = {
                        "id": len(st.session_state.edit_questions) + 1,
                        "consigne": consigne_q,
                        "type": "qcm",
                        "difficulte": "Moyen",
                        "points": points_q,
                        "tag": "Général",
                        "timer_secondes": timer_q,
                        "donnees": {
                            "options": options_liste,
                            "reponses_correctes": add_reponses_correctes
                        },
                        "explication": explication_q,
                        "document_texte": "",
                        "document_image_a4": "",
                        "document_appui": "",
                        "media": {
                            "image": add_img,
                            "video": add_vid
                        }
                    }
                    st.session_state.edit_questions.append(nouv_q)
                    enregistrer_qcm_actuel()
                    st.success("Question ajoutée avec succès !")
                    st.rerun()

# ==========================================
# 🌐 ESPACE COLLECTIF : REJOINDRE UNE SESSION (ÉTUDIANT)
# ==========================================
elif mode == "🌐 Espace Collectif (Rejoindre une session)":
    st.title("🌐 Portail Collectif - Enolou")

    if not url_session:
        st.info("💡 Veuillez scanner le QR code fourni par votre professeur pour rejoindre une session collective.")
        code_saisi = st.text_input("Ou entrez l'identifiant de la session (ex: sess_1725800000) :")
        if code_saisi:
            st.query_params["session"] = code_saisi
            st.rerun()
    else:
        chemin_sess = os.path.join(DOSSIER_SESSIONS, f"{url_session}.json")
        if not os.path.exists(chemin_sess):
            st.error("❌ Session introuvable ou terminée.")
        else:
            with open(chemin_sess, 'r', encoding='utf-8') as f:
                sess_data = json.load(f)

            quiz_info = sess_data.get("quiz_info", {})
            mode_sess = sess_data.get("mode", "battle")
            status_sess = sess_data.get("status", "waiting")
            titre_quiz = quiz_info.get("titre", "Quiz Collectif")
            vol_musique = quiz_info.get('volume_musique', 0.5)
            vol_sons = quiz_info.get('volume_sons', 0.8)

            st.subheader(f"Session : {titre_quiz} (Mode : {mode_sess.upper()})")

            if 'collec_student_name' not in st.session_state:
                st.session_state.collec_student_name = ""

            if not st.session_state.collec_student_name:
                st.markdown("### ✍️ Inscription à la session")
                nom_etudiant = st.text_input("Entrez votre Prénom et Nom :")
                if st.button("S'inscrire et rejoindre le salon", type="primary"):
                    if nom_etudiant.strip():
                        st.session_state.collec_student_name = nom_etudiant.strip()
                        if nom_etudiant.strip() not in sess_data["students"]:
                            indices_questions = list(range(len(sess_data["questions"])))
                            if mode_sess == "examen":
                                random.seed(nom_etudiant.strip())
                                random.shuffle(indices_questions)

                            sess_data["students"][nom_etudiant.strip()] = {
                                "name": nom_etudiant.strip(),
                                "score": 0,
                                "max_points": sum([q.get("points", 10) for q in sess_data["questions"]]),
                                "current_idx": 0,
                                "answered": False,
                                "last_result": None,
                                "finished": False,
                                "question_order": indices_questions,
                                "answers_detail": []
                            }
                            with open(chemin_sess, 'w', encoding='utf-8') as f:
                                json.dump(sess_data, f, ensure_ascii=False, indent=4)
                        st.rerun()
                    else:
                        st.warning("Veuillez entrer un nom valide.")
            else:
                musique_path = quiz_info.get('musique')
                son_declenche = st.session_state.get("declencher_son")
                son_path = quiz_info.get('son_good') if son_declenche == "good" else quiz_info.get('son_bad')
                
                if status_sess == "started":
                    rendre_moteur_audio(musique_path, vol_musique, son_declenche, son_path, vol_sons)
                    if st.session_state.get("declencher_son"):
                        st.session_state.declencher_son = None

                @st.fragment(run_every=2)
                def rendu_session_etudiant():
                    if not os.path.exists(chemin_sess):
                        st.error("Session supprimée.")
                        return
                    with open(chemin_sess, 'r', encoding='utf-8') as f:
                        current_sess_data = json.load(f)
                    
                    cur_status = current_sess_data.get("status", "waiting")
                    s_info = current_sess_data["students"].get(st.session_state.collec_student_name, {})

                    st.write(f"Connecté en tant que : **{st.session_state.collec_student_name}**")

                    if cur_status == "waiting":
                        st.info("⏳ En attente du lancement par le professeur...")
                        if st.button("🔄 Actualiser"):
                            st.rerun()

                    elif cur_status == "ended":
                        st.warning("🛑 Cette session est maintenant terminée.")
                        st.markdown(f"### Votre Score final : {s_info.get('score', 0)} / {s_info.get('max_points', 0)}")

                    elif cur_status == "started":
                        questions_list = current_sess_data["questions"]

                        if mode_sess == "battle":
                            current_global_idx = current_sess_data.get("current_global_idx", 0)
                            in_transition = current_sess_data.get("in_transition", False)

                            if in_transition:
                                trans_start = current_sess_data.get("transition_start_time", time.time())
                                elapsed_trans = time.time() - trans_start
                                remaining_trans = max(0, 5 - int(elapsed_trans))

                                if remaining_trans == 0:
                                    current_sess_data["current_global_idx"] += 1
                                    current_sess_data["in_transition"] = False
                                    if current_sess_data["current_global_idx"] >= len(questions_list):
                                        current_sess_data["status"] = "ended"
                                    else:
                                        current_sess_data["question_start_time"] = time.time()
                                        for s_name in current_sess_data["students"]:
                                            current_sess_data["students"][s_name]["answered_current"] = False
                                            current_sess_data["students"][s_name]["last_result"] = None
                                    with open(chemin_sess, 'w', encoding='utf-8') as f:
                                        json.dump(current_sess_data, f, ensure_ascii=False, indent=4)
                                    st.rerun()
                                else:
                                    st.info(f"⏸️ Fin de la manche ! Question suivante dans **{remaining_trans} secondes**...")
                            else:
                                if current_global_idx >= len(questions_list):
                                    s_info["finished"] = True
                                    current_sess_data["students"][st.session_state.collec_student_name] = s_info
                                    with open(chemin_sess, 'w', encoding='utf-8') as f:
                                        json.dump(current_sess_data, f, ensure_ascii=False, indent=4)
                                    st.balloons()
                                    st.success("🎉 Battle terminée !")
                                    st.markdown(f"### 🏆 Score : {s_info['score']} / {s_info['max_points']} pts")
                                else:
                                    q = questions_list[current_global_idx]
                                    consigne = q.get('consigne', '')
                                    points = q.get('points', 10)
                                    timer_sec = q.get('timer_secondes', 30)
                                    options = q.get('donnees', {}).get('options', [])
                                    reponses_correctes = q.get('donnees', {}).get('reponses_correctes', [])
                                    est_multiple = len(reponses_correctes) > 1

                                    q_start = current_sess_data.get("question_start_time", time.time())
                                    elapsed_q = int(time.time() - q_start)
                                    temps_restant = max(0, timer_sec - elapsed_q)

                                    all_answered = True
                                    if len(current_sess_data["students"]) > 0:
                                        for student_item in current_sess_data["students"].values():
                                            if not student_item.get("answered_current", False):
                                                all_answered = False
                                                break
                                    else:
                                        all_answered = False

                                    if temps_restant == 0 or all_answered:
                                        current_sess_data["in_transition"] = True
                                        current_sess_data["transition_start_time"] = time.time()
                                        with open(chemin_sess, 'w', encoding='utf-8') as f:
                                            json.dump(current_sess_data, f, ensure_ascii=False, indent=4)
                                        st.rerun()

                                    st.subheader(f"⚡ Question {current_global_idx + 1} sur {len(questions_list)} (Mode Battle)")
                                    
                                    if est_multiple:
                                        st.markdown("🔷 **Type :** *Plusieurs réponses possibles (Cochez toutes les options correctes)*")
                                    else:
                                        st.markdown("🔸 **Type :** *Réponse unique (Choisissez une seule option)*")

                                    st.markdown(f"""
                                    <div style="font-size: 1.1rem; font-weight: bold; color: #ff4b4b; margin-bottom: 10px; background-color: #ffe6e6; padding: 10px 15px; border-radius: 6px;">
                                        ⏱️ Temps restant : {temps_restant} secondes
                                    </div>
                                    """, unsafe_allow_html=True)

                                    st.markdown(f"**{consigne}**")
                                    already_answered = s_info.get("answered_current", False)

                                    if est_multiple:
                                        choix = []
                                        for opt_idx, opt in enumerate(options):
                                            if st.checkbox(opt, key=f"battle_m_{current_global_idx}_{opt_idx}", disabled=already_answered):
                                                choix.append(opt)
                                    else:
                                        choix = st.radio("Sélectionnez votre réponse :", options, key=f"battle_r_{current_global_idx}", index=None, disabled=already_answered)

                                    if not already_answered:
                                        if st.button("Valider la réponse", type="primary"):
                                            if not choix:
                                                st.warning("Veuillez sélectionner au moins une option.")
                                            else:
                                                if est_multiple:
                                                    est_correct = set(choix) == set(reponses_correctes)
                                                else:
                                                    est_correct = choix in reponses_correctes
                                                
                                                points_gagnes = 0
                                                if est_correct:
                                                    ratio_temps = (timer_sec - elapsed_q) / timer_sec if timer_sec > 0 else 1
                                                    points_gagnes = int(points * (0.5 + 0.5 * max(0, ratio_temps)))
                                                    res_msg = f"Bonne réponse rapide ! +{points_gagnes} pts ⚡"
                                                    res_type = "success"
                                                    st.session_state.declencher_son = "good"
                                                else:
                                                    res_msg = "Mauvaise réponse ❌"
                                                    res_type = "error"
                                                    st.session_state.declencher_son = "bad"

                                                s_info["score"] += points_gagnes
                                                s_info["answered_current"] = True
                                                s_info["last_result"] = (res_type, res_msg)
                                                s_info["answers_detail"].append({
                                                    "q_num": current_global_idx + 1,
                                                    "consigne": consigne,
                                                    "reponse": choix,
                                                    "correct": est_correct,
                                                    "points": points_gagnes
                                                })

                                                current_sess_data["students"][st.session_state.collec_student_name] = s_info
                                                with open(chemin_sess, 'w', encoding='utf-8') as f:
                                                    json.dump(current_sess_data, f, ensure_ascii=False, indent=4)
                                                st.rerun()
                                    else:
                                        res_type, res_msg = s_info.get("last_result", ("info", "Réponse enregistrée."))
                                        if res_type == "success":
                                            st.success(res_msg)
                                        else:
                                            st.error(res_msg)
                                        st.info("⏳ En attente des autres participants pour la question suivante...")

                        else:
                            question_order = s_info.get("question_order", list(range(len(questions_list))))
                            current_idx_student = s_info.get("current_idx", 0)

                            if current_idx_student < len(question_order):
                                reel_idx = question_order[current_idx_student]
                                q = questions_list[reel_idx]
                                
                                consigne = q.get('consigne', '')
                                points = q.get('points', 10)
                                timer_sec = q.get('timer_secondes', 30)
                                options = q.get('donnees', {}).get('options', [])
                                reponses_correctes = q.get('donnees', {}).get('reponses_correctes', [])
                                est_multiple = len(reponses_correctes) > 1

                                st.subheader(f"Question {current_idx_student + 1} sur {len(questions_list)} (Mode Examen)")
                                
                                if est_multiple:
                                    st.markdown("🔷 **Type :** *Plusieurs réponses possibles (Cochez toutes les options correctes)*")
                                else:
                                    st.markdown("🔸 **Type :** *Réponse unique (Choisissez une seule option)*")

                                st.markdown(f"**{consigne}**")

                                already_answered = s_info.get("answered", False)
                                if est_multiple:
                                    choix = []
                                    for opt_idx, opt in enumerate(options):
                                        if st.checkbox(opt, key=f"ex_m_{current_idx_student}_{opt_idx}", disabled=already_answered):
                                            choix.append(opt)
                                else:
                                    choix = st.radio("Sélectionnez votre réponse :", options, key=f"examen_r_{current_idx_student}", index=None, disabled=already_answered)

                                if not already_answered:
                                    if st.button("Valider la réponse", type="primary"):
                                        if not choix:
                                            st.warning("Veuillez sélectionner au moins une option.")
                                        else:
                                            if est_multiple:
                                                est_correct = set(choix) == set(reponses_correctes)
                                            else:
                                                est_correct = choix in reponses_correctes
                                            
                                            points_gagnes = points if est_correct else 0

                                            if est_correct:
                                                s_info["last_result"] = ("success", f"Réponse enregistrée (+{points} pts) ✅")
                                                st.session_state.declencher_son = "good"
                                            else:
                                                s_info["last_result"] = ("error", "Réponse enregistrée ❌")
                                                st.session_state.declencher_son = "bad"

                                            s_info["score"] += points_gagnes
                                            s_info["answered"] = True
                                            s_info["answers_detail"].append({
                                                "q_num": current_idx_student + 1,
                                                "consigne": consigne,
                                                "reponse": choix,
                                                "correct": est_correct,
                                                "points": points_gagnes
                                            })

                                            current_sess_data["students"][st.session_state.collec_student_name] = s_info
                                            with open(chemin_sess, 'w', encoding='utf-8') as f:
                                                json.dump(current_sess_data, f, ensure_ascii=False, indent=4)
                                            st.rerun()
                                else:
                                    res_type, res_msg = s_info.get("last_result", ("info", ""))
                                    if res_type == "success":
                                        st.success(res_msg)
                                    else:
                                        st.error(res_msg)

                                    if st.button("Question suivante ➡️", type="primary"):
                                        s_info["current_idx"] += 1
                                        s_info["answered"] = False
                                        s_info["last_result"] = None
                                        current_sess_data["students"][st.session_state.collec_student_name] = s_info
                                        with open(chemin_sess, 'w', encoding='utf-8') as f:
                                            json.dump(current_sess_data, f, ensure_ascii=False, indent=4)
                                        st.rerun()
                            else:
                                s_info["finished"] = True
                                current_sess_data["students"][st.session_state.collec_student_name] = s_info
                                with open(chemin_sess, 'w', encoding='utf-8') as f:
                                    json.dump(current_sess_data, f, ensure_ascii=False, indent=4)

                                st.balloons()
                                st.success("🎉 Vous avez terminé l'examen !")
                                st.markdown(f"### 🏆 Votre Score : {s_info['score']} / {s_info['max_points']} points")
                                st.info("Vos résultats ont été enregistrés et transmis au professeur.")

                rendu_session_etudiant()

# ==========================================
# 👨‍🎓 ESPACE ÉTUDIANT : MODE SOLO
# ==========================================
else:
    if not st.session_state.qcm_selectionne:
        st.title("🎓 Portail des Évaluations - Enolou")
        st.warning("🔒 **Accès restreint :** Veuillez scanner le QR code fourni par votre professeur pour accéder à votre QCM en mode Solo.")
    else:
        quiz_info = st.session_state.banque.get('quiz_info', {})
        questions = st.session_state.banque.get('questions', [])
        titre = quiz_info.get('titre', 'Évaluation QCM')
        description = quiz_info.get('description', '')
        vol_musique = quiz_info.get('volume_musique', 0.5)
        vol_sons = quiz_info.get('volume_sons', 0.8)

        musique_path = quiz_info.get('musique')
        son_declenche = st.session_state.get("declencher_son")
        son_path = quiz_info.get('son_good') if son_declenche == "good" else quiz_info.get('son_bad')

        if st.session_state.quiz_started:
            rendre_moteur_audio(musique_path, vol_musique, son_declenche, son_path, vol_sons)
            if st.session_state.get("declencher_son"):
                st.session_state.declencher_son = None

        st.title(f"🎓 {titre}")

        if not st.session_state.quiz_started:
            if description:
                st.write(description)
            
            img_gen = quiz_info.get('image')
            if img_gen and os.path.exists(img_gen):
                st.image(img_gen, use_container_width=True)
            vid_gen = quiz_info.get('video')
            if vid_gen and os.path.exists(vid_gen):
                st.video(vid_gen)

            st.info("💡 Cliquez ci-dessous pour démarrer l'évaluation (active la musique de fond et les effets sonores).")
            if st.button("Commencer le QCM 🎵", type="primary"):
                st.session_state.quiz_started = True
                st.session_state.question_start_time = time.time()
                st.rerun()
        else:
            if st.session_state.current_idx < len(questions):
                q = questions[st.session_state.current_idx]
                q_id = st.session_state.current_idx
                consigne = q.get('consigne', '')
                points = q.get('points', 10)
                timer_sec = q.get('timer_secondes', 30)
                options = q.get('donnees', {}).get('options', [])
                reponses_correctes = q.get('donnees', {}).get('reponses_correctes', [])
                est_multiple = len(reponses_correctes) > 1
                
                col_docs, col_qcm = st.columns([3, 2], gap="large")

                with col_docs:
                    st.markdown("### 📄 Documents de référence")
                    doc_texte = q.get('document_texte')
                    if doc_texte:
                        st.info(doc_texte)
                    
                    img_path = q.get('media', {}).get('image') or quiz_info.get('image')
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)
                    
                    vid_path = q.get('media', {}).get('video') or quiz_info.get('video')
                    if vid_path and os.path.exists(vid_path):
                        st.video(vid_path)

                with col_qcm:
                    st.subheader(f"Question {q_id + 1} sur {len(questions)}")
                    
                    if est_multiple:
                        st.markdown("🔷 **Type :** *Plusieurs réponses possibles (Cochez toutes les options correctes)*")
                    else:
                        st.markdown("🔸 **Type :** *Réponse unique (Choisissez une seule option)*")

                    st.caption(f"🏆 Valeur : {points} pts")
                    
                    temps_ecoule = int(time.time() - st.session_state.question_start_time)
                    temps_restant_initial = max(0, timer_sec - temps_ecoule)
                    
                    components.html(f"""
                    <div style="font-size: 1.1rem; font-weight: bold; color: #ff4b4b; margin-bottom: 10px; background-color: #ffe6e6; padding: 10px 15px; border-radius: 6px; border-left: 5px solid #ff4b4b; font-family: sans-serif;">
                        ⏱️ Temps restant : <span id="countdown_timer">{temps_restant_initial}</span> secondes
                    </div>
                    <script>
                        let timeLeft = {temps_restant_initial};
                        const timerElem = document.getElementById('countdown_timer');
                        if (timerElem) {{
                            const timerId = setInterval(() => {{
                                if (timeLeft > 0) {{
                                    timeLeft--;
                                    timerElem.innerText = timeLeft;
                                }} else {{
                                    clearInterval(timerId);
                                }}
                            }}, 1000);
                        }}
                    </script>
                    """, height=55)

                    st.markdown(f"**{consigne}**")

                    if est_multiple:
                        choix = []
                        for opt_idx, opt in enumerate(options):
                            if st.checkbox(opt, key=f"solo_m_{q_id}_{opt_idx}", disabled=st.session_state.answered):
                                choix.append(opt)
                    else:
                        choix = st.radio("Sélectionnez votre réponse :", options, key=f"radio_q_{q_id}", index=None, disabled=st.session_state.answered)

                    if not st.session_state.answered:
                        if st.button("Valider la réponse", type="primary"):
                            if not choix:
                                st.warning("Veuillez sélectionner au moins une option.")
                            else:
                                elapsed = time.time() - st.session_state.question_start_time
                                
                                if est_multiple:
                                    est_correct = set(choix) == set(reponses_correctes)
                                else:
                                    est_correct = choix in reponses_correctes

                                points_gagnes = 0

                                if est_correct:
                                    if elapsed <= timer_sec:
                                        points_gagnes = points
                                        st.session_state.last_result = ("success", f"Bonne réponse ! +{points} pts 🎉")
                                    else:
                                        points_gagnes = points // 2
                                        st.session_state.last_result = ("warning", f"Bonne réponse mais hors temps. +{points_gagnes} pts ⏱️")
                                    st.session_state.declencher_son = "good"
                                else:
                                    st.session_state.last_result = ("error", "Mauvaise réponse ❌")
                                    st.session_state.declencher_son = "bad"

                                st.session_state.score_total += points_gagnes
                                st.session_state.max_points += points
                                st.session_state.answered = True
                                st.rerun()
                    else:
                        res_type, res_msg = st.session_state.last_result
                        if res_type == "success":
                            st.success(res_msg)
                        elif res_type == "warning":
                            st.warning(res_msg)
                        else:
                            st.error(res_msg)

                        explication = q.get('explication', '')
                        if explication:
                            st.caption(f"💡 *Explication : {explication}*")

                        if st.button("Question suivante ➡️", type="primary"):
                            st.session_state.current_idx += 1
                            st.session_state.answered = False
                            st.session_state.last_result = None
                            st.session_state.question_start_time = time.time()
                            st.rerun()
            else:
                st.balloons()
                st.success("🎉 Évaluation terminée avec succès !")
                st.markdown(f"### 🏆 Score Final : {st.session_state.score_total} / {st.session_state.max_points} points")
                if st.button("Recommencer ce QCM"):
                    st.session_state.current_idx = 0
                    st.session_state.score_total = 0
                    st.session_state.max_points = 0
                    st.session_state.quiz_started = False
                    st.session_state.answered = False
                    st.session_state.last_result = None
                    st.session_state.declencher_son = None
                    st.rerun()