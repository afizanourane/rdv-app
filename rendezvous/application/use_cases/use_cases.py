"""
=============================================================
  rendezvous/application/use_cases/use_cases.py

  COUCHE APPLICATION — Tous les use cases
=============================================================
  Un use case = UNE action précise de l'application.
  Chaque classe fait UNE chose et la fait bien.

  Les use cases :
  - Reçoivent leurs dépendances (repositories) via __init__
  - Appliquent les règles métier (définies dans le Domain)
  - Ne savent pas comment les données sont stockées
  - Ne savent pas comment les réponses sont formatées
=============================================================
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


from rendezvous.infrastructure.django_models.models import AdministrateurModel as AM



from rendezvous.domain.entities.utilisateur import (
    UtilisateurEntity, Role, ClientEntity, PersonnelEntity, AdministrateurEntity
)
from rendezvous.domain.entities.entreprise import DomaineEntity, EntrepriseEntity, AvisEntity
from rendezvous.domain.entities.creneau import PlageCreneauEntity, CreneauEntity
from rendezvous.domain.entities.rendezvous import (
    RendezVousEntity, HistoriqueStatutEntity, StatutRendezVous
)
from rendezvous.domain.entities.paiement import (
    PaiementEntity, NotificationEntity, ModePaiement, StatutPaiement
)
from rendezvous.domain.repositories.interfaces import (
    AbstractUtilisateurRepository, AbstractClientRepository,
    AbstractPersonnelRepository, AbstractAdminRepository,
    AbstractDomaineRepository, AbstractEntrepriseRepository, AbstractAvisRepository,
    AbstractPlageRepository, AbstractCreneauRepository,
    AbstractRendezVousRepository, AbstractHistoriqueRepository,
    AbstractPaiementRepository, AbstractNotificationRepository,
)
from rendezvous.domain.exceptions.exceptions import (
    EmailDejaUtilise, MotDePasseInvalide, UtilisateurNonTrouve,
    CreneauNonTrouve, CreneauNonDisponible,
    RendezVousNonTrouve, RendezVousDejaExistant,
    PaiementNonTrouve, RendezVousNonConfirme, PaiementDejaExistant, RemboursementImpossible,
)


# =============================================================
#   USE CASES UTILISATEUR
# =============================================================

@dataclass
class InscriptionInput:
    """Données nécessaires pour créer un compte."""
    nom: str
    prenom: str
    email: str
    password: str
    password_confirm: str
    role: str
    telephone: str = ""


class InscriptionUseCase:
    """
    Use Case : Inscrire un nouvel utilisateur.

    Injection de dépendances via __init__ :
    → on passe les repositories au constructeur
    → facilite les tests (on peut injecter de faux repos)
    """

    def __init__(
        self,
        utilisateur_repo: AbstractUtilisateurRepository,
        client_repo: AbstractClientRepository,
        personnel_repo: AbstractPersonnelRepository,
        admin_repo: AbstractAdminRepository,
    ):
        self._utilisateur_repo = utilisateur_repo
        self._client_repo      = client_repo
        self._personnel_repo   = personnel_repo
        self._admin_repo       = admin_repo

    def execute(self, data: InscriptionInput) -> UtilisateurEntity:

        # 1. Valider les données de base
        if data.password != data.password_confirm:
            raise MotDePasseInvalide("Les mots de passe ne correspondent pas.")
        if len(data.password) < 8:
            raise MotDePasseInvalide("Le mot de passe doit avoir au moins 8 caractères.")

        # 2. Vérifier que l'email n'est pas déjà utilisé
        if self._utilisateur_repo.find_by_email(data.email):
            raise EmailDejaUtilise(data.email)

        # 3. Créer l'entité utilisateur
        try:
            role = Role(data.role)
        except ValueError:
            raise ValueError(f"Rôle invalide : {data.role}")

        utilisateur = UtilisateurEntity(
            nom=data.nom,
            prenom=data.prenom,
            email=data.email,
            role=role,
            telephone=data.telephone,
        )

        # 4. Sauvegarder via le repository
        utilisateur_sauve = self._utilisateur_repo.save(utilisateur, data.password)

        # 5. Créer le profil selon le rôle
        if role == Role.CLIENT:
            self._client_repo.save(
                ClientEntity(utilisateur=utilisateur_sauve)
            )
        elif role == Role.PERSONNEL:
            self._personnel_repo.save(
                PersonnelEntity(utilisateur=utilisateur_sauve, poste="À définir")
            )
        elif role == Role.ADMIN:
            self._admin_repo.save(
                AdministrateurEntity(utilisateur=utilisateur_sauve)
            )

        return utilisateur_sauve


class ListerUtilisateursUseCase:
    """Use Case : Lister tous les utilisateurs (admin uniquement)."""

    def __init__(self, utilisateur_repo: AbstractUtilisateurRepository):
        self._repo = utilisateur_repo

    def execute(self, role: Optional[str] = None) -> List[UtilisateurEntity]:
        return self._repo.find_all(role=role)


class ObtenirUtilisateurUseCase:
    """Use Case : Voir le détail d'un utilisateur."""

    def __init__(self, utilisateur_repo: AbstractUtilisateurRepository):
        self._repo = utilisateur_repo

    def execute(self, user_id: int) -> UtilisateurEntity:
        utilisateur = self._repo.find_by_id(user_id)
        if not utilisateur:
            raise UtilisateurNonTrouve(user_id)
        return utilisateur


