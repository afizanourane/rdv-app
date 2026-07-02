"""
=============================================================
  rendezvous/domain/entities/paiement.py

  COUCHE DOMAIN — Entité Paiement
=============================================================
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum


class StatutPaiement(Enum):
    EN_ATTENTE = "en_attente"
    PAYE       = "paye"
    REMBOURSE  = "rembourse"
    ECHOUE     = "echoue"


class ModePaiement(Enum):
    CARTE        = "carte"
    MOBILE_MONEY = "mobile_money"
    VIREMENT     = "virement"
    ESPECES      = "especes"


@dataclass
class PaiementEntity:
    """Paiement lié à un rendez-vous confirmé."""
    rendezvous_id: int
    montant: Decimal
    mode_paiement: ModePaiement
    statut: StatutPaiement = StatutPaiement.EN_ATTENTE
    reference_transaction: str = ""
    id: Optional[int] = None
    date_paiement: Optional[datetime] = None

    def peut_etre_rembourse(self) -> bool:
        """Règle : on ne rembourse que ce qui a été payé."""
        return self.statut == StatutPaiement.PAYE

    def marquer_paye(self, reference: str):
        """Règle : confirmer le paiement avec une référence."""
        self.statut = StatutPaiement.PAYE
        self.reference_transaction = reference


@dataclass
class NotificationEntity:
    """Alerte envoyée à un utilisateur."""
    destinataire_id: int
    titre: str
    message: str
    type_notification: str = "systeme"
    est_lue: bool = False
    id: Optional[int] = None