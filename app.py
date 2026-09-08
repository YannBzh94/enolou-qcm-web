import os
import json
import random
import streamlit as st
import streamlit.components.v1 as components
import time
import qrcode
import base64
import requests
from io import BytesIO

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

# --- FONCTIONS AUDIO INDÉPENDANTES ET PERSISTANTES ---
def jouer_musique_fond(chemin, volume=0.5):
    if chemin and os.path.exists(chemin):
        ext = chemin.strip().lower().split('.')[-1]
        mime_map = {'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'ogg': 'audio/ogg', 'm4a': 'audio/mp4', 'aac': 'audio/aac'}
        mime_type = mime_map.get(ext, 'audio/mpeg')
        
        if 'music_active_path' not in st.session_state or st.session_state.music_active_path != chemin:
            st.session_state.music_active_path = chemin
            st.audio(chemin, format=mime_type, autoplay=True, loop=True)
        
        st.markdown(f"""
        <script>
            setTimeout(() => {{
                const audios = document.querySelectorAll('audio');
                if (audios.length > 0) {{
                    audios[0].volume = {volume};
                }}
            }}, 100);
        </script>
        """, unsafe_allow_html=True)

def jouer_effet_sonore(chemin, volume=0.8):
    if chemin and os.path.exists(chemin):
        ext = chemin.strip().lower().split('.')[-1]
        mime_map = {'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'ogg': 'audio/ogg', 'm4a': 'audio/mp4', 'aac': 'audio/aac'}
        mime_type = mime_map.get(ext, 'audio/mpeg')
        
        st.audio(chemin, format=mime_type, autoplay=True, loop=False)
        
        st.markdown(f"""
        <script>
            setTimeout(() => {{
                const audios = document.querySelectorAll('audio');
                if (audios.length > 0) {{
                    const sfx = audios[audios.length - 1];
                    sfx.volume = {volume};
                }}
            }}, 100);
        </script>
        """, unsafe_allow_html=True)

# --- GESTION DES URLS (QR Code Solo ou Session Collective) ---
query_params = st.query_params
url_qcm = query_params.get("qcm")
url_session = query_params.get("session")

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

# Aiguillage automatique de l'index du menu selon l'URL scannée
default_mode_idx = 0
if url_session:
    default_mode_idx = 1

# --- NAVIGATION GLOBALE (Sidebar) ---
st.sidebar.title("🧭 Navigation")
mode = st.sidebar.radio("Choisissez le mode :", [
    "👨‍🎓 Espace Étudiant (Solo)", 
    "🌐 Espace Collectif (Rejoindre une session)", 
    "👨‍🏫 Espace Professeur"
], index=default_mode_idx)

if mode == "👨‍🎓 Espace Étudiant (Solo)":
    if 'music_active_path' in st.session_state:
        del st.session_state.music_active_path

if 'qcm_selectionne' not in st.session_state:
    st.session_state.qcm_selectionne = None

# ==========================================
# 👨‍🏫 ESPACE PROFESSEUR (Édition + Sessions Collectives)
# ==========================================
if mode == "👨‍🏫 Espace Professeur":
    st.title("👨‍🏫 Espace Professeur - Gestion & Sessions Collectives")
    
    tab_gen, tab_sess = st.tabs(["📝 Éditeur & QR Codes Solo", "🌐 Gestion des Sessions Collectives"])

    fichiers_existants = [f for f in os.listdir(DOSSIER_QUIZZES) if f.endswith('.json')]

    with tab_sess:
        st.subheader("Lancer un Quiz en mode Collectif (Battle ou Examen)")
        if fichiers_existants:
            qcm_collectif = st.selectbox("Sélectionnez le QCM pour la session collective :", fichiers_existants, key="sel_collec_qcm")
            type_mode_collec = st.radio("Mode de session :", [
                "🎮 Mode Battle (Classement en direct, rapidité & podium final + cuillère de bois)", 
                "📝 Mode Examen (Questions aléatoires par étudiant & stockage des notes)"
            ], key="type_mode_collec")

            domaine_app = st.text_input(
                "URL de votre application déployée :", 
                value="https://yannbzh94-enolou-qcm-web-app-ngwrt8.streamlit.app/",
                key="domaine_app_collec"
            )

            if st.button("🚀 Créer / Ouvrir la session collective", type="primary"):
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
                    "quiz_info": qcm_data.get("quiz_info", {}),
                    "questions": qcm_data.get("questions", []),
                    "students": {}
                }
                
                with open(os.path.join(DOSSIER_SESSIONS, f"{session_id}.json"), 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=4)
                
                st.session_state.active_teacher_session = session_id
                st.rerun()

            sessions_existantes = [f.replace('.json', '') for f in os.listdir(DOSSIER_SESSIONS) if f.endswith('.json')]
            if sessions_existantes:
                st.markdown("---")
                st.markdown("### 📊 Suivi des Sessions Actives")
                sess_choisie = st.selectbox("Sélectionnez une session à piloter :", sessions_existantes)
                
                chemin_sess = os.path.join(DOSSIER_SESSIONS, f"{sess_choisie}.json")
                if os.path.exists(chemin_sess):
                    with open(chemin_sess, 'r', encoding='utf-8') as f:
                        s_data = json.load(f)
                    
                    url_session_complete = f"{domaine_app.strip('/')}/?session={sess_choisie}"
                    st.write(f"**Lien de connexion pour les étudiants :** [{url_session_complete}]({url_session_complete})")
                    
                    img_qr = qrcode.make(url_session_complete)
                    buffered = BytesIO()
                    img_qr.save(buffered, format="PNG")
                    st.image(buffered.getvalue(), caption=f"QR Code Session : {s_data['quiz_info'].get('titre', '')}", width=220)

                    st.markdown(f"**Mode :** `{s_data['mode'].upper()}` | **Statut actuel :** `{s_data['status'].upper()}`")
                    
                    etudiants = s_data.get("students", {})
                    st.markdown(f"#### 👥 Étudiants inscrits ({len(etudiants)}) :")
                    if etudiants:
                        noms_inscrits = list(etudiants.keys())
                        st.success(", ".join(noms_inscrits))
                    else:
                        st.info("En attente d'inscription des étudiants...")

                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button("🔄 Rafraîchir la liste"):
                            st.rerun()
                    with col_btn2:
                        if s_data["status"] == "waiting" and st.button("▶️ Démarrer la session pour tous", type="primary"):
                            s_data["status"] = "started"
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
                        st.markdown("### 🏆 Résultats en direct / finaux")
                        if etudiants:
                            table_resultats = []
                            for nom, info in etudiants.items():
                                table_resultats.append({
                                    "Nom": nom,
                                    "Score": info.get("score", 0),
                                    "Total Max": info.get("max_points", 0),
                                    "Statut": "Terminé ✅" if info.get("finished", False) else "En cours ⏱️"
                                })
                            st.table(table_resultats)

                            if s_data["mode"] == "battle":
                                finis = [info for info in etudiants.values() if info.get("finished", False)]
                                if finis:
                                    finis_tries = sorted(finis, key=lambda x: x["score"], reverse=True)
                                    st.markdown("---")
                                    st.markdown("### 🥇 PODIUM BATTLE & CUILLÈRE DE BOIS")
                                    if len(finis_tries) >= 1:
                                        st.markdown(f"**🥇 1er :** {finis_tries[0]['name']} ({finis_tries[0]['score']} pts)")
                                    if len(finis_tries) >= 2:
                                        st.markdown(f"**🥈 2ème :** {finis_tries[1]['name']} ({finis_tries[1]['score']} pts)")
                                    if len(finis_tries) >= 3:
                                        st.markdown(f"**🥉 3ème :** {finis_tries[2]['name']} ({finis_tries[2]['score']} pts)")
                                    if len(finis_tries) >= 4:
                                        dernier = finis_tries[-1]
                                        st.markdown(f"**🥄 Cuillère de bois :** {dernier['name']} ({dernier['score']} pts) - Courage pour la prochaine ! 💪")

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

        choix_edition = st.selectbox("Éditer un QCM existant :", ["-- Créer un nouveau QCM --"] + fichiers_existants)
        if 'edit_nom_fichier' not in st.session_state:
            st.session_state.edit_nom_fichier = "nouveau_qcm.json"
            st.session_state.edit_titre = ""
            st.session_state.edit_desc = ""
            st.session_state.edit_musique = ""
            st.session_state.edit_vol_musique = 0.5
            st.session_state.edit_son_good = ""
            st.session_state.edit_son_bad = ""
            st.session_state.edit_vol_sons = 0.8
            st.session_state.edit_questions = []
            st.session_state.edit_q_index = None
            st.session_state.dernier_choix_edition = None

        if choix_edition != st.session_state.dernier_choix_edition:
            st.session_state.dernier_choix_edition = choix_edition
            st.session_state.edit_q_index = None
            if choix_edition == "-- Créer un nouveau QCM --":
                st.session_state.edit_nom_fichier = "nouveau_qcm.json"
                st.session_state.edit_titre = "Mon Nouveau Quiz"
                st.session_state.edit_desc = ""
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
                        st.session_state.edit_questions = data.get("questions", [])
                except Exception:
                    pass

        with st.form("form_edition_qcm"):
            nom_fichier = st.text_input("Nom du fichier JSON :", value=st.session_state.edit_nom_fichier)
            titre_quiz = st.text_input("Titre affiché :", value=st.session_state.edit_titre)
            desc_quiz = st.text_area("Description :", value=st.session_state.edit_desc)
            submitted_meta = st.form_submit_button("💾 Enregistrer les paramètres généraux")
            if submitted_meta:
                if not nom_fichier.endswith(".json"):
                    nom_fichier += ".json"
                donnees_globales = {
                    "quiz_info": {"titre": titre_quiz, "description": desc_quiz},
                    "questions": st.session_state.edit_questions
                }
                contenu_json = json.dumps(donnees_globales, ensure_ascii=False, indent=4)
                with open(os.path.join(DOSSIER_QUIZZES, nom_fichier), "w", encoding="utf-8") as f:
                    f.write(contenu_json)
                sauvegarder_fichier_github(f"QCM/{nom_fichier}", contenu_json)
                st.success("Paramètres enregistrés !")

        st.subheader("Gestion des questions")
        if st.session_state.edit_questions:
            for idx, q in enumerate(st.session_state.edit_questions):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.text(f"Q{idx+1}: {q.get('consigne', '')[:50]}...")
                with col2:
                    if st.button("❌", key=f"del_q_{idx}"):
                        st.session_state.edit_questions.pop(idx)
                        st.rerun()

        with st.form("form_ajout_question"):
            consigne_q = st.text_area("Consigne :")
            points_q = st.number_input("Points :", min_value=1, value=10)
            timer_q = st.number_input("Chronomètre (secondes) :", min_value=5, value=30)
            options_input = st.text_area("Options (une par ligne) :")
            reponse_correcte = st.text_input("Réponse exacte :")
            explication_q = st.text_area("Explication :")
            submitted_q = st.form_submit_button("➕ Ajouter la question")
            if submitted_q:
                options_liste = [opt.strip() for opt in options_input.split("\n") if opt.strip()]
                if consigne_q and options_liste and reponse_correcte:
                    nouv_q = {
                        "id": len(st.session_state.edit_questions) + 1,
                        "consigne": consigne_q,
                        "type": "qcm",
                        "points": points_q,
                        "timer_secondes": timer_q,
                        "donnees": {"options": options_liste, "reponses_correctes": [reponse_correcte]},
                        "explication": explication_q,
                        "document_texte": "",
                        "media": {"image": ""},
                        "document_appui": ""
                    }
                    st.session_state.edit_questions.append(nouv_q)
                    donnees_globales = {
                        "quiz_info": {"titre": st.session_state.edit_titre, "description": st.session_state.edit_desc},
                        "questions": st.session_state.edit_questions
                    }
                    contenu_json = json.dumps(donnees_globales, ensure_ascii=False, indent=4)
                    with open(os.path.join(DOSSIER_QUIZZES, st.session_state.edit_nom_fichier), "w", encoding="utf-8") as f:
                        f.write(contenu_json)
                    sauvegarder_fichier_github(f"QCM/{st.session_state.edit_nom_fichier}", contenu_json)
                    st.success("Question ajoutée !")
                    st.rerun()

# ==========================================
# 🌐 ESPACE COLLECTIF : REJOINDRE UNE SESSION (ÉTUDIANT)
# ==========================================
elif mode == "🌐 Espace Collectif (Rejoindre une session)":
    st.title("🌐 Portail Collectif - Enolou")

    if not url_session:
        st.info("💡 Veuillez utiliser le lien ou scanner le QR code fourni par votre professeur pour rejoindre une session collective (Battle ou Examen).")
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
                                "question_start_time": time.time()
                            }
                            with open(chemin_sess, 'w', encoding='utf-8') as f:
                                json.dump(sess_data, f, ensure_ascii=False, indent=4)
                        st.rerun()
                    else:
                        st.warning("Veuillez entrer un nom valide.")
            else:
                with open(chemin_sess, 'r', encoding='utf-8') as f:
                    sess_data = json.load(f)
                status_sess = sess_data.get("status", "waiting")
                student_info = sess_data["students"].get(st.session_state.collec_student_name, {})

                st.write(f"Connecté en tant que : **{st.session_state.collec_student_name}**")

                if status_sess == "waiting":
                    st.info("⏳ En attente du lancement de la session par le professeur...")
                    if st.button("🔄 Actualiser le statut"):
                        st.rerun()
                elif status_sess == "ended":
                    st.warning("🛑 Cette session est maintenant terminée par le professeur.")
                    st.markdown(f"### Votre Score final : {student_info.get('score', 0)} / {student_info.get('max_points', 0)}")
                elif status_sess == "started":
                    questions_list = sess_data["questions"]
                    question_order = student_info.get("question_order", list(range(len(questions_list))))
                    current_idx_student = student_info.get("current_idx", 0)

                    if current_idx_student < len(question_order):
                        reel_idx = question_order[current_idx_student]
                        q = questions_list[reel_idx]
                        
                        consigne = q.get('consigne', '')
                        points = q.get('points', 10)
                        timer_sec = q.get('timer_secondes', 30)
                        options = q.get('donnees', {}).get('options', [])

                        st.subheader(f"Question {current_idx_student + 1} sur {len(questions_list)}")
                        st.caption(f"🏆 Valeur de base : {points} pts ({'Mode Battle (Rapidité)' if mode_sess=='battle' else 'Mode Examen'})")

                        if "q_start_time" not in st.session_state:
                            st.session_state.q_start_time = time.time()

                        temps_ecoule = int(time.time() - st.session_state.q_start_time)
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
                        choix = st.radio("Sélectionnez votre réponse :", options, key=f"collec_radio_{current_idx_student}", index=None, disabled=student_info.get("answered", False))

                        if not student_info.get("answered", False):
                            if st.button("Valider la réponse", type="primary"):
                                if choix is None:
                                    st.warning("Veuillez sélectionner une option.")
                                else:
                                    elapsed = time.time() - st.session_state.q_start_time
                                    reponses_correctes = q.get('donnees', {}).get('reponses_correctes', [])
                                    est_correct = choix in reponses_correctes

                                    points_gagnes = 0
                                    if est_correct:
                                        if mode_sess == "battle":
                                            if elapsed <= timer_sec:
                                                ratio_temps = (timer_sec - elapsed) / timer_sec
                                                points_gagnes = int(points * (0.5 + 0.5 * ratio_temps))
                                                msg = f"Bonne réponse rapide ! +{points_gagnes} pts ⚡"
                                            else:
                                                points_gagnes = points // 2
                                                msg = f"Bonne réponse mais hors temps (+{points_gagnes} pts) ⏱️"
                                        else:
                                            points_gagnes = points
                                            msg = f"Réponse enregistrée (+{points} pts) ✅"
                                        student_info["last_result"] = ("success", msg)
                                    else:
                                        student_info["last_result"] = ("error", "Mauvaise réponse ❌")

                                    student_info["score"] += points_gagnes
                                    student_info["answered"] = True
                                    
                                    sess_data["students"][st.session_state.collec_student_name] = student_info
                                    with open(chemin_sess, 'w', encoding='utf-8') as f:
                                        json.dump(sess_data, f, ensure_ascii=False, indent=4)
                                    st.rerun()
                        else:
                            res_type, res_msg = student_info.get("last_result", ("info", ""))
                            if res_type == "success":
                                st.success(res_msg)
                            else:
                                st.error(res_msg)

                            explication = q.get('explication', '')
                            if explication:
                                st.caption(f"💡 *Explication : {explication}*")

                            if st.button("Question suivante ➡️", type="primary"):
                                student_info["current_idx"] += 1
                                student_info["answered"] = False
                                student_info["last_result"] = None
                                if "q_start_time" in st.session_state:
                                    del st.session_state.q_start_time
                                
                                sess_data["students"][st.session_state.collec_student_name] = student_info
                                with open(chemin_sess, 'w', encoding='utf-8') as f:
                                    json.dump(sess_data, f, ensure_ascii=False, indent=4)
                                st.rerun()
                    else:
                        student_info["finished"] = True
                        sess_data["students"][st.session_state.collec_student_name] = student_info
                        with open(chemin_sess, 'w', encoding='utf-8') as f:
                            json.dump(sess_data, f, ensure_ascii=False, indent=4)

                        st.balloons()
                        st.success("🎉 Vous avez terminé l'évaluation collective !")
                        st.markdown(f"### 🏆 Votre Score : {student_info['score']} / {student_info['max_points']} points")
                        st.info("Attendez que le professeur clôture la session pour découvrir le classement final.")

