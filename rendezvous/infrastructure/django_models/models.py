"""
=============================================================
  rendezvous/infrastructure/django_models/models.py

  COUCHE INFRASTRUCTURE — Modèles Django (tables PostgreSQL)
=============================================================
  C'est ICI qu'on parle à PostgreSQL via Django ORM.
  Ces modèles font le mapping entre Python et les tables SQL.

  Si on changeait de base de données, seul ce fichier change.
  Toute la logique métier (Domain) reste intacte.
=============================================================
"""
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
from django.db import models


# =============================================================
#   UTILISATEUR (modèle personnalisé)
# =============================================================

class UtilisateurManager(BaseUserManager):
    """
    Manager Django : explique à Django comment créer un utilisateur.
    Nécessaire car on utilise l'email comme identifiant (pas username).
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire.")
        email = self.normalize_email(email)        # met en minuscules
        user = self.model(email=email, **extra_fields)
        user.set_password(password)                # hache le mot de passe
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # Un superuser est forcément admin, staff et superuser
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)


class UtilisateurModel(AbstractBaseUser, PermissionsMixin):
    """
    Table SQL 'utilisateurs' — remplace le User Django par défaut.
    On se connecte avec l'email et non un username.
    """
    ROLE_CHOICES = [
        ('client',    'Client'),
        ('admin',     'Administrateur'),
        ('personnel', 'Personnel'),
    ]

    nom       = models.CharField(max_length=100)
    prenom    = models.CharField(max_length=100)
    # unique=True car c'est notre clé de connexion
    email     = models.EmailField(unique=True)
    telephone = models.CharField(max_length=20, blank=True)
    role      = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')

    # Champs requis par Django
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UtilisateurManager()

    # On utilise l'email pour se connecter (au lieu du username)
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['nom', 'prenom']

    class Meta:
        db_table = 'utilisateurs'   # nom réel de la table en PostgreSQL
        verbose_name = 'Utilisateur'

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.role})"


class ClientModel(models.Model):
    """Table SQL 'clients' — profil spécifique au rôle Client."""

    # OneToOne : 1 client = 1 utilisateur, pas plus
    utilisateur = models.OneToOneField(
        UtilisateurModel,
        on_delete=models.CASCADE,        # si l'utilisateur est supprimé → le client aussi
        related_name='profil_client'
    )
    adresse = models.TextField(blank=True)

    class Meta:
        db_table = 'clients'

    def __str__(self):
        return f"Client: {self.utilisateur}"


class AdministrateurModel(models.Model):
    """Table SQL 'administrateurs'."""

    utilisateur = models.OneToOneField(
        UtilisateurModel,
        on_delete=models.CASCADE,
        related_name='profil_admin'
    )
    role_admin = models.CharField(max_length=100, default='Administrateur général')

    class Meta:
        db_table = 'administrateurs'

    def __str__(self):
        return f"Admin: {self.utilisateur}"


class PersonnelModel(models.Model):
    """Table SQL 'personnels' — lié à une entreprise et un domaine."""

    utilisateur = models.OneToOneField(
        UtilisateurModel,
        on_delete=models.CASCADE,
        related_name='profil_personnel'
    )
    poste = models.CharField(max_length=100)

    # SET_NULL : si l'entreprise est supprimée, le personnel reste sans entreprise
    entreprise = models.ForeignKey(
        'EntrepriseModel',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='personnels'
    )
    domaine = models.ForeignKey(
        'DomaineModel',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='personnels_domaine'
    )

    class Meta:
        db_table = 'personnels'

    def __str__(self):
        return f"Personnel: {self.utilisateur} — {self.poste}"


# =============================================================
#   DOMAINE ET ENTREPRISE
# =============================================================

class DomaineModel(models.Model):
    """Table SQL 'domaines'."""

    nom_domaine = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'domaines'
        ordering = ['nom_domaine']

    def __str__(self):
        return self.nom_domaine


class EntrepriseModel(models.Model):
    """Table SQL 'entreprises'."""

    nom_entreprise = models.CharField(max_length=200)
    adresse        = models.TextField()
    telephone      = models.CharField(max_length=20)
    email          = models.EmailField(unique=True)
    description    = models.TextField(blank=True)
    est_active     = models.BooleanField(default=True)
    date_creation  = models.DateTimeField(auto_now_add=True)

    # PROTECT : on ne peut pas supprimer un domaine qui a des entreprises
    domaine = models.ForeignKey(
        DomaineModel,
        on_delete=models.PROTECT,
        related_name='entreprises'
    )

    class Meta:
        db_table = 'entreprises'
        ordering = ['nom_entreprise']

    def __str__(self):
        return self.nom_entreprise


class AvisModel(models.Model):
    """Table SQL 'avis' — évaluations des entreprises."""

    entreprise = models.ForeignKey(
        EntrepriseModel, on_delete=models.CASCADE, related_name='avis'
    )
    client = models.ForeignKey(
        ClientModel, on_delete=models.CASCADE, related_name='avis'
    )
    note        = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    commentaire = models.TextField(blank=True)
    date_avis   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'avis'
        # Un client ne peut laisser qu'un avis par entreprise
        unique_together = ('entreprise', 'client')


# =============================================================
#   CRÉNEAUX
# =============================================================

class PlageCreneauModel(models.Model):
    """Table SQL 'plages_creneaux' — plage horaire d'une entreprise."""

    entreprise  = models.ForeignKey(
        EntrepriseModel, on_delete=models.CASCADE, related_name='plages'
    )
    date_plage  = models.DateField()
    heure_debut = models.TimeField()
    heure_fin   = models.TimeField()
    libelle     = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'plages_creneaux'
        ordering = ['date_plage', 'heure_debut']

    def __str__(self):
        return f"{self.entreprise} — {self.date_plage}"


