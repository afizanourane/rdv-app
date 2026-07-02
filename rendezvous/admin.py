"""
=============================================================
  rendezvous/admin.py

  Enregistrement des modèles dans l'interface admin Django
=============================================================
  L'interface admin est accessible sur : /admin/
  Elle permet de gérer les données directement via le navigateur.
=============================================================
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from rendezvous.infrastructure.django_models.models import (
    UtilisateurModel, ClientModel, AdministrateurModel, PersonnelModel,
    DomaineModel, EntrepriseModel, AvisModel,
    PlageCreneauModel, CreneauModel,
    RendezVousModel, HistoriqueStatutModel, DocumentModel,
    PaiementModel, NotificationModel,
)


@admin.register(UtilisateurModel)
class UtilisateurAdmin(UserAdmin):
    list_display  = ['email', 'nom', 'prenom', 'role', 'is_active', 'date_joined']
    list_filter   = ['role', 'is_active']
    search_fields = ['email', 'nom', 'prenom']
    ordering      = ['-date_joined']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations', {'fields': ('nom', 'prenom', 'telephone', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'fields': ('email', 'nom', 'prenom', 'role', 'password1', 'password2')
        }),
    )


@admin.register(RendezVousModel)
class RendezVousAdmin(admin.ModelAdmin):
    list_display  = ['id', 'client', 'creneau', 'statut', 'confirmation', 'date_creation']
    list_filter   = ['statut', 'confirmation']
    search_fields = ['client__utilisateur__email']
    ordering      = ['-date_creation']


# Enregistrements simples
admin.site.register(ClientModel)
admin.site.register(AdministrateurModel)
admin.site.register(PersonnelModel)
admin.site.register(DomaineModel)
admin.site.register(EntrepriseModel)
admin.site.register(AvisModel)
admin.site.register(PlageCreneauModel)
admin.site.register(CreneauModel)
admin.site.register(HistoriqueStatutModel)
admin.site.register(DocumentModel)
admin.site.register(PaiementModel)
admin.site.register(NotificationModel)