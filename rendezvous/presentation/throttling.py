"""
=============================================================
  rendezvous/presentation/throttling.py

  Limitation du nombre de requêtes (Rate Limiting)
=============================================================
  Protège contre :
  - Les attaques par force brute (deviner les mots de passe)
  - Les attaques DDoS (surcharge du serveur)
  - Le scraping massif des données
=============================================================
"""
import logging
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

logger = logging.getLogger('rendezvous.securite')


class LoginRateThrottle(AnonRateThrottle):
    """
    Limite les tentatives de connexion.
    Maximum 5 tentatives par minute par IP.
    Protège contre les attaques par force brute.
    """
    scope = 'login'

    def throttle_failure(self):
        """Appelé quand la limite est dépassée — on log l'IP suspecte."""
        logger.warning(
            f"Trop de tentatives de connexion depuis l'IP : "
            f"{self.get_ident(self.request)}"
        )
        return super().throttle_failure()


class InscriptionRateThrottle(AnonRateThrottle):
    """
    Limite la création de comptes.
    Maximum 3 inscriptions par heure par IP.
    Protège contre la création massive de faux comptes.
    """
    scope = 'inscription'

    def get_rate(self):
        return '3/hour'


class ApiRateThrottle(UserRateThrottle):
    """
    Limite générale pour les utilisateurs connectés.
    Maximum 200 requêtes par heure.
    """
    scope = 'user'

    def get_rate(self):
        return '200/hour'