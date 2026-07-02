"""
=============================================================
  rendezvous/presentation/views/views.py

  COUCHE PRESENTATION — Vues API REST (version sécurisée)
=============================================================
  Grâce au gestionnaire global, les vues n'ont plus besoin
  de try/except partout. On laisse les exceptions remonter
  et le gestionnaire les traduit en réponses JSON propres.
=============================================================
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from rendezvous.application.use_cases.use_cases import (
    InscriptionUseCase, InscriptionInput,
    ListerUtilisateursUseCase, ObtenirUtilisateurUseCase,
    MettreAJourProfilUseCase, StatistiquesUseCase,
    CreerDomaineUseCase, ListerDominesUseCase,
    CreerEntrepriseUseCase, ListerEntreprisesUseCase, LaisserAvisUseCase,
    CreerCreneauUseCase, ListerCreneauxDisponiblesUseCase,
    CreerRendezVousUseCase, CreerRendezVousInput,
    ConfirmerRendezVousUseCase, RefuserRendezVousUseCase, AnnulerRendezVousUseCase,
    InitierPaiementUseCase, ConfirmerPaiementUseCase, RembourserPaiementUseCase,
    ListerNotificationsUseCase, MarquerLueUseCase, MarquerToutesLuesUseCase,
)
from rendezvous.infrastructure.repositories.implementations import (
    DjangoUtilisateurRepository, DjangoClientRepository,
    DjangoPersonnelRepository, DjangoAdminRepository,
    DjangoDomaineRepository, DjangoEntrepriseRepository, DjangoAvisRepository,
    DjangoPlageRepository, DjangoCreneauRepository,
    DjangoRendezVousRepository, DjangoHistoriqueRepository,
    DjangoPaiementRepository, DjangoNotificationRepository,
)
from rendezvous.infrastructure.django_models.models import (
    UtilisateurModel, EntrepriseModel, CreneauModel,
    RendezVousModel, PaiementModel, NotificationModel,
)
from rendezvous.presentation.serializers.serializers import (
    LoginSerializer, InscriptionSerializer, UtilisateurSerializer,
    MettreAJourProfilSerializer, ClientSerializer,
    DomaineSerializer, EntrepriseSerializer, AvisSerializer,
    PlageCreneauSerializer, CreneauSerializer,
    RendezVousSerializer, CreerRendezVousSerializer, TraiterRendezVousSerializer,
    PaiementSerializer, InitierPaiementSerializer, ConfirmerPaiementSerializer,
    NotificationSerializer,
)
from rendezvous.presentation.views.auth_views import (
    LoginView,
    LogoutView,
    ChangerMotDePasseView,
)
from rendezvous.domain.exceptions.exceptions import RendezVousNonTrouve


# =============================================================
#   PERMISSIONS
# =============================================================

class EstAdmin(BasePermission):
    message = "Accès réservé aux administrateurs."
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class EstClient(BasePermission):
    message = "Accès réservé aux clients."
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'client'


class EstAdminOuPersonnel(BasePermission):
    message = "Accès réservé aux admins et au personnel."
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'personnel']


# =============================================================
#   HELPER
# =============================================================

def get_repos():
    """Fabrique tous les repositories — injection de dépendances."""
    return {
        'utilisateur': DjangoUtilisateurRepository(),
        'client':      DjangoClientRepository(),
        'personnel':   DjangoPersonnelRepository(),
        'admin':       DjangoAdminRepository(),
        'domaine':     DjangoDomaineRepository(),
        'entreprise':  DjangoEntrepriseRepository(),
        'avis':        DjangoAvisRepository(),
        'plage':       DjangoPlageRepository(),
        'creneau':     DjangoCreneauRepository(),
        'rdv':         DjangoRendezVousRepository(),
        'historique':  DjangoHistoriqueRepository(),
        'paiement':    DjangoPaiementRepository(),
        'notif':       DjangoNotificationRepository(),
    }


def get_client_profile(user):
    """
    Récupère le profil client de l'utilisateur connecté.
    Lève une ValueError claire si le profil est manquant.
    """
    try:
        return user.profil_client
    except Exception:
        raise ValueError(
            "Profil client introuvable. "
            "Contactez un administrateur."
        )


def get_admin_profile(user):
    """Récupère le profil admin de l'utilisateur connecté."""
    try:
        return user.profil_admin
    except Exception:
        raise ValueError(
            "Profil administrateur introuvable. "
            "Contactez un administrateur."
        )


