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
    PaiementModel, NotificationModel,
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
    """Affiche les informations d'un utilisateur (sans mot de passe)."""
    nom_complet = serializers.SerializerMethodField()

    class Meta:
        model  = UtilisateurModel
        fields = [
            'id', 'nom', 'prenom', 'nom_complet',
            'email', 'telephone', 'role', 'is_active', 'date_joined'
        ]
        read_only_fields = ['date_joined']

    def get_nom_complet(self, obj):
        return f"{obj.prenom} {obj.nom}"


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
    utilisateur = UtilisateurSerializer(read_only=True)

    class Meta:
        model  = PersonnelModel
        fields = ['id', 'utilisateur', 'poste', 'entreprise', 'domaine']


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
    class Meta:
        model  = CreneauModel
        fields = ['id', 'personnel', 'heure_debut', 'heure_fin', 'statut', 'plage']


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
        fields = ['id', 'fichier', 'type_document', 'nom', 'date_upload']
        read_only_fields = ['date_upload']


class RendezVousSerializer(serializers.ModelSerializer):
    """Affiche un rendez-vous complet avec historique et documents."""
    historique     = HistoriqueStatutSerializer(many=True, read_only=True)
    documents      = DocumentSerializer(many=True, read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    client_nom     = serializers.SerializerMethodField()

    class Meta:
        model  = RendezVousModel
        fields = [
            'id', 'client', 'client_nom', 'creneau',
            'confirmation', 'statut', 'statut_display',
            'description', 'date_creation', 'date_modification',
            'traite_par', 'motif_refus',
            'historique', 'documents',
        ]
        read_only_fields = [
            'confirmation', 'statut', 'date_creation',
            'date_modification', 'traite_par', 'motif_refus',
        ]

    def get_client_nom(self, obj):
        return f"{obj.client.utilisateur.prenom} {obj.client.utilisateur.nom}"


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