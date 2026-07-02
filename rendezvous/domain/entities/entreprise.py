"""
=============================================================
  rendezvous/domain/entities/entreprise.py

  COUCHE DOMAIN — Entités Entreprise et Domaine
=============================================================
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class DomaineEntity:
    """Domaine d'activité ex: informatique, nettoyage..."""
    nom_domaine: str
    description: str = ""
    id: Optional[int] = None


@dataclass
class EntrepriseEntity:
    """Entreprise prestataire de services."""
    nom_entreprise: str
    adresse: str
    telephone: str
    email: str
    domaine_id: int
    description: str = ""
    est_active: bool = True
    id: Optional[int] = None

    def est_valide(self) -> bool:
        """Règle : une entreprise valide a un nom, email et domaine."""
        return bool(self.nom_entreprise and self.email and self.domaine_id)


@dataclass
class AvisEntity:
    """Évaluation d'une entreprise par un client."""
    entreprise_id: int
    client_id: int
    note: int           # entre 1 et 5
    commentaire: str = ""
    id: Optional[int] = None

    def note_valide(self) -> bool:
        """Règle : la note est entre 1 et 5."""
        return 1 <= self.note <= 5