# =============================================================
#   AUTHENTIFICATION
# =============================================================

class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Body: {"email": "...", "password": "..."}
    """
    serializer_class = LoginSerializer


# =============================================================
#   UTILISATEUR
# =============================================================

class InscriptionView(APIView):
    """POST /api/users/inscription/ — Créer un compte."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InscriptionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'erreur': 'Les données envoyées sont invalides.',
                    'code': 'DONNEES_INVALIDES',
                    'details': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        repos = get_repos()
        use_case = InscriptionUseCase(
            repos['utilisateur'], repos['client'],
            repos['personnel'], repos['admin'],
        )

        # On laisse remonter les exceptions :
        # EmailDejaUtilise → 409, MotDePasseInvalide → 400
        utilisateur = use_case.execute(InscriptionInput(
            nom=data['nom'],
            prenom=data['prenom'],
            email=data['email'],
            password=data['password'],
            password_confirm=data['password_confirm'],
            role=data['role'],
            telephone=data.get('telephone', ''),
        ))

        return Response(
            {
                'message': 'Compte créé avec succès.',
                'email': utilisateur.email,
                'role': utilisateur.role.value,
            },
            status=status.HTTP_201_CREATED
        )


class MonProfilView(APIView):
    """
    GET /api/users/moi/  → Voir son profil
    PUT /api/users/moi/  → Modifier son profil
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UtilisateurSerializer(request.user).data)

    def put(self, request):
        serializer = MettreAJourProfilSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'erreur': 'Données invalides.',
                    'code': 'DONNEES_INVALIDES',
                    'details': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        repos = get_repos()
        MettreAJourProfilUseCase(repos['utilisateur']).execute(
            user_id=request.user.id,
            **serializer.validated_data
        )
        user = UtilisateurModel.objects.get(id=request.user.id)
        return Response(UtilisateurSerializer(user).data)


class UtilisateurListView(APIView):
    """GET /api/users/ — Liste les utilisateurs (admin)."""
    permission_classes = [EstAdmin]

    def get(self, request):
        role = request.query_params.get('role')

        # Valider le rôle si fourni
        roles_valides = ['client', 'admin', 'personnel']
        if role and role not in roles_valides:
            return Response(
                {
                    'erreur': f"Rôle invalide. Valeurs acceptées : {roles_valides}",
                    'code': 'PARAMETRE_INVALIDE',
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        repos = get_repos()
        utilisateurs = ListerUtilisateursUseCase(repos['utilisateur']).execute(role=role)
        ids = [u.id for u in utilisateurs]
        models = UtilisateurModel.objects.filter(id__in=ids).order_by('-date_joined')
        return Response(UtilisateurSerializer(models, many=True).data)


class StatistiquesView(APIView):
    """GET /api/users/statistiques/ — Dashboard admin."""
    permission_classes = [EstAdmin]

    def get(self, request):
        repos = get_repos()
        return Response(
            StatistiquesUseCase(repos['utilisateur'], repos['rdv']).execute()
        )


# =============================================================
#   DOMAINE ET ENTREPRISE
# =============================================================

class DomaineListView(APIView):
    """
    GET  /api/domaines/ → Lister (tout le monde)
    POST /api/domaines/ → Créer (admin)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [EstAdmin()]

    def get(self, request):
        repos = get_repos()
        domaines = ListerDominesUseCase(repos['domaine']).execute()
        return Response([
            {'id': d.id, 'nom_domaine': d.nom_domaine, 'description': d.description}
            for d in domaines
        ])

    def post(self, request):
        serializer = DomaineSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'erreur': 'Données invalides.',
                    'code': 'DONNEES_INVALIDES',
                    'details': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        repos = get_repos()
        domaine = CreerDomaineUseCase(repos['domaine']).execute(
            nom_domaine=serializer.validated_data['nom_domaine'],
            description=serializer.validated_data.get('description', ''),
        )
        return Response(
            {'id': domaine.id, 'nom_domaine': domaine.nom_domaine},
            status=status.HTTP_201_CREATED
        )


