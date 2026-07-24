"""
rendezvous/presentation/views/auth_views.py
"""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from drf_spectacular.utils import extend_schema, OpenApiExample

from config import settings
from rendezvous.presentation.serializers.serializers import LoginSerializer
from rendezvous.presentation.throttling import LoginRateThrottle
from rendezvous.presentation.validators import ValidateurSecurite

logger = logging.getLogger('rendezvous.securite')


"""
rendezvous/presentation/views/auth_views.py
"""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from rendezvous.presentation.serializers.serializers import LoginSerializer
from rendezvous.presentation.validators import ValidateurSecurite

logger = logging.getLogger('rendezvous.securite')


class LoginView(APIView):
    """
    POST /api/auth/login/
    Si 2FA activée → envoie OTP par email et retourne un token temporaire.
    Sinon → retourne les tokens JWT directement.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate
        from rest_framework_simplejwt.tokens import RefreshToken
        from django.utils import timezone
        from datetime import timedelta

        email    = request.data.get('email',    '').strip().lower()
        password = request.data.get('password', '').strip()

        if not email or not password:
            return Response(
                {'erreur': 'Email et mot de passe obligatoires.'},
                status=400
            )

        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response(
                {
                    'erreur': 'Identifiant ou mot de passe incorrect.',
                    'code':   'IDENTIFIANTS_INCORRECTS',
                },
                status=401
            )

        if not user.is_active:
            return Response(
                {
                    'erreur': 'Compte désactivé. Contactez un administrateur.',
                    'code':   'COMPTE_DESACTIVE',
                },
                status=403
            )

        # ── 2FA activée → envoyer OTP ─────────────────────────
        if getattr(user, 'deux_fa_active', False):
            from rendezvous.infrastructure.django_models.models import CodeOtpModel
            from django.core.mail import send_mail

            # Invalider anciens OTP
            CodeOtpModel.objects.filter(
                utilisateur=user, utilise=False
            ).update(utilise=True)

            # Créer nouveau OTP valable 10 minutes
            otp = CodeOtpModel.objects.create(
                utilisateur=user,
                date_expiration=timezone.now() + timedelta(minutes=10),
                
            )
            print(f"CODE OTP pour {user.email} : {otp.code}")

            # Envoyer par email
            send_mail(
                subject='🔐 Code de vérification — RendezVous Pro',
                message=(
                    f"Bonjour {user.prenom},\n\n"
                    f"Votre code de vérification est : {otp.code}\n\n"
                    f"Ce code expire dans 10 minutes.\n"
                    f"Ne le partagez avec personne.\n\n"
                    f"RendezVous Pro"
                ),
                html_message=f"""
<div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;border:1px solid #e2e8f0">
  <div style="background:linear-gradient(135deg,#6366f1,#4f46e5);padding:28px 32px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:20px">🔐 Code de vérification</h1>
  </div>
  <div style="padding:28px 32px;text-align:center">
    <p style="color:#4b5563;font-size:14px">Bonjour <strong>{user.prenom}</strong>,</p>
    <p style="color:#4b5563;font-size:14px">Votre code de vérification est :</p>
    <div style="background:#f0f4ff;border:2px dashed #6366f1;border-radius:12px;padding:20px;margin:20px 0">
      <span style="font-size:36px;font-weight:900;color:#6366f1;letter-spacing:12px">{otp.code}</span>
    </div>
    <p style="color:#9ca3af;font-size:12px"> Expire dans <strong>10 minutes</strong></p>
    <p style="color:#ef4444;font-size:12px">⚠️ Ne partagez jamais ce code.</p>
  </div>
