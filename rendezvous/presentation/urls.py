"""
rendezvous/presentation/urls.py
NE PAS mettre les routes auth ici — elles sont dans config/urls.py
"""
from django.urls import path
from rendezvous.presentation.views.views import (
    # ── Utilisateurs ──────────────────────────────────────────
    InscriptionView, MonProfilView,
    UtilisateurListView, StatistiquesView,
    UtilisateurDetailView, CreerUtilisateurView,
    ActiverDesactiverUtilisateurView,

    # ── Domaines & Entreprises ────────────────────────────────
    DomaineListView, EntrepriseListView, AvisView,

    # ── Services (NOUVEAU) ────────────────────────────────────
    ServiceListView, PersonnelParServiceView,

    # ── Créneaux ─────────────────────────────────────────────
    CreneauListView, CreneauDisponiblesView,
    CreneauxParPersonnelView,

    # ── Rendez-vous ───────────────────────────────────────────
    RendezVousListView, RendezVousDetailView,
    TraiterRendezVousView, AnnulerRendezVousView,
    TableauDeBordView,

    # ── Paiements ─────────────────────────────────────────────
    PaiementListView, ConfirmerPaiementView, RembourserPaiementView,
    TelechargerRecuPaiementView, EnvoyerRecuEmailView,

    # ── Notifications ─────────────────────────────────────────
    NotificationListView, MarquerLueView, MarquerToutesLuesView,

    # ── Calendrier & Statistiques ─────────────────────────────
    CalendrierView, StatistiquesAvanceesView,
    PersonnelParEntrepriseView,
    ModifierPersonnelView,
)


urlpatterns = [

    # ==========================================================
    #   UTILISATEURS
    # ==========================================================
    # IMPORTANT : les routes fixes (creer/, statistiques/) doivent
    # être déclarées AVANT les routes dynamiques (<int:user_id>/)
    # sinon Django interpréterait "creer" comme un user_id

    path('users/creer/',
         CreerUtilisateurView.as_view(),            name='creer-user'),
    path('users/statistiques/',
         StatistiquesView.as_view(),                name='statistiques'),
    path('users/inscription/',
         InscriptionView.as_view(),                 name='inscription'),
    path('users/moi/',
         MonProfilView.as_view(),                   name='mon-profil'),
    path('users/',
         UtilisateurListView.as_view(),             name='liste-users'),

    # Routes dynamiques APRÈS les routes fixes
    path('users/<int:user_id>/activer/',
         ActiverDesactiverUtilisateurView.as_view(), name='user-activer'),
    path('users/<int:user_id>/',
         UtilisateurDetailView.as_view(),           name='user-detail'),

    # ==========================================================
    #   DOMAINES & ENTREPRISES
    # ==========================================================

    path('domaines/',
         DomaineListView.as_view(),                 name='domaines'),
    path('entreprises/',
         EntrepriseListView.as_view(),              name='entreprises'),
    path('avis/',
         AvisView.as_view(),                        name='avis'),

    # ==========================================================
    #   SERVICES (NOUVEAU)
    # ==========================================================
    # Ordre important : services/<id>/personnels/ AVANT services/
    # pour que Django ne confonde pas "personnels" avec un filtre

    path('services/',
         ServiceListView.as_view(),                 name='services'),
    path('services/<int:service_id>/personnels/',
         PersonnelParServiceView.as_view(),         name='service-personnels'),

    # ==========================================================
    #   CRÉNEAUX
    # ==========================================================
    # IMPORTANT : disponibles/ AVANT <int:...>/ pour éviter les conflits

    path('creneaux/disponibles/',
         CreneauDisponiblesView.as_view(),          name='creneaux-disponibles'),
    path('creneaux/',
         CreneauListView.as_view(),                 name='creneaux'),

    # Créneaux d'un personnel précis (NOUVEAU)
    # Permet au client de voir les disponibilités avant de réserver
    path('personnels/<int:personnel_id>/creneaux/',
         CreneauxParPersonnelView.as_view(),        name='creneaux-par-personnel'),

    # ==========================================================
    #   RENDEZ-VOUS
    # ==========================================================
    # IMPORTANT : les routes fixes avant les routes dynamiques

    path('rendezvous/tableau-de-bord/',
         TableauDeBordView.as_view(),               name='rdv-dashboard'),
    path('rendezvous/',
         RendezVousListView.as_view(),              name='rdv-list'),
    path('rendezvous/<int:rdv_id>/traiter/',
         TraiterRendezVousView.as_view(),           name='rdv-traiter'),
    path('rendezvous/<int:rdv_id>/annuler/',
         AnnulerRendezVousView.as_view(),           name='rdv-annuler'),
    path('rendezvous/<int:rdv_id>/',
         RendezVousDetailView.as_view(),            name='rdv-detail'),

    # ==========================================================
    #   PAIEMENTS
    # ==========================================================
    # Routes fixes (recu/, envoyer-recu/, confirmer/, rembourser/)
    # AVANT la route dynamique racine

    path('paiements/<int:paiement_id>/confirmer/',
         ConfirmerPaiementView.as_view(),           name='paiement-confirmer'),
    path('paiements/<int:paiement_id>/rembourser/',
         RembourserPaiementView.as_view(),          name='paiement-rembourser'),
    path('paiements/<int:paiement_id>/recu/',
         TelechargerRecuPaiementView.as_view(),     name='recu-pdf'),
    path('paiements/<int:paiement_id>/envoyer-recu/',
         EnvoyerRecuEmailView.as_view(),            name='envoyer-recu'),
    path('paiements/',
         PaiementListView.as_view(),                name='paiements'),

    # ==========================================================
    #   NOTIFICATIONS
    # ==========================================================
    # tout-lire/ AVANT <int:notif_id>/lire/ pour éviter le conflit

    path('notifications/tout-lire/',
         MarquerToutesLuesView.as_view(),           name='notif-tout-lire'),
    path('notifications/<int:notif_id>/lire/',
         MarquerLueView.as_view(),                  name='notif-lire'),
    path('notifications/',
         NotificationListView.as_view(),            name='notifications'),

    # ==========================================================
    #   CALENDRIER & STATISTIQUES
    # ==========================================================

    path('calendrier/',
         CalendrierView.as_view(),                  name='calendrier'),
    path('statistiques/avancees/',
         StatistiquesAvanceesView.as_view(),        name='stats-avancees'),

     path('entreprises/<int:entreprise_id>/personnels/',
          PersonnelParEntrepriseView.as_view(), name='entreprise-personnels'),
     
     path('personnels/<int:personnel_id>/',
          ModifierPersonnelView.as_view(), name='modifier-personnel'),
]