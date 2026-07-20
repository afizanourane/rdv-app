"""
=============================================================
  rendezvous/presentation/serializers/serializers.py

  COUCHE PRESENTATION — Serializers
=============================================================
  Les serializers font deux choses :
  1. Valider les données JSON entrantes (POST/PUT)
  2. Convertir les objets Django en JSON pour la réponse

  Ils ne contiennent pas de logique métier.
=============================================================
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from rendezvous.infrastructure.django_models.models import (
    UtilisateurModel, ClientModel, PersonnelModel,
    DomaineModel, EntrepriseModel, AvisModel,
    PlageCreneauModel, CreneauModel,
    RendezVousModel, HistoriqueStatutModel, DocumentModel,
    PaiementModel, NotificationModel, ServiceModel,
)


# =============================================================
#   AUTHENTIFICATION
# =============================================================

class LoginSerializer(TokenObtainPairSerializer):
    """
    Surcharge du login JWT pour enrichir la réponse.
    Le frontend reçoit le token + les infos de l'utilisateur.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Données encodées dans le token JWT
        token['nom']    = user.nom
        token['prenom'] = user.prenom
        token['role']   = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Ajouter les infos utilisateur dans la réponse JSON
        data['utilisateur'] = {
            'id':         self.user.pk,
            'nom_complet': f"{self.user.prenom} {self.user.nom}",
            'email':      self.user.email,
            'role':       self.user.role,
        }
        return data


# =============================================================
#   UTILISATEUR
# =============================================================

class InscriptionSerializer(serializers.Serializer):
    """Valide les données d'inscription."""
    nom            = serializers.CharField(max_length=100)
    prenom         = serializers.CharField(max_length=100)
    email          = serializers.EmailField()
    telephone      = serializers.CharField(max_length=20, required=False, default='')
    # write_only = ce champ n'apparaît jamais dans les réponses
    password       = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    role           = serializers.ChoiceField(
        choices=['client', 'admin', 'personnel'],
        default='client'
    )

class UtilisateurSerializer(serializers.ModelSerializer):
    photo_url    = serializers.SerializerMethodField()
    nom_complet  = serializers.SerializerMethodField()  # ← ajouter ça
    profil_personnel_id = serializers.SerializerMethodField()

    class Meta:
        model  = UtilisateurModel
        fields = [
            'id', 'nom', 'prenom', 'nom_complet', 'email',
            'telephone', 'role', 'is_active', 'date_joined',
            'photo', 'photo_url', 'deux_fa_active',
            'profil_personnel_id',  # ← AJOUTER
        ]
        extra_kwargs = {
            'photo': {'required': False, 'allow_null': True},
        }
    def get_profil_personnel_id(self, obj):
        # Retourne l'ID du profil PersonnelModel si l'utilisateur est personnel
        try:
            return obj.profil_personnel.id
        except Exception:
            return None
    def get_nom_complet(self, obj):
        return f"{obj.prenom} {obj.nom}".strip()

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return f"http://127.0.0.1:8000{obj.photo.url}"
        return None

class MettreAJourProfilSerializer(serializers.Serializer):
    """Valide les données de mise à jour du profil."""
    nom       = serializers.CharField(max_length=100, required=False)
    prenom    = serializers.CharField(max_length=100, required=False)
    telephone = serializers.CharField(max_length=20, required=False)


class ClientSerializer(serializers.ModelSerializer):
    utilisateur = UtilisateurSerializer(read_only=True)

    class Meta:
        model  = ClientModel
        fields = ['id', 'utilisateur', 'adresse']


