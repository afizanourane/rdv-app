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
import os
import uuid
import random
import string


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


def chemin_photo_profil(instance, filename):
    ext = filename.split('.')[-1].lower()
    nom = f"profil_{instance.id}.{ext}"
    return os.path.join('photos_profil', nom)


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
    photo     = models.ImageField(
        upload_to=chemin_photo_profil,
        null=True, blank=True,
        verbose_name='Photo de profil',
    )
    deux_fa_active = models.BooleanField(default=False, verbose_name='2FA activée')

    # Champs requis par Django
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UtilisateurManager()

    # On utilise l'email pour se connecter (au lieu du username)
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['nom', 'prenom']

    class Meta:
        db_table     = 'utilisateurs'   # nom réel de la table en PostgreSQL
        verbose_name = 'Utilisateur'

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.role})"


# =============================================================
#   PROFILS PAR RÔLE
# =============================================================

class ClientModel(models.Model):
    """Table SQL 'clients' — profil spécifique au rôle Client."""

    # OneToOne : 1 client = 1 utilisateur, pas plus
    utilisateur = models.OneToOneField(
        UtilisateurModel,
        on_delete=models.CASCADE,       # si l'utilisateur est supprimé → le client aussi
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
    # null=True, blank=True : un personnel peut être indépendant (sans entreprise)
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

    # ManyToMany : un personnel peut proposer plusieurs services
    # et un même service peut être proposé par plusieurs personnels
    # Ex : Dr. Dupont propose "Consultation" et "Suivi post-op"
    # blank=True : au moment de la création, aucun service n'est obligatoire
    # related_name='personnels' → depuis un service : service.personnels.all()
    #   donne la liste de tous les personnels qui proposent ce service
    services_proposes = models.ManyToManyField(
        'ServiceModel',
        blank=True,
        related_name='personnels'
    )

    class Meta:
        db_table = 'personnels'

    def __str__(self):
        return f"Personnel: {self.utilisateur} — {self.poste}"


# =============================================================
#   DOMAINE ET ENTREPRISE
# =============================================================

class DomaineModel(models.Model):
    """
    Table SQL 'domaines'.
    Catégorie métier d'une entreprise.
    Ex : Santé, Beauté, Juridique, Informatique.
    """

    nom_domaine = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'domaines'
        ordering = ['nom_domaine']

    def __str__(self):
        return self.nom_domaine


class EntrepriseModel(models.Model):
    """
    Table SQL 'entreprises'.
    Une entreprise appartient à un domaine et propose des services.
    """

    nom_entreprise = models.CharField(max_length=200)
    adresse        = models.TextField()
    telephone      = models.CharField(max_length=20)
    email          = models.EmailField(unique=True)
    description    = models.TextField(blank=True)
    est_active     = models.BooleanField(default=True)
    date_creation  = models.DateTimeField(auto_now_add=True)

    # PROTECT : on ne peut pas supprimer un domaine qui a encore des entreprises
    # Oblige à réassigner les entreprises avant de supprimer un domaine
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


# =============================================================
#   SERVICE
# =============================================================

class ServiceModel(models.Model):
    """
    Table SQL 'services'.
    Un service est une prestation précise proposée par une entreprise.
    Ex : 'Consultation générale', 'Coupe femme', 'Audit comptable'.
    Chaque service a un prix fixé à l'avance par l'entreprise.
    """

    nom         = models.CharField(max_length=200)
    # TextField : description longue sans limite fixe
    description = models.TextField(blank=True)

    # DecimalField pour l'argent : évite les erreurs d'arrondi du float
    # max_digits=10 → jusqu'à 99 999 999 FCFA
    # decimal_places=2 → centimes inclus (ex : 5000.00 FCFA)
    prix = models.DecimalField(max_digits=10, decimal_places=2)

    # Durée estimée du service en minutes (ex : 30, 60, 90)
    # Utile pour calculer automatiquement les créneaux disponibles
    duree_minutes = models.PositiveIntegerField(default=30)

    # CASCADE : si l'entreprise est supprimée, ses services le sont aussi
    # Logique : sans entreprise, le service n'a plus de raison d'exister
    # related_name='services' → depuis une entreprise : entreprise.services.all()
    entreprise = models.ForeignKey(
        EntrepriseModel,
        on_delete=models.CASCADE,
        related_name='services'
    )

    # Un service peut être désactivé sans être supprimé
    # Ex : service saisonnier ou temporairement indisponible
    est_actif     = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table     = 'services'
        ordering     = ['nom']
        verbose_name = 'Service'

    def __str__(self):
        return f"{self.nom} — {self.prix} FCFA ({self.entreprise})"


# =============================================================
#   AVIS
# =============================================================

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
        # Un client ne peut laisser qu'un seul avis par entreprise
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
    """Table SQL 'creneaux' — créneau individuel d'un personnel."""

    STATUT_CHOICES = [
        ('disponible', 'Disponible'),
        ('reserve',    'Réservé'),
        ('annule',     'Annulé'),
        ('termine',    'Terminé'),
    ]

    # Le créneau appartient à un personnel précis
    # CASCADE : si le personnel est supprimé, ses créneaux le sont aussi
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

    # PROTECT : interdit de supprimer un créneau déjà réservé
    creneau = models.ForeignKey(
        CreneauModel, on_delete=models.PROTECT, related_name='rendezvous'
    )

    # Le service choisi par le client au moment de la demande
    # SET_NULL : si le service est supprimé plus tard, le RDV reste intact
    # null=True, blank=True : compatibilité avec les anciens RDV sans service
    service = models.ForeignKey(
        ServiceModel,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rendezvous'
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

    # Snapshot du prix au moment de la prise de RDV
    # IMPORTANT : on ne lit pas service.prix directement car le prix
    # peut changer dans le futur. Ce champ fige le prix comme un devis.
    # null=True, blank=True : compatibilité avec les anciens RDV
    prix_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True, blank=True,
        verbose_name='Prix au moment du RDV'
    )

    # Verrou de paiement — False par défaut (paiement bloqué)
    # Passe à True UNIQUEMENT quand le personnel confirme le RDV
    # L'use case EffectuerPaiementUseCase vérifie ce champ avant tout traitement
    # False → RDV en attente ou refusé → paiement impossible
    # True  → RDV confirmé par le personnel → paiement autorisé
    paiement_autorise = models.BooleanField(
        default=False,
        verbose_name='Paiement autorisé'
    )

    class Meta:
        db_table     = 'rendezvous'
        ordering     = ['-date_creation']
        verbose_name = 'Rendez-vous'

    def __str__(self):
        return f"RDV #{self.pk} — {self.client} ({self.statut})"


# =============================================================
#   HISTORIQUE ET DOCUMENTS
# =============================================================

class HistoriqueStatutModel(models.Model):
    """
    Table SQL 'historique_statuts'.
    Enregistrement immuable — jamais modifié, uniquement ajouté.
    Trace chaque changement de statut d'un RDV.
    """

    rendezvous      = models.ForeignKey(
        RendezVousModel, on_delete=models.CASCADE, related_name='historique'
    )
    ancien_statut   = models.CharField(max_length=20)
    nouveau_statut  = models.CharField(max_length=20)
    date_changement = models.DateTimeField(auto_now_add=True)
    change_par      = models.ForeignKey(
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
    est_lue      = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_lecture  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-date_creation']

    def __str__(self):
        lu = '✓' if self.est_lue else '●'
        return f"{lu} {self.titre}"


# =============================================================
#   RAPPELS ET SÉCURITÉ
# =============================================================

class RappelModel(models.Model):
    """Trace les rappels envoyés pour éviter les doublons."""

    TYPE_CHOICES = [
        ('24h', 'Rappel 24 heures avant'),
        ('1h',  'Rappel 1 heure avant'),
    ]
    STATUT_CHOICES = [
        ('envoye', 'Envoyé'),
        ('echoue', 'Échoué'),
    ]

    rendezvous   = models.ForeignKey(
        RendezVousModel, on_delete=models.CASCADE, related_name='rappels'
    )
    type_rappel  = models.CharField(max_length=10, choices=TYPE_CHOICES)
    email_envoye = models.EmailField()
    statut       = models.CharField(
        max_length=10, choices=STATUT_CHOICES, default='envoye'
    )
    date_envoi = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = 'rappels'
        # Un seul rappel de chaque type par RDV — évite les doublons
        unique_together = [['rendezvous', 'type_rappel']]
        verbose_name        = 'Rappel'
        verbose_name_plural = 'Rappels'

    def __str__(self):
        return f"Rappel {self.type_rappel} — RDV #{self.rendezvous_id}"

# =============================================================
#   CHAT — MESSAGERIE INTERNE
# =============================================================

class ConversationModel(models.Model):
    """
    Table SQL 'conversations'.
    Une conversation regroupe les messages entre 2 participants.
    2 types possibles :
    - 'client_personnel' : client discute avec le personnel d'un RDV
    - 'admin_personnel'  : admin discute avec un personnel
    """
    TYPE_CHOICES = [
        ('client_personnel', 'Client ↔ Personnel'),
        ('admin_personnel',  'Admin ↔ Personnel'),
    ]

    type_conversation = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='client_personnel'
    )

    # Lié à un RDV précis pour les conversations client ↔ personnel
    # null si c'est une conversation admin ↔ personnel
    rdv = models.ForeignKey(
        RendezVousModel,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='conversations'
    )

    # Participants — selon le type, l'un ou l'autre sera null
    # Client : présent si type = 'client_personnel'
    client = models.ForeignKey(
        ClientModel,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='conversations'
    )

    # Personnel : toujours présent
    personnel = models.ForeignKey(
        PersonnelModel,
        on_delete=models.CASCADE,
        related_name='conversations'
    )

    # Admin : présent si type = 'admin_personnel'
    admin = models.ForeignKey(
        AdministrateurModel,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='conversations'
    )

    date_creation     = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table  = 'conversations'
        ordering  = ['-date_modification']
        # Un seul fil de discussion par RDV entre client et personnel
        unique_together = [['rdv', 'client', 'personnel']]
        verbose_name = 'Conversation'

    def __str__(self):
        if self.type_conversation == 'client_personnel':
            return f"Conv Client↔Personnel — RDV #{self.rdv_id}"
        return f"Conv Admin↔Personnel — {self.personnel}"


class MessageModel(models.Model):
    """
    Table SQL 'messages'.
    Un message appartient à une conversation.
    Immuable : jamais modifié, uniquement ajouté.
    """

    # La conversation à laquelle appartient ce message
    conversation = models.ForeignKey(
        ConversationModel,
        on_delete=models.CASCADE,
        related_name='messages'
    )

    # Qui a envoyé ce message
    expediteur = models.ForeignKey(
        UtilisateurModel,
        on_delete=models.CASCADE,
        related_name='messages_envoyes'
    )

    # Le contenu du message
    contenu = models.TextField()

    # False → message non lu par le destinataire
    # True  → message lu
    est_lu = models.BooleanField(default=False)

    # Généré automatiquement à la création — jamais modifié
    date_envoi = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        # Du plus ancien au plus récent pour l'affichage
        ordering  = ['date_envoi']
        verbose_name = 'Message'

    def __str__(self):
        return f"Msg de {self.expediteur} — {self.date_envoi.strftime('%d/%m %H:%M')}"
    
class TokenResetModel(models.Model):
    """Token sécurisé pour la réinitialisation de mot de passe."""

    utilisateur = models.ForeignKey(
        UtilisateurModel, on_delete=models.CASCADE, related_name='tokens_reset'
    )
    # uuid4 : token unique aléatoire, impossible à deviner
    token           = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    date_expiration = models.DateTimeField()
    utilise         = models.BooleanField(default=False)
    date_creation   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table     = 'tokens_reset'
        verbose_name = 'Token de réinitialisation'

    def est_valide(self):
        from django.utils import timezone
        return not self.utilise and self.date_expiration > timezone.now()

    def __str__(self):
        return f"Token reset — {self.utilisateur.email}"


def generer_code_otp():
    """Génère un code numérique aléatoire à 6 chiffres."""
    return ''.join(random.choices(string.digits, k=6))


class CodeOtpModel(models.Model):
    """Code OTP à 6 chiffres pour la 2FA."""

    utilisateur = models.ForeignKey(
        UtilisateurModel, on_delete=models.CASCADE, related_name='codes_otp'
    )
    # default=generer_code_otp : appelé à chaque création d'instance
    code            = models.CharField(max_length=6, default=generer_code_otp)
    date_expiration = models.DateTimeField()
    utilise         = models.BooleanField(default=False)
    date_creation   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table     = 'codes_otp'
        verbose_name = 'Code OTP'

    def est_valide(self):
        from django.utils import timezone
        return not self.utilise and self.date_expiration > timezone.now()

    def __str__(self):
        return f"OTP {self.code} — {self.utilisateur.email}"