</div>""",
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@rdvpro.cm'),
                recipient_list=[user.email],
                fail_silently=True,
            )

            return Response({
                'deux_fa_requis': True,
                'email_masque':   user.email[:3] + '***@' + user.email.split('@')[1],
                'message':        f'Code envoyé à {user.email[:3]}***',
                'user_id':        user.id,
            }, status=200)

        # ── Pas de 2FA → tokens JWT directs ──────────────────
        refresh = RefreshToken.for_user(user)
        return Response({
            'deux_fa_requis': False,
            'access':         str(refresh.access_token),
            'refresh':        str(refresh),
            'utilisateur': {
                'id':     user.id,
                'nom':    user.nom,
                'prenom': user.prenom,
                'email':  user.email,
                'role':   user.role,
            },
        })


class VerifierOtpView(APIView):
    """
    POST /api/auth/verifier-otp/
    Corps : { "user_id": 1, "code": "123456" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from rendezvous.infrastructure.django_models.models import CodeOtpModel
        from rest_framework_simplejwt.tokens import RefreshToken

        user_id = request.data.get('user_id')
        code    = request.data.get('code', '').strip()

        if not user_id or not code:
            return Response(
                {'erreur': 'user_id et code obligatoires.'},
                status=400
            )

        # Trouver le code OTP
        try:
            otp = CodeOtpModel.objects.filter(
                utilisateur_id=user_id,
                code=code,
                utilise=False,
            ).latest('date_creation')
        except CodeOtpModel.DoesNotExist:
            return Response(
                {
                    'erreur': 'Code incorrect.',
                    'code':   'OTP_INVALIDE',
                },
                status=400
            )

        if not otp.est_valide():
            return Response(
                {
                    'erreur': 'Code expiré. Reconnectez-vous pour recevoir un nouveau code.',
                    'code':   'OTP_EXPIRE',
                },
                status=400
            )

        # Marquer utilisé
        otp.utilise = True
        otp.save()

        # Générer les tokens JWT
        user    = otp.utilisateur
        refresh = RefreshToken.for_user(user)

        return Response({
            'access':      str(refresh.access_token),
            'refresh':     str(refresh),
            'utilisateur': {
                'id':     user.id,
                'nom':    user.nom,
                'prenom': user.prenom,
                'email':  user.email,
                'role':   user.role,
            },
        })


class Activer2FAView(APIView):
    """
    POST /api/auth/activer-2fa/
    Active ou désactive la 2FA pour l'utilisateur connecté.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user.deux_fa_active = not user.deux_fa_active
        user.save()

        action = 'activée' if user.deux_fa_active else 'désactivée'
        return Response({
            'message':        f'Authentification à deux facteurs {action}.',
            'deux_fa_active': user.deux_fa_active,
        })


class LogoutView(APIView):
    """POST /api/auth/logout/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'erreur': 'Le token de rafraîchissement est requis.', 'code': 'TOKEN_MANQUANT'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info(f"Déconnexion : {request.user.email}")
            return Response({'message': 'Déconnexion réussie.'}, status=status.HTTP_200_OK)
        except Exception:
            # Si la blacklist n'est pas activée, on retourne quand même OK
            return Response({'message': 'Déconnexion réussie.'}, status=status.HTTP_200_OK)


class ChangerMotDePasseView(APIView):
    """POST /api/auth/changer-mot-de-passe/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ancien  = request.data.get('ancien_mot_de_passe', '')
        nouveau = request.data.get('nouveau_mot_de_passe', '')
        confirm = request.data.get('confirmation', '')

        if not request.user.check_password(ancien):
            return Response(
                {'erreur': "L'ancien mot de passe est incorrect.", 'code': 'MOT_DE_PASSE_INCORRECT'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if nouveau != confirm:
            return Response(
                {'erreur': 'Les mots de passe ne correspondent pas.', 'code': 'MOT_DE_PASSE_DIFFERENT'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if ancien == nouveau:
            return Response(
                {'erreur': "Le nouveau mot de passe doit être différent.", 'code': 'MOT_DE_PASSE_IDENTIQUE'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            ValidateurSecurite.valider_mot_de_passe(nouveau)
        except ValueError as e:
            return Response({'erreur': str(e), 'code': 'MOT_DE_PASSE_FAIBLE'}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(nouveau)
        request.user.save()
        logger.info(f"MDP changé : {request.user.email}")

        return Response({'message': 'Mot de passe changé. Veuillez vous reconnecter.'})


class LogoutView(APIView):
    """Déconnexion simple sans blacklist."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Sans blacklist — le client supprime juste ses tokens locaux
        return Response(
            {'message': 'Déconnexion réussie.'},
            status=status.HTTP_200_OK
        )

class ChangerMotDePasseView(APIView):
    """Changer son mot de passe."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['auth'],
        summary="Changer le mot de passe",
        description="L'ancien mot de passe est requis. "
                    "Le nouveau doit contenir 8+ caractères, "
                    "une majuscule, un chiffre et un caractère spécial.",
        examples=[
            OpenApiExample(
                name="Exemple",
                value={
                    "ancien_mot_de_passe": "AncienMdp1!",
                    "nouveau_mot_de_passe": "NouveauMdp1!",
                    "confirmation": "NouveauMdp1!",
                },
                request_only=True,
            )
        ]
    )
    def post(self, request):
        ancien  = request.data.get('ancien_mot_de_passe', '')
        nouveau = request.data.get('nouveau_mot_de_passe', '')
        confirm = request.data.get('confirmation', '')

        if not request.user.check_password(ancien):
            logger.warning(
                f"Mauvais ancien MDP : utilisateur #{request.user.id}"
            )
            return Response(
                {
                    'erreur': "L'ancien mot de passe est incorrect.",
                    'code':   'MOT_DE_PASSE_INCORRECT',
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if nouveau != confirm:
            return Response(
                {
                    'erreur': 'Les nouveaux mots de passe ne correspondent pas.',
                    'code':   'MOT_DE_PASSE_DIFFERENT',
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ValidateurSecurite.valider_mot_de_passe(nouveau)
        except ValueError as e:
            return Response(
                {'erreur': str(e), 'code': 'MOT_DE_PASSE_FAIBLE'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if ancien == nouveau:
            return Response(
                {
                    'erreur': "Le nouveau mot de passe doit être différent de l'ancien.",
                    'code':   'MOT_DE_PASSE_IDENTIQUE',
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.set_password(nouveau)
        request.user.save()

        logger.info(f"MDP changé : {request.user.email}")

        return Response(
            {'message': 'Mot de passe changé. Veuillez vous reconnecter.'},
            status=status.HTTP_200_OK
        )