class CreneauModel(models.Model):
    """Table SQL 'creneaux' — créneau individuel."""

    STATUT_CHOICES = [
        ('disponible', 'Disponible'),
        ('reserve',    'Réservé'),
        ('annule',     'Annulé'),
        ('termine',    'Terminé'),
    ]

    personnel   = models.ForeignKey(
        PersonnelModel, on_delete=models.CASCADE, related_name='creneaux'
    )
    heure_debut = models.TimeField()
    heure_fin   = models.TimeField()
    statut      = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='disponible'
    )
    # SET_NULL : si la plage est supprimée, le créneau reste
    plage = models.ForeignKey(
        PlageCreneauModel,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='creneaux'
    )

    class Meta:
        db_table = 'creneaux'
        ordering = ['heure_debut']

    def __str__(self):
        return f"Créneau {self.heure_debut}-{self.heure_fin} ({self.statut})"


# =============================================================
#   RENDEZ-VOUS
# =============================================================

class RendezVousModel(models.Model):
    """Table SQL 'rendezvous' — cœur de l'application."""

    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('confirme',   'Confirmé'),
        ('refuse',     'Refusé'),
        ('annule',     'Annulé'),
        ('termine',    'Terminé'),
    ]

    client = models.ForeignKey(
        ClientModel, on_delete=models.CASCADE, related_name='rendezvous'
    )
    # PROTECT : ne pas supprimer un créneau réservé
    creneau = models.ForeignKey(
        CreneauModel, on_delete=models.PROTECT, related_name='rendezvous'
    )
    confirmation      = models.BooleanField(default=False)
    statut            = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='en_attente'
    )
    description       = models.TextField(blank=True)
    date_creation     = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    traite_par        = models.ForeignKey(
        AdministrateurModel,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rendezvous_traites'
    )
    motif_refus = models.TextField(blank=True)

    class Meta:
        db_table = 'rendezvous'
        ordering = ['-date_creation']
        verbose_name = 'Rendez-vous'

    def __str__(self):
        return f"RDV #{self.pk} — {self.client} ({self.statut})"


