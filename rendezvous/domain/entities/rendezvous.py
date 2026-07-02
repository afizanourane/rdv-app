"""
=============================================================
  rendezvous/domain/entities/rendezvous.py

  COUCHE DOMAIN — Entité RendezVous
=============================================================
  Entité centrale de l'application.
  Contient toutes les règles métier liées aux rendez-vous.
=============================================================
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class StatutRendezVous(Enum):
    """Cycle de vie complet d'un rendez-vous."""
    EN_ATTENTE = "en_attente"  # Soumis, pas encore traité
    CONFIRME   = "confirme"    # Validé par l'admin
    REFUSE     = "refuse"      # Refusé par l'admin
    ANNULE     = "annule"      # Annulé par le client
    TERMINE    = "termine"     # Prestation effectuée


@dataclass
class RendezVousEntity:
    """
    Un rendez-vous = un client réserve un créneau
    auprès d'un personnel, validé par un admin.
    """
    client_id: int
    creneau_id: int
    description: str = ""
    confirmation: bool = False
    statut: StatutRendezVous = StatutRendezVous.EN_ATTENTE
    id: Optional[int] = None
    traite_par_id: Optional[int] = None
    motif_refus: str = ""
    date_creation: Optional[datetime] = None

    # --- Règles métier -----------------------------------

    def peut_etre_confirme(self) -> bool:
        """On ne confirme que les RDV en attente."""
        return self.statut == StatutRendezVous.EN_ATTENTE

    def peut_etre_annule(self) -> bool:
        """Le client annule seulement si le RDV est en attente."""
        return self.statut == StatutRendezVous.EN_ATTENTE

    def confirmer(self, admin_id: int):
        """Confirmer le rendez-vous — déclenché par un admin."""
        if not self.peut_etre_confirme():
            raise ValueError(
                f"Impossible de confirmer un RDV au statut '{self.statut.value}'."
            )
        self.confirmation = True
        self.statut = StatutRendezVous.CONFIRME
        self.traite_par_id = admin_id

    def refuser(self, admin_id: int, motif: str):
        """Refuser le rendez-vous — motif obligatoire."""
        if not motif.strip():
            raise ValueError("Le motif de refus est obligatoire.")
        if self.statut != StatutRendezVous.EN_ATTENTE:
            raise ValueError(
                f"Impossible de refuser un RDV au statut '{self.statut.value}'."
            )
        self.confirmation = False
        self.statut = StatutRendezVous.REFUSE
        self.traite_par_id = admin_id
        self.motif_refus = motif

    def annuler(self):
        """Annuler le rendez-vous — déclenché par le client."""
        if not self.peut_etre_annule():
            raise ValueError("Ce rendez-vous ne peut plus être annulé.")
        self.statut = StatutRendezVous.ANNULE


@dataclass
class HistoriqueStatutEntity:
    """
    Trace chaque changement de statut d'un rendez-vous.
    Permet un audit complet (qui a fait quoi et quand).
    """
    rendezvous_id: int
    ancien_statut: str
    nouveau_statut: str
    change_par_id: int
    commentaire: str = ""
    id: Optional[int] = None