# ==========================================
# 👨‍🎓 ESPACE ÉTUDIANT : MODE SOLO (Standard)
# ==========================================
else:
    if not st.session_state.qcm_selectionne:
        st.title("🎓 Portail des Évaluations - Enolou")
        st.warning("🔒 **Accès restreint :** Veuillez scanner le QR code ou utiliser le lien direct fourni par votre professeur pour accéder à votre QCM en mode Solo.")
    else:
        quiz_info = st.session_state.banque.get('quiz_info', {})
        questions = st.session_state.banque.get('questions', [])
        titre = quiz_info.get('titre', 'Évaluation QCM')
        description = quiz_info.get('description', '')
        vol_musique = quiz_info.get('volume_musique', 0.5)
        vol_sons = quiz_info.get('volume_sons', 0.8)

        st.title(f"🎓 {titre}")

        if not st.session_state.quiz_started:
            if description:
                st.write(description)
            st.info("💡 Cliquez sur le bouton ci-dessous pour démarrer l'évaluation (active la musique de fond et les effets sonores).")
            if st.button("Commencer le QCM 🎵", type="primary"):
                st.session_state.quiz_started = True
                st.session_state.question_start_time = time.time()
                st.rerun()
        else:
            musique_path = quiz_info.get('musique')
            if musique_path and os.path.exists(musique_path):
                jouer_musique_fond(musique_path, vol_musique)

            if st.session_state.current_idx < len(questions):
                q = questions[st.session_state.current_idx]
                q_id = st.session_state.current_idx
                consigne = q.get('consigne', '')
                points = q.get('points', 10)
                timer_sec = q.get('timer_secondes', 30)
                options = q.get('donnees', {}).get('options', [])
                
                col_docs, col_qcm = st.columns([3, 2], gap="large")

                with col_docs:
                    st.markdown("### 📄 Documents de référence")
                    doc_texte = q.get('document_texte')
                    if doc_texte:
                        st.info(doc_texte)
                    img_path = q.get('media', {}).get('image')
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)

                with col_qcm:
                    st.subheader(f"Question {q_id + 1} sur {len(questions)}")
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
                    choix = st.radio("Sélectionnez votre réponse :", options, key=f"radio_q_{q_id}", index=None, disabled=st.session_state.answered)

                    if not st.session_state.answered:
                        if st.button("Valider la réponse", type="primary"):
                            if choix is None:
                                st.warning("Veuillez sélectionner une option.")
                            else:
                                elapsed = time.time() - st.session_state.question_start_time
                                reponses_correctes = q.get('donnees', {}).get('reponses_correctes', [])
                                est_correct = choix in reponses_correctes
                                points_gagnes = 0

                                if est_correct:
                                    if elapsed <= timer_sec:
                                        points_gagnes = points
                                        st.session_state.last_result = ("success", f"Bonne réponse ! +{points} pts 🎉", quiz_info.get('son_good'))
                                    else:
                                        points_gagnes = points // 2
                                        st.session_state.last_result = ("warning", f"Bonne réponse mais hors temps. +{points_gagnes} pts ⏱️", quiz_info.get('son_good'))
                                else:
                                    st.session_state.last_result = ("error", "Mauvaise réponse ❌", quiz_info.get('son_bad'))

                                st.session_state.score_total += points_gagnes
                                st.session_state.max_points += points
                                st.session_state.answered = True
                                st.rerun()
                    else:
                        res_type, res_msg, son_path = st.session_state.last_result
                        if res_type == "success":
                            st.success(res_msg)
                        elif res_type == "warning":
                            st.warning(res_msg)
                        else:
                            st.error(res_msg)

                        if son_path and os.path.exists(son_path):
                            jouer_effet_sonore(son_path, vol_sons)

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
                if 'music_active_path' in st.session_state:
                    del st.session_state.music_active_path
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
                    if 'music_active_path' in st.session_state:
                        del st.session_state.music_active_path
                    st.rerun()