class PersonnelSerializer(serializers.ModelSerializer):
    """
    Serializer enrichi du Personnel.
    Inclut ses services proposés et son entreprise
    pour que le client puisse choisir un personnel
    en connaissant exactement ce qu'il propose.
    """
    utilisateur = UtilisateurSerializer(read_only=True)

    # SerializerMethodField : calcule une valeur à partir de l'objet
    # ici on appelle get_services_proposes() défini ci-dessous
    services_proposes = serializers.SerializerMethodField()

    # Nom lisible de l'entreprise (null si personnel indépendant)
    entreprise_nom = serializers.CharField(
        source='entreprise.nom_entreprise',
        read_only=True,
        default=None    # null si le personnel n'a pas d'entreprise
    )

    # Nom du domaine via entreprise → domaine
    domaine_nom = serializers.CharField(
        source='domaine.nom_domaine',
        read_only=True,
        default=None
    )

    class Meta:
        model  = PersonnelModel
        fields = [
            'id',
            'utilisateur',
            'poste',
            'entreprise',      # ID de l'entreprise
            'entreprise_nom',  # nom lisible
            'domaine',         # ID du domaine
            'domaine_nom',     # nom lisible
            'services_proposes', # liste des services que ce personnel propose
        ]

    def get_services_proposes(self, obj):
        """
        Retourne la liste des services proposés par ce personnel.
        On réutilise ServiceSerializer pour avoir prix + durée + nom.
        """
        # obj.services_proposes.all() → QuerySet des services ManyToMany
        services = obj.services_proposes.filter(est_actif=True)
        return ServiceSerializer(services, many=True).data

# =============================================================
#   DOMAINE ET ENTREPRISE
# =============================================================

class DomaineSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DomaineModel
        fields = ['id', 'nom_domaine', 'description']


class EntrepriseSerializer(serializers.ModelSerializer):
    domaine_nom  = serializers.CharField(source='domaine.nom_domaine', read_only=True)
    note_moyenne = serializers.SerializerMethodField()

    class Meta:
        model  = EntrepriseModel
        fields = [
            'id', 'nom_entreprise', 'adresse', 'telephone',
            'email', 'description', 'domaine', 'domaine_nom',
            'est_active', 'date_creation', 'note_moyenne'
        ]
        read_only_fields = ['date_creation']

    def get_note_moyenne(self, obj):
        avis = obj.avis.all()
        if not avis.exists():
            return None
        return round(sum(a.note for a in avis) / avis.count(), 1)


class AvisSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AvisModel
        fields = ['id', 'entreprise', 'client', 'note', 'commentaire', 'date_avis']
        read_only_fields = ['date_avis', 'client']
# =============================================================
#   SERVICE
# =============================================================

class ServiceSerializer(serializers.ModelSerializer):
    """
    Serializer du modèle Service.
    Affiche le nom de l'entreprise en plus de son ID
    pour que le frontend n'ait pas à faire une deuxième requête.
    """
    # source='entreprise.nom_entreprise' : navigue la FK automatiquement
    # read_only=True : ce champ est calculé, pas envoyé par le client
    entreprise_nom = serializers.CharField(
        source='entreprise.nom_entreprise',
        read_only=True
    )

    # Idem pour le domaine via entreprise → domaine
    domaine_nom = serializers.CharField(
        source='entreprise.domaine.nom_domaine',
        read_only=True
    )

    class Meta:
        model  = ServiceModel
        fields = [
            'id',
            'nom',
            'description',
            'prix',            # le prix affiché au client avant réservation
            'duree_minutes',   # durée estimée — utile pour l'affichage calendrier
            'entreprise',      # ID de l'entreprise (pour les filtres)
            'entreprise_nom',  # nom lisible de l'entreprise
            'domaine_nom',     # domaine de l'entreprise
            'est_actif',       # si False, le service n'est pas proposé
            'date_creation',
        ]
        # date_creation est générée automatiquement, jamais envoyée par le client
        read_only_fields = ['date_creation']

# =============================================================
#   CRÉNEAU
# =============================================================

class PlageCreneauSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PlageCreneauModel
        fields = ['id', 'entreprise', 'date_plage', 'heure_debut', 'heure_fin', 'libelle']

    def validate(self, data):
        if data.get('heure_debut') and data.get('heure_fin'):
            if data['heure_debut'] >= data['heure_fin']:
                raise serializers.ValidationError(
                    "L'heure de début doit précéder l'heure de fin."
                )
        return data


