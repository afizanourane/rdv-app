"""
=============================================================
  rendezvous/domain/entities/utilisateur.py

  COUCHE DOMAIN — Entité Utilisateur
=============================================================
  RÈGLE : ce fichier ne contient AUCUN import Django.
  C'est du Python pur qui décrit ce qu'est un utilisateur
  dans notre métier.

  Si demain on change de framework, ce fichier ne change pas.
=============================================================
"""
from dataclasses import dataclass   # génère __init__ automatiquement
from datetime import datetime
from typing import Optional
from enum import Enum               # liste de valeurs fixes


class Role(Enum):
    """Les 3 rôles possibles dans l'application."""
    CLIENT    = "client"
    ADMIN     = "admin"
    PERSONNEL = "personnel"


@dataclass
class UtilisateurEntity:
    """
    Représentation pure d'un utilisateur.
    Pas de lien avec Django ou la base de données.
    """
    nom: str
    prenom: str
    email: str
    role: Role

    # Champs optionnels
    id: Optional[int] = None
    telephone: Optional[str] = None
    is_active: bool = True
    date_joined: Optional[datetime] = None

    # --- Règles métier -----------------------------------

    def nom_complet(self) -> str:
        """Retourne le prénom + nom."""
        return f"{self.prenom} {self.nom}"

    def est_admin(self) -> bool:
        return self.role == Role.ADMIN

    def est_client(self) -> bool:
        return self.role == Role.CLIENT

    def est_personnel(self) -> bool:
        return self.role == Role.PERSONNEL

    def peut_prendre_rendezvous(self) -> bool:
        """Seuls les clients actifs peuvent prendre des RDV."""
        return self.est_client() and self.is_active


@dataclass
class ClientEntity:
    """Profil spécifique du Client."""
    utilisateur: UtilisateurEntity
    adresse: str = ""
    id: Optional[int] = None


@dataclass
class PersonnelEntity:
    """Profil spécifique du Personnel."""
    utilisateur: UtilisateurEntity
    poste: str
    id: Optional[int] = None
    entreprise_id: Optional[int] = None
    domaine_id: Optional[int] = None


@dataclass
class AdministrateurEntity:
    """Profil spécifique de l'Administrateur."""
    utilisateur: UtilisateurEntity
    role_admin: str = "Administrateur général"
    id: Optional[int] = None