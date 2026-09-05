import os
import json
import streamlit as st
import time
import base64

st.set_page_config(page_title="Portail QCM Enolou", page_icon="🎓", layout="wide")

DOSSIER_QUIZZES = "QCM"

if not os.path.exists(DOSSIER_QUIZZES):
    os.makedirs(DOSSIER_QUIZZES)

# --- NAVIGATION GLOBALE (Sidebar) ---
st.sidebar.title("🧭 Navigation")
mode = st.sidebar.radio("Choisissez le mode :", ["👨‍🎓 Espace Étudiant (Passer un QCM)", "👨‍🏫 Espace Professeur (Créateur / Éditeur)"])

if 'qcm_selectionne' not in st.session_state:
    st.session_state.qcm_selectionne = None

# ==========================================
# ESPACE PROFESSEUR : CRÉATEUR / ÉDITEUR
# ==========================================
if mode == "👨‍🏫 Espace Professeur (Créateur / Éditeur)":
    st.title("👨‍🏫 Espace Professeur - Gestion des QCM")
    st.write("Modifiez un QCM existant ou créez-en un nouveau directement depuis le navigateur.")

    fichiers_existants = [f for f in os.listdir(DOSSIER_QUIZZES) if f.endswith('.json')]
    
    # Sélection du fichier à éditer ou création d'un nouveau
    choix_edition = st.selectbox(
        "Sélectionnez un QCM à modifier ou choisissez '-- Créer un nouveau QCM --' :", 
        ["-- Créer un nouveau QCM --"] + fichiers_existants
    )

    # Initialisation de la session pour l'éditeur
    if 'edit_nom_fichier' not in st.session_state:
        st.session_state.edit_nom_fichier = "nouveau_qcm.json"
        st.session_state.edit_titre = ""
        st.session_state.edit_desc = ""
        st.session_state.edit_musique = ""
        st.session_state.edit_son_good = ""
        st.session_state.edit_son_bad = ""
        st.session_state.edit_questions = []
        st.session_state.dernier_choix_edition = None

    # Si l'utilisateur change de sélection dans le menu déroulant
    if choix_edition != st.session_state.dernier_choix_edition:
        st.session_state.dernier_choix_edition = choix_edition
        if choix_edition == "-- Créer un nouveau QCM --":
            st.session_state.edit_nom_fichier = "nouveau_qcm.json"
            st.session_state.edit_titre = "Mon Nouveau Quiz"
            st.session_state.edit_desc = ""
            st.session_state.edit_musique = ""
            st.session_state.edit_son_good = ""
            st.session_state.edit_son_bad = ""
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
                    st.session_state.edit_son_good = info.get("son_good", "")
                    st.session_state.edit_son_bad = info.get("son_bad", "")
                    st.session_state.edit_questions = data.get("questions", [])
            except Exception as e:
                st.error(f"Erreur lors du chargement du fichier : {e}")

    with st.form("form_edition_qcm"):
        st.subheader("1. Informations générales")
        nom_fichier = st.text_input("Nom du fichier JSON :", value=st.session_state.edit_nom_fichier)
        titre_quiz = st.text_input("Titre affiché du Quiz :", value=st.session_state.edit_titre)
        desc_quiz = st.text_area("Description / Consignes générales :", value=st.session_state.edit_desc)
        
        st.markdown("---")
        st.subheader("2. Paramètres audio")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            musique_path = st.text_input("Chemin musique de fond :", value=st.session_state.edit_musique)
        with col_s2:
            son_good_path = st.text_input("Son bonne réponse :", value=st.session_state.edit_son_good)
        with col_s3:
            son_bad_path = st.text_input("Son mauvaise réponse :", value=st.session_state.edit_son_bad)

        submitted_meta = st.form_submit_button("💾 Enregistrer les modifications du QCM", type="primary")
        if submitted_meta:
            if not nom_fichier.endswith(".json"):
                nom_fichier += ".json"
            
            chemin_complet = os.path.join(DOSSIER_QUIZZES, nom_fichier)
            donnees_globales = {
                "quiz_info": {
                    "titre": titre_quiz,
                    "description": desc_quiz,
                    "musique": musique_path,
                    "son_good": son_good_path,
                    "son_bad": son_bad_path
                },
                "questions": st.session_state.edit_questions
            }
            with open(chemin_complet, "w", encoding="utf-8") as f:
                json.dump(donnees_globales, f, ensure_ascii=False, indent=4)
            st.success(f"QCM '{nom_fichier}' mis à jour et sauvegardé avec succès ({len(st.session_state.edit_questions)} questions) !")

    st.markdown("---")
    st.subheader("3. Ajouter une question à ce QCM")

    with st.form("form_ajout_question"):
        consigne_q = st.text_area("Énoncé / Consigne de la question :")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            points_q = st.number_input("Nombre de points :", min_value=1, value=10)
        with col_p2:
            timer_q = st.number_input("Chronomètre (secondes) :", min_value=5, value=30)

        options_input = st.text_area("Options de réponse (une par ligne) :", value="Option A\nOption B\nOption C\nOption D")
        reponse_correcte = st.text_input("Réponse exacte (doit correspondre à l'une des options) :")
        explication_q = st.text_area("Explication pédagogique :", value="")
        img_q = st.text_input("Chemin optionnel d'une image (ex: docs/image.png) :", value="")

        submitted_q = st.form_submit_button("➕ Ajouter cette question")
        if submitted_q:
            options_liste = [opt.strip() for opt in options_input.split("\n") if opt.strip()]
            if not consigne_q or not options_liste or not reponse_correcte:
                st.error("Veuillez remplir la consigne, les options et la réponse correcte.")
            else:
                nouvelle_q = {
                    "id": len(st.session_state.edit_questions) + 1,
                    "consigne": consigne_q,
                    "type": "qcm",
                    "points": points_q,
                    "timer_secondes": timer_q,
                    "donnees": {
                        "options": options_liste,
                        "reponses_correctes": [reponse_correcte]
                    },
                    "explication": explication_q,
                    "media": {
                        "image": img_q
                    }
                }
                st.session_state.edit_questions.append(nouvelle_q)
                st.success("Question ajoutée ! Pensez à cliquer sur 'Enregistrer les modifications du QCM' plus haut pour valider.")

    if st.session_state.edit_questions:
        st.markdown("### Questions actuelles dans ce QCM :")
        for idx, q in enumerate(st.session_state.edit_questions):
            st.info(f"**Q{idx+1} ({q['points']} pts) :** {q['consigne']} | *Réponse : {q['donnees']['reponses_correctes']}*")
        
        if st.button("🗑️ Vider / Supprimer toutes les questions"):
            st.session_state.edit_questions = []
            st.rerun()