class CreneauSerializer(serializers.ModelSerializer):
    # Date de la plage
    date = serializers.DateField(
        source='plage.date_plage',
        read_only=True,
        default=None
    )
    # Jour lisible en français
    jour_semaine = serializers.SerializerMethodField()

    # Nom complet du personnel
    personnel_nom = serializers.SerializerMethodField()

    # Entreprise du personnel
    entreprise_nom = serializers.SerializerMethodField()

    # Domaine du personnel
    domaine_nom = serializers.SerializerMethodField()

    class Meta:
        model  = CreneauModel
        fields = [
            'id', 'personnel', 'heure_debut', 'heure_fin',
            'statut', 'plage',
            'date',
            'jour_semaine',
            'personnel_nom',   # ← NOUVEAU
            'entreprise_nom',  # ← NOUVEAU
            'domaine_nom',     # ← NOUVEAU
        ]

    def get_jour_semaine(self, obj):
        if not obj.plage or not obj.plage.date_plage:
            return None
        JOURS = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche']
        MOIS  = ['jan','fév','mar','avr','mai','juin','juil','août','sep','oct','nov','déc']
        d = obj.plage.date_plage
        return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]}"

    def get_personnel_nom(self, obj):
        try:
            u = obj.personnel.utilisateur
            return f"{u.prenom} {u.nom}"
        except Exception:
            return None

    def get_entreprise_nom(self, obj):
        try:
            return obj.personnel.entreprise.nom_entreprise
        except Exception:
            return None

    def get_domaine_nom(self, obj):
        try:
            # Domaine via entreprise ou domaine direct du personnel
            if obj.personnel.entreprise:
                return obj.personnel.entreprise.domaine.nom_domaine
            if obj.personnel.domaine:
                return obj.personnel.domaine.nom_domaine
            return None
        except Exception:
            return None
# =============================================================
#   RENDEZ-VOUS
# =============================================================

class HistoriqueStatutSerializer(serializers.ModelSerializer):
    class Meta:
        model  = HistoriqueStatutModel
        fields = ['id', 'ancien_statut', 'nouveau_statut', 'date_changement', 'commentaire']


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DocumentModel
        fields = ['id', 'nom', 'type_document', 'date_upload']


class RendezVousSerializer(serializers.ModelSerializer):
    historique     = HistoriqueStatutSerializer(many=True, read_only=True)
    documents      = DocumentSerializer(many=True, read_only=True)
    client_nom     = serializers.SerializerMethodField()
    statut_display = serializers.SerializerMethodField()
    traite_par_nom = serializers.SerializerMethodField()
    service_nom    = serializers.CharField(source='service.nom', read_only=True, default=None)
    service_prix   = serializers.DecimalField(source='service.prix', max_digits=10, decimal_places=2, read_only=True, default=None)
    personnel_nom  = serializers.SerializerMethodField()
    entreprise_nom = serializers.SerializerMethodField()
    # Infos du créneau
    creneau_heure_debut = serializers.SerializerMethodField()
    creneau_heure_fin   = serializers.SerializerMethodField()
    creneau_date        = serializers.SerializerMethodField()
    creneau_jour        = serializers.SerializerMethodField()
        # Dans RendezVousSerializer
    personnel_profil_id = serializers.SerializerMethodField()

    # Dans fields
    'personnel_profil_id',

    # Méthode
    def get_personnel_profil_id(self, obj):
        try:
            return obj.creneau.personnel.id
        except Exception:
            return None
    
    class Meta:
        model  = RendezVousModel
        fields = [
            'id', 'client', 'client_nom', 'creneau',
            'service', 'service_nom', 'service_prix', 'prix_snapshot',
            'paiement_autorise', 'confirmation', 'statut', 'statut_display',
            'description', 'date_creation', 'date_modification',
            'traite_par', 'traite_par_nom', 'motif_refus',
            'personnel_nom', 'entreprise_nom',
            'historique', 'documents',
            'creneau_heure_debut', 'creneau_heure_fin',
            'creneau_date', 'creneau_jour',
            'personnel_profil_id',
        ]
        read_only_fields = [
            'confirmation', 'statut', 'date_creation',
            'date_modification', 'traite_par', 'motif_refus',
            'prix_snapshot', 'paiement_autorise',
        ]

    def get_client_nom(self, obj):
        try:
            return f"{obj.client.utilisateur.prenom} {obj.client.utilisateur.nom}"
        except Exception:
            return f"Client #{obj.client_id}"

    def get_statut_display(self, obj):
        return {
            'en_attente': 'En attente',
            'confirme':   'Confirmé',
            'refuse':     'Refusé',
            'annule':     'Annulé',
            'termine':    'Terminé',
        }.get(obj.statut, obj.statut)

    def get_traite_par_nom(self, obj):
        try:
            if obj.traite_par and obj.traite_par.utilisateur:
                return f"{obj.traite_par.utilisateur.prenom} {obj.traite_par.utilisateur.nom}"
            return None
        except Exception:
            return None

    def get_personnel_nom(self, obj):
        try:
            p = obj.creneau.personnel.utilisateur
            return f"{p.prenom} {p.nom}"
        except Exception:
            return None

    def get_entreprise_nom(self, obj):
        try:
            return obj.creneau.personnel.entreprise.nom_entreprise
        except Exception:
            return None
        
    def get_creneau_heure_debut(self, obj):
        try:
            return obj.creneau.heure_debut.strftime('%H:%M')
        except Exception:
            return None

    def get_creneau_heure_fin(self, obj):
        try:
            return obj.creneau.heure_fin.strftime('%H:%M')
        except Exception:
            return None

    def get_creneau_date(self, obj):
        try:
            if obj.creneau.plage and obj.creneau.plage.date_plage:
                return obj.creneau.plage.date_plage.strftime('%d/%m/%Y')
            return None
        except Exception:
            return None

    def get_creneau_jour(self, obj):
        try:
            if obj.creneau.plage and obj.creneau.plage.date_plage:
                JOURS = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche']
                MOIS  = ['jan','fév','mar','avr','mai','juin','juil','août','sep','oct','nov','déc']
                d = obj.creneau.plage.date_plage
                return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month-1]}"
            return None
        except Exception:
            return None 
