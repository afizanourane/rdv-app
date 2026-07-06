"""
rendezvous/presentation/views/views.py
Permissions strictes par rôle
"""

from django.db import models
from django.conf import settings


from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from rendezvous.application.use_cases.use_cases import (
    InscriptionUseCase, InscriptionInput,
    ListerUtilisateursUseCase, MettreAJourProfilUseCase, StatistiquesUseCase,
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
    MettreAJourProfilSerializer,
    DomaineSerializer, EntrepriseSerializer, AvisSerializer,
    CreneauSerializer,
    RendezVousSerializer, CreerRendezVousSerializer, TraiterRendezVousSerializer,
    PaiementSerializer, InitierPaiementSerializer, ConfirmerPaiementSerializer,
    NotificationSerializer,
)
from rendezvous.domain.exceptions.exceptions import (
    EmailDejaUtilise, MotDePasseInvalide,
    CreneauNonTrouve, CreneauNonDisponible,
    RendezVousNonTrouve, RendezVousDejaExistant,
    RendezVousNonConfirme, PaiementDejaExistant,
    PaiementNonTrouve, RemboursementImpossible,
)


# =============================================================
#   PERMISSIONS PERSONNALISÉES
# =============================================================

class EstAdmin(BasePermission):
    """Réservé aux administrateurs uniquement."""
    message = "Accès réservé aux administrateurs."
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class EstClient(BasePermission):
    """Réservé aux clients uniquement."""
    message = "Accès réservé aux clients."
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'client'


class EstPersonnel(BasePermission):
    """Réservé au personnel uniquement."""
    message = "Accès réservé au personnel."
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'personnel'


class EstAdminOuPersonnel(BasePermission):
    """Admins et personnel seulement."""
    message = "Accès réservé aux admins et au personnel."
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'personnel']


# =============================================================
#   HELPER — Injection de dépendances
# =============================================================

def get_repos():
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


# =============================================================
#   AUTHENTIFICATION
# =============================================================

class LoginView(TokenObtainPairView):
    serializer_class   = LoginSerializer
    permission_classes = [AllowAny]


# =============================================================
#   UTILISATEURS
# =============================================================

class InscriptionView(APIView):
    """POST /api/users/inscription/ — Tout le monde peut s'inscrire."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InscriptionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        data = serializer.validated_data
        repos = get_repos()
        try:
            utilisateur = InscriptionUseCase(
                repos['utilisateur'], repos['client'],
                repos['personnel'], repos['admin'],
            ).execute(InscriptionInput(
                nom=data['nom'], prenom=data['prenom'],
                email=data['email'], password=data['password'],
                password_confirm=data['password_confirm'],
                role=data['role'],
                telephone=data.get('telephone', ''),
            ))
            return Response(
                {'message': 'Compte créé.', 'email': utilisateur.email},
                status=201
            )
        except (EmailDejaUtilise, MotDePasseInvalide) as e:
            return Response({'erreur': str(e)}, status=400)


class MonProfilView(APIView):
    """
    GET /api/users/moi/  → Tout utilisateur connecté voit son profil
    PUT /api/users/moi/  → Tout utilisateur connecté modifie son profil
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UtilisateurSerializer(request.user).data)

    def put(self, request):
        serializer = MettreAJourProfilSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        repos = get_repos()
        MettreAJourProfilUseCase(repos['utilisateur']).execute(
            user_id=request.user.id, **serializer.validated_data
        )
        user = UtilisateurModel.objects.get(id=request.user.id)
        return Response(UtilisateurSerializer(user).data)


class UtilisateurListView(APIView):
    """
    GET /api/users/ — ADMIN SEULEMENT
    Seul l'admin peut voir tous les utilisateurs.
    """
    permission_classes = [EstAdmin]

    def get(self, request):
        role = request.query_params.get('role')
        repos = get_repos()
        utilisateurs = ListerUtilisateursUseCase(repos['utilisateur']).execute(role=role)
        ids = [u.id for u in utilisateurs]
        models = UtilisateurModel.objects.filter(id__in=ids).order_by('-date_joined')
        return Response(UtilisateurSerializer(models, many=True).data)


class StatistiquesView(APIView):
    """
    GET /api/users/statistiques/ — ADMIN SEULEMENT
    """
    permission_classes = [EstAdmin]

    def get(self, request):
        repos = get_repos()
        return Response(
            StatistiquesUseCase(repos['utilisateur'], repos['rdv']).execute()
        )


# =============================================================
#   DOMAINES & ENTREPRISES
# =============================================================

class DomaineListView(APIView):
    """
    GET  /api/domaines/ → Tout le monde (public)
    POST /api/domaines/ → ADMIN SEULEMENT
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
            return Response(serializer.errors, status=400)
        repos = get_repos()
        domaine = CreerDomaineUseCase(repos['domaine']).execute(
            nom_domaine=serializer.validated_data['nom_domaine'],
            description=serializer.validated_data.get('description', ''),
        )
        return Response({'id': domaine.id, 'nom_domaine': domaine.nom_domaine}, status=201)


class EntrepriseListView(APIView):
    """
    GET  /api/entreprises/ → Tout utilisateur connecté
    POST /api/entreprises/ → ADMIN SEULEMENT
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [EstAdmin()]
        return [IsAuthenticated()]

    def get(self, request):
        domaine_id = request.query_params.get('domaine')
        repos = get_repos()
        entreprises = ListerEntreprisesUseCase(repos['entreprise']).execute(
            domaine_id=int(domaine_id) if domaine_id else None
        )
        ids = [e.id for e in entreprises]
        models = EntrepriseModel.objects.filter(id__in=ids).select_related('domaine').prefetch_related('avis')
        return Response(EntrepriseSerializer(models, many=True).data)

    def post(self, request):
        serializer = EntrepriseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data, status=201)


class AvisView(APIView):
    """
    POST /api/avis/ — CLIENT SEULEMENT
    Seul un client peut laisser un avis.
    """
    permission_classes = [EstClient]

    def post(self, request):
        try:
            client = request.user.profil_client
        except Exception:
            return Response({'erreur': 'Profil client introuvable.'}, status=400)
        repos = get_repos()
        try:
            avis = LaisserAvisUseCase(repos['avis']).execute(
                entreprise_id=request.data.get('entreprise_id'),
                client_id=client.id,
                note=request.data.get('note'),
                commentaire=request.data.get('commentaire', ''),
            )
            return Response({'id': avis.id, 'note': avis.note}, status=201)
        except Exception as e:
            return Response({'erreur': str(e)}, status=400)


# =============================================================
#   CRÉNEAUX
# =============================================================

class CreneauDisponiblesView(APIView):
    """
    GET /api/creneaux/disponibles/ → Tout utilisateur connecté
    """
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