class EntrepriseListView(APIView):
    """
    GET  /api/entreprises/ → Lister
    POST /api/entreprises/ → Créer (admin)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        domaine_id = request.query_params.get('domaine')
        repos = get_repos()
        entreprises = ListerEntreprisesUseCase(repos['entreprise']).execute(
            domaine_id=int(domaine_id) if domaine_id else None
        )
        ids = [e.id for e in entreprises]
        models = (
            EntrepriseModel.objects
            .filter(id__in=ids)
            .select_related('domaine')
            .prefetch_related('avis')
        )
        return Response(EntrepriseSerializer(models, many=True).data)

    def post(self, request):
        if request.user.role != 'admin':
            return Response(
                {
                    'erreur': 'Seuls les admins peuvent créer une entreprise.',
                    'code': 'PERMISSION_REFUSEE',
                },
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = EntrepriseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'erreur': 'Données invalides.',
                    'code': 'DONNEES_INVALIDES',
                    'details': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AvisView(APIView):
    """POST /api/avis/ — Laisser un avis (client)."""
    permission_classes = [EstClient]

    def post(self, request):
        client = get_client_profile(request.user)

        note = request.data.get('note')
        if not note:
            return Response(
                {
                    'erreur': 'La note est obligatoire.',
                    'code': 'CHAMP_MANQUANT',
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        repos = get_repos()
        # LaisserAvisUseCase lève ValueError si note invalide
        avis = LaisserAvisUseCase(repos['avis']).execute(
            entreprise_id=request.data.get('entreprise_id'),
            client_id=client.id,
            note=int(note),
            commentaire=request.data.get('commentaire', ''),
        )
        return Response(
            {'id': avis.id, 'note': avis.note},
            status=status.HTTP_201_CREATED
        )


# =============================================================
#   CRÉNEAU
# =============================================================

class CreneauListView(APIView):
    """
    GET  /api/creneaux/ → Lister les créneaux
    POST /api/creneaux/ → Créer un créneau (admin/personnel)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = CreneauModel.objects.select_related('personnel').all()

        if request.user.role == 'personnel':
            try:
                qs = qs.filter(personnel=request.user.profil_personnel)
            except Exception:
                return Response(
                    {
                        'erreur': 'Profil personnel introuvable.',
                        'code': 'PROFIL_INTROUVABLE',
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        statut = request.query_params.get('statut')
        statuts_valides = ['disponible', 'reserve', 'annule', 'termine']
        if statut:
            if statut not in statuts_valides:
                return Response(
                    {
                        'erreur': f"Statut invalide. Valeurs acceptées : {statuts_valides}",
                        'code': 'PARAMETRE_INVALIDE',
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            qs = qs.filter(statut=statut)

        return Response(CreneauSerializer(qs, many=True).data)

    def post(self, request):
        if request.user.role not in ['admin', 'personnel']:
            return Response(
                {
                    'erreur': 'Seuls les admins et le personnel peuvent créer des créneaux.',
                    'code': 'PERMISSION_REFUSEE',
                },
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = CreneauSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'erreur': 'Données invalides.',
                    'code': 'DONNEES_INVALIDES',
                    'details': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CreneauDisponiblesView(APIView):
    """GET /api/creneaux/disponibles/ — Créneaux libres."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        entreprise_id = request.query_params.get('entreprise')
        repos = get_repos()
        creneaux = ListerCreneauxDisponiblesUseCase(repos['creneau']).execute(
            entreprise_id=int(entreprise_id) if entreprise_id else None
        )
        ids = [c.id for c in creneaux]
        models = CreneauModel.objects.filter(id__in=ids)
        return Response(CreneauSerializer(models, many=True).data)


# =============================================================
#   RENDEZ-VOUS
# =============================================================

class RendezVousListView(APIView):
    """
    GET  /api/rendezvous/ → Lister les RDV
    POST /api/rendezvous/ → Prendre un RDV (client)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = RendezVousModel.objects.select_related(
            'client__utilisateur', 'creneau', 'traite_par'
        ).prefetch_related('historique', 'documents')

        if request.user.role == 'client':
            try:
                qs = qs.filter(client=request.user.profil_client)
            except Exception:
                return Response(
                    {
                        'erreur': 'Profil client introuvable.',
                        'code': 'PROFIL_INTROUVABLE',
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            statut = request.query_params.get('statut')
            statuts_valides = ['en_attente', 'confirme', 'refuse', 'annule', 'termine']
            if statut:
                if statut not in statuts_valides:
                    return Response(
                        {
                            'erreur': f"Statut invalide. Valeurs acceptées : {statuts_valides}",
                            'code': 'PARAMETRE_INVALIDE',
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                qs = qs.filter(statut=statut)

        return Response(RendezVousSerializer(qs, many=True).data)

    def post(self, request):
        if request.user.role != 'client':
            return Response(
                {
                    'erreur': 'Seuls les clients peuvent prendre un rendez-vous.',
                    'code': 'PERMISSION_REFUSEE',
                },
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CreerRendezVousSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'erreur': 'Données invalides.',
                    'code': 'DONNEES_INVALIDES',
                    'details': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        client = get_client_profile(request.user)
        repos = get_repos()

        # Les exceptions remontent au gestionnaire global
        rdv = CreerRendezVousUseCase(
            repos['rdv'], repos['historique'],
            repos['creneau'], repos['notif'],
        ).execute(CreerRendezVousInput(
            client_id=client.id,
            creneau_id=serializer.validated_data['creneau_id'],
            description=serializer.validated_data.get('description', ''),
        ))

        model = RendezVousModel.objects.prefetch_related(
            'historique', 'documents'
        ).get(id=rdv.id)
        return Response(
            RendezVousSerializer(model).data,
            status=status.HTTP_201_CREATED
        )


class RendezVousDetailView(APIView):
    """GET /api/rendezvous/{id}/ — Détail d'un RDV."""
    permission_classes = [IsAuthenticated]

    def get(self, request, rdv_id):
        try:
            rdv = RendezVousModel.objects.select_related(
                'client__utilisateur', 'creneau', 'traite_par'
            ).prefetch_related('historique', 'documents').get(id=rdv_id)
        except RendezVousModel.DoesNotExist:
            return Response(
                {
                    'erreur': f"Rendez-vous #{rdv_id} introuvable.",
                    'code': 'RESSOURCE_INTROUVABLE',
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Un client ne voit que ses propres RDV
        if request.user.role == 'client':
            try:
                if rdv.client != request.user.profil_client:
                    return Response(
                        {
                            'erreur': 'Vous ne pouvez pas voir ce rendez-vous.',
                            'code': 'PERMISSION_REFUSEE',
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Exception:
                return Response(
                    {
                        'erreur': 'Profil client introuvable.',
                        'code': 'PROFIL_INTROUVABLE',
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(RendezVousSerializer(rdv).data)


class TraiterRendezVousView(APIView):
    """
    POST /api/rendezvous/{id}/traiter/
    Body: {"action": "confirmer"} ou {"action": "refuser", "motif_refus": "..."}
    """
    permission_classes = [EstAdmin]

    def post(self, request, rdv_id):
        serializer = TraiterRendezVousSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'erreur': 'Données invalides.',
                    'code': 'DONNEES_INVALIDES',
                    'details': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        admin = get_admin_profile(request.user)
        action = serializer.validated_data['action']
        motif  = serializer.validated_data.get('motif_refus', '')
        repos  = get_repos()

        # Les exceptions (RendezVousNonTrouve, StatutInvalide...)
        # remontent au gestionnaire global
        if action == 'confirmer':
            rdv = ConfirmerRendezVousUseCase(
                repos['rdv'], repos['historique'],
                repos['creneau'], repos['notif'],
            ).execute(rdv_id, admin.id)
        else:
            rdv = RefuserRendezVousUseCase(
                repos['rdv'], repos['historique'], repos['notif'],
            ).execute(rdv_id, admin.id, motif)

        model = RendezVousModel.objects.prefetch_related(
            'historique', 'documents'
        ).get(id=rdv.id)
        return Response(RendezVousSerializer(model).data)


class AnnulerRendezVousView(APIView):
    """POST /api/rendezvous/{id}/annuler/ — Client annule son RDV."""
    permission_classes = [EstClient]

    def post(self, request, rdv_id):
        client = get_client_profile(request.user)
        repos  = get_repos()

        rdv = AnnulerRendezVousUseCase(
            repos['rdv'], repos['historique'], repos['creneau']
        ).execute(rdv_id, client.id)

        return Response(
            {'message': f'Rendez-vous #{rdv.id} annulé avec succès.'}
        )


class TableauDeBordView(APIView):
    """GET /api/rendezvous/tableau-de-bord/ — Statistiques admin."""
    permission_classes = [EstAdmin]

    def get(self, request):
        repos = get_repos()
        return Response(repos['rdv'].compter_par_statut())


# =============================================================
#   PAIEMENT
# =============================================================

class PaiementListView(APIView):
    """
    GET  /api/paiements/ → Lister les paiements
    POST /api/paiements/ → Initier un paiement (client)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = PaiementModel.objects.select_related('rendezvous').all()
        if request.user.role == 'client':
            try:
                qs = qs.filter(rendezvous__client=request.user.profil_client)
            except Exception:
                return Response(
                    {
                        'erreur': 'Profil client introuvable.',
                        'code': 'PROFIL_INTROUVABLE',
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(PaiementSerializer(qs, many=True).data)

    def post(self, request):
        if request.user.role != 'client':
            return Response(
                {
                    'erreur': 'Seuls les clients peuvent initier un paiement.',
                    'code': 'PERMISSION_REFUSEE',
                },
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = InitierPaiementSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'erreur': 'Données invalides.',
                    'code': 'DONNEES_INVALIDES',
                    'details': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        repos = get_repos()
        paiement = InitierPaiementUseCase(
            repos['paiement'], repos['rdv']
        ).execute(**serializer.validated_data)

        model = PaiementModel.objects.get(id=paiement.id)
        return Response(
            PaiementSerializer(model).data,
            status=status.HTTP_201_CREATED
        )


class ConfirmerPaiementView(APIView):
    """POST /api/paiements/{id}/confirmer/ — Admin confirme."""
    permission_classes = [EstAdmin]

    def post(self, request, paiement_id):
        serializer = ConfirmerPaiementSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'erreur': 'Données invalides.',
                    'code': 'DONNEES_INVALIDES',
                    'details': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        repos = get_repos()
        paiement = ConfirmerPaiementUseCase(
            repos['paiement'], repos['rdv'], repos['notif']
        ).execute(paiement_id, serializer.validated_data['reference_transaction'])

        model = PaiementModel.objects.get(id=paiement.id)
        return Response(PaiementSerializer(model).data)


class RembourserPaiementView(APIView):
    """POST /api/paiements/{id}/rembourser/ — Admin rembourse."""
    permission_classes = [EstAdmin]

    def post(self, request, paiement_id):
        repos    = get_repos()
        paiement = RembourserPaiementUseCase(repos['paiement']).execute(paiement_id)
        model    = PaiementModel.objects.get(id=paiement.id)
        return Response(PaiementSerializer(model).data)


# =============================================================
#   NOTIFICATION
# =============================================================

class NotificationListView(APIView):
    """GET /api/notifications/ — Mes notifications."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        non_lues = request.query_params.get('non_lues') == 'true'
        repos    = get_repos()
        notifs   = ListerNotificationsUseCase(repos['notif']).execute(
            request.user.id, non_lues
        )
        ids    = [n.id for n in notifs]
        models = NotificationModel.objects.filter(id__in=ids)
        nb_non_lues = NotificationModel.objects.filter(
            destinataire=request.user, est_lue=False
        ).count()

        return Response({
            'non_lues': nb_non_lues,
            'notifications': NotificationSerializer(models, many=True).data,
        })


class MarquerLueView(APIView):
    """POST /api/notifications/{id}/lire/ — Marquer une notification lue."""
    permission_classes = [IsAuthenticated]

    def post(self, request, notif_id):
        repos = get_repos()
        notif = MarquerLueUseCase(repos['notif']).execute(notif_id)
        model = NotificationModel.objects.get(id=notif.id)
        return Response(NotificationSerializer(model).data)


class MarquerToutesLuesView(APIView):
    """POST /api/notifications/tout-lire/ — Tout marquer comme lu."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        repos  = get_repos()
        result = MarquerToutesLuesUseCase(repos['notif']).execute(request.user.id)
        return Response(result)