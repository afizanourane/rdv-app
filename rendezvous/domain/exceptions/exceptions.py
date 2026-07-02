"""
=============================================================
  rendezvous/domain/exceptions/exceptions.py

  COUCHE DOMAIN — Exceptions métier
=============================================================
  Des erreurs qui parlent le langage du métier.
  Au lieu d'une ValueError générique, on lève une erreur
  explicite comme "CreneauNonDisponible".
=============================================================
"""


# --- Utilisateur -----------------------------------------
class UtilisateurNonTrouve(Exception):
    def __init__(self, identifiant):
        super().__init__(f"Aucun utilisateur trouvé : {identifiant}")


class EmailDejaUtilise(Exception):
    def __init__(self, email):
        super().__init__(f"L'email '{email}' est déjà utilisé.")


class MotDePasseInvalide(Exception):
    def __init__(self, raison="Mot de passe invalide."):
        super().__init__(raison)


class PermissionRefusee(Exception):
    def __init__(self, action=""):
        super().__init__(f"Permission refusée : {action}")


# --- Entreprise ------------------------------------------
class EntrepriseNonTrouvee(Exception):
    def __init__(self, eid):
        super().__init__(f"Entreprise introuvable : ID {eid}")


class DomaineNonTrouve(Exception):
    def __init__(self, did):
        super().__init__(f"Domaine introuvable : ID {did}")


# --- Créneau ---------------------------------------------
class CreneauNonDisponible(Exception):
    def __init__(self, cid):
        super().__init__(f"Le créneau {cid} n'est plus disponible.")


class CreneauNonTrouve(Exception):
    def __init__(self, cid):
        super().__init__(f"Créneau introuvable : ID {cid}")


# --- Rendez-vous -----------------------------------------
class RendezVousNonTrouve(Exception):
    def __init__(self, rid):
        super().__init__(f"Rendez-vous introuvable : ID {rid}")


class RendezVousDejaExistant(Exception):
    def __init__(self):
        super().__init__("Vous avez déjà un RDV en attente sur ce créneau.")


class StatutInvalide(Exception):
    def __init__(self, statut, action):
        super().__init__(f"Action '{action}' impossible sur un RDV '{statut}'.")


# --- Paiement --------------------------------------------
class PaiementNonTrouve(Exception):
    def __init__(self, pid):
        super().__init__(f"Paiement introuvable : ID {pid}")


class RendezVousNonConfirme(Exception):
    def __init__(self):
        super().__init__("Le RDV doit être confirmé avant le paiement.")


class PaiementDejaExistant(Exception):
    def __init__(self):
        super().__init__("Un paiement existe déjà pour ce rendez-vous.")


class RemboursementImpossible(Exception):
    def __init__(self):
        super().__init__("On ne rembourse que les paiements confirmés.")