"""
rendezvous/tasks.py — Version Django-Q
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def envoyer_rappels_rdv():
    """
    Vérifie les RDV confirmés et envoie des rappels 24h et 1h avant.
    Appelée par Django-Q toutes les 15 minutes.
    """
    from rendezvous.infrastructure.django_models.models import (
        RendezVousModel, RappelModel
    )

    maintenant   = timezone.now()
    dans_24h_min = maintenant + timedelta(hours=23, minutes=45)
    dans_24h_max = maintenant + timedelta(hours=24, minutes=15)
    dans_1h_min  = maintenant + timedelta(minutes=45)
    dans_1h_max  = maintenant + timedelta(hours=1, minutes=15)

    rdvs = RendezVousModel.objects.filter(
        statut='confirme'
    ).select_related(
        'client__utilisateur',
        'creneau__personnel__utilisateur',
        'creneau__plage',
    )

    envoyes_24h = envoyes_1h = 0

    for rdv in rdvs:
        try:
            date_rdv = _get_datetime_rdv(rdv)
            if not date_rdv:
                continue

            client_email = rdv.client.utilisateur.email
            client_nom   = f"{rdv.client.utilisateur.prenom} {rdv.client.utilisateur.nom}"

            if dans_24h_min <= date_rdv <= dans_24h_max:
                if not RappelModel.objects.filter(rendezvous=rdv, type_rappel='24h').exists():
                    _envoyer_email_rappel(rdv, client_email, client_nom, '24h', date_rdv)
                    envoyes_24h += 1

            if dans_1h_min <= date_rdv <= dans_1h_max:
                if not RappelModel.objects.filter(rendezvous=rdv, type_rappel='1h').exists():
                    _envoyer_email_rappel(rdv, client_email, client_nom, '1h', date_rdv)
                    envoyes_1h += 1

        except Exception as e:
            logger.error(f"Erreur rappel RDV #{rdv.id}: {e}", exc_info=True)

    logger.info(f"Rappels — 24h: {envoyes_24h} | 1h: {envoyes_1h}")
    return {'24h': envoyes_24h, '1h': envoyes_1h}


def _envoyer_email_rappel(rdv, client_email, client_nom, type_rappel, date_rdv):
    """Envoie l'email et enregistre le rappel en BD."""
    from rendezvous.infrastructure.django_models.models import (
        RappelModel, NotificationModel
    )

    date_fr  = date_rdv.strftime('%A %d %B %Y')
    heure_fr = date_rdv.strftime('%H:%M')
    delai    = "demain" if type_rappel == '24h' else "dans 1 heure"

    sujet = (
        f"⏰ Rappel — Votre RDV demain à {heure_fr}"
        if type_rappel == '24h' else
        f"⏰ Rappel — Votre RDV dans 1 heure ({heure_fr})"
    )

    personnel_nom = (
        f"{rdv.creneau.personnel.utilisateur.prenom} "
        f"{rdv.creneau.personnel.utilisateur.nom}"
    )

    corps_html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; background: #f8fafc; margin: 0; padding: 20px; }}
    .container {{ max-width: 580px; margin: 0 auto; background: #fff; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; }}
    .header {{ background: linear-gradient(135deg, #10b981, #059669); padding: 28px 32px; text-align: center; }}
    .header h1 {{ color: #fff; margin: 0; font-size: 20px; font-weight: 700; }}
    .header p  {{ color: rgba(255,255,255,.85); margin: 6px 0 0; font-size: 13px; }}
    .body {{ padding: 28px 32px; }}
    .rdv-card {{ background: #f0fdf4; border: 1.5px solid #a7f3d0; border-radius: 12px; padding: 18px 22px; margin: 18px 0; }}
    .rdv-card h3 {{ color: #065f46; margin: 0 0 12px; font-size: 14px; font-weight: 700; }}
    .row {{ display: flex; margin: 6px 0; font-size: 13px; }}
    .lbl {{ color: #6b7280; min-width: 90px; }}
    .val {{ font-weight: 600; color: #111827; }}
    .badge {{ display: inline-block; padding: 5px 14px; border-radius: 50px; font-size: 12px; font-weight: 700; color: #fff; margin-top: 10px; background: {'#f59e0b' if type_rappel == '1h' else '#10b981'}; }}
    .tip {{ background: #fffbeb; border-left: 3px solid #f59e0b; padding: 10px 14px; border-radius: 0 8px 8px 0; font-size: 12px; color: #92400e; margin: 16px 0; }}
    .btn {{ display: block; text-align: center; background: #10b981; color: #fff; padding: 13px; border-radius: 10px; text-decoration: none; font-weight: 700; font-size: 14px; margin: 20px 0 0; }}
    .footer {{ background: #f8fafc; padding: 16px 32px; text-align: center; font-size: 11px; color: #9ca3af; border-top: 1px solid #e5e7eb; }}
  </style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>⏰ Rappel de rendez-vous</h1>
    <p>Votre RDV est {delai}</p>
  </div>
  <div class="body">
    <p style="font-size:15px;color:#1a2332;">Bonjour <strong>{client_nom}</strong>,</p>
    <p style="font-size:13px;color:#4b5563;line-height:1.6;">
      Vous avez un rendez-vous confirmé <strong style="color:#10b981">{delai}</strong>.
    </p>
    <div class="rdv-card">
      <h3>📋 RDV #{rdv.id}</h3>
      <div class="row"><span class="lbl"> Date</span><span class="val">{date_fr}</span></div>
      <div class="row"><span class="lbl">🕐 Heure</span><span class="val">{heure_fr}</span></div>
      <div class="row"><span class="lbl">👤 Personnel</span><span class="val">{personnel_nom}</span></div>
      {f'<div class="row"><span class="lbl">📝 Objet</span><span class="val">{rdv.description}</span></div>' if rdv.description else ''}
      <span class="badge">{'🔴 Dans 1 heure !' if type_rappel == '1h' else '🟡 Demain'}</span>
    </div>
    <div class="tip">
      💡 En cas d'empêchement, connectez-vous pour annuler votre RDV à temps.
    </div>
    <a href="http://localhost:3000/rendezvous" class="btn">Voir mon rendez-vous →</a>
  </div>
  <div class="footer">
    © {date_rdv.year} RendezVous Pro — Email automatique, ne pas répondre.
  </div>
</div>
</body>
</html>"""

    corps_texte = (
        f"Bonjour {client_nom},\n\n"
        f"Rappel : vous avez un RDV {delai}.\n\n"
        f"RDV #{rdv.id} | {date_fr} à {heure_fr} | Personnel : {personnel_nom}\n\n"
        f"RendezVous Pro"
    )

    send_mail(
        subject=sujet,
        message=corps_texte,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@rdvpro.cm'),
        recipient_list=[client_email],
        html_message=corps_html,
        fail_silently=False,
    )

    RappelModel.objects.create(
        rendezvous=rdv,
        type_rappel=type_rappel,
        email_envoye=client_email,
        statut='envoye',
    )

    NotificationModel.objects.create(
        destinataire=rdv.client.utilisateur,
        titre=f"⏰ Rappel RDV #{rdv.id} — {delai.capitalize()}",
        message=f"Votre rendez-vous est prévu {delai} à {heure_fr}.",
        type_notification='rendezvous',
        est_lue=False,
    )

    logger.info(f"Rappel {type_rappel} envoyé → {client_email} (RDV #{rdv.id})")


def _get_datetime_rdv(rdv):
    """Calcule la datetime du RDV depuis le créneau et la plage."""
    from datetime import datetime
    try:
        creneau = rdv.creneau
        plage   = getattr(creneau, 'plage', None)

        if plage and plage.date_plage:
            dt = datetime.combine(plage.date_plage, creneau.heure_debut)
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt

        dt = rdv.date_creation.replace(
            hour=creneau.heure_debut.hour,
            minute=creneau.heure_debut.minute,
            second=0, microsecond=0,
        )
        return dt
    except Exception as e:
        logger.warning(f"Date RDV #{rdv.id} incalculable: {e}")
        return None


def tester_rappel_manuel(rdv_id, type_rappel='24h'):
    """Test direct sans worker — exécute immédiatement dans le process courant."""
    from rendezvous.infrastructure.django_models.models import RendezVousModel
    from django.utils import timezone

    rdv = RendezVousModel.objects.select_related(
        'client__utilisateur',
        'creneau__personnel__utilisateur',
        'creneau__plage',
    ).get(id=rdv_id)

    client_email = rdv.client.utilisateur.email
    client_nom   = f"{rdv.client.utilisateur.prenom} {rdv.client.utilisateur.nom}"
    date_rdv     = timezone.now() + timedelta(hours=2)

    _envoyer_email_rappel(rdv, client_email, client_nom, type_rappel, date_rdv)
    print(f"✅ Rappel {type_rappel} envoyé pour RDV #{rdv_id} → {client_email}")