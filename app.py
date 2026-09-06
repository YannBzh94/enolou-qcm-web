import os
import json
import streamlit as st
import time
import base64
import qrcode
from io import BytesIO

st.set_page_config(page_title="Portail QCM Enolou", page_icon="🎓", layout="wide")

# Masquer les éléments superflus de l'interface Streamlit
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
# ESPACE PROFESSEUR : GESTION & QR CODES
# ==========================================
if mode == "👨‍🏫 Espace Professeur (Créateur / Éditeur)":
    st.title("👨‍🏫 Espace Professeur - Gestion & QR Codes")
    st.write("Gérez vos QCM, configurez vos médias et générez les QR codes associés pour la classe.")

    fichiers_existants = [f for f in os.listdir(DOSSIER_QUIZZES) if f.endswith('.json')]
    
    if fichiers_existants:
        st.markdown("### 📱 Générateur de QR Code pour la classe")
        qcm_pour_qr = st.selectbox("Sélectionnez le QCM à transformer en QR Code :", fichiers_existants)
        domaine_app = st.text_input("URL de votre application déployée (ex: https://votre-app.streamlit.app) :", value="")
        
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
            except Exception:
                pass

    with st.form("form_edition_qcm"):
        st.subheader("1. Paramètres généraux et Audio")
        nom_fichier = st.text_input("Nom du fichier JSON :", value=st.session_state.edit_nom_fichier)
        titre_quiz = st.text_input("Titre affiché :", value=st.session_state.edit_titre)
        desc_quiz = st.text_area("Description :", value=st.session_state.edit_desc)
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            musique_path = st.text_input("Chemin musique de fond :", value=st.session_state.edit_musique)
        with col_m2:
            son_good_path = st.text_input("Son bonne réponse :", value=st.session_state.edit_son_good)
        with col_m3:
            son_bad_path = st.text_input("Son mauvaise réponse :", value=st.session_state.edit_son_bad)

        submitted_meta = st.form_submit_button("💾 Enregistrer les paramètres généraux", type="primary")
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
            st.success(f"QCM '{nom_fichier}' enregistré avec succès !")

    st.markdown("---")
    st.subheader("2. Gestion des Questions et Documents associés")
    
    # Affichage des questions actuelles avec option de suppression
    if st.session_state.edit_questions:
        st.write(f"Nombre de questions actuelles : {len(st.session_state.edit_questions)}")
        for idx, q in enumerate(st.session_state.edit_questions):
            col_q_info, col_q_del = st.columns([5, 1])
            with col_q_info:
                st.text(f"Q{idx+1}: {q.get('consigne', '')[:50]}... ({q.get('points', 10)} pts)")
            with col_q_del:
                if st.button("❌ Supprimer", key=f"del_q_{idx}"):
                    st.session_state.edit_questions.pop(idx)
                    st.rerun()

    with st.form("form_ajout_question"):
        st.markdown("#### Ajouter une nouvelle question")
        consigne_q = st.text_area("Consigne de la question :")
        points_q = st.number_input("Points :", min_value=1, value=10)
        timer_q = st.number_input("Chronomètre (secondes) :", min_value=5, value=30)
        
        options_input = st.text_area("Options de réponse (une par ligne) :", value="Option A\nOption B\nOption C")
        reponse_correcte = st.text_input("Réponse exacte (doit correspondre exactement à l'une des options) :")
        explication_q = st.text_area("Explication pédagogique :", value="")
        
        st.markdown("##### Documents associés à la question (chemins relatifs)")
        doc_texte_q = st.text_area("Texte de référence (optionnel) :", value="")
        img_path_q = st.text_input("Chemin de l'image (ex: QCM/image.png ou media/schema.png) :", value="")
        pdf_path_q = st.text_input("Chemin du PDF joint (ex: QCM/document.pdf) :", value="")

        submitted_q = st.form_submit_button("➕ Ajouter cette question à la liste")
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
                    "document_texte": doc_texte_q,
                    "media": {"image": img_path_q},
                    "document_appui": pdf_path_q
                }
                st.session_state.edit_questions.append(nouvelle_q)
                
                # Sauvegarde automatique de la liste mise à jour dans le fichier JSON en cours
                chemin_complet = os.path.join(DOSSIER_QUIZZES, st.session_state.edit_nom_fichier)
                donnees_globales = {
                    "quiz_info": {
                        "titre": st.session_state.edit_titre,
                        "description": st.session_state.edit_desc,
                        "musique": st.session_state.edit_musique,
                        "son_good": st.session_state.edit_son_good,
                        "son_bad": st.session_state.edit_son_bad
                    },
                    "questions": st.session_state.edit_questions
                }
                with open(chemin_complet, "w", encoding="utf-8") as f:
                    json.dump(donnees_globales, f, ensure_ascii=False, indent=4)
                st.success("Question ajoutée et sauvegardée avec succès ! Rechargez la page si nécessaire.")
            else:
                st.warning("Veuillez remplir la consigne, au moins une option et la réponse exacte.")

# ==========================================
# ESPACE ÉTUDIANT : PASSER UN QCM
# ==========================================
else:
    if not st.session_state.qcm_selectionne:
        st.title("🎓 Portail des Évaluations - Enolou")
        st.write("Veuillez sélectionner le QCM à lancer :")
        
        fichiers_json = [f for f in os.listdir(DOSSIER_QUIZZES) if f.endswith('.json')]
        if not fichiers_json:
            st.warning("Aucun QCM disponible dans le dossier.")
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
            st.info("💡 Cliquez pour lancer l'évaluation (active le son et la musique).")
            if st.button("Commencer le QCM 🎵", type="primary"):
                st.session_state.quiz_started = True
                st.session_state.question_start_time = time.time()
                st.rerun()
        else:
            # Lancement de la musique de fond globale
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
                
                # Barre de progression
                st.progress((q_id) / len(questions) if len(questions) > 0 else 0)
                
                # Disposition en 2 colonnes : Documents à gauche (3 parts), QCM à droite (2 parts)
                col_docs, col_qcm = st.columns([3, 2], gap="large")

                with col_docs:
                    st.markdown("### 📄 Documents de référence")
                    
                    # 1. Texte de référence
                    doc_texte = q.get('document_texte')
                    if doc_texte:
                        st.info(doc_texte)
                        
                    # 2. Image de référence
                    media = q.get('media', {})
                    img_path = media.get('image')
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)

                    # 3. Document PDF joint en téléchargement
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

                        # Lecture du son de validation (bonne/mauvaise réponse)
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