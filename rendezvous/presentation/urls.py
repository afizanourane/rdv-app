"""
rendezvous/presentation/urls.py
ATTENTION : ce fichier ne contient PAS les routes auth
car elles sont déjà dans config/urls.py
"""
from django.urls import path
from rendezvous.presentation.views.views import (
    # Utilisateurs
    InscriptionView,
    MonProfilView,
    UtilisateurListView,
    StatistiquesView,
    # Entreprises
    DomaineListView,
    EntrepriseListView,
    AvisView,
    # Créneaux
    CreneauListView,
    CreneauDisponiblesView,
    # Rendez-vous
    RendezVousListView,
    RendezVousDetailView,
    TraiterRendezVousView,
    AnnulerRendezVousView,
    TableauDeBordView,
    # Paiements
    PaiementListView,
    ConfirmerPaiementView,
    RembourserPaiementView,
    # Notifications
    NotificationListView,
    MarquerLueView,
    MarquerToutesLuesView,
)

urlpatterns = [

    # ── Utilisateurs ──────────────────────────────────────────
    path('users/inscription/',
         InscriptionView.as_view(),
         name='inscription'),

    path('users/moi/',
         MonProfilView.as_view(),
         name='mon-profil'),

    path('users/',
         UtilisateurListView.as_view(),
         name='liste-users'),

    path('users/statistiques/',
         StatistiquesView.as_view(),
         name='statistiques'),

    # ── Entreprises ───────────────────────────────────────────
    path('domaines/',
         DomaineListView.as_view(),
         name='domaines'),

    path('entreprises/',
         EntrepriseListView.as_view(),
         name='entreprises'),

    path('avis/',
         AvisView.as_view(),
         name='avis'),

    # ── Créneaux ──────────────────────────────────────────────
    path('creneaux/',
         CreneauListView.as_view(),
         name='creneaux'),

    path('creneaux/disponibles/',
         CreneauDisponiblesView.as_view(),
         name='creneaux-disponibles'),

    # ── Rendez-vous ───────────────────────────────────────────
    path('rendezvous/',
         RendezVousListView.as_view(),
         name='rdv-list'),

    path('rendezvous/tableau-de-bord/',
         TableauDeBordView.as_view(),
         name='rdv-dashboard'),

    path('rendezvous/<int:rdv_id>/',
         RendezVousDetailView.as_view(),
         name='rdv-detail'),

    path('rendezvous/<int:rdv_id>/traiter/',
         TraiterRendezVousView.as_view(),
         name='rdv-traiter'),

    path('rendezvous/<int:rdv_id>/annuler/',
         AnnulerRendezVousView.as_view(),
         name='rdv-annuler'),

    # ── Paiements ─────────────────────────────────────────────
    path('paiements/',
         PaiementListView.as_view(),
         name='paiements'),

    path('paiements/<int:paiement_id>/confirmer/',
         ConfirmerPaiementView.as_view(),
         name='paiement-confirmer'),

    path('paiements/<int:paiement_id>/rembourser/',
         RembourserPaiementView.as_view(),
         name='paiement-rembourser'),

    # ── Notifications ─────────────────────────────────────────
    path('notifications/',
         NotificationListView.as_view(),
         name='notifications'),

    path('notifications/tout-lire/',
         MarquerToutesLuesView.as_view(),
         name='notif-tout-lire'),

    path('notifications/<int:notif_id>/lire/',
         MarquerLueView.as_view(),
         name='notif-lire'),
]