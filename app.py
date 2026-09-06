import os
import json
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
    /* Masquage total des bandeaux audio de Streamlit */
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
if not os.path.exists(DOSSIER_QUIZZES):
    os.makedirs(DOSSIER_QUIZZES)

# --- FONCTION DE SYNCHRONISATION AUTOMATIQUE AVEC GITHUB ---
def sauvegarder_fichier_github(chemin_relatif, contenu_str):
    """Pousse le fichier JSON directement sur GitHub si le token est configuré dans les secrets Streamlit."""
    try:
        if "GITHUB_TOKEN" in st.secrets:
            token = st.secrets["GITHUB_TOKEN"]
            owner_repo = "YannBzh94/enolou-qcm-web"  # Votre dépôt GitHub
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
    """Joue la musique de fond en continu sans la redémarrer et gère son volume dédié."""
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
    """Joue un effet sonore (bonne/mauvaise réponse) et règle son volume sans toucher à la musique."""
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

# --- GESTION DE L'URL DIRECTE (via QR Code) ---
query_params = st.query_params
url_qcm = query_params.get("qcm")

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
        if 'music_active_path' in st.session_state:
            del st.session_state.music_active_path

# --- NAVIGATION GLOBALE (Sidebar) ---
st.sidebar.title("🧭 Navigation")
mode = st.sidebar.radio("Choisissez le mode :", ["👨‍🎓 Espace Étudiant (Passer un QCM)", "👨‍🏫 Espace Professeur (Créateur / Éditeur)"])

if mode == "👨‍🎓 Espace Étudiant (Passer un QCM)":
    if 'music_active_path' in st.session_state:
        del st.session_state.music_active_path

if 'qcm_selectionne' not in st.session_state:
    st.session_state.qcm_selectionne = None