class CreneauListView(APIView):
    """
    GET  /api/creneaux/ → Connecté (client voit disponibles, admin/personnel voit tout)
    POST /api/creneaux/ → ADMIN ou PERSONNEL seulement
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [EstAdminOuPersonnel()]
        return [IsAuthenticated()]

    def get(self, request):
        qs = CreneauModel.objects.select_related('personnel').all()

        # Personnel : voit seulement ses propres créneaux
        if request.user.role == 'personnel':
            try:
                qs = qs.filter(personnel=request.user.profil_personnel)
            except Exception:
                qs = qs.none()
        # Client : voit seulement les créneaux disponibles
        elif request.user.role == 'client':
            qs = qs.filter(statut='disponible')
        # Admin : voit tout

        statut = request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)

        return Response(CreneauSerializer(qs, many=True).data)

    def post(self, request):
        heure_debut = request.data.get('heure_debut')
        heure_fin   = request.data.get('heure_fin')

        if not heure_debut or not heure_fin:
            return Response(
                {'erreur': 'heure_debut et heure_fin sont obligatoires.'},
                status=400
            )

        try:
            if request.user.role == 'personnel':
                personnel = request.user.profil_personnel
            else:
                from rendezvous.infrastructure.django_models.models import PersonnelModel as PM
                pid = request.data.get('personnel')
                personnel = PM.objects.get(id=pid) if pid else PM.objects.first()
                if not personnel:
                    return Response({'erreur': 'Aucun personnel disponible.'}, status=400)
        except Exception as e:
            return Response({'erreur': str(e)}, status=400)

        try:
            creneau = CreneauModel.objects.create(
                personnel=personnel,
                heure_debut=heure_debut,
                heure_fin=heure_fin,
                statut='disponible',
            )
            return Response(CreneauSerializer(creneau).data, status=201)
        except Exception as e:
            return Response({'erreur': str(e)}, status=400)


# =============================================================
#   RENDEZ-VOUS
# =============================================================

class RendezVousListView(APIView):
    """
    GET  /api/rendezvous/ → Filtré par rôle :
         - Client   : ses propres RDV uniquement
         - Personnel: RDV liés à ses créneaux
         - Admin    : TOUS les RDV
    POST /api/rendezvous/ → CLIENT SEULEMENT
    """
    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request):
        qs = RendezVousModel.objects.select_related(
            'client__utilisateur', 'creneau__personnel__utilisateur',
            'creneau__plage', 'traite_par'
        ).prefetch_related('historique', 'documents').order_by('-date_creation')

        # ── Filtre par rôle ───────────────────────────────────────
        if request.user.role == 'client':
            try:
                qs = qs.filter(client=request.user.profil_client)
            except Exception:
                return Response({'erreur': 'Profil client introuvable.'}, status=400)
        elif request.user.role == 'personnel':
            try:
                qs = qs.filter(creneau__personnel=request.user.profil_personnel)
            except Exception:
                qs = qs.none()

        # ── Filtres query params ───────────────────────────────────
        statut     = request.query_params.get('statut')
        client_nom = request.query_params.get('client')
        date_debut = request.query_params.get('date_debut')
        date_fin   = request.query_params.get('date_fin')
        entreprise = request.query_params.get('entreprise')
        search     = request.query_params.get('search')

        STATUTS_VALIDES = ['en_attente','confirme','refuse','annule','termine']

        if statut and statut in STATUTS_VALIDES:
            qs = qs.filter(statut=statut)

        if client_nom:
            qs = qs.filter(
                models.Q(client__utilisateur__nom__icontains=client_nom) |
                models.Q(client__utilisateur__prenom__icontains=client_nom) |
                models.Q(client__utilisateur__email__icontains=client_nom)
            )

        if date_debut:
            try:
                from datetime import datetime
                d = datetime.strptime(date_debut, '%Y-%m-%d')
                qs = qs.filter(date_creation__date__gte=d.date())
            except ValueError:
                pass

        if date_fin:
            try:
                from datetime import datetime
                d = datetime.strptime(date_fin, '%Y-%m-%d')
                qs = qs.filter(date_creation__date__lte=d.date())
            except ValueError:
                pass

        if entreprise:
            qs = qs.filter(
                creneau__personnel__entreprise__nom_entreprise__icontains=entreprise
            )

        if search:
            from django.db import models as django_models
            qs = qs.filter(
                django_models.Q(description__icontains=search) |
                django_models.Q(client__utilisateur__nom__icontains=search) |
                django_models.Q(client__utilisateur__prenom__icontains=search) |
                django_models.Q(client__utilisateur__email__icontains=search) |
                django_models.Q(id__icontains=search)
            )

        # ── Export CSV ────────────────────────────────────────────
        if request.query_params.get('export') == 'csv':
            return self._export_csv(qs)

        return Response(RendezVousSerializer(qs, many=True).data)

    def _export_csv(self, qs):
        """Génère un fichier CSV des rendez-vous filtrés."""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="rendez-vous.csv"'
        response.write('\ufeff')  # BOM UTF-8 pour Excel

        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'ID', 'Client', 'Email client', 'Personnel',
            'Entreprise', 'Description', 'Statut',
            'Date création', 'Motif refus',
        ])

        for rdv in qs:
            try:
                client_nom = f"{rdv.client.utilisateur.prenom} {rdv.client.utilisateur.nom}"
                client_email = rdv.client.utilisateur.email
            except Exception:
                client_nom = f"Client #{rdv.client_id}"
                client_email = ''

            try:
                personnel_nom = (
                    f"{rdv.creneau.personnel.utilisateur.prenom} "
                    f"{rdv.creneau.personnel.utilisateur.nom}"
                )
                entreprise_nom = getattr(rdv.creneau.personnel.entreprise, 'nom_entreprise', '—')
            except Exception:
                personnel_nom  = '—'
                entreprise_nom = '—'

            STATUTS = {
                'en_attente': 'En attente', 'confirme': 'Confirmé',
                'refuse': 'Refusé', 'annule': 'Annulé', 'termine': 'Terminé',
            }

            writer.writerow([
                rdv.id,
                client_nom,
                client_email,
                personnel_nom,
                entreprise_nom,
                rdv.description or '',
                STATUTS.get(rdv.statut, rdv.statut),
                rdv.date_creation.strftime('%d/%m/%Y %H:%M'),
                rdv.motif_refus or '',
            ])

        return response


    def post(self, request):
        # SEUL LE CLIENT peut prendre un RDV
        if request.user.role != 'client':
            return Response(
                {
                    'erreur': 'Seuls les clients peuvent prendre un rendez-vous.',
                    'code':   'PERMISSION_REFUSEE',
                },
                status=403
            )

        serializer = CreerRendezVousSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            client = request.user.profil_client
        except Exception:
            return Response({'erreur': 'Profil client introuvable.'}, status=400)

        repos = get_repos()   # ← LIGNE MANQUANTE — ajouter ici

        try:
            rdv = CreerRendezVousUseCase(
                repos['rdv'], repos['historique'],
                repos['creneau'], repos['notif'],
            ).execute(CreerRendezVousInput(
                client_id=client.id,
                creneau_id=serializer.validated_data['creneau_id'],
                description=serializer.validated_data.get('description', ''),
            ))

            # Retour simplifié — impossible de planter
            return Response({
                'message': '🎉 Rendez-vous créé avec succès !',
                'id':      rdv.id,
                'statut':  'en_attente',
                'info':    'Un email de confirmation vous a été envoyé.',
            }, status=201)

        except (RendezVousDejaExistant, CreneauNonTrouve, CreneauNonDisponible) as e:
            return Response({'erreur': str(e)}, status=400)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erreur création RDV: {e}", exc_info=True)
            return Response({'erreur': str(e)}, status=400)

           


class RendezVousDetailView(APIView):
    """
    GET /api/rendezvous/{id}/ → Connecté (client voit seulement les siens)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, rdv_id):
        try:
            rdv = RendezVousModel.objects.select_related(
                'client__utilisateur', 'creneau', 'traite_par'
            ).prefetch_related('historique', 'documents').get(id=rdv_id)
        except RendezVousModel.DoesNotExist:
            return Response({'erreur': f'RDV #{rdv_id} introuvable.'}, status=404)

        # Client ne voit que ses propres RDV
        if request.user.role == 'client':
            try:
                if rdv.client != request.user.profil_client:
                    return Response({'erreur': 'Non autorisé.'}, status=403)
            except Exception:
                return Response({'erreur': 'Non autorisé.'}, status=403)

        return Response(RendezVousSerializer(rdv).data)


