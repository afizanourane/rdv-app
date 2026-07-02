"""
=============================================================
  rendezvous/presentation/validators.py

  Validateurs de sécurité — nettoient les données entrantes
=============================================================
  Principe : ne jamais faire confiance aux données utilisateur.
  Tout ce qui entre dans l'API doit être validé et nettoyé.
=============================================================
"""
import re
import os
import logging

logger = logging.getLogger('rendezvous.securite')


class ValidateurSecurite:
    """
    Classe utilitaire avec des méthodes de validation sécurisées.
    Utilisée dans les serializers et les vues.
    """

    # Expression régulière pour un email valide
    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    )

    # Caractères dangereux à détecter (injection SQL, XSS)
    PATTERNS_DANGEREUX = [
        r'<script',          # XSS basique
        r'javascript:',      # XSS via javascript:
        r'on\w+=',           # Événements HTML (onclick=, onload=...)
        r'--',               # Commentaire SQL
        r';\s*drop\s+table', # SQL injection DROP TABLE
        r';\s*delete\s+from',# SQL injection DELETE
        r'union\s+select',   # SQL injection UNION SELECT
        r'exec\s*\(',        # Exécution de code SQL
        r'xp_cmdshell',      # Commandes système SQL Server
    ]

    @classmethod
    def valider_email(cls, email: str) -> str:
        """
        Valide et nettoie un email.
        Lève ValueError si l'email est invalide.
        """
        if not email:
            raise ValueError("L'email est obligatoire.")

        email = email.strip().lower()

        if len(email) > 254:
            raise ValueError("L'email est trop long (max 254 caractères).")

        if not cls.EMAIL_REGEX.match(email):
            raise ValueError("L'adresse email n'est pas valide.")

        return email

    @classmethod
    def valider_mot_de_passe(cls, password: str) -> None:
        """
        Vérifie que le mot de passe respecte les règles de sécurité.
        Lève ValueError si non conforme.
        """
        if len(password) < 8:
            raise ValueError(
                "Le mot de passe doit contenir au moins 8 caractères."
            )

        if len(password) > 128:
            raise ValueError(
                "Le mot de passe est trop long (max 128 caractères)."
            )

        # Vérifier la présence d'au moins une majuscule
        if not any(c.isupper() for c in password):
            raise ValueError(
                "Le mot de passe doit contenir au moins une majuscule."
            )

        # Vérifier la présence d'au moins un chiffre
        if not any(c.isdigit() for c in password):
            raise ValueError(
                "Le mot de passe doit contenir au moins un chiffre."
            )

        # Vérifier la présence d'au moins un caractère spécial
        caracteres_speciaux = set('!@#$%^&*()_+-=[]{}|;:,.<>?')
        if not any(c in caracteres_speciaux for c in password):
            raise ValueError(
                "Le mot de passe doit contenir au moins un caractère spécial "
                "(!@#$%^&*...)."
            )

    @classmethod
    def nettoyer_texte(cls, texte: str, max_longueur: int = 500) -> str:
        """
        Nettoie un texte en supprimant les caractères dangereux.
        Utilisé pour les champs libres (description, commentaire...).
        """
        if not texte:
            return ''

        # Limiter la longueur
        texte = texte[:max_longueur]

        # Supprimer les caractères de contrôle dangereux
        texte = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texte)

        # Détecter les patterns dangereux et logger
        texte_lower = texte.lower()
        for pattern in cls.PATTERNS_DANGEREUX:
            if re.search(pattern, texte_lower):
                logger.warning(
                    f"Pattern dangereux détecté dans un champ texte : "
                    f"pattern={pattern}, texte={texte[:50]}..."
                )
                raise ValueError(
                    "Le texte contient des caractères non autorisés."
                )

        return texte.strip()

    @classmethod
    def valider_entier_positif(cls, valeur, nom_champ: str) -> int:
        """
        Valide qu'une valeur est un entier positif.
        Utilisé pour les IDs.
        """
        try:
            valeur = int(valeur)
        except (TypeError, ValueError):
            raise ValueError(f"'{nom_champ}' doit être un nombre entier.")

        if valeur <= 0:
            raise ValueError(f"'{nom_champ}' doit être un nombre positif.")

        return valeur

    @classmethod
    def valider_montant(cls, montant) -> float:
        """
        Valide un montant financier.
        """
        try:
            montant = float(montant)
        except (TypeError, ValueError):
            raise ValueError("Le montant doit être un nombre valide.")

        if montant <= 0:
            raise ValueError("Le montant doit être supérieur à 0.")

        if montant > 10_000_000:
            raise ValueError("Le montant dépasse la limite autorisée.")

        return montant

    @classmethod
    def valider_fichier(cls, fichier) -> None:
        """
        Valide un fichier uploadé.
        Vérifie l'extension et la taille.
        """
        from django.conf import settings

        # Vérifier la taille
        if fichier.size > settings.MAX_UPLOAD_SIZE:
            taille_max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            raise ValueError(
                f"Le fichier est trop volumineux. "
                f"Taille maximale : {taille_max_mb} MB."
            )

        # Vérifier l'extension
        _, extension = os.path.splitext(fichier.name)
        extension = extension.lower()

        if extension not in settings.ALLOWED_UPLOAD_EXTENSIONS:
            raise ValueError(
                f"Extension de fichier non autorisée : {extension}. "
                f"Extensions acceptées : "
                f"{', '.join(settings.ALLOWED_UPLOAD_EXTENSIONS)}"
            )

        # Vérifier que le nom de fichier ne contient pas de chemin
        if '..' in fichier.name or '/' in fichier.name or '\\' in fichier.name:
            raise ValueError("Le nom de fichier est invalide.")

    @classmethod
    def valider_note(cls, note) -> int:
        """Valide une note entre 1 et 5."""
        try:
            note = int(note)
        except (TypeError, ValueError):
            raise ValueError("La note doit être un nombre entier.")

        if not 1 <= note <= 5:
            raise ValueError("La note doit être comprise entre 1 et 5.")

        return note

    @classmethod
    def valider_telephone(cls, telephone: str) -> str:
        """Valide un numéro de téléphone."""
        if not telephone:
            return ''

        # Supprimer les espaces et tirets
        telephone = re.sub(r'[\s\-\.\(\)]', '', telephone)

        # Vérifier le format (chiffres uniquement, 8-15 caractères)
        if not re.match(r'^\+?[0-9]{8,15}$', telephone):
            raise ValueError(
                "Le numéro de téléphone est invalide. "
                "Format attendu : +237690000001"
            )

        return telephone