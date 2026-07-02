"""
=============================================================
  rendezvous/domain/repositories/interfaces.py

  COUCHE DOMAIN — Contrats des repositories
=============================================================
  Un repository = la "porte" vers le stockage des données.

  Ici on dit CE QU'ON PEUT FAIRE (le menu),
  sans dire COMMENT c'est fait (la recette).

  L'implémentation réelle (avec Django) est dans
  la couche INFRASTRUCTURE.
=============================================================
"""
from abc import ABC, abstractmethod     # ABC = classe qu'on ne peut pas instancier directement
from typing import Optional, List

from rendezvous.domain.entities.utilisateur import (
    UtilisateurEntity, ClientEntity, PersonnelEntity, AdministrateurEntity
)
from rendezvous.domain.entities.entreprise import (
    DomaineEntity, EntrepriseEntity, AvisEntity
)
from rendezvous.domain.entities.creneau import PlageCreneauEntity, CreneauEntity
from rendezvous.domain.entities.rendezvous import RendezVousEntity, HistoriqueStatutEntity
from rendezvous.domain.entities.paiement import PaiementEntity, NotificationEntity


# =============================================================
#   REPOSITORIES UTILISATEUR
# =============================================================

class AbstractUtilisateurRepository(ABC):
    """Contrat pour le stockage des utilisateurs."""

    @abstractmethod
    def save(self, utilisateur: UtilisateurEntity, password: str) -> UtilisateurEntity:
        pass

    @abstractmethod
    def find_by_id(self, user_id: int) -> Optional[UtilisateurEntity]:
        pass

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[UtilisateurEntity]:
        pass

    @abstractmethod
    def find_all(self, role: Optional[str] = None) -> List[UtilisateurEntity]:
        pass

    @abstractmethod
    def update(self, utilisateur: UtilisateurEntity) -> UtilisateurEntity:
        pass

    @abstractmethod
    def count_by_role(self) -> dict:
        pass


class AbstractClientRepository(ABC):
    @abstractmethod
    def save(self, client: ClientEntity) -> ClientEntity:
        pass

    @abstractmethod
    def find_by_utilisateur_id(self, user_id: int) -> Optional[ClientEntity]:
        pass


class AbstractPersonnelRepository(ABC):
    @abstractmethod
    def save(self, personnel: PersonnelEntity) -> PersonnelEntity:
        pass

    @abstractmethod
    def find_by_utilisateur_id(self, user_id: int) -> Optional[PersonnelEntity]:
        pass

    @abstractmethod
    def find_by_entreprise(self, entreprise_id: int) -> List[PersonnelEntity]:
        pass


class AbstractAdminRepository(ABC):
    @abstractmethod
    def save(self, admin: AdministrateurEntity) -> AdministrateurEntity:
        pass

    @abstractmethod
    def find_by_utilisateur_id(self, user_id: int) -> Optional[AdministrateurEntity]:
        pass


# =============================================================
#   REPOSITORIES ENTREPRISE
# =============================================================

class AbstractDomaineRepository(ABC):
    @abstractmethod
    def save(self, domaine: DomaineEntity) -> DomaineEntity:
        pass

    @abstractmethod
    def find_all(self) -> List[DomaineEntity]:
        pass

    @abstractmethod
    def find_by_id(self, did: int) -> Optional[DomaineEntity]:
        pass

    @abstractmethod
    def delete(self, did: int) -> bool:
        pass


class AbstractEntrepriseRepository(ABC):
    @abstractmethod
    def save(self, entreprise: EntrepriseEntity) -> EntrepriseEntity:
        pass

    @abstractmethod
    def find_by_id(self, eid: int) -> Optional[EntrepriseEntity]:
        pass

    @abstractmethod
    def find_all(self, domaine_id: Optional[int] = None) -> List[EntrepriseEntity]:
        pass

    @abstractmethod
    def update(self, entreprise: EntrepriseEntity) -> EntrepriseEntity:
        pass

    @abstractmethod
    def delete(self, eid: int) -> bool:
        pass