class TraiterRendezVousView(APIView):
    """
    POST /api/rendezvous/{id}/traiter/ — ADMIN SEULEMENT
    Action : {"action": "confirmer"} ou {"action": "refuser", "motif_refus": "..."}
    """
    permission_classes = [EstAdmin]

    def post(self, request, rdv_id):
        serializer = TraiterRendezVousSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            admin = request.user.profil_admin
        except Exception:
            return Response({'erreur': 'Profil admin introuvable.'}, status=400)

        action = serializer.validated_data['action']
        motif  = serializer.validated_data.get('motif_refus', '')
        repos  = get_repos()

        try:
            if action == 'confirmer':
                rdv = ConfirmerRendezVousUseCase(
                    repos['rdv'], repos['historique'],
                    repos['creneau'], repos['notif'],
                ).execute(rdv_id, admin.id)
            else:
                rdv = RefuserRendezVousUseCase(
                    repos['rdv'], repos['historique'], repos['notif'],
                ).execute(rdv_id, admin.id, motif)

            model = RendezVousModel.objects.prefetch_related('historique','documents').get(id=rdv.id)
            return Response(RendezVousSerializer(model).data)
        except RendezVousNonTrouve as e:
            return Response({'erreur': str(e)}, status=404)
        except Exception as e:
            return Response({'erreur': str(e)}, status=400)


class AnnulerRendezVousView(APIView):
    """
    POST /api/rendezvous/{id}/annuler/ — CLIENT SEULEMENT
    Un client ne peut annuler QUE ses propres RDV.
    """
    permission_classes = [EstClient]

    def post(self, request, rdv_id):
        try:
            client = request.user.profil_client
        except Exception:
            return Response({'erreur': 'Profil client introuvable.'}, status=400)

        # Vérifier que le RDV appartient bien à ce client
        try:
            rdv_model = RendezVousModel.objects.get(id=rdv_id)
            if rdv_model.client != client:
                return Response(
                    {
                        'erreur': 'Vous ne pouvez annuler que vos propres rendez-vous.',
                        'code':   'PERMISSION_REFUSEE',
                    },
                    status=403
                )
        except RendezVousModel.DoesNotExist:
            return Response({'erreur': f'RDV #{rdv_id} introuvable.'}, status=404)

        repos = get_repos()
        try:
            rdv = AnnulerRendezVousUseCase(
                repos['rdv'], repos['historique'], repos['creneau']
            ).execute(rdv_id, client.id)
            return Response({'message': f'RDV #{rdv.id} annulé avec succès.'})
        except Exception as e:
            return Response({'erreur': str(e)}, status=400)


class TableauDeBordView(APIView):
    """
    GET /api/rendezvous/tableau-de-bord/ — ADMIN SEULEMENT
    """
    permission_classes = [EstAdmin]

    def get(self, request):
        repos = get_repos()
        return Response(repos['rdv'].compter_par_statut())


# =============================================================
#   PAIEMENTS
# =============================================================

class PaiementListView(APIView):
    """
    GET  /api/paiements/ → Filtré par rôle :
         - Client : ses propres paiements
         - Admin  : TOUS les paiements
    POST /api/paiements/ → CLIENT SEULEMENT (initier un paiement)
    """
    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request):
        qs = PaiementModel.objects.select_related(
            'rendezvous__client__utilisateur'
        ).order_by('-date_paiement')

        if request.user.role == 'client':
            try:
                qs = qs.filter(rendezvous__client=request.user.profil_client)
            except Exception:
                return Response({'erreur': 'Profil client introuvable.'}, status=400)
        elif request.user.role == 'personnel':
            return Response({'erreur': 'Non autorisé.'}, status=403)

        # ── Filtres ───────────────────────────────────────────────
        statut        = request.query_params.get('statut')
        mode_paiement = request.query_params.get('mode')
        date_debut    = request.query_params.get('date_debut')
        date_fin      = request.query_params.get('date_fin')
        montant_min   = request.query_params.get('montant_min')
        montant_max   = request.query_params.get('montant_max')

        STATUTS_VALIDES = ['en_attente', 'paye', 'rembourse', 'echoue']
        MODES_VALIDES   = ['mobile_money', 'carte', 'virement', 'especes']

        if statut and statut in STATUTS_VALIDES:
            qs = qs.filter(statut=statut)

        if mode_paiement and mode_paiement in MODES_VALIDES:
            qs = qs.filter(mode_paiement=mode_paiement)

        if date_debut:
            try:
                from datetime import datetime
                qs = qs.filter(
                    date_paiement__date__gte=datetime.strptime(date_debut, '%Y-%m-%d').date()
                )
            except ValueError:
                pass

        if date_fin:
            try:
                from datetime import datetime
                qs = qs.filter(
                    date_paiement__date__lte=datetime.strptime(date_fin, '%Y-%m-%d').date()
                )
            except ValueError:
                pass

        if montant_min:
            try:
                qs = qs.filter(montant__gte=float(montant_min))
            except ValueError:
                pass

        if montant_max:
            try:
                qs = qs.filter(montant__lte=float(montant_max))
            except ValueError:
                pass

        # ── Export CSV ────────────────────────────────────────────
        if request.query_params.get('export') == 'csv':
            return self._export_csv(qs)

        return Response(PaiementSerializer(qs, many=True).data)

    def _export_csv(self, qs):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="paiements.csv"'
        response.write('\ufeff')

        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'ID', 'RDV', 'Client', 'Montant (FCFA)',
            'Mode', 'Statut', 'Référence', 'Date',
        ])

        MODES   = {'mobile_money':'Mobile Money','carte':'Carte','virement':'Virement','especes':'Espèces'}
        STATUTS = {'en_attente':'En attente','paye':'Payé','rembourse':'Remboursé','echoue':'Échoué'}

        for p in qs:
            try:
                client_nom = (
                    f"{p.rendezvous.client.utilisateur.prenom} "
                    f"{p.rendezvous.client.utilisateur.nom}"
                )
            except Exception:
                client_nom = '—'

            writer.writerow([
                p.id,
                f"#{p.rendezvous_id}",
                client_nom,
                p.montant,
                MODES.get(p.mode_paiement, p.mode_paiement),
                STATUTS.get(p.statut, p.statut),
                p.reference_transaction or '',
                p.date_paiement.strftime('%d/%m/%Y %H:%M') if p.date_paiement else '',
            ])

        return response
    def post(self, request):
        # SEUL LE CLIENT peut initier un paiement
        if request.user.role != 'client':
            return Response(
                {
                    'erreur': 'Seuls les clients peuvent initier un paiement.',
                    'code':   'PERMISSION_REFUSEE',
                },
                status=403
            )

        serializer = InitierPaiementSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        repos = get_repos()
        try:
            paiement = InitierPaiementUseCase(
                repos['paiement'], repos['rdv']
            ).execute(**serializer.validated_data)
            model = PaiementModel.objects.get(id=paiement.id)
            return Response(PaiementSerializer(model).data, status=201)
        except (RendezVousNonConfirme, PaiementDejaExistant) as e:
            return Response({'erreur': str(e)}, status=400)
        except Exception as e:
            return Response({'erreur': str(e)}, status=400)