class CreerRendezVousSerializer(serializers.Serializer):
    """Valide les données de création d'un rendez-vous."""
    creneau_id  = serializers.IntegerField()
    description = serializers.CharField(required=False, default='', allow_blank=True)


class TraiterRendezVousSerializer(serializers.Serializer):
    """Valide les données de confirmation ou refus."""
    action      = serializers.ChoiceField(choices=['confirmer', 'refuser'])
    motif_refus = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data['action'] == 'refuser' and not data.get('motif_refus', '').strip():
            raise serializers.ValidationError(
                {"motif_refus": "Le motif est obligatoire pour un refus."}
            )
        return data


# =============================================================
#   PAIEMENT
# =============================================================

class PaiementSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model  = PaiementModel
        fields = [
            'id', 'rendezvous', 'montant', 'mode_paiement',
            'statut', 'statut_display', 'date_paiement', 'reference_transaction'
        ]
        read_only_fields = ['date_paiement', 'reference_transaction']


class InitierPaiementSerializer(serializers.Serializer):
    rendezvous_id = serializers.IntegerField()
    montant       = serializers.DecimalField(max_digits=10, decimal_places=2)
    mode_paiement = serializers.ChoiceField(
        choices=['carte', 'mobile_money', 'virement', 'especes']
    )


class ConfirmerPaiementSerializer(serializers.Serializer):
    reference_transaction = serializers.CharField(max_length=100)


# =============================================================
#   NOTIFICATION
# =============================================================

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NotificationModel
        fields = [
            'id', 'titre', 'message', 'type_notification',
            'est_lue', 'date_creation', 'date_lecture'
        ]
class CreerRendezVousSerializer(serializers.Serializer):
    """
    Valide les données de création d'un rendez-vous.
    Le client envoie : creneau_id + service_id + description.
    Le service_id est optionnel pour compatibilité avec l'existant.
    """
    creneau_id  = serializers.IntegerField()

    # service_id : l'ID du service choisi parmi ceux du personnel
    # required=False : compatibilité avec anciens RDV sans service
    service_id  = serializers.IntegerField(required=False, allow_null=True)

    description = serializers.CharField(
        required=False, default='', allow_blank=True
    )