class MettreAJourProfilUseCase:
    """Use Case : Modifier son propre profil."""

    def __init__(self, utilisateur_repo: AbstractUtilisateurRepository):
        self._repo = utilisateur_repo

    def execute(
        self, user_id: int,
        nom: str = None, prenom: str = None, telephone: str = None
    ) -> UtilisateurEntity:
        utilisateur = self._repo.find_by_id(user_id)
        if not utilisateur:
            raise UtilisateurNonTrouve(user_id)
        # Mettre à jour uniquement les champs fournis
        if nom:
            utilisateur.nom = nom
        if prenom:
            utilisateur.prenom = prenom
        if telephone is not None:
            utilisateur.telephone = telephone
        return self._repo.update(utilisateur)


class StatistiquesUseCase:
    """Use Case : Statistiques pour le dashboard admin."""

    def __init__(self, utilisateur_repo: AbstractUtilisateurRepository,
                 rdv_repo: AbstractRendezVousRepository):
        self._utilisateur_repo = utilisateur_repo
        self._rdv_repo = rdv_repo

    def execute(self) -> dict:
        return {
            'utilisateurs': self._utilisateur_repo.count_by_role(),
            'rendezvous':   self._rdv_repo.compter_par_statut(),
        }


# =============================================================
#   USE CASES ENTREPRISE
# =============================================================

class CreerDomaineUseCase:
    def __init__(self, domaine_repo: AbstractDomaineRepository):
        self._repo = domaine_repo

    def execute(self, nom_domaine: str, description: str = "") -> DomaineEntity:
        return self._repo.save(
            DomaineEntity(nom_domaine=nom_domaine, description=description)
        )


class ListerDominesUseCase:
    def __init__(self, domaine_repo: AbstractDomaineRepository):
        self._repo = domaine_repo

    def execute(self) -> List[DomaineEntity]:
        return self._repo.find_all()


class CreerEntrepriseUseCase:
    def __init__(self, entreprise_repo: AbstractEntrepriseRepository):
        self._repo = entreprise_repo

    def execute(
        self, nom: str, adresse: str, telephone: str,
        email: str, domaine_id: int, description: str = ""
    ) -> EntrepriseEntity:
        return self._repo.save(EntrepriseEntity(
            nom_entreprise=nom, adresse=adresse,
            telephone=telephone, email=email,
            domaine_id=domaine_id, description=description,
        ))


class ListerEntreprisesUseCase:
    def __init__(self, entreprise_repo: AbstractEntrepriseRepository):
        self._repo = entreprise_repo

    def execute(self, domaine_id: Optional[int] = None) -> List[EntrepriseEntity]:
        return self._repo.find_all(domaine_id=domaine_id)


