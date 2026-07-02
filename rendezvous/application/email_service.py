"""
=============================================================
  rendezvous/application/email_service.py

  SERVICE EMAIL — Envoi automatique des notifications
=============================================================
  Ce service est appelé depuis les use cases après chaque
  action importante sur un rendez-vous.

  Il est dans la couche APPLICATION car il orchestre
  l'envoi d'emails en réponse à des actions métier.

  Emails envoyés :
  1. Confirmation de la prise de RDV (au client)
  2. Nouvelle demande de RDV (à l'admin)
  3. RDV confirmé (au client)
  4. RDV refusé avec motif (au client)
  5. RDV annulé (à l'admin)
  6. Paiement confirmé (au client)
=============================================================
"""
import logging
from django.core.mail import send_mail, send_mass_mail
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger('rendezvous.securite')


class EmailService:
    """
    Service centralisé pour tous les emails de l'application.
    Chaque méthode correspond à un événement métier précis.
    """

    @staticmethod
    def _envoyer(sujet: str, message: str, destinataires: list) -> bool:
        """
        Méthode privée — envoie un email et gère les erreurs.
        Retourne True si succès, False si échec.
        """
        try:
            send_mail(
                subject=sujet,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=destinataires,
                # fail_silently=False → on veut voir les erreurs en dev
                fail_silently=False,
            )
            logger.info(
                f"Email envoyé : '{sujet}' → {destinataires}"
            )
            return True
        except Exception as e:
            # On log l'erreur mais on ne plante pas l'application
            # Un email raté ne doit pas bloquer la création d'un RDV
            logger.error(
                f"Erreur envoi email '{sujet}' → {destinataires} : {e}"
            )
            return False

    @staticmethod
    def email_prise_rdv(
        client_email: str,
        client_prenom: str,
        rdv_id: int,
        creneau_heure_debut: str,
        creneau_heure_fin: str,
        description: str = "",
    ) -> bool:
        """
        Email envoyé au CLIENT quand il crée un rendez-vous.
        Confirme que sa demande a bien été reçue.
        """
        sujet = f"[RDV #{rdv_id}] Votre demande a été reçue"

        message = f"""Bonjour {client_prenom},

Votre demande de rendez-vous a bien été enregistrée.

Détails de votre demande :
──────────────────────────
Numéro de RDV  : #{rdv_id}
Créneau        : {creneau_heure_debut} - {creneau_heure_fin}
Description    : {description or 'Aucune description'}
Statut actuel  : En attente de confirmation
──────────────────────────

Un administrateur va examiner votre demande et vous informer
par email dès qu'une décision sera prise.

Vous pouvez suivre l'état de votre rendez-vous en vous
connectant sur votre espace client.

Cordialement,
L'équipe Rendez-vous
"""
        return EmailService._envoyer(sujet, message, [client_email])

    @staticmethod
    def email_nouveau_rdv_admin(
        admin_emails: list,
        rdv_id: int,
        client_nom: str,
        client_email: str,
        creneau_heure_debut: str,
        creneau_heure_fin: str,
        description: str = "",
    ) -> bool:
        """
        Email envoyé aux ADMINS quand un client crée un RDV.
        Les informe qu'une nouvelle demande attend leur validation.
        """
        if not admin_emails:
            return True  # Pas d'admins, pas d'email à envoyer

        sujet = f"[Action requise] Nouveau RDV #{rdv_id} en attente"

        message = f"""Bonjour,

Un nouveau rendez-vous est en attente de votre validation.

Détails de la demande :
──────────────────────────
Numéro de RDV  : #{rdv_id}
Client         : {client_nom}
Email client   : {client_email}
Créneau        : {creneau_heure_debut} - {creneau_heure_fin}
Description    : {description or 'Aucune description'}
──────────────────────────

Connectez-vous à l'interface d'administration pour
confirmer ou refuser cette demande.

URL admin : http://127.0.0.1:8000/admin/

Cordialement,
Système de gestion des rendez-vous
"""
        return EmailService._envoyer(sujet, message, admin_emails)

    @staticmethod
    def email_rdv_confirme(
        client_email: str,
        client_prenom: str,
        rdv_id: int,
        creneau_heure_debut: str,
        creneau_heure_fin: str,
        montant_a_payer: float = None,
    ) -> bool:
        """
        Email envoyé au CLIENT quand son RDV est confirmé par l'admin.
        L'informe qu'il peut maintenant procéder au paiement.
        """
        sujet = f"[RDV #{rdv_id}] Votre rendez-vous est confirmé !"

        section_paiement = ""
        if montant_a_payer:
            section_paiement = f"""
Paiement :
──────────────────────────
Montant à régler : {montant_a_payer:,.0f} FCFA
Mode de paiement : Mobile Money, Carte, Virement, Espèces
──────────────────────────

Veuillez effectuer votre paiement pour finaliser votre RDV.
"""

        message = f"""Bonjour {client_prenom},

Excellente nouvelle ! Votre rendez-vous a été confirmé.

Détails de votre rendez-vous :
──────────────────────────
Numéro de RDV  : #{rdv_id}
Créneau        : {creneau_heure_debut} - {creneau_heure_fin}
Statut         : Confirmé
──────────────────────────
{section_paiement}

Merci de votre confiance.

Cordialement,
L'équipe Rendez-vous
"""
        return EmailService._envoyer(sujet, message, [client_email])

    @staticmethod
    def email_rdv_refuse(
        client_email: str,
        client_prenom: str,
        rdv_id: int,
        creneau_heure_debut: str,
        creneau_heure_fin: str,
        motif_refus: str,
    ) -> bool:
        """
        Email envoyé au CLIENT quand son RDV est refusé.
        Le motif de refus est obligatoire et toujours inclus.
        """
        sujet = f"[RDV #{rdv_id}] Votre demande de rendez-vous"

        message = f"""Bonjour {client_prenom},

Nous avons examiné votre demande de rendez-vous.

Malheureusement, nous ne pouvons pas donner suite à cette
demande pour la raison suivante :

Motif : {motif_refus}

Détails de la demande refusée :
──────────────────────────
Numéro de RDV  : #{rdv_id}
Créneau        : {creneau_heure_debut} - {creneau_heure_fin}
Statut         : Refusé
──────────────────────────

Vous pouvez soumettre une nouvelle demande en choisissant
un autre créneau disponible.

Cordialement,
L'équipe Rendez-vous
"""
        return EmailService._envoyer(sujet, message, [client_email])

    @staticmethod
    def email_rdv_annule(
        client_email: str,
        client_prenom: str,
        rdv_id: int,
        admin_emails: list = None,
    ) -> bool:
        """
        Email envoyé au CLIENT et aux ADMINS quand un RDV est annulé.
        """
        sujet = f"[RDV #{rdv_id}] Rendez-vous annulé"

        message_client = f"""Bonjour {client_prenom},

Votre rendez-vous #{rdv_id} a bien été annulé.

Le créneau est maintenant à nouveau disponible pour d'autres
réservations.

Si vous souhaitez reprendre un rendez-vous, vous pouvez
consulter les créneaux disponibles sur votre espace client.

Cordialement,
L'équipe Rendez-vous
"""
        # Email au client
        EmailService._envoyer(sujet, message_client, [client_email])

        # Email aux admins si fournis
        if admin_emails:
            message_admin = f"""Bonjour,

Le rendez-vous #{rdv_id} a été annulé par le client.

Client : {client_prenom} ({client_email})

Le créneau est maintenant libéré.

Cordialement,
Système de gestion des rendez-vous
"""
            EmailService._envoyer(
                f"[Info] RDV #{rdv_id} annulé par le client",
                message_admin,
                admin_emails
            )

        return True

    @staticmethod
    def email_paiement_confirme(
        client_email: str,
        client_prenom: str,
        rdv_id: int,
        montant: float,
        reference_transaction: str,
        creneau_heure_debut: str,
        creneau_heure_fin: str,
    ) -> bool:
        """
        Email de reçu envoyé au CLIENT après confirmation du paiement.
        Sert de preuve de paiement et de confirmation finale.
        """
        sujet = f"[RDV #{rdv_id}] Paiement confirmé — Reçu"

        message = f"""Bonjour {client_prenom},

Votre paiement a été confirmé avec succès.

══════════════════════════════
         REÇU DE PAIEMENT
══════════════════════════════
Numéro de RDV      : #{rdv_id}
Montant payé       : {montant:,.0f} FCFA
Référence          : {reference_transaction}
Créneau            : {creneau_heure_debut} - {creneau_heure_fin}
Statut RDV         : Terminé
══════════════════════════════

Conservez cet email comme preuve de votre paiement.

Merci pour votre confiance. À bientôt !

Cordialement,
L'équipe Rendez-vous
"""
        return EmailService._envoyer(sujet, message, [client_email])