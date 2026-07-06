"""
rendezvous/presentation/urls.py
NE PAS mettre les routes auth ici — elles sont dans config/urls.py
"""
from django.urls import path
from rendezvous.presentation.views.views import (
    InscriptionView, MonProfilView,
    UtilisateurListView, StatistiquesView,
    DomaineListView, EntrepriseListView, AvisView,
    CreneauListView, CreneauDisponiblesView,
    RendezVousListView, RendezVousDetailView,
    TraiterRendezVousView, AnnulerRendezVousView,
    TableauDeBordView,
    PaiementListView, ConfirmerPaiementView, RembourserPaiementView,
    NotificationListView, MarquerLueView, MarquerToutesLuesView, 
    CalendrierView, StatistiquesAvanceesView,
    TelechargerRecuPaiementView,
    EnvoyerRecuEmailView,
    UtilisateurDetailView,
    CreerUtilisateurView,
    ActiverDesactiverUtilisateurView,
    
)





urlpatterns = [
    

    #Gestions des utilisateurs par l'admin
     # Dans urlpatterns — AVANT users/ pour éviter les conflits :
     path('users/creer/',
          CreerUtilisateurView.as_view(), name='creer-user'),
     path('users/<int:user_id>/',
          UtilisateurDetailView.as_view(), name='user-detail'),
     path('users/<int:user_id>/activer/',
          ActiverDesactiverUtilisateurView.as_view(), name='user-activer'),

    # ── Utilisateurs ──────────────────────────────────────────
    path('users/inscription/',
         InscriptionView.as_view(), name='inscription'),
    path('users/moi/',
         MonProfilView.as_view(), name='mon-profil'),
    path('users/',
         UtilisateurListView.as_view(), name='liste-users'),
    path('users/statistiques/',
         StatistiquesView.as_view(), name='statistiques'),

    # ── Domaines & Entreprises ────────────────────────────────
    path('domaines/',
         DomaineListView.as_view(), name='domaines'),
    path('entreprises/',
         EntrepriseListView.as_view(), name='entreprises'),
    path('avis/',
         AvisView.as_view(), name='avis'),

    # ── Créneaux ─────────────────────────────────────────────
    # IMPORTANT : disponibles/ AVANT creneaux/ sinon conflit
    path('creneaux/disponibles/',
         CreneauDisponiblesView.as_view(), name='creneaux-disponibles'),
    path('creneaux/',
         CreneauListView.as_view(), name='creneaux'),

    # ── Rendez-vous ───────────────────────────────────────────
    # IMPORTANT : tableau-de-bord/ AVANT <int:rdv_id>/
    path('rendezvous/tableau-de-bord/',
         TableauDeBordView.as_view(), name='rdv-dashboard'),
    path('rendezvous/',
         RendezVousListView.as_view(), name='rdv-list'),
    path('rendezvous/<int:rdv_id>/',
         RendezVousDetailView.as_view(), name='rdv-detail'),
    path('rendezvous/<int:rdv_id>/traiter/',
         TraiterRendezVousView.as_view(), name='rdv-traiter'),
    path('rendezvous/<int:rdv_id>/annuler/',
         AnnulerRendezVousView.as_view(), name='rdv-annuler'),

    # ── Paiements ─────────────────────────────────────────────
    path('paiements/',
         PaiementListView.as_view(), name='paiements'),
    path('paiements/<int:paiement_id>/confirmer/',
         ConfirmerPaiementView.as_view(), name='paiement-confirmer'),
    path('paiements/<int:paiement_id>/rembourser/',
         RembourserPaiementView.as_view(), name='paiement-rembourser'),

    # ── Notifications ─────────────────────────────────────────
    path('notifications/',
         NotificationListView.as_view(), name='notifications'),
    path('notifications/tout-lire/',
         MarquerToutesLuesView.as_view(), name='notif-tout-lire'),
    path('notifications/<int:notif_id>/lire/',
         MarquerLueView.as_view(), name='notif-lire'),

     # ___ Calendrier visuel_______________________________________
     path('calendrier/', CalendrierView.as_view(), name='calendrier'),

     #______Statistiques avec graphique_______________
     path('statistiques/avancees/',
     StatistiquesAvanceesView.as_view(), name='stats-avancees'),

     # _____Telecharger le Recu de Paiement et Envoyer de Recu Email_____________
     path('paiements/<int:paiement_id>/recu/',
          TelechargerRecuPaiementView.as_view(), name='recu-pdf'),
     path('paiements/<int:paiement_id>/envoyer-recu/',
     EnvoyerRecuEmailView.as_view(), name='envoyer-recu'),

]