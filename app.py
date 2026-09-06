import os
import json
import streamlit as st
import time
import base64
import qrcode
from io import BytesIO

st.set_page_config(page_title="Portail QCM Enolou", page_icon="🎓", layout="wide")

# Masquer les éléments de l'interface Streamlit (menu, header, footer)
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

DOSSIER_QUIZZES = "QCM"
if not os.path.exists(DOSSIER_QUIZZES):
    os.makedirs(DOSSIER_QUIZZES)

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
        st.session_state.sound_trigger = 0

# --- NAVIGATION GLOBALE (Sidebar) ---
st.sidebar.title("🧭 Navigation")
mode = st.sidebar.radio("Choisissez le mode :", ["👨‍🎓 Espace Étudiant (Passer un QCM)", "👨‍🏫 Espace Professeur (Créateur / Éditeur)"])

if 'qcm_selectionne' not in st.session_state:
    st.session_state.qcm_selectionne = None

# ==========================================
# ESPACE PROFESSEUR : CRÉATEUR / ÉDITEUR & QR CODES
# ==========================================
if mode == "👨‍🏫 Espace Professeur (Créateur / Éditeur)":
    st.title("👨‍🏫 Espace Professeur - Gestion & QR Codes")
    st.write("Gérez vos QCM et générez les QR codes associés à afficher dans la classe.")

    fichiers_existants = [f for f in os.listdir(DOSSIER_QUIZZES) if f.endswith('.json')]
    
    if fichiers_existants:
        st.markdown("### 📱 Générateur de QR Code pour la classe")
        qcm_pour_qr = st.selectbox("Sélectionnez le QCM à transformer en QR Code :", fichiers_existants)
        
        # Récupération de l'URL de base de l'application (à adapter une fois déployé sur Streamlit Cloud)
        domaine_app = st.text_input("URL de votre application déployée (ex: https://votre-app.streamlit.app) :", value="")
        
        if domaine_app:
            url_complete = f"{domaine_app.strip('/')}/?qcm={qcm_pour_qr}"
            st.write(lien := f"Lien direct : [{url_complete}]({url_complete})")
            
            # Génération du QR code en image
            img_qr = qrcode.make(url_complete)
            buffered = BytesIO()
            img_qr.save(buffered, format="PNG")
            img_bytes = buffered.getvalue()
            
            st.image(img_bytes, caption=f"QR Code pour accéder directement à : {qcm_pour_qr}", width=250)
            st.download_button(
                label="📥 Télécharger ce QR Code (Image PNG)",
                data=img_bytes,
                file_name=f"qrcode_{qcm_pour_qr.replace('.json', '')}.png",
                mime="image/png"
            )
        else:
            st.info("💡 Saisissez l'URL de votre application Streamlit Cloud ci-dessus pour générer le QR code cliquable par vos élèves.")

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
        st.session_state.edit_son_good = ""
        st.session_state.edit_son_bad = ""
        st.session_state.edit_questions = []
        st.session_state.dernier_choix_edition = None

    if choix_edition != st.session_state.dernier_choix_edition:
        st.session_state.dernier_choix_edition = choix_edition
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
        st.subheader("Paramètres du QCM")
        nom_fichier = st.text_input("Nom du fichier JSON :", value=st.session_state.edit_nom_fichier)
        titre_quiz = st.text_input("Titre affiché :", value=st.session_state.edit_titre)
        desc_quiz = st.text_area("Description :", value=st.session_state.edit_desc)
        
        submitted_meta = st.form_submit_button("💾 Enregistrer le QCM", type="primary")
        if submitted_meta:
            if not nom_fichier.endswith(".json"):
                nom_fichier += ".json"
            chemin_complet = os.path.join(DOSSIER_QUIZZES, nom_fichier)
            donnees_globales = {
                "quiz_info": {"titre": titre_quiz, "description": desc_quiz},
                "questions": st.session_state.edit_questions
            }
            with open(chemin_complet, "w", encoding="utf-8") as f:
                json.dump(donnees_globales, f, ensure_ascii=False, indent=4)
            st.success(f"QCM '{nom_fichier}' sauvegardé !")

    with st.form("form_ajout_question"):
        st.subheader("Ajouter une question")
        consigne_q = st.text_area("Consigne :")
        points_q = st.number_input("Points :", min_value=1, value=10)
        timer_q = st.number_input("Chronomètre (s) :", min_value=5, value=30)
        options_input = st.text_area("Options (une par ligne) :", value="Option A\nOption B")
        reponse_correcte = st.text_input("Réponse exacte :")
        explication_q = st.text_area("Explication :", value="")

        submitted_q = st.form_submit_button("➕ Ajouter la question")
        if submitted_q:
            options_liste = [opt.strip() for opt in options_input.split("\n") if opt.strip()]
            if consigne_q and options_liste and reponse_correcte:
                nouvelle_q = {
                    "id": len(st.session_state.edit_questions) + 1,
                    "consigne": consigne_q,
                    "type": "qcm",
                    "points": points_q,
                    "timer_secondes": timer_q,
                    "donnees": {"options": options_liste, "reponses_correctes": [reponse_correcte]},
                    "explication": explication_q,
                    "media": {"image": ""}
                }
                st.session_state.edit_questions.append(nouvelle_q)
                st.success("Question ajoutée temporairement !")

