"""
rendezvous/application/pdf_service.py
Génération de reçus PDF pour les paiements confirmés
"""
import io
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class PdfService:
    """Génère des reçus PDF pour les paiements."""

    MODES = {
        'mobile_money': 'Mobile Money',
        'carte':        'Carte bancaire',
        'virement':     'Virement bancaire',
        'especes':      'Espèces',
    }

    STATUTS = {
        'en_attente': 'En attente',
        'paye':       'Payé',
        'rembourse':  'Remboursé',
        'echoue':     'Échoué',
    }

    def generer_recu_paiement(self, paiement) -> bytes:
        """
        Génère un reçu PDF pour un paiement.
        Retourne les bytes du PDF.
        """
        try:
            return self._generer_avec_reportlab(paiement)
        except Exception as e:
            logger.error(f"Erreur génération PDF paiement #{paiement.id}: {e}")
            raise

    def _generer_avec_reportlab(self, paiement) -> bytes:
        """Génère le PDF avec ReportLab."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer,
            Table, TableStyle, HRFlowable,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from datetime import datetime

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )

        # ── Couleurs ──────────────────────────────────────────
        VERT   = colors.HexColor('#10b981')
        SOMBRE = colors.HexColor('#1a2332')
        GRIS   = colors.HexColor('#64748b')
        GRIS_C = colors.HexColor('#f8fafc')
        BLANC  = colors.white

        # ── Styles ────────────────────────────────────────────
        styles  = getSampleStyleSheet()
        story   = []

        s_titre = ParagraphStyle(
            'titre', fontName='Helvetica-Bold',
            fontSize=24, textColor=BLANC,
            alignment=TA_CENTER, spaceAfter=4,
        )
        s_sous  = ParagraphStyle(
            'sous', fontName='Helvetica',
            fontSize=11, textColor=colors.HexColor('#a7f3d0'),
            alignment=TA_CENTER,
        )
        s_label = ParagraphStyle(
            'label', fontName='Helvetica',
            fontSize=9, textColor=GRIS,
        )
        s_valeur = ParagraphStyle(
            'valeur', fontName='Helvetica-Bold',
            fontSize=11, textColor=SOMBRE,
        )
        s_montant = ParagraphStyle(
            'montant', fontName='Helvetica-Bold',
            fontSize=28, textColor=VERT,
            alignment=TA_CENTER, spaceAfter=4,
        )
        s_centre = ParagraphStyle(
            'centre', fontName='Helvetica',
            fontSize=10, textColor=GRIS,
            alignment=TA_CENTER,
        )
        s_pied = ParagraphStyle(
            'pied', fontName='Helvetica',
            fontSize=8, textColor=GRIS,
            alignment=TA_CENTER,
        )

        # ── Données paiement ──────────────────────────────────
        try:
            client_nom   = f"{paiement.rendezvous.client.utilisateur.prenom} {paiement.rendezvous.client.utilisateur.nom}"
            client_email = paiement.rendezvous.client.utilisateur.email
            client_tel   = paiement.rendezvous.client.utilisateur.telephone or '—'
        except Exception:
            client_nom, client_email, client_tel = 'Client', '', '—'

        try:
            personnel_nom = (
                f"{paiement.rendezvous.creneau.personnel.utilisateur.prenom} "
                f"{paiement.rendezvous.creneau.personnel.utilisateur.nom}"
            )
            entreprise_nom = getattr(
                paiement.rendezvous.creneau.personnel.entreprise,
                'nom_entreprise', '—'
            )
        except Exception:
            personnel_nom, entreprise_nom = '—', '—'

        montant_fcfa = f"{int(paiement.montant):,} FCFA".replace(',', ' ')
        date_paie    = paiement.date_paiement.strftime('%d/%m/%Y à %H:%M') if paiement.date_paiement else '—'
        annee        = datetime.now().year

        # ══════════════════════════════════════════════════════
        # HEADER — Bandeau vert
        # ══════════════════════════════════════════════════════
        header_data = [[
            Paragraph("RendezVous Pro", s_titre),
        ]]
        header_table = Table(header_data, colWidths=[170*mm])
        header_table.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,-1), VERT),
            ('ROWPADDING',  (0,0), (-1,-1), 16),
            ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
            ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING',  (0,0), (-1,-1), 20),
            ('BOTTOMPADDING',(0,0),(-1,-1), 20),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 6*mm))

        # ── Sous-titre ────────────────────────────────────────
        story.append(Paragraph("REÇU DE PAIEMENT", ParagraphStyle(
            'rec', fontName='Helvetica-Bold', fontSize=14,
            textColor=SOMBRE, alignment=TA_CENTER, spaceAfter=2,
        )))
        story.append(Paragraph(
            f"N° REF-{str(paiement.id).zfill(6)}",
            ParagraphStyle('ref', fontName='Helvetica', fontSize=10,
                           textColor=GRIS, alignment=TA_CENTER),
        ))
        story.append(Spacer(1, 6*mm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        story.append(Spacer(1, 6*mm))

        # ── Montant central ───────────────────────────────────
        story.append(Paragraph(montant_fcfa, s_montant))
        story.append(Paragraph(
            f"Statut : {self.STATUTS.get(paiement.statut, paiement.statut)}",
            s_centre,
        ))
        story.append(Spacer(1, 8*mm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        story.append(Spacer(1, 6*mm))

        # ── Tableau infos ─────────────────────────────────────
        def ligne(label, valeur):
            return [
                Paragraph(label, s_label),
                Paragraph(str(valeur), s_valeur),
            ]

        data_infos = [
            ligne("Référence transaction",
                  paiement.reference_transaction or '—'),
            ligne("Date de paiement", date_paie),
            ligne("Mode de paiement",
                  self.MODES.get(paiement.mode_paiement, paiement.mode_paiement)),
            ligne("Rendez-vous", f"RDV #{paiement.rendezvous_id}"),
            ['', ''],
            ligne("Client",    client_nom),
            ligne("Email",     client_email),
            ligne("Téléphone", client_tel),
            ['', ''],
            ligne("Personnel",  personnel_nom),
            ligne("Entreprise", entreprise_nom),
        ]

        t = Table(data_infos, colWidths=[65*mm, 105*mm])
        t.setStyle(TableStyle([
            ('ROWPADDING',      (0,0), (-1,-1), 6),
            ('VALIGN',          (0,0), (-1,-1), 'MIDDLE'),
            ('LINEBELOW',       (0,0), (-1,-2),
             0.5, colors.HexColor('#f1f5f9')),
            ('BACKGROUND',      (0,0), (0,-1),
             colors.HexColor('#fafafa')),
        ]))
        story.append(t)
        story.append(Spacer(1, 8*mm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        story.append(Spacer(1, 6*mm))

        # ── Pied de page ──────────────────────────────────────
        story.append(Paragraph(
            "Ce reçu constitue une preuve de paiement valide.",
            s_pied,
        ))
        story.append(Paragraph(
            f"RendezVous Pro — Plateforme de gestion de rendez-vous — © {annee}",
            s_pied,
        ))
        story.append(Paragraph(
            "Ce document a été généré automatiquement.",
            s_pied,
        ))

        doc.build(story)
        return buffer.getvalue()