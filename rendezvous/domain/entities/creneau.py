"""
=============================================================
  rendezvous/domain/entities/creneau.py

  COUCHE DOMAIN — Entités Créneau et Plage horaire
=============================================================
"""
from dataclasses import dataclass
from datetime import date, time
from typing import Optional
from enum import Enum


class StatutCreneau(Enum):
    DISPONIBLE = "disponible"
    RESERVE    = "reserve"
    ANNULE     = "annule"
    TERMINE    = "termine"


@dataclass
class PlageCreneauEntity:
    """
    Plage horaire générale d'une entreprise.
    Ex : Lundi 8h-17h pour l'entreprise X.
    """
    entreprise_id: int
    date_plage: date
    heure_debut: time
    heure_fin: time
    libelle: str = ""
    id: Optional[int] = None

    def est_valide(self) -> bool:
        """Règle : l'heure de début doit précéder l'heure de fin."""
        return self.heure_debut < self.heure_fin


@dataclass
class CreneauEntity:
    """Créneau individuel disponible pour un rendez-vous."""
    personnel_id: int
    heure_debut: time
    heure_fin: time
    statut: StatutCreneau = StatutCreneau.DISPONIBLE
    plage_id: Optional[int] = None
    id: Optional[int] = None

    def est_disponible(self) -> bool:
        """Règle : on ne réserve que les créneaux disponibles."""
        return self.statut == StatutCreneau.DISPONIBLE

    def reserver(self):
        """Règle : réserver le créneau."""
        if not self.est_disponible():
            raise ValueError("Ce créneau n'est plus disponible.")
        self.statut = StatutCreneau.RESERVE

    def liberer(self):
        """Règle : libérer le créneau (ex: annulation)."""
        self.statut = StatutCreneau.DISPONIBLE