class LaisserAvisUseCase:
    def __init__(self, avis_repo: AbstractAvisRepository):
        self._repo = avis_repo

    def execute(
        self, entreprise_id: int, client_id: int,
        note: int, commentaire: str = ""
    ) -> AvisEntity:
        avis = AvisEntity(
            entreprise_id=entreprise_id,
            client_id=client_id,
            note=note,
            commentaire=commentaire,
        )
        if not avis.note_valide():
            raise ValueError("La note doit être entre 1 et 5.")
        return self._repo.save(avis)


# =============================================================
#   USE CASES CRÉNEAU
# =============================================================

class CreerCreneauUseCase:
    def __init__(self, creneau_repo: AbstractCreneauRepository):
        self._repo = creneau_repo

    def execute(
        self, personnel_id: int, heure_debut, heure_fin, plage_id=None
    ) -> CreneauEntity:
        creneau = CreneauEntity(
            personnel_id=personnel_id,
            heure_debut=heure_debut,
            heure_fin=heure_fin,
            plage_id=plage_id,
        )
        return self._repo.save(creneau)


class ListerCreneauxDisponiblesUseCase:
    def __init__(self, creneau_repo: AbstractCreneauRepository):
        self._repo = creneau_repo

    def execute(self, entreprise_id: Optional[int] = None) -> List[CreneauEntity]:
        return self._repo.find_disponibles(entreprise_id=entreprise_id)


# =============================================================
#   USE CASES RENDEZ-VOUS
# =============================================================

@dataclass
class CreerRendezVousInput:
    """Données nécessaires pour prendre un rendez-vous."""
    client_id:   int
    creneau_id:  int
    description: str = ""