class ConfirmerPaiementView(APIView):
    """
    POST /api/paiements/{id}/confirmer/ — ADMIN SEULEMENT
    """
    permission_classes = [EstAdmin]

    def post(self, request, paiement_id):
        serializer = ConfirmerPaiementSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        repos = get_repos()
        try:
            paiement = ConfirmerPaiementUseCase(
                repos['paiement'], repos['rdv'], repos['notif']
            ).execute(paiement_id, serializer.validated_data['reference_transaction'])
            model = PaiementModel.objects.get(id=paiement.id)
            return Response(PaiementSerializer(model).data)
        except PaiementNonTrouve as e:
            return Response({'erreur': str(e)}, status=404)
        except Exception as e:
            return Response({'erreur': str(e)}, status=400)


class RembourserPaiementView(APIView):
    """
    POST /api/paiements/{id}/rembourser/ — ADMIN SEULEMENT
    """
    permission_classes = [EstAdmin]

    def post(self, request, paiement_id):
        repos = get_repos()
        try:
            paiement = RembourserPaiementUseCase(repos['paiement']).execute(paiement_id)
            model = PaiementModel.objects.get(id=paiement.id)
            return Response(PaiementSerializer(model).data)
        except (PaiementNonTrouve, RemboursementImpossible) as e:
            return Response({'erreur': str(e)}, status=400)


# =============================================================
#   NOTIFICATIONS
# =============================================================

class NotificationListView(APIView):
    """
    GET /api/notifications/ → Chaque utilisateur voit SEULEMENT ses propres notifications.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        non_lues = request.query_params.get('non_lues') == 'true'
        repos = get_repos()
        notifs = ListerNotificationsUseCase(repos['notif']).execute(
            request.user.id, non_lues
        )
        ids    = [n.id for n in notifs]
        models = NotificationModel.objects.filter(id__in=ids).order_by('-date_creation')
        nb_non_lues = NotificationModel.objects.filter(
            destinataire=request.user, est_lue=False
        ).count()
        return Response({
            'non_lues':      nb_non_lues,
            'notifications': NotificationSerializer(models, many=True).data,
        })


class MarquerLueView(APIView):
    """
    POST /api/notifications/{id}/lire/ — Chaque utilisateur marque ses propres notifs.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, notif_id):
        # Vérifier que la notification appartient à cet utilisateur
        try:
            notif_model = NotificationModel.objects.get(id=notif_id)
            if notif_model.destinataire != request.user:
                return Response({'erreur': 'Non autorisé.'}, status=403)
        except NotificationModel.DoesNotExist:
            return Response({'erreur': 'Notification introuvable.'}, status=404)

        repos = get_repos()
        notif = MarquerLueUseCase(repos['notif']).execute(notif_id)
        model = NotificationModel.objects.get(id=notif.id)
        return Response(NotificationSerializer(model).data)


class MarquerToutesLuesView(APIView):
    """
    POST /api/notifications/tout-lire/ — Marque toutes les notifs de l'utilisateur connecté.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        repos  = get_repos()
        result = MarquerToutesLuesUseCase(repos['notif']).execute(request.user.id)
        return Response(result)
    





class CalendrierView(APIView):
    """
    GET /api/calendrier/ — Données pour le calendrier visuel
    Retourne RDV + créneaux formatés pour FullCalendar
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rendezvous.infrastructure.django_models.models import CreneauModel
        from datetime import datetime

        # Paramètres de période
        debut = request.query_params.get('debut')
        fin   = request.query_params.get('fin')

        # ── RDV ──────────────────────────────────────────────
        rdvs_qs = RendezVousModel.objects.select_related(
            'client__utilisateur',
            'creneau__personnel__utilisateur',
            'creneau__plage',
        )

        if request.user.role == 'client':
            try:
                rdvs_qs = rdvs_qs.filter(client=request.user.profil_client)
            except Exception:
                rdvs_qs = rdvs_qs.none()
        elif request.user.role == 'personnel':
            try:
                rdvs_qs = rdvs_qs.filter(
                    creneau__personnel=request.user.profil_personnel
                )
            except Exception:
                rdvs_qs = rdvs_qs.none()

        rdvs_qs = rdvs_qs.exclude(statut__in=['annule', 'refuse'])

        # ── Créneaux ─────────────────────────────────────────
        creneaux_qs = CreneauModel.objects.select_related(
            'personnel__utilisateur', 'plage'
        )
        if request.user.role == 'personnel':
            try:
                creneaux_qs = creneaux_qs.filter(
                    personnel=request.user.profil_personnel
                )
            except Exception:
                creneaux_qs = creneaux_qs.none()
        elif request.user.role == 'client':
            creneaux_qs = creneaux_qs.filter(statut='disponible')

        # ── Couleurs par statut ───────────────────────────────
        COULEURS_RDV = {
            'en_attente': {'bg': '#f59e0b', 'border': '#d97706'},
            'confirme':   {'bg': '#10b981', 'border': '#059669'},
            'termine':    {'bg': '#6366f1', 'border': '#4f46e5'},
        }
        COULEURS_CRENEAU = {
            'disponible': {'bg': '#e0f2fe', 'border': '#0284c7', 'text': '#075985'},
            'reserve':    {'bg': '#fef3c7', 'border': '#d97706', 'text': '#92400e'},
        }

        evenements = []

        # ── Ajouter les RDV ───────────────────────────────────
        for rdv in rdvs_qs:
            try:
                date_debut_ev, date_fin_ev = self._get_dates_rdv(rdv)
                if not date_debut_ev:
                    continue

                couleur = COULEURS_RDV.get(rdv.statut, {'bg': '#94a3b8', 'border': '#64748b'})

                try:
                    client_nom = (
                        f"{rdv.client.utilisateur.prenom} "
                        f"{rdv.client.utilisateur.nom}"
                    )
                except Exception:
                    client_nom = f"Client #{rdv.client_id}"

                try:
                    personnel_nom = (
                        f"{rdv.creneau.personnel.utilisateur.prenom} "
                        f"{rdv.creneau.personnel.utilisateur.nom}"
                    )
                except Exception:
                    personnel_nom = "Personnel"

                LABELS = {
                    'en_attente': 'En attente',
                    'confirme':   'Confirmé',
                    'termine':    'Terminé',
                }

                evenements.append({
                    'id':              f"rdv-{rdv.id}",
                    'title':           f"RDV #{rdv.id} — {client_nom}",
                    'start':           date_debut_ev.isoformat(),
                    'end':             date_fin_ev.isoformat() if date_fin_ev else None,
                    'backgroundColor': couleur['bg'],
                    'borderColor':     couleur['border'],
                    'textColor':       '#ffffff',
                    'extendedProps': {
                        'type':        'rdv',
                        'rdv_id':      rdv.id,
                        'statut':      rdv.statut,
                        'statut_label':LABELS.get(rdv.statut, rdv.statut),
                        'client':      client_nom,
                        'personnel':   personnel_nom,
                        'description': rdv.description or '',
                    },
                })
            except Exception as e:
                continue

        # ── Ajouter les créneaux ──────────────────────────────
        for creneau in creneaux_qs:
            try:
                if not creneau.plage or not creneau.plage.date_plage:
                    continue

                from datetime import datetime as dt
                from django.utils import timezone as tz

                date_plage = creneau.plage.date_plage
                debut_ev = tz.make_aware(
                    dt.combine(date_plage, creneau.heure_debut)
                )
                fin_ev = tz.make_aware(
                    dt.combine(date_plage, creneau.heure_fin)
                )

                couleur = COULEURS_CRENEAU.get(
                    creneau.statut,
                    {'bg': '#f1f5f9', 'border': '#cbd5e1', 'text': '#475569'}
                )

                try:
                    pers_nom = (
                        f"{creneau.personnel.utilisateur.prenom} "
                        f"{creneau.personnel.utilisateur.nom}"
                    )
                except Exception:
                    pers_nom = "Personnel"

                evenements.append({
                    'id':              f"creneau-{creneau.id}",
                    'title':           f"🕐 {creneau.heure_debut.strftime('%H:%M')}–{creneau.heure_fin.strftime('%H:%M')} {pers_nom}",
                    'start':           debut_ev.isoformat(),
                    'end':             fin_ev.isoformat(),
                    'backgroundColor': couleur['bg'],
                    'borderColor':     couleur['border'],
                    'textColor':       couleur['text'],
                    'extendedProps': {
                        'type':      'creneau',
                        'creneau_id': creneau.id,
                        'statut':    creneau.statut,
                        'personnel': pers_nom,
                    },
                })
            except Exception:
                continue

        return Response({
            'evenements': evenements,
            'total_rdv':       rdvs_qs.count(),
            'total_creneaux':  creneaux_qs.count(),
        })

    def _get_dates_rdv(self, rdv):
        """Calcule start/end d'un RDV pour FullCalendar."""
        from datetime import datetime as dt
        from django.utils import timezone as tz
        try:
            creneau = rdv.creneau
            plage   = getattr(creneau, 'plage', None)
            if plage and plage.date_plage:
                debut = tz.make_aware(dt.combine(plage.date_plage, creneau.heure_debut))
                fin   = tz.make_aware(dt.combine(plage.date_plage, creneau.heure_fin))
                return debut, fin
            # Fallback sur date_creation
            debut = rdv.date_creation.replace(
                hour=creneau.heure_debut.hour,
                minute=creneau.heure_debut.minute,
                second=0, microsecond=0,
            )
            fin = rdv.date_creation.replace(
                hour=creneau.heure_fin.hour,
                minute=creneau.heure_fin.minute,
                second=0, microsecond=0,
            )
            return debut, fin
        except Exception:
            return None, None
        



