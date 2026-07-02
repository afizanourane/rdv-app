"""
=============================================================
  rendezvous/presentation/middleware.py

  Middleware de sécurité personnalisé
=============================================================
  Un middleware s'exécute à CHAQUE requête HTTP,
  avant et après la vue. C'est le bon endroit pour
  ajouter des vérifications globales de sécurité.
=============================================================
"""
import logging
import time
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

# Logger dédié à la sécurité
logger = logging.getLogger('rendezvous.securite')


class SecurityMiddleware(MiddlewareMixin):
    """
    Middleware qui s'exécute sur chaque requête pour :
    1. Ajouter des headers de sécurité à chaque réponse
    2. Logger les requêtes suspectes
    3. Bloquer les user-agents malveillants connus
    4. Mesurer le temps de réponse
    """

    # User-agents connus pour être malveillants ou des scanners
    USER_AGENTS_BLOQUES = [
        'sqlmap',       # Outil d'injection SQL automatique
        'nikto',        # Scanner de vulnérabilités
        'nmap',         # Scanner de ports
        'masscan',      # Scanner massif
        'zgrab',        # Scanner réseau
    ]

    def process_request(self, request):
        """Appelé AVANT la vue — vérifie la requête entrante."""

        # Enregistrer l'heure de début pour mesurer le temps de réponse
        request._start_time = time.time()

        # Vérifier le User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        for agent_bloque in self.USER_AGENTS_BLOQUES:
            if agent_bloque in user_agent:
                # Logger la tentative
                logger.warning(
                    f"User-Agent suspect bloqué : {user_agent} "
                    f"| IP : {self._get_ip(request)} "
                    f"| URL : {request.path}"
                )
                return JsonResponse(
                    {
                        'erreur': 'Accès refusé.',
                        'code': 'ACCES_REFUSE',
                    },
                    status=403
                )

        # Logger les requêtes sur les routes sensibles
        routes_sensibles = ['/api/auth/', '/api/users/inscription/']
        if any(request.path.startswith(r) for r in routes_sensibles):
            logger.info(
                f"Route sensible accédée : {request.method} {request.path} "
                f"| IP : {self._get_ip(request)}"
            )

        return None  # Continuer normalement

    def process_response(self, request, response):
        """Appelé APRÈS la vue — modifie la réponse sortante."""

        # Ajouter les headers de sécurité à chaque réponse
        response['X-Content-Type-Options']    = 'nosniff'
        response['X-Frame-Options']           = 'DENY'
        response['X-XSS-Protection']          = '1; mode=block'
        response['Referrer-Policy']           = 'strict-origin-when-cross-origin'
        response['Permissions-Policy']        = 'geolocation=(), microphone=(), camera=()'

        # Content Security Policy — contrôle ce que le navigateur peut charger
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )

        # Supprimer les headers qui révèlent des infos sur le serveur
        if 'Server' in response:
            del response['Server']
        if 'X-Powered-By' in response:
            del response['X-Powered-By']

        # Logger le temps de réponse et les erreurs 5xx
        if hasattr(request, '_start_time'):
            duree = round((time.time() - request._start_time) * 1000, 2)

            if response.status_code >= 500:
                logger.error(
                    f"Erreur serveur {response.status_code} : "
                    f"{request.method} {request.path} "
                    f"| IP : {self._get_ip(request)} "
                    f"| Durée : {duree}ms"
                )
            elif response.status_code == 401:
                logger.warning(
                    f"Tentative d'accès non autorisée : "
                    f"{request.method} {request.path} "
                    f"| IP : {self._get_ip(request)}"
                )
            elif response.status_code == 403:
                logger.warning(
                    f"Permission refusée : "
                    f"{request.method} {request.path} "
                    f"| IP : {self._get_ip(request)}"
                )

        return response

    def _get_ip(self, request):
        """
        Récupère la vraie IP du client, même derrière un proxy.
        X-Forwarded-For est ajouté par les proxies et load balancers.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Prendre la première IP de la liste
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'IP inconnue')