class CreerRendezVousUseCase:
    """
    Use Case : Un client prend un rendez-vous sur un créneau.

    Orchestration :
    1. Vérifier le créneau
    2. Vérifier pas de doublon
    3. Créer le rendez-vous
    4. Enregistrer dans l'historique
    5. Notifier les admins
    """


    def __init__(
        self,
        rdv_repo:        AbstractRendezVousRepository,
        historique_repo: AbstractHistoriqueRepository,
        creneau_repo:    AbstractCreneauRepository,
        notif_repo:      AbstractNotificationRepository,
    ):
        self._rdv_repo        = rdv_repo
        self._historique_repo = historique_repo
        self._creneau_repo    = creneau_repo
        self._notif_repo      = notif_repo

    def execute(self, data: CreerRendezVousInput) -> RendezVousEntity:
            # 1. Vérifier que le créneau existe et est disponible
            creneau = self._creneau_repo.find_by_id(data.creneau_id)
            if not creneau:
                raise CreneauNonTrouve(data.creneau_id)
            if not creneau.est_disponible():
                raise CreneauNonDisponible(data.creneau_id)

            # 2. Vérifier doublon
            rdvs_existants = self._rdv_repo.find_by_client(data.client_id)
            doublon = any(
                r.creneau_id == data.creneau_id and r.statut == StatutRendezVous.EN_ATTENTE
                for r in rdvs_existants
            )
            if doublon:
                raise RendezVousDejaExistant()

            # 3. Créer le rendez-vous
            rdv = RendezVousEntity(
                client_id=data.client_id,
                creneau_id=data.creneau_id,
                description=data.description,
            )
            rdv_sauve = self._rdv_repo.save(rdv)

            # 4. Historique
            self._historique_repo.save(HistoriqueStatutEntity(
                rendezvous_id=rdv_sauve.id,
                ancien_statut="",
                nouveau_statut="en_attente",
                change_par_id=data.client_id,
                commentaire="Rendez-vous créé par le client",
            ))

            # 5. Notifier les admins
            self._notifier_admins(rdv_sauve)

            # 6. Emails
            self._envoyer_emails_creation(rdv_sauve, data)

            return rdv_sauve

    def _notifier_admins(self, rdv):
        """Notifie les admins qu'un nouveau RDV a été créé."""
        try:
            from rendezvous.infrastructure.django_models.models import (
                UtilisateurModel, NotificationModel
            )
            admins = UtilisateurModel.objects.filter(role='admin', is_active=True)
            for admin in admins:
                NotificationModel.objects.create(
                    destinataire=admin,
                    titre=f"📅 Nouveau RDV #{rdv.id} en attente",
                    message="Un client vient de créer un rendez-vous en attente de confirmation.",
                    type_notification='rendezvous',
                    est_lue=False,
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Erreur notification admin: {e}")

    def _envoyer_emails_creation(self, rdv, data):
        """Envoie les emails de confirmation de création."""
        try:
            from rendezvous.application.email_service import EmailService
            EmailService().envoyer_confirmation_creation(rdv)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Erreur email création RDV: {e}")
    

    # Integration des emails dans les use cases

    def _envoyer_emails_creation(self, rdv, data):
        """
        Envoie les emails après la création d'un RDV.
        Appelé séparément pour ne pas bloquer la création si l'email échoue.
        """
        from rendezvous.application.email_service import EmailService
        from rendezvous.infrastructure.django_models.models import (
            UtilisateurModel, ClientModel, CreneauModel
        )
        try:
            # Récupérer les infos du client
            client_model = ClientModel.objects.select_related(
                'utilisateur'
            ).get(id=data.client_id)
            client = client_model.utilisateur

            # Récupérer le créneau
            creneau = CreneauModel.objects.get(id=data.creneau_id)

            # Email de confirmation au client
            EmailService.email_prise_rdv(
                client_email=client.email,
                client_prenom=client.prenom,
                rdv_id=rdv.id,
                creneau_heure_debut=str(creneau.heure_debut),
                creneau_heure_fin=str(creneau.heure_fin),
                description=data.description,
            )

            # Email de notification aux admins
            admin_emails = list(
                UtilisateurModel.objects
                .filter(role='admin', is_active=True)
                .values_list('email', flat=True)
            )
            EmailService.email_nouveau_rdv_admin(
                admin_emails=admin_emails,
                rdv_id=rdv.id,
                client_nom=client.get_full_name() if hasattr(client, 'get_full_name')
                        else f"{client.prenom} {client.nom}",
                client_email=client.email,
                creneau_heure_debut=str(creneau.heure_debut),
                creneau_heure_fin=str(creneau.heure_fin),
                description=data.description,
            )
        except Exception as e:
            # L'email ne doit jamais bloquer la création du RDV
            import logging
            logging.getLogger('rendezvous.securite').error(
                f"Erreur emails création RDV #{rdv.id} : {e}"
            )
    




    def _notifier_admins(self, rdv: RendezVousEntity):
        """Envoie une notification à chaque admin (1 seule requête SQL)."""
        from rendezvous.infrastructure.django_models.models import UtilisateurModel
        admin_ids = list(
            UtilisateurModel.objects
            .filter(role='admin', is_active=True)
            .values_list('id', flat=True)
        )
        if admin_ids:
            self._notif_repo.save_many([
                NotificationEntity(
                    destinataire_id=aid,
                    titre="Nouveau rendez-vous en attente",
                    message=f"Le rendez-vous #{rdv.id} attend votre confirmation.",
                    type_notification="rendezvous",
                )
                for aid in admin_ids
            ])


class ConfirmerRendezVousUseCase:
    """Use Case : Admin confirme un rendez-vous."""

    def __init__(
        self,
        rdv_repo:        AbstractRendezVousRepository,
        historique_repo: AbstractHistoriqueRepository,
        creneau_repo:    AbstractCreneauRepository,
        notif_repo:      AbstractNotificationRepository,
    ):
        self._rdv_repo        = rdv_repo
        self._historique_repo = historique_repo
        self._creneau_repo    = creneau_repo
        self._notif_repo      = notif_repo

    def execute(self, rdv_id: int, admin_id: int, commentaire: str = "", user_id: int = None) -> RendezVousEntity:
        rdv = self._rdv_repo.find_by_id(rdv_id)
        if not rdv:
            raise RendezVousNonTrouve(rdv_id)

        ancien_statut = rdv.statut.value
       # admin_id peut être None si c'est un personnel qui confirme
        rdv.confirmer(admin_id)

        creneau = self._creneau_repo.find_by_id(rdv.creneau_id)
        if creneau:
            creneau.reserver()
            self._creneau_repo.update(creneau)

        rdv_maj = self._rdv_repo.update(rdv)

        # Utiliser user_id si fourni, sinon résoudre depuis admin_id
        change_par = user_id
        if not change_par:
            try:
                from rendezvous.infrastructure.django_models.models import AdministrateurModel as AM
                change_par = AM.objects.get(id=admin_id).utilisateur_id
            except Exception:
                change_par = admin_id

        self._historique_repo.save(HistoriqueStatutEntity(
            rendezvous_id=rdv_maj.id,
            ancien_statut=ancien_statut,
            nouveau_statut="confirme",
            change_par_id=change_par,
            commentaire=commentaire or "Confirmé par l'administrateur",
        ))

        # ← AJOUTER ICI — Notifier le client
        try:
            from rendezvous.infrastructure.django_models.models import (
                RendezVousModel, NotificationModel
            )
            rdv_model = RendezVousModel.objects.select_related(
                'client__utilisateur'
            ).get(id=rdv_maj.id)

            # Notification au client
            # Notification au client
            NotificationModel.objects.create(
                destinataire=rdv_model.client.utilisateur,
                titre=f"✅ Rendez-vous #{rdv_maj.id} confirmé !",
                message=(
                    f"Votre rendez-vous #{rdv_maj.id} a été confirmé.\n\n"
                    f"📋 Détails :\n"
                    f"• Personnel : {rdv_model.creneau.personnel.utilisateur.prenom} "
                    f"{rdv_model.creneau.personnel.utilisateur.nom}\n"
                    f"• Créneau : {rdv_model.creneau.heure_debut.strftime('%H:%M')} – "
                    f"{rdv_model.creneau.heure_fin.strftime('%H:%M')}\n"
                    f"• Service : {rdv_model.service.nom if rdv_model.service else 'Non précisé'}\n"
                    f"• Montant : {int(rdv_model.prix_snapshot):,} FCFA\n\n"
                    f"💳 Vous pouvez maintenant effectuer le paiement depuis votre espace client."
                ) if rdv_model.prix_snapshot else (
                    f"Votre rendez-vous #{rdv_maj.id} a été confirmé.\n\n"
                    f"📋 Détails :\n"
                    f"• Personnel : {rdv_model.creneau.personnel.utilisateur.prenom} "
                    f"{rdv_model.creneau.personnel.utilisateur.nom}\n"
                    f"• Créneau : {rdv_model.creneau.heure_debut.strftime('%H:%M')} – "
                    f"{rdv_model.creneau.heure_fin.strftime('%H:%M')}\n"
                    f"• Service : {rdv_model.service.nom if rdv_model.service else 'Non précisé'}\n\n"
                    f"💳 Vous pouvez maintenant effectuer le paiement depuis votre espace client."
                ),
                type_notification='rendezvous',
                est_lue=False,
            )

            # Notifier le personnel si c'est l'admin qui a confirmé
            if admin_id:
                try:
                    personnel = rdv_model.creneau.personnel.utilisateur
                    NotificationModel.objects.create(
                        destinataire=personnel,
                        titre=f" RDV #{rdv_maj.id} confirmé par l'admin",
                        message=(
                            f"Le rendez-vous #{rdv_maj.id} a été confirmé par l'administrateur.\n\n"
                            f"📋 Détails :\n"
                            f"• Client : {rdv_model.client.utilisateur.prenom} "
                            f"{rdv_model.client.utilisateur.nom}\n"
                            f"• Créneau : {rdv_model.creneau.heure_debut.strftime('%H:%M')} – "
                            f"{rdv_model.creneau.heure_fin.strftime('%H:%M')}\n"
                            f"• Service : {rdv_model.service.nom if rdv_model.service else 'Non précisé'}"
                        ),
                        type_notification='rendezvous',
                        est_lue=False,
                    )
                except Exception:
                    pass

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Erreur notification confirmation: {e}")

        return rdv_maj

        self._notif_repo.save(NotificationEntity(
            destinataire_id=rdv.client_id,
            titre="Rendez-vous confirmé ✅",
            message=f"Votre RDV #{rdv_id} est confirmé. Procédez au paiement.",
            type_notification="rendezvous",
        ))

        self._envoyer_email_confirmation(rdv_maj, rdv_id)
        return rdv_maj


    def _envoyer_email_confirmation(self, rdv, rdv_id):
        """Envoie l'email de confirmation au client."""
        from rendezvous.application.email_service import EmailService
        from rendezvous.infrastructure.django_models.models import (
            ClientModel, CreneauModel
        )
        try:
            client_model = ClientModel.objects.select_related(
                'utilisateur'
            ).get(id=rdv.client_id)
            creneau = CreneauModel.objects.get(id=rdv.creneau_id)

            EmailService.email_rdv_confirme(
                client_email=client_model.utilisateur.email,
                client_prenom=client_model.utilisateur.prenom,
                rdv_id=rdv_id,
                creneau_heure_debut=str(creneau.heure_debut),
                creneau_heure_fin=str(creneau.heure_fin),
            )
        except Exception as e:
            import logging
            logging.getLogger('rendezvous.securite').error(
                f"Erreur email confirmation RDV #{rdv_id} : {e}"
            )



class RefuserRendezVousUseCase:
    """Use Case : Admin refuse un rendez-vous avec un motif."""

    def __init__(
        self,
        rdv_repo:        AbstractRendezVousRepository,
        historique_repo: AbstractHistoriqueRepository,
        notif_repo:      AbstractNotificationRepository,
    ):
        self._rdv_repo        = rdv_repo
        self._historique_repo = historique_repo
        self._notif_repo      = notif_repo

    def execute(self, rdv_id: int, admin_id: int, motif: str = "", user_id: int = None) -> RendezVousEntity:
        rdv = self._rdv_repo.find_by_id(rdv_id)
        if not rdv:
            raise RendezVousNonTrouve(rdv_id)

        ancien_statut = rdv.statut.value
        rdv.refuser(admin_id, motif)
        rdv_maj = self._rdv_repo.update(rdv)

        change_par = user_id
        if not change_par:
            try:
                from rendezvous.infrastructure.django_models.models import AdministrateurModel as AM
                change_par = AM.objects.get(id=admin_id).utilisateur_id
            except Exception:
                change_par = admin_id

        self._historique_repo.save(HistoriqueStatutEntity(
            rendezvous_id=rdv_maj.id,
            ancien_statut=ancien_statut,
            nouveau_statut="refuse",
            change_par_id=change_par,
            commentaire=motif or "Refusé par l'administrateur",
        ))

        self._notif_repo.save(NotificationEntity(
            destinataire_id=rdv.client_id,
            titre="Rendez-vous refusé ❌",
            message=f"Votre RDV #{rdv_id} a été refusé. Motif : {motif}",
            type_notification="rendezvous",
        ))

        return rdv_maj


def _envoyer_email_refus(self, rdv, rdv_id, motif):
    """Envoie l'email de refus au client."""
    from rendezvous.application.email_service import EmailService
    from rendezvous.infrastructure.django_models.models import (
        ClientModel, CreneauModel
    )
    try:
        client_model = ClientModel.objects.select_related(
            'utilisateur'
        ).get(id=rdv.client_id)
        creneau = CreneauModel.objects.get(id=rdv.creneau_id)

        EmailService.email_rdv_refuse(
            client_email=client_model.utilisateur.email,
            client_prenom=client_model.utilisateur.prenom,
            rdv_id=rdv_id,
            creneau_heure_debut=str(creneau.heure_debut),
            creneau_heure_fin=str(creneau.heure_fin),
            motif_refus=motif,
        )
    except Exception as e:
        import logging
        logging.getLogger('rendezvous.securite').error(
            f"Erreur email refus RDV #{rdv_id} : {e}"
        )


class AnnulerRendezVousUseCase:
    """Use Case : Client annule son propre rendez-vous."""

    def __init__(
        self,
        rdv_repo:        AbstractRendezVousRepository,
        historique_repo: AbstractHistoriqueRepository,
        creneau_repo:    AbstractCreneauRepository,
    ):
        self._rdv_repo        = rdv_repo
        self._historique_repo = historique_repo
        self._creneau_repo    = creneau_repo

    def execute(self, rdv_id: int, client_id: int) -> RendezVousEntity:
        rdv = self._rdv_repo.find_by_id(rdv_id)
        if not rdv:
            raise RendezVousNonTrouve(rdv_id)

        # Vérifier que le RDV appartient bien à ce client
        if rdv.client_id != client_id:
            raise PermissionError("Vous ne pouvez annuler que vos propres RDV.")

        ancien_statut = rdv.statut.value
        rdv.annuler()       # règle métier dans le Domain

        rdv_maj = self._rdv_repo.update(rdv)

        # Libérer le créneau
        creneau = self._creneau_repo.find_by_id(rdv.creneau_id)
        if creneau:
            creneau.liberer()
            self._creneau_repo.update(creneau)

        self._historique_repo.save(HistoriqueStatutEntity(
            rendezvous_id=rdv_id,
            ancien_statut=ancien_statut,
            nouveau_statut="annule",
            change_par_id=client_id,
            commentaire="Annulé par le client",
        ))

        # ── EMAIL ────────────────────────────────────────────────
        self._envoyer_email_annulation(rdv_maj)
        # ────────────────────────────────────────────────────────

        return rdv_maj


def _envoyer_email_annulation(self, rdv):
    """Envoie les emails d'annulation."""
    from rendezvous.application.email_service import EmailService
    from rendezvous.infrastructure.django_models.models import (
        ClientModel, UtilisateurModel
    )
    try:
        client_model = ClientModel.objects.select_related(
            'utilisateur'
        ).get(id=rdv.client_id)

        admin_emails = list(
            UtilisateurModel.objects
            .filter(role='admin', is_active=True)
            .values_list('email', flat=True)
        )

        EmailService.email_rdv_annule(
            client_email=client_model.utilisateur.email,
            client_prenom=client_model.utilisateur.prenom,
            rdv_id=rdv.id,
            admin_emails=admin_emails,
        )
    except Exception as e:
        import logging
        logging.getLogger('rendezvous.securite').error(
            f"Erreur email annulation RDV #{rdv.id} : {e}"
        )


# =============================================================
#   USE CASES PAIEMENT
# =============================================================

class InitierPaiementUseCase:
    """Use Case : Client initie un paiement pour un RDV confirmé."""

    def __init__(
        self,
        paiement_repo: AbstractPaiementRepository,
        rdv_repo:      AbstractRendezVousRepository,
    ):
        self._paiement_repo = paiement_repo
        self._rdv_repo      = rdv_repo

    def execute(
        self, rendezvous_id: int, montant: Decimal, mode_paiement: str
    ) -> PaiementEntity:
        # Le RDV doit être confirmé
        # Le RDV doit être confirmé
        rdv = self._rdv_repo.find_by_id(rendezvous_id)
        if not rdv or rdv.statut != StatutRendezVous.CONFIRME:
            raise RendezVousNonConfirme()

        # Vérifier que le paiement est autorisé (verrou de sécurité)
        from rendezvous.infrastructure.django_models.models import RendezVousModel
        try:
            rdv_model = RendezVousModel.objects.get(id=rendezvous_id)
            if not rdv_model.paiement_autorise:
                raise RendezVousNonConfirme()
        except RendezVousModel.DoesNotExist:
            raise RendezVousNonConfirme()

        # Pas de double paiement
        if self._paiement_repo.find_by_rendezvous(rendezvous_id):
            raise PaiementDejaExistant()

        try:
            mode = ModePaiement(mode_paiement)
        except ValueError:
            raise ValueError(f"Mode de paiement invalide : {mode_paiement}")

        return self._paiement_repo.save(PaiementEntity(
            rendezvous_id=rendezvous_id,
            montant=montant,
            mode_paiement=mode,
        ))


class ConfirmerPaiementUseCase:
    """Use Case : Admin confirme la réception du paiement."""

    def __init__(
        self,
        paiement_repo: AbstractPaiementRepository,
        rdv_repo:      AbstractRendezVousRepository,
        notif_repo:    AbstractNotificationRepository,
    ):
        self._paiement_repo = paiement_repo
        self._rdv_repo      = rdv_repo
        self._notif_repo    = notif_repo

    def execute(self, paiement_id: int, reference: str) -> PaiementEntity:
        paiement = self._paiement_repo.find_by_id(paiement_id)
        if not paiement:
            raise PaiementNonTrouve(paiement_id)

        paiement.marquer_paye(reference)    # règle métier dans Domain
        paiement_maj = self._paiement_repo.update(paiement)

        # Passer le RDV à "terminé"
        rdv = self._rdv_repo.find_by_id(paiement.rendezvous_id)
        if rdv:
            rdv.statut = StatutRendezVous.TERMINE
            self._rdv_repo.update(rdv)

            # Notifier le client
            self._notif_repo.save(NotificationEntity(
                destinataire_id=rdv.client_id,
                titre="Paiement confirmé ✅",
                message=(
                    f"Votre paiement de {paiement.montant} FCFA est confirmé. "
                    f"Référence : {reference}"
                ),
                type_notification="paiement",
            ))

        # ── EMAIL ────────────────────────────────────────────────
        self._envoyer_email_paiement(paiement_maj, reference)
        # ────────────────────────────────────────────────────────

        return paiement_maj


    def _envoyer_email_paiement(self, paiement, reference):
        """Envoie l'email de reçu de paiement."""
        from rendezvous.application.email_service import EmailService
        from rendezvous.infrastructure.django_models.models import (
            ClientModel, CreneauModel, RendezVousModel
        )
        try:
            rdv_model = RendezVousModel.objects.select_related(
                'client__utilisateur', 'creneau'
            ).get(id=paiement.rendezvous_id)

            EmailService.email_paiement_confirme(
                client_email=rdv_model.client.utilisateur.email,
                client_prenom=rdv_model.client.utilisateur.prenom,
                rdv_id=rdv_model.id,
                montant=float(paiement.montant),
                reference_transaction=reference,
                creneau_heure_debut=str(rdv_model.creneau.heure_debut),
                creneau_heure_fin=str(rdv_model.creneau.heure_fin),
            )
        except Exception as e:
            import logging
            logging.getLogger('rendezvous.securite').error(
                f"Erreur email paiement RDV #{paiement.rendezvous_id} : {e}"
            )


class RembourserPaiementUseCase:
    """Use Case : Admin rembourse un paiement."""

    def __init__(self, paiement_repo: AbstractPaiementRepository):
        self._paiement_repo = paiement_repo

    def execute(self, paiement_id: int) -> PaiementEntity:
        paiement = self._paiement_repo.find_by_id(paiement_id)
        if not paiement:
            raise PaiementNonTrouve(paiement_id)
        if not paiement.peut_etre_rembourse():  # règle métier dans Domain
            raise RemboursementImpossible()
        paiement.statut = StatutPaiement.REMBOURSE
        return self._paiement_repo.update(paiement)


# =============================================================
#   USE CASES NOTIFICATION
# =============================================================

class ListerNotificationsUseCase:
    def __init__(self, notif_repo: AbstractNotificationRepository):
        self._repo = notif_repo

    def execute(
        self, user_id: int, non_lues_seulement: bool = False
    ) -> List[NotificationEntity]:
        return self._repo.find_by_destinataire(user_id, non_lues_seulement)


class MarquerLueUseCase:
    def __init__(self, notif_repo: AbstractNotificationRepository):
        self._repo = notif_repo

    def execute(self, notif_id: int) -> NotificationEntity:
        return self._repo.marquer_lue(notif_id)


class MarquerToutesLuesUseCase:
    def __init__(self, notif_repo: AbstractNotificationRepository):
        self._repo = notif_repo

    def execute(self, user_id: int) -> dict:
        count = self._repo.marquer_toutes_lues(user_id)
        return {"message": f"{count} notifications marquées comme lues.", "count": count}