# ==========================================
# ESPACE PROFESSEUR : GESTION & QR CODES
# ==========================================
if mode == "👨‍🏫 Espace Professeur (Créateur / Éditeur)":
    st.title("👨‍🏫 Espace Professeur - Gestion & QR Codes")
    st.write("Gérez vos QCM, configurez vos médias et générez les QR codes associés pour la classe.")

    fichiers_existants = [f for f in os.listdir(DOSSIER_QUIZZES) if f.endswith('.json')]
    
    if fichiers_existants:
        st.markdown("### 📱 Générateur de QR Code pour la classe")
        qcm_pour_qr = st.selectbox("Sélectionnez le QCM à transformer en QR Code :", fichiers_existants)
        domaine_app = st.text_input(
            "URL de votre application déployée :", 
            value="https://yannbzh94-enolou-qcm-web-app-ngwrt8.streamlit.app/"
        )
        
        if domaine_app:
            url_complete = f"{domaine_app.strip('/')}/?qcm={qcm_pour_qr}"
            st.write(f"Lien direct : [{url_complete}]({url_complete})")
            
            img_qr = qrcode.make(url_complete)
            buffered = BytesIO()
            img_qr.save(buffered, format="PNG")
            img_bytes = buffered.getvalue()
            
            st.image(img_bytes, caption=f"QR Code pour : {qcm_pour_qr}", width=250)
            st.download_button(
                label="📥 Télécharger ce QR Code (Image PNG)",
                data=img_bytes,
                file_name=f"qrcode_{qcm_pour_qr.replace('.json', '')}.png",
                mime="image/png"
            )

    st.markdown("---")
    choix_edition = st.selectbox(
        "Éditer un QCM existant ou en créer un nouveau :", 
        ["-- Créer un nouveau QCM --"] + fichiers_existants
    )

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
            st.session_state.edit_musique = ""
            st.session_state.edit_vol_musique = 0.5
            st.session_state.edit_son_good = ""
            st.session_state.edit_son_bad = ""
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
                    st.session_state.edit_musique = info.get("musique", "")
                    st.session_state.edit_vol_musique = info.get("volume_musique", 0.5)
                    st.session_state.edit_son_good = info.get("son_good", "")
                    st.session_state.edit_son_bad = info.get("son_bad", "")
                    st.session_state.edit_vol_sons = info.get("volume_sons", 0.8)
                    st.session_state.edit_questions = data.get("questions", [])
            except Exception:
                pass

    with st.form("form_edition_qcm"):
        st.subheader("1. Paramètres généraux, Audio et Volumes")
        nom_fichier = st.text_input("Nom du fichier JSON :", value=st.session_state.edit_nom_fichier)
        titre_quiz = st.text_input("Titre affiché :", value=st.session_state.edit_titre)
        desc_quiz = st.text_area("Description :", value=st.session_state.edit_desc)
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            musique_path = st.text_input("Chemin musique de fond :", value=st.session_state.edit_musique)
            vol_musique = st.slider("Volume de la musique :", min_value=0.0, max_value=1.0, value=float(st.session_state.edit_vol_musique), step=0.05)
        with col_m2:
            son_good_path = st.text_input("Son bonne réponse :", value=st.session_state.edit_son_good)
            vol_sons = st.slider("Volume des effets sonores :", min_value=0.0, max_value=1.0, value=float(st.session_state.edit_vol_sons), step=0.05)
        with col_m3:
            son_bad_path = st.text_input("Son mauvaise réponse :", value=st.session_state.edit_son_bad)

        submitted_meta = st.form_submit_button("💾 Enregistrer les paramètres généraux", type="primary")
        if submitted_meta:
            if not nom_fichier.endswith(".json"):
                nom_fichier += ".json"
            
            st.session_state.edit_nom_fichier = nom_fichier
            st.session_state.edit_titre = titre_quiz
            st.session_state.edit_desc = desc_quiz
            st.session_state.edit_musique = musique_path
            st.session_state.edit_vol_musique = vol_musique
            st.session_state.edit_son_good = son_good_path
            st.session_state.edit_son_bad = son_bad_path
            st.session_state.edit_vol_sons = vol_sons

            donnees_globales = {
                "quiz_info": {
                    "titre": titre_quiz,
                    "description": desc_quiz,
                    "musique": musique_path,
                    "volume_musique": vol_musique,
                    "son_good": son_good_path,
                    "son_bad": son_bad_path,
                    "volume_sons": vol_sons
                },
                "questions": st.session_state.edit_questions
            }
            contenu_json = json.dumps(donnees_globales, ensure_ascii=False, indent=4)
            
            chemin_complet = os.path.join(DOSSIER_QUIZZES, nom_fichier)
            with open(chemin_complet, "w", encoding="utf-8") as f:
                f.write(contenu_json)
            
            succes_gh = sauvegarder_fichier_github(f"QCM/{nom_fichier}", contenu_json)
            if succes_gh:
                st.success(f"Paramètres enregistrés et mis à jour directement sur GitHub avec succès ! 🎉")
            else:
                st.success(f"Paramètres enregistrés localement ! (Utilisez le bouton de téléchargement ci-dessous pour mettre à jour GitHub)")

    if 'edit_nom_fichier' in st.session_state:
        donnees_a_telecharger = {
            "quiz_info": {
                "titre": st.session_state.edit_titre,
                "description": st.session_state.edit_desc,
                "musique": st.session_state.edit_musique,
                "volume_musique": st.session_state.edit_vol_musique,
                "son_good": st.session_state.edit_son_good,
                "son_bad": st.session_state.edit_son_bad,
                "volume_sons": st.session_state.edit_vol_sons
            },
            "questions": st.session_state.edit_questions
        }
        st.download_button(
            label=f"📥 Télécharger le fichier JSON mis à jour ({st.session_state.edit_nom_fichier}) pour GitHub (si pas de Token)",
            data=json.dumps(donnees_a_telecharger, ensure_ascii=False, indent=4),
            file_name=st.session_state.edit_nom_fichier,
            mime="application/json",
            type="secondary"
        )

    st.markdown("---")
    st.subheader("2. Gestion, Modification et Ajout des Questions")
    
    if st.session_state.edit_questions:
        st.write(f"Nombre de questions actuelles : {len(st.session_state.edit_questions)}")
        for idx, q in enumerate(st.session_state.edit_questions):
            col_q_info, col_q_edit, col_q_del = st.columns([4, 1, 1])
            with col_q_info:
                st.text(f"Q{idx+1}: {q.get('consigne', '')[:40]}... ({q.get('points', 10)} pts)")
            with col_q_edit:
                if st.button("✏️ Éditer", key=f"edit_q_{idx}"):
                    st.session_state.edit_q_index = idx
                    st.rerun()
            with col_q_del:
                if st.button("❌ Supprimer", key=f"del_q_{idx}"):
                    if st.session_state.edit_q_index == idx:
                        st.session_state.edit_q_index = None
                    st.session_state.edit_questions.pop(idx)
                    
                    donnees_globales = {
                        "quiz_info": {
                            "titre": st.session_state.edit_titre,
                            "description": st.session_state.edit_desc,
                            "musique": st.session_state.edit_musique,
                            "volume_musique": st.session_state.edit_vol_musique,
                            "son_good": st.session_state.edit_son_good,
                            "son_bad": st.session_state.edit_son_bad,
                            "volume_sons": st.session_state.edit_vol_sons
                        },
                        "questions": st.session_state.edit_questions
                    }
                    contenu_json = json.dumps(donnees_globales, ensure_ascii=False, indent=4)
                    chemin_complet = os.path.join(DOSSIER_QUIZZES, st.session_state.edit_nom_fichier)
                    with open(chemin_complet, "w", encoding="utf-8") as f:
                        f.write(contenu_json)
                    
                    sauvegarder_fichier_github(f"QCM/{st.session_state.edit_nom_fichier}", contenu_json)
                    st.rerun()

    is_editing = st.session_state.edit_q_index is not None
    current_q_data = st.session_state.edit_questions[st.session_state.edit_q_index] if is_editing else {}

    with st.form("form_ajout_question"):
        if is_editing:
            st.markdown(f"#### ✏️ Modifier la question {st.session_state.edit_q_index + 1}")
        else:
            st.markdown("#### ➕ Ajouter une nouvelle question")

        consigne_q = st.text_area("Consigne de la question :", value=current_q_data.get('consigne', ''))
        points_q = st.number_input("Points :", min_value=1, value=current_q_data.get('points', 10))
        timer_q = st.number_input("Chronomètre (secondes) :", min_value=5, value=current_q_data.get('timer_secondes', 30))
        
        default_opts = "\n".join(current_q_data.get('donnees', {}).get('options', ["Option A", "Option B", "Option C"]))
        options_input = st.text_area("Options de réponse (une par ligne) :", value=default_opts)
        
        reps_actuelles = current_q_data.get('donnees', {}).get('reponses_correctes', [""])
        def_rep = reps_actuelles[0] if reps_actuelles else ""
        reponse_correcte = st.text_input("Réponse exacte (doit correspondre exactement à l'une des options) :", value=def_rep)
        
        explication_q = st.text_area("Explication pédagogique :", value=current_q_data.get('explication', ''))
        
        st.markdown("##### Documents associés à la question (chemins relatifs)")
        doc_texte_q = st.text_area("Texte de référence (optionnel) :", value=current_q_data.get('document_texte', ''))
        img_path_q = st.text_input("Chemin de l'image (ex: QCM/image.png ou media/schema.png) :", value=current_q_data.get('media', {}).get('image', ''))
        pdf_path_q = st.text_input("Chemin du PDF joint (ex: QCM/document.pdf) :", value=current_q_data.get('document_appui', ''))

        submitted_q = st.form_submit_button("💾 Enregistrer les modifications" if is_editing else "➕ Ajouter cette question à la liste")
        
        if submitted_q:
            options_liste = [opt.strip() for opt in options_input.split("\n") if opt.strip()]
            if consigne_q and options_liste and reponse_correcte:
                nouvelle_q = {
                    "id": (st.session_state.edit_q_index + 1) if is_editing else (len(st.session_state.edit_questions) + 1),
                    "consigne": consigne_q,
                    "type": "qcm",
                    "points": points_q,
                    "timer_secondes": timer_q,
                    "donnees": {"options": options_liste, "reponses_correctes": [reponse_correcte]},
                    "explication": explication_q,
                    "document_texte": doc_texte_q,
                    "media": {"image": img_path_q},
                    "document_appui": pdf_path_q
                }
                
                if is_editing:
                    st.session_state.edit_questions[st.session_state.edit_q_index] = nouvelle_q
                    st.session_state.edit_q_index = None
                else:
                    st.session_state.edit_questions.append(nouvelle_q)
                
                donnees_globales = {
                    "quiz_info": {
                        "titre": st.session_state.edit_titre,
                        "description": st.session_state.edit_desc,
                        "musique": st.session_state.edit_musique,
                        "volume_musique": st.session_state.edit_vol_musique,
                        "son_good": st.session_state.edit_son_good,
                        "son_bad": st.session_state.edit_son_bad,
                        "volume_sons": st.session_state.edit_vol_sons
                    },
                    "questions": st.session_state.edit_questions
                }
                contenu_json = json.dumps(donnees_globales, ensure_ascii=False, indent=4)
                chemin_complet = os.path.join(DOSSIER_QUIZZES, st.session_state.edit_nom_fichier)
                with open(chemin_complet, "w", encoding="utf-8") as f:
                    f.write(contenu_json)
                
                sauvegarder_fichier_github(f"QCM/{st.session_state.edit_nom_fichier}", contenu_json)
                st.success("Question enregistrée avec succès !")
                st.rerun()
            else:
                st.warning("Veuillez remplir la consigne, au moins une option et la réponse exacte.")

    if is_editing:
        if st.button("❌ Annuler l'édition"):
            st.session_state.edit_q_index = None
            st.rerun()