class AbstractAvisRepository(ABC):
    @abstractmethod
    def save(self, avis: AvisEntity) -> AvisEntity:
        pass

    @abstractmethod
    def find_by_entreprise(self, eid: int) -> List[AvisEntity]:
        pass


# =============================================================
#   REPOSITORIES CRÉNEAU
# =============================================================

class AbstractPlageRepository(ABC):
    @abstractmethod
    def save(self, plage: PlageCreneauEntity) -> PlageCreneauEntity:
        pass

    @abstractmethod
    def find_by_id(self, pid: int) -> Optional[PlageCreneauEntity]:
        pass

    @abstractmethod
    def find_by_entreprise(self, eid: int) -> List[PlageCreneauEntity]:
        pass


class AbstractCreneauRepository(ABC):
    @abstractmethod
    def save(self, creneau: CreneauEntity) -> CreneauEntity:
        pass

    @abstractmethod
    def find_by_id(self, cid: int) -> Optional[CreneauEntity]:
        pass

    @abstractmethod
    def find_disponibles(self, entreprise_id: Optional[int] = None) -> List[CreneauEntity]:
        pass

    @abstractmethod
    def update(self, creneau: CreneauEntity) -> CreneauEntity:
        pass

    @abstractmethod
    def delete(self, cid: int) -> bool:
        pass


# =============================================================
#   REPOSITORIES RENDEZ-VOUS
# =============================================================

class AbstractRendezVousRepository(ABC):
    @abstractmethod
    def save(self, rdv: RendezVousEntity) -> RendezVousEntity:
        pass

    @abstractmethod
    def find_by_id(self, rdv_id: int) -> Optional[RendezVousEntity]:
        pass

    @abstractmethod
    def find_by_client(self, client_id: int) -> List[RendezVousEntity]:
        pass

    @abstractmethod
    def find_all(self, statut: Optional[str] = None) -> List[RendezVousEntity]:
        pass

    @abstractmethod
    def update(self, rdv: RendezVousEntity) -> RendezVousEntity:
        pass

    @abstractmethod
    def compter_par_statut(self) -> dict:
        pass


class AbstractHistoriqueRepository(ABC):
    @abstractmethod
    def save(self, h: HistoriqueStatutEntity) -> HistoriqueStatutEntity:
        pass

    @abstractmethod
    def find_by_rendezvous(self, rdv_id: int) -> List[HistoriqueStatutEntity]:
        pass


# =============================================================
#   REPOSITORIES PAIEMENT ET NOTIFICATION
# =============================================================

class AbstractPaiementRepository(ABC):
    @abstractmethod
    def save(self, paiement: PaiementEntity) -> PaiementEntity:
        pass

    @abstractmethod
    def find_by_id(self, pid: int) -> Optional[PaiementEntity]:
        pass

    @abstractmethod
    def find_by_rendezvous(self, rdv_id: int) -> Optional[PaiementEntity]:
        pass

    @abstractmethod
    def find_by_client(self, client_id: int) -> List[PaiementEntity]:
        pass

    @abstractmethod
    def update(self, paiement: PaiementEntity) -> PaiementEntity:
        pass


class AbstractNotificationRepository(ABC):
    @abstractmethod
    def save(self, notif: NotificationEntity) -> NotificationEntity:
        pass

    @abstractmethod
    def save_many(self, notifs: List[NotificationEntity]) -> None:
        pass

    @abstractmethod
    def find_by_destinataire(
        self, user_id: int, non_lues_seulement: bool = False
    ) -> List[NotificationEntity]:
        pass

    @abstractmethod
    def marquer_lue(self, notif_id: int) -> NotificationEntity:
        pass

    @abstractmethod
    def marquer_toutes_lues(self, user_id: int) -> int:
        pass