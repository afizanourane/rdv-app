# rendezvous/models.py
# Django cherche les modèles ici pour générer les migrations.
# On réexporte simplement depuis l'infrastructure.

from rendezvous.infrastructure.django_models.models import (
    UtilisateurModel,
    ClientModel,
    AdministrateurModel,
    PersonnelModel,
    DomaineModel,
    EntrepriseModel,
    AvisModel,
    PlageCreneauModel,
    CreneauModel,
    RendezVousModel,
    HistoriqueStatutModel,
    DocumentModel,
    PaiementModel,
    NotificationModel,
)