# ==========================================
# ESPACE ÉTUDIANT : PASSER UN QCM
# ==========================================
else:
    if not st.session_state.qcm_selectionne:
        st.title("🎓 Portail des Évaluations - Enolou")
        st.write("Veuillez sélectionner le QCM que vous souhaitez lancer dans la liste ci-dessous :")
        
        fichiers_json = [f for f in os.listdir(DOSSIER_QUIZZES) if f.endswith('.json')]
        
        if not fichiers_json:
            st.warning(f"Aucun fichier JSON n'a été trouvé dans le dossier '{DOSSIER_QUIZZES}'. Veuillez en créer un via l'Espace Professeur.")
        else:
            choix_fichier = st.selectbox("Liste des QCM disponibles :", fichiers_json)
            
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
            st.rerun()

        if not st.session_state.quiz_started:
            if description:
                st.write(description)
            st.info("💡 Cliquez sur le bouton ci-dessous pour lancer l'évaluation (ceci active automatiquement le son et la musique).")
            
            if st.button("Commencer le QCM 🎵", type="primary"):
                st.session_state.quiz_started = True
                st.session_state.question_start_time = time.time()
                st.rerun()
        else:
            musique_path = quiz_info.get('musique')
            if musique_path and os.path.exists(musique_path):
                try:
                    with open(musique_path, "rb") as f:
                        b64_music = base64.b64encode(f.read()).decode()
                    st.markdown(f'<audio autoplay loop src="data:audio/mp3;base64,{b64_music}"></audio>', unsafe_allow_html=True)
                except Exception:
                    pass

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
                        
                    doc_img = q.get('document_image_a4')
                    media = q.get('media', {})
                    img_path = doc_img if (doc_img and os.path.exists(doc_img)) else media.get('image')
                    
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
                    st.caption(f"⏱️ Temps conseillé : {timer_sec}s | 🏆 Valeur : {points} pts")
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
                                st.session_state.sound_trigger += 1
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
                            try:
                                with open(son_path, "rb") as f:
                                    b64_sound = base64.b64encode(f.read()).decode()
                                st.markdown(f'<audio autoplay src="data:audio/mp3;base64,{b64_sound}" id="sound_{st.session_state.sound_trigger}"></audio>', unsafe_allow_html=True)
                            except Exception:
                                pass

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
                    st.rerun()