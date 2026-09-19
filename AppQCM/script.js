document.addEventListener("DOMContentLoaded", async () => {
    const container = document.getElementById("qcm-container"); // Assurez-vous que c'est l'ID de votre conteneur dans index.html
    
    if (!container) return;

    try {
        // Chargement de la liste des QCM
        const reponse = await fetch('index-qcm.json');
        const listeQCM = await reponse.json();

        container.innerHTML = ""; // Nettoyage

        listeQCM.forEach(qcm => {
            const card = document.createElement("div");
            card.className = "qcm-card"; // Votre classe CSS pour les cartes
            
            // Gestion de l'image (si elle existe dans le JSON)
            let imageHtml = '';
            if (qcm.image && qcm.image !== "") {
                imageHtml = `<img src="${qcm.image}" alt="${qcm.titre}" class="qcm-img" onerror="this.style.display='none'">`;
            } else {
                imageHtml = `<div class="qcm-placeholder"><i class="fas fa-file-alt"></i></div>`;
            }

            card.innerHTML = `
                <div class="card-header">
                    <h3>${qcm.titre}</h3>
                </div>
                <div class="card-body">
                    ${imageHtml}
                    <span class="badge"><i class="fas fa-bolt"></i> ${qcm.questions} Questions</span>
                    <p>${qcm.description}</p>
                </div>
                <div class="card-footer">
                    <button class="btn-selectionner" data-fichier="${qcm.fichier}">Sélectionner</button>
                </div>
            `;

            // Action au clic sur la carte ou le bouton
            card.addEventListener("click", () => {
                // Retirer la sélection des autres cartes
                document.querySelectorAll('.qcm-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');

                // Sauvegarder le choix pour la page du quiz
                localStorage.setItem('qcmActif', qcm.fichier);
            });

            container.appendChild(card);
        });

    } catch (erreur) {
        console.error("Erreur lors du chargement des QCM :", erreur);
        container.innerHTML = "<p>Impossible de charger la liste des QCM.</p>";
    }
});