# ==========================================
# ESPACE ÉTUDIANT : PASSER UN QCM
# ==========================================
else:
    if not st.session_state.qcm_selectionne:
        st.title("🎓 Portail des Évaluations - Enolou")
        st.write("Veuillez sélectionner le QCM à lancer :")
        
        fichiers_json = [f for f in os.listdir(DOSSIER_QUIZZES) if f.endswith('.json')]
        if not fichiers_json:
            st.warning("Aucun QCM disponible.")
        else:
            choix_fichier = st.selectbox("Liste des QCM :", fichiers_json)
            if st.button("Lancer ce QCM", type="primary"):
                chemin_complet = os.path.join(DOSSIER_QUIZZES, choix_fichier)
                with open(chemin_complet, 'r', encoding='utf-8') as f:
                    banque = json.load(f)
                st.session_state.banque = banque if isinstance(banque, dict) else {"quiz_info": {}, "questions": banque}
                st.session_state.qcm_selectionne = choix_fichier
                st.session_state.current_idx = 0
                st.session_state.score_total = 0
                st.session_state.max_points = 0
                st.session_state.quiz_started = False
                st.session_state.answered = False
                st.session_state.last_result = None
                st.session_state.sound_trigger = 0
                st.rerun()
    else:
        quiz_info = st.session_state.banque.get('quiz_info', {})
        questions = st.session_state.banque.get('questions', [])
        titre = quiz_info.get('titre', 'Évaluation QCM')
        description = quiz_info.get('description', '')

        st.title(f"🎓 {titre}")

        if st.button("⬅️ Changer de QCM"):
            st.session_state.qcm_selectionne = None
            st.session_state.quiz_started = False
            st.query_params.clear()
            st.rerun()

        if not st.session_state.quiz_started:
            if description:
                st.write(description)
            st.info("💡 Cliquez pour lancer l'évaluation.")
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
                donnees = q.get('donnees', {})
                options = donnees.get('options', [])
                
                st.progress((q_id) / len(questions) if len(questions) > 0 else 0)
                
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

                with col_qcm:
                    st.subheader(f"Question {q_id + 1} sur {len(questions)}")
                    st.caption(f"⏱️ Temps : {timer_sec}s | 🏆 {points} pts")
                    st.markdown(f"**{consigne}**")

                    choix = st.radio("Votre réponse :", options, key=f"radio_q_{q_id}", index=None, disabled=st.session_state.answered)

                    if not st.session_state.answered:
                        if st.button("Valider la réponse", type="primary"):
                            if choix is None:
                                st.warning("Veuillez sélectionner une option.")
                            else:
                                elapsed = time.time() - st.session_state.question_start_time
                                reponses_correctes = donnees.get('reponses_correctes', [])
                                est_correct = choix in reponses_correctes
                                points_gagnes = points if (est_correct and elapsed <= timer_sec) else (points // 2 if est_correct else 0)
                                
                                msg = "Bonne réponse ! 🎉" if est_correct else "Mauvaise réponse ❌"
                                st.session_state.score_total += points_gagnes
                                st.session_state.max_points += points
                                st.session_state.answered = True
                                st.session_state.last_result = ("success" if est_correct else "error", msg)
                                st.rerun()
                    else:
                        res_type, res_msg = st.session_state.last_result
                        if res_type == "success":
                            st.success(res_msg)
                        else:
                            st.error(res_msg)

                        if explication := q.get('explication', ''):
                            st.caption(f"💡 *{explication}*")

                        if st.button("Question suivante ➡️", type="primary"):
                            st.session_state.current_idx += 1
                            st.session_state.answered = False
                            st.session_state.last_result = None
                            st.session_state.question_start_time = time.time()
                            st.rerun()
            else:
                st.balloons()
                st.success("🎉 Évaluation terminée !")
                st.markdown(f"### 🏆 Score : {st.session_state.score_total} / {st.session_state.max_points}")
                if st.button("Recommencer"):
                    st.session_state.current_idx = 0
                    st.session_state.score_total = 0
                    st.session_state.max_points = 0
                    st.session_state.quiz_started = False
                    st.session_state.answered = False
                    st.rerun()