class HistoriqueStatutModel(models.Model):
    """
    Table SQL 'historique_statuts'.
    Enregistrement immuable — jamais modifié, uniquement ajouté.
    """
    rendezvous    = models.ForeignKey(
        RendezVousModel, on_delete=models.CASCADE, related_name='historique'
    )
    ancien_statut  = models.CharField(max_length=20)
    nouveau_statut = models.CharField(max_length=20)
    date_changement = models.DateTimeField(auto_now_add=True)
    change_par     = models.ForeignKey(
        UtilisateurModel, on_delete=models.SET_NULL, null=True
    )
    commentaire = models.TextField(blank=True)

    class Meta:
        db_table = 'historique_statuts'
        ordering = ['-date_changement']


class DocumentModel(models.Model):
    """Table SQL 'documents' — pièces jointes d'un rendez-vous."""

    TYPE_CHOICES = [
        ('contrat',      'Contrat'),
        ('bon_commande', 'Bon de commande'),
        ('photo',        'Photo'),
        ('autre',        'Autre'),
    ]

    rendezvous    = models.ForeignKey(
        RendezVousModel, on_delete=models.CASCADE, related_name='documents'
    )
    # Les fichiers sont stockés dans media/documents/2025/06/
    fichier       = models.FileField(upload_to='documents/%Y/%m/')
    type_document = models.CharField(max_length=20, choices=TYPE_CHOICES, default='autre')
    nom           = models.CharField(max_length=200)
    date_upload   = models.DateTimeField(auto_now_add=True)
    uploade_par   = models.ForeignKey(
        UtilisateurModel,
        on_delete=models.SET_NULL,
        null=True,
        related_name='documents_uploades'
    )

    class Meta:
        db_table = 'documents'


# =============================================================
#   PAIEMENT ET NOTIFICATION
# =============================================================

class PaiementModel(models.Model):
    """Table SQL 'paiements'."""

    MODE_CHOICES = [
        ('carte',        'Carte bancaire'),
        ('mobile_money', 'Mobile Money'),
        ('virement',     'Virement bancaire'),
        ('especes',      'Espèces'),
    ]
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('paye',       'Payé'),
        ('rembourse',  'Remboursé'),
        ('echoue',     'Échoué'),
    ]

    # OneToOne : un rendez-vous = un seul paiement
    rendezvous = models.OneToOneField(
        RendezVousModel,
        on_delete=models.PROTECT,
        related_name='paiement',
        null=True, blank=True
    )
    montant               = models.DecimalField(max_digits=10, decimal_places=2)
    mode_paiement         = models.CharField(max_length=20, choices=MODE_CHOICES)
    statut                = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='en_attente'
    )
    date_paiement         = models.DateTimeField(auto_now_add=True)
    date_modification     = models.DateTimeField(auto_now=True)
    reference_transaction = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'paiements'
        ordering = ['-date_paiement']

    def __str__(self):
        return f"Paiement #{self.pk} — {self.montant} FCFA ({self.statut})"


class NotificationModel(models.Model):
    """Table SQL 'notifications'."""

    TYPE_CHOICES = [
        ('rendezvous', 'Rendez-vous'),
        ('paiement',   'Paiement'),
        ('systeme',    'Système'),
    ]

    destinataire      = models.ForeignKey(
        UtilisateurModel, on_delete=models.CASCADE, related_name='notifications'
    )
    titre             = models.CharField(max_length=200)
    message           = models.TextField()
    type_notification = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default='systeme'
    )
    est_lue           = models.BooleanField(default=False)
    date_creation     = models.DateTimeField(auto_now_add=True)
    date_lecture      = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-date_creation']

    def __str__(self):
        lu = '✓' if self.est_lue else '●'
        return f"{lu} {self.titre}"