# ==========================================
# ESPACE ÉTUDIANT : PASSER UN QCM
# ==========================================
else:
    if not st.session_state.qcm_selectionne:
        st.title("🎓 Portail des Évaluations - Enolou")
        st.warning("🔒 **Accès restreint :** Veuillez scanner le QR code ou utiliser le lien direct fourni par votre professeur pour accéder à votre QCM.")
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
                
                donnees = q.get('donnees', {})
                options = donnees.get('options', [])
                
                col_docs, col_qcm = st.columns([3, 2], gap="large")

                with col_docs:
                    st.markdown("### 📄 Documents de référence")
                    
                    doc_texte = q.get('document_texte')
                    if doc_texte:
                        st.info(doc_texte)
                        
                    media = q.get('media', {})
                    img_path = media.get('image')
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)

                    doc_appui = q.get('document_appui')
                    if doc_appui and os.path.exists(doc_appui):
                        with open(doc_appui, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                        st.download_button(
                            label="📥 Télécharger / Ouvrir le PDF joint",
                            data=pdf_bytes,
                            file_name=os.path.basename(doc_appui),
                            mime="application/pdf",
                            key=f"pdf_{q_id}"
                        )

                with col_qcm:
                    st.subheader(f"Question {q_id + 1} sur {len(questions)}")
                    st.caption(f"🏆 Valeur : {points} pts")
                    
                    # --- COMPTE À REBOURS NUMÉRIQUE FLUIDE (VIA COMPOSANT HTML) ---
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
                                st.warning("Veuillez sélectionner une option avant de valider.")
                            else:
                                elapsed = time.time() - st.session_state.question_start_time
                                
                                reponses_correctes = donnees.get('reponses_correctes', [])
                                if isinstance(reponses_correctes, dict):
                                    reponses_correctes = list(reponses_correctes.values())

                                est_correct = choix in reponses_correctes
                                points_gagnes = 0

                                if est_correct:
                                    if elapsed <= timer_sec:
                                        points_gagnes = points
                                        msg = f"Bonne réponse dans les temps ({int(elapsed)}s) ! +{points} pts 🎉"
                                        st.session_state.last_result = ("success", msg, quiz_info.get('son_good'))
                                    else:
                                        points_gagnes = points // 2
                                        msg = f"Bonne réponse mais hors temps imparti ({int(elapsed)}s / {timer_sec}s). Points réduits : +{points_gagnes} pts ⏱️"
                                        st.session_state.last_result = ("warning", msg, quiz_info.get('son_good'))
                                else:
                                    msg = "Mauvaise réponse ❌"
                                    st.session_state.last_result = ("error", msg, quiz_info.get('son_bad'))

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