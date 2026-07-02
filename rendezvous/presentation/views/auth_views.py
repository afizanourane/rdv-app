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


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Body: {"email": "...", "password": "..."}
    """
    serializer_class   = LoginSerializer
    permission_classes = [AllowAny]
    # ← Plus de throttle_classes ici — géré par DEFAULT_THROTTLE_RATES

    def post(self, request, *args, **kwargs):
        # Nettoyer l'email
        if hasattr(request.data, '_mutable'):
            request.data._mutable = True
            request.data['email'] = request.data.get('email', '').strip().lower()
            request.data._mutable = False

        response = super().post(request, *args, **kwargs)

        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '?'))
        email = request.data.get('email', 'inconnu')

        if response.status_code == 200:
            logger.info(f"Connexion réussie : {email} | IP : {ip}")
        else:
            logger.warning(f"Connexion échouée : {email} | IP : {ip}")

        return response


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