class DemanderResetMotDePasseView(APIView):
    """
    POST /api/auth/demander-reset/
    Corps : { "email": "user@exemple.com" }
    Envoie un email avec un lien de reset valable 1 heure.
    Toujours retourne 200 même si l'email n'existe pas (sécurité).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from rendezvous.infrastructure.django_models.models import TokenResetModel
        from django.utils import timezone
        from datetime import timedelta
        from django.core.mail import send_mail

        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response(
                {'erreur': 'Email obligatoire.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Réponse identique que l'email existe ou non (anti-énumération)
        MSG = {
            'message': 'Si cet email existe, un lien de réinitialisation a été envoyé.',
            'code':    'RESET_ENVOYE',
        }

        try:
            utilisateur = UtilisateurModel.objects.get(email=email)
        except UtilisateurModel.DoesNotExist:
            return Response(MSG)

        # Invalider les anciens tokens
        TokenResetModel.objects.filter(
            utilisateur=utilisateur, utilise=False
        ).update(utilise=True)

        # Créer un nouveau token valable 1 heure
        expiration = timezone.now() + timedelta(hours=1)
        token_obj  = TokenResetModel.objects.create(
            utilisateur=utilisateur,
            date_expiration=expiration,
        )

        # Lien de reset
        lien = f"http://localhost:3000/reset-password/{token_obj.token}"

        # Email HTML
        corps_html = f"""
            <!DOCTYPE html>
            <html lang="fr">
            <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; background: #f8fafc; margin: 0; padding: 20px; }}
                .container {{ max-width: 560px; margin: 0 auto; background: #fff; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; }}
                .header {{ background: linear-gradient(135deg, #6366f1, #4f46e5); padding: 28px 32px; text-align: center; }}
                .header h1 {{ color: #fff; margin: 0; font-size: 20px; font-weight: 700; }}
                .header p  {{ color: rgba(255,255,255,.85); margin: 6px 0 0; font-size: 13px; }}
                .body {{ padding: 28px 32px; }}
                .info-box {{ background: #faf5ff; border: 1.5px solid #e9d5ff; border-radius: 12px; padding: 16px 20px; margin: 18px 0; font-size: 13px; color: #6b21a8; }}
                .btn {{ display: block; text-align: center; background: #6366f1; color: #fff; padding: 14px 28px; border-radius: 10px; text-decoration: none; font-weight: 700; font-size: 15px; margin: 24px 0; }}
                .lien-fallback {{ font-size: 11px; color: #94a3b8; word-break: break-all; margin-top: 8px; }}
                .warn {{ background: #fff7ed; border-left: 3px solid #f59e0b; padding: 10px 14px; border-radius: 0 8px 8px 0; font-size: 12px; color: #92400e; margin: 16px 0; }}
                .footer {{ background: #f8fafc; padding: 16px 32px; text-align: center; font-size: 11px; color: #9ca3af; border-top: 1px solid #e5e7eb; }}
            </style>
            </head>
            <body>
            <div class="container">
            <div class="header">
                <h1>🔑 Réinitialisation de mot de passe</h1>
                <p>RendezVous Pro — Sécurité de votre compte</p>
            </div>
            <div class="body">
                <p style="font-size:15px;color:#1a2332;">Bonjour <strong>{utilisateur.prenom} {utilisateur.nom}</strong>,</p>
                <p style="font-size:13px;color:#4b5563;line-height:1.6;">
                Vous avez demandé la réinitialisation de votre mot de passe.
                Cliquez sur le bouton ci-dessous pour créer un nouveau mot de passe.
                </p>
                <div class="info-box">
                🔐 Ce lien est <strong>personnel et sécurisé</strong>. Ne le partagez avec personne.
                </div>
                <a href="{lien}" class="btn">Réinitialiser mon mot de passe →</a>
                <p style="font-size:12px;color:#6b7280;">Si le bouton ne fonctionne pas, copiez ce lien :</p>
                <p class="lien-fallback">{lien}</p>
                <div class="warn">
                ⏰ Ce lien expire dans <strong>1 heure</strong>.
                Si vous n'avez pas demandé cette réinitialisation, ignorez cet email — votre mot de passe reste inchangé.
                </div>
            </div>
            <div class="footer">
                © {timezone.now().year} RendezVous Pro — Email automatique, ne pas répondre.
            </div>
            </div>
            </body>
            </html>"""

        corps_texte = (
            f"Bonjour {utilisateur.prenom},\n\n"
            f"Lien de réinitialisation (expire dans 1h) :\n{lien}\n\n"
            f"Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.\n\n"
            f"RendezVous Pro"
        )

        send_mail(
            subject="🔑 Réinitialisation de votre mot de passe — RendezVous Pro",
            message=corps_texte,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@rdvpro.cm'),
            recipient_list=[email],
            html_message=corps_html,
            fail_silently=False,
        )

        return Response(MSG)


class ResetMotDePasseView(APIView):
    """
    POST /api/auth/reset-password/
    Corps : { "token": "uuid", "nouveau_mot_de_passe": "...", "confirmation": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from rendezvous.infrastructure.django_models.models import TokenResetModel

        token_str  = request.data.get('token', '').strip()
        nouveau    = request.data.get('nouveau_mot_de_passe', '')
        confirmation = request.data.get('confirmation', '')

        # ── Validations ───────────────────────────────────────
        if not token_str:
            return Response({'erreur': 'Token obligatoire.'}, status=400)

        if not nouveau:
            return Response({'erreur': 'Nouveau mot de passe obligatoire.'}, status=400)

        if nouveau != confirmation:
            return Response(
                {'erreur': 'Les mots de passe ne correspondent pas.'},
                status=400
            )

        if len(nouveau) < 8:
            return Response(
                {'erreur': 'Le mot de passe doit contenir au moins 8 caractères.'},
                status=400
            )

        # Vérifier complexité
        import re
        if not re.search(r'[A-Z]', nouveau):
            return Response(
                {'erreur': 'Le mot de passe doit contenir au moins une majuscule.'},
                status=400
            )
        if not re.search(r'[0-9]', nouveau):
            return Response(
                {'erreur': 'Le mot de passe doit contenir au moins un chiffre.'},
                status=400
            )

        # ── Récupérer et valider le token ─────────────────────
        try:
            token_obj = TokenResetModel.objects.select_related(
                'utilisateur'
            ).get(token=token_str)
        except (TokenResetModel.DoesNotExist, ValueError):
            return Response(
                {'erreur': 'Token invalide ou expiré.', 'code': 'TOKEN_INVALIDE'},
                status=400
            )

        if not token_obj.est_valide():
            return Response(
                {
                    'erreur': 'Ce lien a expiré ou a déjà été utilisé. Faites une nouvelle demande.',
                    'code': 'TOKEN_EXPIRE',
                },
                status=400
            )

        # ── Changer le mot de passe ───────────────────────────
        utilisateur = token_obj.utilisateur
        utilisateur.set_password(nouveau)
        utilisateur.save()

        # Marquer le token comme utilisé
        token_obj.utilise = True
        token_obj.save()

        # Invalider tous les tokens JWT existants (sécurité)
        try:
            from rest_framework_simplejwt.token_blacklist.models import (
                OutstandingToken, BlacklistedToken
            )
            tokens = OutstandingToken.objects.filter(user=utilisateur)
            for t in tokens:
                BlacklistedToken.objects.get_or_create(token=t)
        except Exception:
            pass

        return Response({
            'message': 'Mot de passe réinitialisé avec succès. Vous pouvez vous connecter.',
            'code':    'RESET_SUCCES',
        })


class ValiderTokenResetView(APIView):
    """
    GET /api/auth/valider-token/?token=uuid
    Vérifie si un token est encore valide avant d'afficher le formulaire.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from rendezvous.infrastructure.django_models.models import TokenResetModel

        token_str = request.query_params.get('token', '').strip()
        if not token_str:
            return Response({'valide': False, 'erreur': 'Token manquant.'})

        try:
            token_obj = TokenResetModel.objects.get(token=token_str)
            if token_obj.est_valide():
                return Response({
                    'valide': True,
                    'email':  token_obj.utilisateur.email[:3] + '***',
                    'prenom': token_obj.utilisateur.prenom,
                })
            else:
                return Response({
                    'valide': False,
                    'erreur': 'Ce lien a expiré ou a déjà été utilisé.',
                    'code':   'TOKEN_EXPIRE',
                })
        except (TokenResetModel.DoesNotExist, ValueError):
            return Response({
                'valide': False,
                'erreur': 'Token invalide.',
                'code':   'TOKEN_INVALIDE',
            })
        

#_________________________________________________

    #____Statistiques avec graphique______
#_________________________________________________

class StatistiquesAvanceesView(APIView):
    """
    GET /api/statistiques/avancees/ — ADMIN SEULEMENT
    Retourne toutes les données pour les graphiques du dashboard.
    """
    permission_classes = [EstAdmin]

    def get(self, request):
        from django.db.models import Count, Sum, Avg
        from django.db.models.functions import TruncMonth, TruncWeek
        from django.utils import timezone
        from datetime import timedelta
        from rendezvous.infrastructure.django_models.models import (
            RendezVousModel, PaiementModel, UtilisateurModel,
            CreneauModel, EntrepriseModel,
        )

        maintenant  = timezone.now()
        il_y_a_30j  = maintenant - timedelta(days=30)
        il_y_a_365j = maintenant - timedelta(days=365)

        # ── 1. RDV par mois (12 derniers mois) ───────────────
        rdv_par_mois_qs = (
            RendezVousModel.objects
            .filter(date_creation__gte=il_y_a_365j)
            .annotate(mois=TruncMonth('date_creation'))
            .values('mois')
            .annotate(
                total=Count('id'),
                confirmes=Count('id', filter=models.Q(statut='confirme')),
                refuses=Count('id',   filter=models.Q(statut='refuse')),
                annules=Count('id',   filter=models.Q(statut='annule')),
                termines=Count('id',  filter=models.Q(statut='termine')),
            )
            .order_by('mois')
        )

        rdv_par_mois = [
            {
                'mois':      r['mois'].strftime('%b %Y'),
                'mois_iso':  r['mois'].strftime('%Y-%m'),
                'total':     r['total'],
                'confirmes': r['confirmes'],
                'refuses':   r['refuses'],
                'annules':   r['annules'],
                'termines':  r['termines'],
            }
            for r in rdv_par_mois_qs
        ]

        # ── 2. Revenus par mois (12 derniers mois) ────────────
        revenus_qs = (
            PaiementModel.objects
            .filter(statut='paye', date_paiement__gte=il_y_a_365j)
            .annotate(mois=TruncMonth('date_paiement'))
            .values('mois')
            .annotate(total=Sum('montant'), nb=Count('id'))
            .order_by('mois')
        )

        revenus_par_mois = [
            {
                'mois':     r['mois'].strftime('%b %Y'),
                'mois_iso': r['mois'].strftime('%Y-%m'),
                'total':    float(r['total'] or 0),
                'nb':       r['nb'],
            }
            for r in revenus_qs
        ]

        # ── 3. Répartition par statut ─────────────────────────
        statuts = (
            RendezVousModel.objects
            .values('statut')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        LABELS_STATUT = {
            'en_attente': 'En attente',
            'confirme':   'Confirmé',
            'refuse':     'Refusé',
            'annule':     'Annulé',
            'termine':    'Terminé',
        }
        COULEURS_STATUT = {
            'en_attente': '#f59e0b',
            'confirme':   '#10b981',
            'refuse':     '#ef4444',
            'annule':     '#94a3b8',
            'termine':    '#6366f1',
        }

        repartition_statuts = [
            {
                'statut':  s['statut'],
                'label':   LABELS_STATUT.get(s['statut'], s['statut']),
                'count':   s['count'],
                'couleur': COULEURS_STATUT.get(s['statut'], '#94a3b8'),
            }
            for s in statuts
        ]

        # ── 4. Répartition paiements par mode ─────────────────
        modes_qs = (
            PaiementModel.objects
            .filter(statut='paye')
            .values('mode_paiement')
            .annotate(count=Count('id'), total=Sum('montant'))
            .order_by('-total')
        )

        LABELS_MODE = {
            'mobile_money': 'Mobile Money',
            'carte':        'Carte bancaire',
            'virement':     'Virement',
            'especes':      'Espèces',
        }
        COULEURS_MODE = {
            'mobile_money': '#10b981',
            'carte':        '#6366f1',
            'virement':     '#3b82f6',
            'especes':      '#f59e0b',
        }

        modes_paiement = [
            {
                'mode':    m['mode_paiement'],
                'label':   LABELS_MODE.get(m['mode_paiement'], m['mode_paiement']),
                'count':   m['count'],
                'total':   float(m['total'] or 0),
                'couleur': COULEURS_MODE.get(m['mode_paiement'], '#94a3b8'),
            }
            for m in modes_qs
        ]

        # ── 5. Top entreprises par nb de RDV ─────────────────
        top_entreprises_qs = (
            RendezVousModel.objects
            .filter(date_creation__gte=il_y_a_365j)
            .values('creneau__personnel__entreprise__nom_entreprise')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        top_entreprises = [
            {
                'nom':   e['creneau__personnel__entreprise__nom_entreprise'] or 'Inconnue',
                'count': e['count'],
            }
            for e in top_entreprises_qs
        ]

        # ── 6. KPIs globaux ───────────────────────────────────
        total_rdv         = RendezVousModel.objects.count()
        rdv_ce_mois       = RendezVousModel.objects.filter(date_creation__month=maintenant.month, date_creation__year=maintenant.year).count()
        rdv_mois_precedent= RendezVousModel.objects.filter(date_creation__month=(maintenant.replace(day=1) - timedelta(days=1)).month).count()

        total_revenus     = PaiementModel.objects.filter(statut='paye').aggregate(t=Sum('montant'))['t'] or 0
        revenus_ce_mois   = PaiementModel.objects.filter(statut='paye', date_paiement__month=maintenant.month, date_paiement__year=maintenant.year).aggregate(t=Sum('montant'))['t'] or 0

        total_clients     = UtilisateurModel.objects.filter(role='client').count()
        clients_ce_mois   = UtilisateurModel.objects.filter(role='client', date_joined__month=maintenant.month, date_joined__year=maintenant.year).count()

        taux_confirmation = round(
            (RendezVousModel.objects.filter(statut__in=['confirme','termine']).count() / total_rdv * 100)
            if total_rdv > 0 else 0, 1
        )

        evolution_rdv = round(
            ((rdv_ce_mois - rdv_mois_precedent) / rdv_mois_precedent * 100)
            if rdv_mois_precedent > 0 else 0, 1
        )

        # ── 7. RDV des 7 derniers jours ───────────────────────
        from django.db.models.functions import TruncDate
        rdv_7j = (
            RendezVousModel.objects
            .filter(date_creation__gte=maintenant - timedelta(days=7))
            .annotate(jour=TruncDate('date_creation'))
            .values('jour')
            .annotate(count=Count('id'))
            .order_by('jour')
        )

        rdv_semaine = [
            {
                'jour':  r['jour'].strftime('%a %d'),
                'count': r['count'],
            }
            for r in rdv_7j
        ]

        return Response({
            'kpis': {
                'total_rdv':          total_rdv,
                'rdv_ce_mois':        rdv_ce_mois,
                'evolution_rdv':      evolution_rdv,
                'total_revenus':      float(total_revenus),
                'revenus_ce_mois':    float(revenus_ce_mois),
                'total_clients':      total_clients,
                'clients_ce_mois':    clients_ce_mois,
                'taux_confirmation':  taux_confirmation,
            },
            'rdv_par_mois':       rdv_par_mois,
            'revenus_par_mois':   revenus_par_mois,
            'repartition_statuts':repartition_statuts,
            'modes_paiement':     modes_paiement,
            'top_entreprises':    top_entreprises,
            'rdv_semaine':        rdv_semaine,
        })
    


#________________________________________________

         #Pour les recus apres paiements
#_________________________________________________


class TelechargerRecuPaiementView(APIView):
    """
    GET /api/paiements/{id}/recu/
    Télécharge le reçu PDF du paiement.
    Client : seulement ses propres paiements.
    Admin  : tous les paiements.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, paiement_id):
        from rendezvous.infrastructure.django_models.models import PaiementModel
        from rendezvous.application.pdf_service import PdfService
        from django.http import HttpResponse

        try:
            paiement = PaiementModel.objects.select_related(
                'rendezvous__client__utilisateur',
                'rendezvous__creneau__personnel__utilisateur',
                'rendezvous__creneau__personnel__entreprise',
            ).get(id=paiement_id)
        except PaiementModel.DoesNotExist:
            return Response({'erreur': 'Paiement introuvable.'}, status=404)

        # Vérification propriété
        if request.user.role == 'client':
            try:
                if paiement.rendezvous.client != request.user.profil_client:
                    return Response({'erreur': 'Non autorisé.'}, status=403)
            except Exception:
                return Response({'erreur': 'Non autorisé.'}, status=403)

        if paiement.statut not in ['paye', 'rembourse']:
            return Response(
                {'erreur': 'Le reçu n\'est disponible que pour les paiements confirmés.'},
                status=400
            )

        try:
            pdf_bytes = PdfService().generer_recu_paiement(paiement)
            response  = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="recu-paiement-{paiement_id}.pdf"'
            )
            return response
        except Exception as e:
            return Response({'erreur': f'Erreur génération PDF : {str(e)}'}, status=500)


class EnvoyerRecuEmailView(APIView):
    """
    POST /api/paiements/{id}/envoyer-recu/
    Envoie le reçu PDF par email au client.
    Admin seulement.
    """
    permission_classes = [EstAdmin]

    def post(self, request, paiement_id):
        from rendezvous.infrastructure.django_models.models import PaiementModel
        from rendezvous.application.pdf_service import PdfService
        from django.core.mail import EmailMessage

        try:
            paiement = PaiementModel.objects.select_related(
                'rendezvous__client__utilisateur',
                'rendezvous__creneau__personnel__utilisateur',
                'rendezvous__creneau__personnel__entreprise',
            ).get(id=paiement_id)
        except PaiementModel.DoesNotExist:
            return Response({'erreur': 'Paiement introuvable.'}, status=404)

        if paiement.statut not in ['paye', 'rembourse']:
            return Response(
                {'erreur': 'Reçu disponible seulement pour paiements confirmés.'},
                status=400
            )

        try:
            pdf_bytes   = PdfService().generer_recu_paiement(paiement)
            client_email = paiement.rendezvous.client.utilisateur.email
            client_nom   = (
                f"{paiement.rendezvous.client.utilisateur.prenom} "
                f"{paiement.rendezvous.client.utilisateur.nom}"
            )
            montant_fcfa = f"{int(paiement.montant):,} FCFA".replace(',', ' ')

            mail = EmailMessage(
                subject=f"💳 Votre reçu de paiement — {montant_fcfa}",
                body=(
                    f"Bonjour {client_nom},\n\n"
                    f"Veuillez trouver ci-joint votre reçu de paiement "
                    f"de {montant_fcfa}.\n\n"
                    f"Merci de votre confiance.\n\n"
                    f"RendezVous Pro"
                ),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@rdvpro.cm'),
                to=[client_email],
            )
            mail.attach(
                f"recu-paiement-{paiement_id}.pdf",
                pdf_bytes,
                'application/pdf',
            )
            mail.send()

            return Response({
                'message': f'Reçu envoyé à {client_email}',
                'email':   client_email,
            })
        except Exception as e:
            return Response({'erreur': str(e)}, status=500)
        


#_________________________________________________________________

     #Gestion des utilisateurs par l'admin
#___________________________________________________________________

class UtilisateurDetailView(APIView):
    """
    GET    /api/users/{id}/  → Admin : voir un utilisateur
    PUT    /api/users/{id}/  → Admin : modifier un utilisateur
    DELETE /api/users/{id}/  → Admin : supprimer un utilisateur
    """
    permission_classes = [EstAdmin]

    def _get_user(self, user_id):
        try:
            return UtilisateurModel.objects.get(id=user_id)
        except UtilisateurModel.DoesNotExist:
            return None

    def get(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({'erreur': 'Utilisateur introuvable.'}, status=404)
        return Response(UtilisateurSerializer(user).data)

    def put(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({'erreur': 'Utilisateur introuvable.'}, status=404)

        # Champs modifiables par l'admin
        nom        = request.data.get('nom',       user.nom)
        prenom     = request.data.get('prenom',    user.prenom)
        email      = request.data.get('email',     user.email)
        telephone  = request.data.get('telephone', user.telephone)
        role       = request.data.get('role',      user.role)
        is_active  = request.data.get('is_active', user.is_active)

        ROLES_VALIDES = ['client', 'personnel', 'admin']
        if role not in ROLES_VALIDES:
            return Response(
                {'erreur': f'Rôle invalide. Valeurs acceptées : {ROLES_VALIDES}'},
                status=400
            )

        # Vérifier unicité email
        if email != user.email:
            if UtilisateurModel.objects.filter(email=email).exclude(id=user_id).exists():
                return Response({'erreur': 'Cet email est déjà utilisé.'}, status=400)

        user.nom       = nom
        user.prenom    = prenom
        user.email     = email
        user.telephone = telephone
        user.role      = role
        user.is_active = is_active
        user.save()

        # Réinitialiser le mot de passe si fourni
        nouveau_mdp = request.data.get('nouveau_mot_de_passe')
        if nouveau_mdp:
            if len(nouveau_mdp) < 8:
                return Response({'erreur': 'Mot de passe trop court (min 8 caractères).'}, status=400)
            user.set_password(nouveau_mdp)
            user.save()

        return Response({
            'message':     'Utilisateur mis à jour.',
            'utilisateur': UtilisateurSerializer(user).data,
        })

    def delete(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({'erreur': 'Utilisateur introuvable.'}, status=404)

        # Empêcher l'admin de se supprimer lui-même
        if user.id == request.user.id:
            return Response(
                {'erreur': 'Vous ne pouvez pas supprimer votre propre compte.'},
                status=400
            )

        email = user.email
        user.delete()
        return Response({
            'message': f'Utilisateur {email} supprimé avec succès.',
        })


class CreerUtilisateurView(APIView):
    """
    POST /api/users/creer/ → Admin crée un utilisateur directement
    """
    permission_classes = [EstAdmin]

    def post(self, request):
        nom       = request.data.get('nom', '').strip()
        prenom    = request.data.get('prenom', '').strip()
        email     = request.data.get('email', '').strip().lower()
        telephone = request.data.get('telephone', '').strip()
        role      = request.data.get('role', 'client')
        password  = request.data.get('password', '').strip()

        # Validations
        if not all([nom, prenom, email, password]):
            return Response(
                {'erreur': 'nom, prenom, email et password sont obligatoires.'},
                status=400
            )
        if len(password) < 8:
            return Response({'erreur': 'Mot de passe min. 8 caractères.'}, status=400)

        ROLES_VALIDES = ['client', 'personnel', 'admin']
        if role not in ROLES_VALIDES:
            return Response({'erreur': f'Rôle invalide : {ROLES_VALIDES}'}, status=400)

        if UtilisateurModel.objects.filter(email=email).exists():
            return Response({'erreur': 'Cet email est déjà utilisé.'}, status=400)

        try:
            # Créer l'utilisateur
            user = UtilisateurModel.objects.create_user(
                email=email, password=password,
                nom=nom, prenom=prenom,
                telephone=telephone, role=role,
            )

            # Créer le profil selon le rôle
            from rendezvous.infrastructure.django_models.models import (
                ClientModel, PersonnelModel, AdministrateurModel
            )
            if role == 'client':
                ClientModel.objects.create(utilisateur=user)
            elif role == 'personnel':
                PersonnelModel.objects.create(
                    utilisateur=user,
                    poste=request.data.get('poste', 'Agent'),
                )
            elif role == 'admin':
                AdministrateurModel.objects.create(utilisateur=user)

            return Response({
                'message':     f'Utilisateur {email} créé avec succès.',
                'utilisateur': UtilisateurSerializer(user).data,
            }, status=201)

        except Exception as e:
            return Response({'erreur': str(e)}, status=400)


class ActiverDesactiverUtilisateurView(APIView):
    """
    POST /api/users/{id}/activer/  → Activer/désactiver un compte
    """
    permission_classes = [EstAdmin]

    def post(self, request, user_id):
        try:
            user = UtilisateurModel.objects.get(id=user_id)
        except UtilisateurModel.DoesNotExist:
            return Response({'erreur': 'Utilisateur introuvable.'}, status=404)

        if user.id == request.user.id:
            return Response(
                {'erreur': 'Vous ne pouvez pas désactiver votre propre compte.'},
                status=400
            )

        user.is_active = not user.is_active
        user.save()

        action = 'activé' if user.is_active else 'désactivé'
        return Response({
            'message':   f'Compte {action} avec succès.',
            'is_active': user.is_active,
        })

