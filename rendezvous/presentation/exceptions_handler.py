"""
=============================================================
  rendezvous/presentation/exceptions_handler.py

  Gestionnaire global des erreurs API
=============================================================
  Ce fichier centralise TOUTE la gestion des erreurs.
  Chaque type d'erreur retourne un JSON clair avec :
  - "erreur"  : le message lisible par l'utilisateur
  - "code"    : un code technique pour le frontend
  - "details" : informations supplémentaires (optionnel)
=============================================================
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404

from rendezvous.domain.exceptions.exceptions import (
    # Utilisateur
    UtilisateurNonTrouve,
    EmailDejaUtilise,
    MotDePasseInvalide,
    PermissionRefusee,
    # Entreprise
    EntrepriseNonTrouvee,
    DomaineNonTrouve,
    # Créneau
    CreneauNonDisponible,
    CreneauNonTrouve,
    # Rendez-vous
    RendezVousNonTrouve,
    RendezVousDejaExistant,
    StatutInvalide,
    # Paiement
    PaiementNonTrouve,
    RendezVousNonConfirme,
    PaiementDejaExistant,
    RemboursementImpossible,
)


def custom_exception_handler(exc, context):
    """
    Gestionnaire d'erreurs personnalisé pour DRF.
    Appelé automatiquement pour chaque erreur dans les vues.

    On l'enregistre dans settings.py sous :
    REST_FRAMEWORK = {
        'EXCEPTION_HANDLER': 'rendezvous.presentation.exceptions_handler.custom_exception_handler'
    }
    """

    # 1. Laisser DRF gérer ses propres erreurs d'abord
    response = exception_handler(exc, context)

    # 2. Si DRF a déjà géré l'erreur, on améliore juste le format
    if response is not None:
        return _formater_erreur_drf(exc, response)

    # 3. Gérer nos exceptions métier (Domain)
    return _gerer_exception_metier(exc)


def _formater_erreur_drf(exc, response):
    """Reformate les erreurs DRF dans notre format standard."""

    # Erreur 401 — non authentifié
    if response.status_code == 401:
        response.data = {
            'erreur': 'Vous devez être connecté pour accéder à cette ressource.',
            'code': 'NON_AUTHENTIFIE',
        }

    # Erreur 403 — permission refusée
    elif response.status_code == 403:
        response.data = {
            'erreur': 'Vous n\'avez pas la permission d\'effectuer cette action.',
            'code': 'PERMISSION_REFUSEE',
        }

    # Erreur 404 — ressource introuvable
    elif response.status_code == 404:
        response.data = {
            'erreur': 'La ressource demandée est introuvable.',
            'code': 'RESSOURCE_INTROUVABLE',
        }

    # Erreur 405 — méthode non autorisée
    elif response.status_code == 405:
        response.data = {
            'erreur': 'Cette méthode HTTP n\'est pas autorisée sur cette route.',
            'code': 'METHODE_NON_AUTORISEE',
        }

    # Erreur 429 — trop de requêtes
    elif response.status_code == 429:
        response.data = {
            'erreur': 'Trop de requêtes. Veuillez patienter avant de réessayer.',
            'code': 'TROP_DE_REQUETES',
        }

    # Erreurs de validation (400) — données invalides
    elif response.status_code == 400:
        response.data = {
            'erreur': 'Les données envoyées sont invalides.',
            'code': 'DONNEES_INVALIDES',
            'details': response.data,  # détails des champs en erreur
        }

    return response


def _gerer_exception_metier(exc):
    """
    Gère les exceptions métier définies dans le Domain.
    Retourne le bon code HTTP selon le type d'erreur.
    """

    # ── Erreurs 404 — ressource introuvable ─────────────────
    not_found_exceptions = (
        UtilisateurNonTrouve,
        EntrepriseNonTrouvee,
        DomaineNonTrouve,
        CreneauNonTrouve,
        RendezVousNonTrouve,
        PaiementNonTrouve,
    )
    if isinstance(exc, not_found_exceptions):
        return Response(
            {
                'erreur': str(exc),
                'code': 'RESSOURCE_INTROUVABLE',
            },
            status=status.HTTP_404_NOT_FOUND
        )

    # ── Erreurs 409 — conflit (doublon) ─────────────────────
    conflict_exceptions = (
        EmailDejaUtilise,
        RendezVousDejaExistant,
        PaiementDejaExistant,
    )
    if isinstance(exc, conflict_exceptions):
        return Response(
            {
                'erreur': str(exc),
                'code': 'CONFLIT',
            },
            status=status.HTTP_409_CONFLICT
        )

    # ── Erreurs 400 — mauvaise requête ──────────────────────
    bad_request_exceptions = (
        MotDePasseInvalide,
        StatutInvalide,
        RendezVousNonConfirme,
        RemboursementImpossible,
        CreneauNonDisponible,
        ValueError,
    )
    if isinstance(exc, bad_request_exceptions):
        return Response(
            {
                'erreur': str(exc),
                'code': 'REQUETE_INVALIDE',
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # ── Erreurs 403 — permission refusée ────────────────────
    if isinstance(exc, (PermissionRefusee, PermissionError)):
        return Response(
            {
                'erreur': str(exc),
                'code': 'PERMISSION_REFUSEE',
            },
            status=status.HTTP_403_FORBIDDEN
        )

    # ── Erreur 404 Django ────────────────────────────────────
    if isinstance(exc, Http404):
        return Response(
            {
                'erreur': 'La ressource demandée est introuvable.',
                'code': 'RESSOURCE_INTROUVABLE',
            },
            status=status.HTTP_404_NOT_FOUND
        )

    # ── Erreur de validation Django ──────────────────────────
    if isinstance(exc, DjangoValidationError):
        return Response(
            {
                'erreur': 'Données invalides.',
                'code': 'DONNEES_INVALIDES',
                'details': exc.message_dict if hasattr(exc, 'message_dict') else str(exc),
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # ── Erreur inconnue — 500 ────────────────────────────────
    # En production, on ne révèle jamais les détails d'une erreur interne
    return Response(
        {
            'erreur': 'Une erreur interne est survenue. Veuillez réessayer.',
            'code': 'ERREUR_INTERNE',
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )