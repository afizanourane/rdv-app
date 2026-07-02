"""
=============================================================
  rendezvous/infrastructure/repositories/implementations.py

  COUCHE INFRASTRUCTURE — Implémentation des repositories
=============================================================
  Ces classes implémentent les CONTRATS définis dans le Domain.

  Méthode de travail :
  1. Reçoit une entité Domain (ex: RendezVousEntity)
  2. La convertit en modèle Django (_to_entity / _to_model)
  3. Effectue l'opération en base (save, filter, get...)
  4. Reconvertit le modèle Django en entité Domain
  5. Retourne l'entité Domain à la couche Application

  Le Domain ne sait pas que Django existe → c'est voulu.
=============================================================
"""
from typing import Optional, List
from django.utils import timezone

# Entités Domain
from rendezvous.domain.entities.utilisateur import (
    UtilisateurEntity, Role, ClientEntity, PersonnelEntity, AdministrateurEntity
)
from rendezvous.domain.entities.entreprise import DomaineEntity, EntrepriseEntity, AvisEntity
from rendezvous.domain.entities.creneau import PlageCreneauEntity, CreneauEntity, StatutCreneau
from rendezvous.domain.entities.rendezvous import RendezVousEntity, StatutRendezVous, HistoriqueStatutEntity
from rendezvous.domain.entities.paiement import PaiementEntity, NotificationEntity, StatutPaiement, ModePaiement

# Contrats du Domain
from rendezvous.domain.repositories.interfaces import (
    AbstractUtilisateurRepository, AbstractClientRepository,
    AbstractPersonnelRepository, AbstractAdminRepository,
    AbstractDomaineRepository, AbstractEntrepriseRepository, AbstractAvisRepository,
    AbstractPlageRepository, AbstractCreneauRepository,
    AbstractRendezVousRepository, AbstractHistoriqueRepository,
    AbstractPaiementRepository, AbstractNotificationRepository,
)

# Modèles Django (Infrastructure)
from rendezvous.infrastructure.django_models.models import (
    UtilisateurModel, ClientModel, AdministrateurModel, PersonnelModel,
    DomaineModel, EntrepriseModel, AvisModel,
    PlageCreneauModel, CreneauModel,
    RendezVousModel, HistoriqueStatutModel,
    PaiementModel, NotificationModel,
)


# =============================================================
#   REPOSITORIES UTILISATEUR
# =============================================================

class DjangoUtilisateurRepository(AbstractUtilisateurRepository):
    """
    Implémentation concrète avec Django ORM + PostgreSQL.
    Convertit UtilisateurModel ↔ UtilisateurEntity.
    """

    def _to_entity(self, model: UtilisateurModel) -> UtilisateurEntity:
        """Convertit un modèle Django → entité Domain (mapper)."""
        return UtilisateurEntity(
            id=model.id,
            nom=model.nom,
            prenom=model.prenom,
            email=model.email,
            telephone=model.telephone,
            # "client" (string) → Role.CLIENT (Enum)
            role=Role(model.role),
            is_active=model.is_active,
            date_joined=model.date_joined,
        )

    def save(self, utilisateur: UtilisateurEntity, password: str) -> UtilisateurEntity:
        """Crée un utilisateur avec mot de passe haché."""
        model = UtilisateurModel.objects.create_user(
            email=utilisateur.email,
            password=password,                  # haché automatiquement
            nom=utilisateur.nom,
            prenom=utilisateur.prenom,
            telephone=utilisateur.telephone or '',
            # Role.CLIENT (Enum) → "client" (string)
            role=utilisateur.role.value,
        )
        return self._to_entity(model)

    def find_by_id(self, user_id: int) -> Optional[UtilisateurEntity]:
        try:
            return self._to_entity(UtilisateurModel.objects.get(id=user_id))
        except UtilisateurModel.DoesNotExist:
            return None     # on retourne None, pas d'exception

    def find_by_email(self, email: str) -> Optional[UtilisateurEntity]:
        try:
            return self._to_entity(UtilisateurModel.objects.get(email=email))
        except UtilisateurModel.DoesNotExist:
            return None

    def find_all(self, role: Optional[str] = None) -> List[UtilisateurEntity]:
        qs = UtilisateurModel.objects.all().order_by('-date_joined')
        if role:
            qs = qs.filter(role=role)
        return [self._to_entity(m) for m in qs]

    def update(self, utilisateur: UtilisateurEntity) -> UtilisateurEntity:
        # update() : une seule requête SQL ciblée (plus rapide que save())
        UtilisateurModel.objects.filter(id=utilisateur.id).update(
            nom=utilisateur.nom,
            prenom=utilisateur.prenom,
            telephone=utilisateur.telephone or '',
            is_active=utilisateur.is_active,
            role=utilisateur.role.value,
        )
        return self.find_by_id(utilisateur.id)

    def count_by_role(self) -> dict:
        """Agrégation SQL directe — plus efficace qu'un comptage Python."""
        from django.db.models import Count
        counts = (
            UtilisateurModel.objects
            .values('role')
            .annotate(total=Count('id'))
        )
        return {item['role']: item['total'] for item in counts}


class DjangoClientRepository(AbstractClientRepository):

    def _to_entity(self, model: ClientModel) -> ClientEntity:
        user_repo = DjangoUtilisateurRepository()
        return ClientEntity(
            id=model.id,
            utilisateur=user_repo._to_entity(model.utilisateur),
            adresse=model.adresse,
        )

    def save(self, client: ClientEntity) -> ClientEntity:
        model = ClientModel.objects.create(
            utilisateur_id=client.utilisateur.id,
            adresse=client.adresse,
        )
        # reload avec select_related pour avoir l'utilisateur
        model = ClientModel.objects.select_related('utilisateur').get(id=model.id)
        return self._to_entity(model)

    def find_by_utilisateur_id(self, user_id: int) -> Optional[ClientEntity]:
        try:
            model = ClientModel.objects.select_related('utilisateur').get(
                utilisateur_id=user_id
            )
            return self._to_entity(model)
        except ClientModel.DoesNotExist:
            return None


class DjangoPersonnelRepository(AbstractPersonnelRepository):

    def _to_entity(self, model: PersonnelModel) -> PersonnelEntity:
        user_repo = DjangoUtilisateurRepository()
        return PersonnelEntity(
            id=model.id,
            utilisateur=user_repo._to_entity(model.utilisateur),
            poste=model.poste,
            entreprise_id=model.entreprise_id,
            domaine_id=model.domaine_id,
        )

    def save(self, personnel: PersonnelEntity) -> PersonnelEntity:
        model = PersonnelModel.objects.create(
            utilisateur_id=personnel.utilisateur.id,
            poste=personnel.poste,
        )
        model = PersonnelModel.objects.select_related('utilisateur').get(id=model.id)
        return self._to_entity(model)

    def find_by_utilisateur_id(self, user_id: int) -> Optional[PersonnelEntity]:
        try:
            model = PersonnelModel.objects.select_related('utilisateur').get(
                utilisateur_id=user_id
            )
            return self._to_entity(model)
        except PersonnelModel.DoesNotExist:
            return None

    def find_by_entreprise(self, entreprise_id: int) -> List[PersonnelEntity]:
        models = PersonnelModel.objects.select_related('utilisateur').filter(
            entreprise_id=entreprise_id
        )
        return [self._to_entity(m) for m in models]


class DjangoAdminRepository(AbstractAdminRepository):

    def _to_entity(self, model: AdministrateurModel) -> AdministrateurEntity:
        user_repo = DjangoUtilisateurRepository()
        return AdministrateurEntity(
            id=model.id,
            utilisateur=user_repo._to_entity(model.utilisateur),
            role_admin=model.role_admin,
        )

    def save(self, admin: AdministrateurEntity) -> AdministrateurEntity:
        model = AdministrateurModel.objects.create(
            utilisateur_id=admin.utilisateur.id,
            role_admin=admin.role_admin,
        )
        model = AdministrateurModel.objects.select_related('utilisateur').get(id=model.id)
        return self._to_entity(model)

    def find_by_utilisateur_id(self, user_id: int) -> Optional[AdministrateurEntity]:
        try:
            model = AdministrateurModel.objects.select_related('utilisateur').get(
                utilisateur_id=user_id
            )
            return self._to_entity(model)
        except AdministrateurModel.DoesNotExist:
            return None


# =============================================================
#   REPOSITORIES DOMAINE ET ENTREPRISE
# =============================================================

class DjangoDomaineRepository(AbstractDomaineRepository):

    def _to_entity(self, model: DomaineModel) -> DomaineEntity:
        return DomaineEntity(
            id=model.id,
            nom_domaine=model.nom_domaine,
            description=model.description,
        )

    def save(self, domaine: DomaineEntity) -> DomaineEntity:
        model = DomaineModel.objects.create(
            nom_domaine=domaine.nom_domaine,
            description=domaine.description,
        )
        return self._to_entity(model)

    def find_all(self) -> List[DomaineEntity]:
        return [self._to_entity(m) for m in DomaineModel.objects.all()]

    def find_by_id(self, did: int) -> Optional[DomaineEntity]:
        try:
            return self._to_entity(DomaineModel.objects.get(id=did))
        except DomaineModel.DoesNotExist:
            return None

    def delete(self, did: int) -> bool:
        count, _ = DomaineModel.objects.filter(id=did).delete()
        return count > 0


class DjangoEntrepriseRepository(AbstractEntrepriseRepository):

    def _to_entity(self, model: EntrepriseModel) -> EntrepriseEntity:
        return EntrepriseEntity(
            id=model.id,
            nom_entreprise=model.nom_entreprise,
            adresse=model.adresse,
            telephone=model.telephone,
            email=model.email,
            description=model.description,
            domaine_id=model.domaine_id,
            est_active=model.est_active,
        )

    def save(self, e: EntrepriseEntity) -> EntrepriseEntity:
        model = EntrepriseModel.objects.create(
            nom_entreprise=e.nom_entreprise,
            adresse=e.adresse,
            telephone=e.telephone,
            email=e.email,
            description=e.description,
            domaine_id=e.domaine_id,
        )
        return self._to_entity(model)

    def find_by_id(self, eid: int) -> Optional[EntrepriseEntity]:
        try:
            return self._to_entity(EntrepriseModel.objects.get(id=eid))
        except EntrepriseModel.DoesNotExist:
            return None

    def find_all(self, domaine_id: Optional[int] = None) -> List[EntrepriseEntity]:
        qs = EntrepriseModel.objects.all()
        if domaine_id:
            qs = qs.filter(domaine_id=domaine_id)
        return [self._to_entity(m) for m in qs]

    def update(self, e: EntrepriseEntity) -> EntrepriseEntity:
        EntrepriseModel.objects.filter(id=e.id).update(
            nom_entreprise=e.nom_entreprise,
            adresse=e.adresse,
            telephone=e.telephone,
            email=e.email,
            est_active=e.est_active,
        )
        return self.find_by_id(e.id)

    def delete(self, eid: int) -> bool:
        count, _ = EntrepriseModel.objects.filter(id=eid).delete()
        return count > 0


class DjangoAvisRepository(AbstractAvisRepository):

    def save(self, avis: AvisEntity) -> AvisEntity:
        model = AvisModel.objects.create(
            entreprise_id=avis.entreprise_id,
            client_id=avis.client_id,
            note=avis.note,
            commentaire=avis.commentaire,
        )
        return AvisEntity(
            id=model.id,
            entreprise_id=model.entreprise_id,
            client_id=model.client_id,
            note=model.note,
            commentaire=model.commentaire,
        )

    def find_by_entreprise(self, eid: int) -> List[AvisEntity]:
        return [
            AvisEntity(
                id=m.id, entreprise_id=m.entreprise_id,
                client_id=m.client_id, note=m.note,
                commentaire=m.commentaire,
            )
            for m in AvisModel.objects.filter(entreprise_id=eid)
        ]


# =============================================================
#   REPOSITORIES CRÉNEAU
# =============================================================

class DjangoPlageRepository(AbstractPlageRepository):

    def _to_entity(self, model: PlageCreneauModel) -> PlageCreneauEntity:
        return PlageCreneauEntity(
            id=model.id,
            entreprise_id=model.entreprise_id,
            date_plage=model.date_plage,
            heure_debut=model.heure_debut,
            heure_fin=model.heure_fin,
            libelle=model.libelle,
        )

    def save(self, plage: PlageCreneauEntity) -> PlageCreneauEntity:
        model = PlageCreneauModel.objects.create(
            entreprise_id=plage.entreprise_id,
            date_plage=plage.date_plage,
            heure_debut=plage.heure_debut,
            heure_fin=plage.heure_fin,
            libelle=plage.libelle,
        )
        return self._to_entity(model)

    def find_by_id(self, pid: int) -> Optional[PlageCreneauEntity]:
        try:
            return self._to_entity(PlageCreneauModel.objects.get(id=pid))
        except PlageCreneauModel.DoesNotExist:
            return None

    def find_by_entreprise(self, eid: int) -> List[PlageCreneauEntity]:
        return [
            self._to_entity(m)
            for m in PlageCreneauModel.objects.filter(entreprise_id=eid)
        ]


class DjangoCreneauRepository(AbstractCreneauRepository):

    def _to_entity(self, model: CreneauModel) -> CreneauEntity:
        return CreneauEntity(
            id=model.id,
            personnel_id=model.personnel_id,
            heure_debut=model.heure_debut,
            heure_fin=model.heure_fin,
            # "disponible" (string) → StatutCreneau.DISPONIBLE (Enum)
            statut=StatutCreneau(model.statut),
            plage_id=model.plage_id,
        )

    def save(self, creneau: CreneauEntity) -> CreneauEntity:
        model = CreneauModel.objects.create(
            personnel_id=creneau.personnel_id,
            heure_debut=creneau.heure_debut,
            heure_fin=creneau.heure_fin,
            statut=creneau.statut.value,
            plage_id=creneau.plage_id,
        )
        return self._to_entity(model)

    def find_by_id(self, cid: int) -> Optional[CreneauEntity]:
        try:
            return self._to_entity(CreneauModel.objects.get(id=cid))
        except CreneauModel.DoesNotExist:
            return None

    def find_disponibles(self, entreprise_id: Optional[int] = None) -> List[CreneauEntity]:
        qs = CreneauModel.objects.filter(statut='disponible')
        if entreprise_id:
            # filtre via la relation personnel → entreprise
            qs = qs.filter(personnel__entreprise_id=entreprise_id)
        return [self._to_entity(m) for m in qs]

    def update(self, creneau: CreneauEntity) -> CreneauEntity:
        CreneauModel.objects.filter(id=creneau.id).update(
            statut=creneau.statut.value
        )
        return self.find_by_id(creneau.id)

    def delete(self, cid: int) -> bool:
        count, _ = CreneauModel.objects.filter(id=cid).delete()
        return count > 0


# =============================================================
#   REPOSITORIES RENDEZ-VOUS
# =============================================================

class DjangoRendezVousRepository(AbstractRendezVousRepository):

    def _to_entity(self, model: RendezVousModel) -> RendezVousEntity:
        return RendezVousEntity(
            id=model.id,
            client_id=model.client_id,
            creneau_id=model.creneau_id,
            confirmation=model.confirmation,
            statut=StatutRendezVous(model.statut),
            description=model.description,
            traite_par_id=model.traite_par_id,
            motif_refus=model.motif_refus,
            date_creation=model.date_creation,
        )

    def save(self, rdv: RendezVousEntity) -> RendezVousEntity:
        model = RendezVousModel.objects.create(
            client_id=rdv.client_id,
            creneau_id=rdv.creneau_id,
            description=rdv.description,
            statut=rdv.statut.value,
        )
        return self._to_entity(model)

    def find_by_id(self, rdv_id: int) -> Optional[RendezVousEntity]:
        try:
            return self._to_entity(RendezVousModel.objects.get(id=rdv_id))
        except RendezVousModel.DoesNotExist:
            return None

    def find_by_client(self, client_id: int) -> List[RendezVousEntity]:
        return [
            self._to_entity(m)
            for m in RendezVousModel.objects.filter(client_id=client_id)
        ]

    def find_all(self, statut: Optional[str] = None) -> List[RendezVousEntity]:
        # select_related évite les requêtes N+1
        qs = RendezVousModel.objects.select_related('client', 'creneau').all()
        if statut:
            qs = qs.filter(statut=statut)
        return [self._to_entity(m) for m in qs]

    def update(self, rdv: RendezVousEntity) -> RendezVousEntity:
        RendezVousModel.objects.filter(id=rdv.id).update(
            confirmation=rdv.confirmation,
            statut=rdv.statut.value,
            traite_par_id=rdv.traite_par_id,
            motif_refus=rdv.motif_refus,
        )
        return self.find_by_id(rdv.id)

    def compter_par_statut(self) -> dict:
        from django.db.models import Count
        counts = (
            RendezVousModel.objects
            .values('statut')
            .annotate(total=Count('id'))
        )
        result = {item['statut']: item['total'] for item in counts}
        result['total'] = sum(result.values())
        return result


class DjangoHistoriqueRepository(AbstractHistoriqueRepository):

    def save(self, h: HistoriqueStatutEntity) -> HistoriqueStatutEntity:
        model = HistoriqueStatutModel.objects.create(
            rendezvous_id=h.rendezvous_id,
            ancien_statut=h.ancien_statut,
            nouveau_statut=h.nouveau_statut,
            change_par_id=h.change_par_id,
            commentaire=h.commentaire,
        )
        return HistoriqueStatutEntity(
            id=model.id,
            rendezvous_id=model.rendezvous_id,
            ancien_statut=model.ancien_statut,
            nouveau_statut=model.nouveau_statut,
            change_par_id=model.change_par_id,
            commentaire=model.commentaire,
        )

    def find_by_rendezvous(self, rdv_id: int) -> List[HistoriqueStatutEntity]:
        return [
            HistoriqueStatutEntity(
                id=m.id, rendezvous_id=m.rendezvous_id,
                ancien_statut=m.ancien_statut,
                nouveau_statut=m.nouveau_statut,
                change_par_id=m.change_par_id,
                commentaire=m.commentaire,
            )
            for m in HistoriqueStatutModel.objects.filter(rendezvous_id=rdv_id)
        ]


# =============================================================
#   REPOSITORIES PAIEMENT ET NOTIFICATION
# =============================================================

class DjangoPaiementRepository(AbstractPaiementRepository):

    def _to_entity(self, model: PaiementModel) -> PaiementEntity:
        return PaiementEntity(
            id=model.id,
            rendezvous_id=model.rendezvous_id,
            montant=model.montant,
            mode_paiement=ModePaiement(model.mode_paiement),
            statut=StatutPaiement(model.statut),
            reference_transaction=model.reference_transaction,
            date_paiement=model.date_paiement,
        )

    def save(self, paiement: PaiementEntity) -> PaiementEntity:
        model = PaiementModel.objects.create(
            rendezvous_id=paiement.rendezvous_id,
            montant=paiement.montant,
            mode_paiement=paiement.mode_paiement.value,
            statut=paiement.statut.value,
        )
        return self._to_entity(model)

    def find_by_id(self, pid: int) -> Optional[PaiementEntity]:
        try:
            return self._to_entity(PaiementModel.objects.get(id=pid))
        except PaiementModel.DoesNotExist:
            return None

    def find_by_rendezvous(self, rdv_id: int) -> Optional[PaiementEntity]:
        try:
            return self._to_entity(PaiementModel.objects.get(rendezvous_id=rdv_id))
        except PaiementModel.DoesNotExist:
            return None

    def find_by_client(self, client_id: int) -> List[PaiementEntity]:
        return [
            self._to_entity(m)
            for m in PaiementModel.objects.filter(rendezvous__client_id=client_id)
        ]

    def update(self, paiement: PaiementEntity) -> PaiementEntity:
        PaiementModel.objects.filter(id=paiement.id).update(
            statut=paiement.statut.value,
            reference_transaction=paiement.reference_transaction,
        )
        return self.find_by_id(paiement.id)


class DjangoNotificationRepository(AbstractNotificationRepository):

    def _to_entity(self, model: NotificationModel) -> NotificationEntity:
        return NotificationEntity(
            id=model.id,
            destinataire_id=model.destinataire_id,
            titre=model.titre,
            message=model.message,
            type_notification=model.type_notification,
            est_lue=model.est_lue,
        )

    def save(self, notif: NotificationEntity) -> NotificationEntity:
        model = NotificationModel.objects.create(
            destinataire_id=notif.destinataire_id,
            titre=notif.titre,
            message=notif.message,
            type_notification=notif.type_notification,
        )
        return self._to_entity(model)

    def save_many(self, notifs: List[NotificationEntity]) -> None:
        """Insère N notifications en une seule requête SQL (bulk_create)."""
        NotificationModel.objects.bulk_create([
            NotificationModel(
                destinataire_id=n.destinataire_id,
                titre=n.titre,
                message=n.message,
                type_notification=n.type_notification,
            )
            for n in notifs
        ])

    def find_by_destinataire(
        self, user_id: int, non_lues_seulement: bool = False
    ) -> List[NotificationEntity]:
        qs = NotificationModel.objects.filter(destinataire_id=user_id)
        if non_lues_seulement:
            qs = qs.filter(est_lue=False)
        return [self._to_entity(m) for m in qs]

    def marquer_lue(self, notif_id: int) -> NotificationEntity:
        NotificationModel.objects.filter(id=notif_id).update(
            est_lue=True,
            date_lecture=timezone.now()
        )
        return self._to_entity(NotificationModel.objects.get(id=notif_id))

    def marquer_toutes_lues(self, user_id: int) -> int:
        """Retourne le nombre de notifications marquées."""
        count = NotificationModel.objects.filter(
            destinataire_id=user_id,
            est_lue=False
        ).update(est_lue=True, date_lecture=timezone.now())
        return count