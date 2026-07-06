from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from datetime import date, time, timedelta
from decimal import Decimal
import random

from rendezvous.infrastructure.django_models.models import (
    UtilisateurModel,
    ClientModel,
    AdministrateurModel,
    PersonnelModel,
    DomaineModel,
    EntrepriseModel,
    AvisModel,
    PlageCreneauModel,
    CreneauModel,
    RendezVousModel,
    HistoriqueStatutModel,
    PaiementModel,
    NotificationModel,
)

print("=" * 60)
print("        REMPLISSAGE BASE DE DONNÉES - RENDEZVOUS PRO")
print("=" * 60)

with transaction.atomic():

    # ==========================================================
    # ADMINISTRATEUR
    # ==========================================================

    admin_u, created = UtilisateurModel.objects.get_or_create(
        email="afizanoura@icloud.com",
        defaults={
            "nom": "Afiza",
            "prenom": "Nourane",
            "telephone": "690000000",
            "role": "admin",
            "is_staff": True,
            "is_superuser": True,
        },
    )

    if created:
        admin_u.set_password("123")
        admin_u.save()
        print("✅ Administrateur créé")
    else:
        print("ℹ️ Administrateur déjà existant")

    admin_mdl, _ = AdministrateurModel.objects.get_or_create(
        utilisateur=admin_u
    )

    # ==========================================================
    # CLIENTS
    # ==========================================================

    CLIENTS_DATA = [
        ("Marie", "Antoinette", "antoinnette@gmail.com", "690001001", "Rue de la Paix, Yaoundé"),
        ("Marie", "Claire", "marie@gmail.com", "691002002", "Quartier Bastos, Yaoundé"),
        ("Fotso", "Claire", "claire@gmail.com", "692003003", "Akwa, Douala"),
        ("Bello", "Ahmed", "bello@gmail.com", "693004004", "Bonanjo, Douala"),
    ]

    clients = []

    for nom, prenom, email, tel, adresse in CLIENTS_DATA:

        utilisateur, created = UtilisateurModel.objects.get_or_create(
            email=email,
            defaults={
                "nom": nom,
                "prenom": prenom,
                "telephone": tel,
                "role": "client",
            },
        )

        if created:
            utilisateur.set_password("client123")
            utilisateur.save()

        client, _ = ClientModel.objects.get_or_create(
            utilisateur=utilisateur,
            defaults={
                "adresse": adresse
            },
        )

        clients.append(client)

    print(f"✅ {len(clients)} clients prêts")

    # ==========================================================
    # PERSONNELS
    # ==========================================================

    PERSONNELS_DATA = [
        ("Souga", "Bphane", "bphanesouga@gmail.com", "698009009", "Agent principal"),
        ("Djomo", "Jefferson", "jefferson@gmail.com", "699010010", "Coordinateur"),
    ]

    personnels = []

    for nom, prenom, email, tel, poste in PERSONNELS_DATA:

        utilisateur, created = UtilisateurModel.objects.get_or_create(
            email=email,
            defaults={
                "nom": nom,
                "prenom": prenom,
                "telephone": tel,
                "role": "personnel",
            },
        )

        if created:
            utilisateur.set_password("personnel123")
            utilisateur.save()

        personnel, _ = PersonnelModel.objects.get_or_create(
            utilisateur=utilisateur,
            defaults={
                "poste": poste
            },
        )

        personnels.append(personnel)

    print(f"✅ {len(personnels)} personnels prêts")

    print(f"👥 Utilisateurs : {UtilisateurModel.objects.count()}")



        # ==========================================================
    # DOMAINES
    # ==========================================================

    print("\nCréation des domaines...")

    DOMAINES_DATA = [
        ("Nettoyage", "Services de nettoyage résidentiel et professionnel"),
        ("Informatique", "Maintenance et assistance informatique"),
        ("Plomberie", "Installation et réparation de plomberie"),
        ("Électricité", "Travaux électriques"),
        ("Jardinage", "Entretien des espaces verts"),
        ("Sécurité", "Gardiennage"),
        ("Coiffure", "Salon de coiffure"),
        ("Climatisation", "Installation climatiseurs"),
        ("Peinture", "Travaux de peinture"),
        ("Transport", "Transport et livraison"),
    ]

    domaines = []

    for nom, description in DOMAINES_DATA:

        domaine, created = DomaineModel.objects.get_or_create(
            nom_domaine=nom,
            defaults={
                "description": description,
            }
        )

        domaines.append(domaine)

        if created:
            print(f"   ✅ {nom}")

    print(f"Domaines : {DomaineModel.objects.count()}")




        # ==========================================================
    # ENTREPRISES
    # ==========================================================

    print("\nCréation des entreprises...")

    ENTREPRISES_DATA = [
        ("CleanPro Cameroun", "Bastos, Yaoundé", "677100001", "contact@cleanpro.cm", 0),
        ("TechSupport SARL", "Rue Nachtigal", "691200002", "info@techsupport.cm", 1),
        ("PlombiTech", "Akwa", "699300003", "plombitech@gmail.com", 2),
        ("ElectroPro", "Bonanjo", "688400004", "electropro@yahoo.fr", 3),
        ("GardenCare CM", "Bastos", "677500005", "garden@care.cm", 4),
        ("SecuGuard Cameroun", "Omnisport", "691600006", "secuguard@gmail.com", 5),
        ("Salon Excellence", "Mvog Ada", "699700007", "salon@excellence.cm", 6),
        ("ClimaFroid SARL", "Bali", "688800008", "climafroid@gmail.com", 7),
    ]

    entreprises = []

    for nom, adresse, tel, email, idx in ENTREPRISES_DATA:

        entreprise, created = EntrepriseModel.objects.get_or_create(

            email=email,

            defaults={

                "nom_entreprise": nom,

                "adresse": adresse,

                "telephone": tel,

                "description": f"Entreprise spécialisée en {domaines[idx].nom_domaine.lower()}",

                "est_active": True,

                "domaine": domaines[idx],

            },

        )

        entreprises.append(entreprise)

        if created:

            print(f"   ✅ {nom}")

    print(f"Entreprises : {EntrepriseModel.objects.count()}")







        # ==========================================================
    # AFFECTATION PERSONNELS
    # ==========================================================

    print("\nAffectation du personnel...")

    for i, personnel in enumerate(personnels):

        entreprise = entreprises[i % len(entreprises)]

        personnel.entreprise = entreprise

        personnel.domaine = entreprise.domaine

        personnel.save()

    print("Personnel affecté.")





        # ==========================================================
    # AVIS
    # ==========================================================

    print("\nCréation des avis...")

    COMMENTAIRES = [

        "Excellent service.",

        "Très professionnel.",

        "Je recommande.",

        "Travail impeccable.",

        "Très satisfait.",

        "Personnel agréable.",

        "Ponctuel.",

        "Excellent rapport qualité prix.",

    ]

    nb = 0

    for i, client in enumerate(clients):

        for j, entreprise in enumerate(entreprises):

            _, created = AvisModel.objects.get_or_create(

                client=client,

                entreprise=entreprise,

                defaults={

                    "note": random.choice([3,4,4,5,5,5]),

                    "commentaire": COMMENTAIRES[(i+j) % len(COMMENTAIRES)]

                }

            )

            if created:

                nb += 1

    print(f"Avis créés : {nb}")



    # ==========================================================
    # PLAGES DE CRÉNEAUX
    # ==========================================================

    print("\nCréation des plages...")

    plages = []

    today = date.today()

    nb = 0

    for personnel in personnels:

        if personnel.entreprise is None:
            continue

        for i in range(16):

            jour = today + timedelta(days=i + 1)

            plage, created = PlageCreneauModel.objects.get_or_create(

                entreprise=personnel.entreprise,

                date_plage=jour,

                heure_debut=time(8,0),

                heure_fin=time(17,0),

                defaults={
                    "libelle":f"Journée {jour.strftime('%d/%m/%Y')}"
                }

            )

            plages.append(plage)

            if created:
                nb += 1

    print(f"Plages créées : {nb}")




        # ==========================================================
    # CRÉNEAUX
    # ==========================================================

    print("\nCréation des créneaux...")

    HORAIRES = [

        (time(8,0),time(10,0)),

        (time(10,0),time(12,0)),

        (time(13,0),time(15,0)),

        (time(15,0),time(17,0)),

        (time(17,0),time(19,0))

    ]

    creneaux=[]

    nb=0

    for personnel in personnels:

        plages_personnel = [

            p for p in plages

            if p.entreprise == personnel.entreprise

        ]

        if not plages_personnel:
            continue

        for plage in plages_personnel[:4]:

            for hdeb,hfin in HORAIRES:

                creneau,created = CreneauModel.objects.get_or_create(

                    personnel=personnel,

                    plage=plage,

                    heure_debut=hdeb,

                    heure_fin=hfin,

                    defaults={

                        "statut":"disponible"

                    }

                )

                creneaux.append(creneau)

                if created:
                    nb+=1

    print(f"Créneaux créés : {nb}")




    
    # ==========================================================
    # RENDEZ-VOUS
    # ==========================================================

    print("\nCréation des rendez-vous...")

    creneaux_disponibles = list(

        CreneauModel.objects.filter(

            statut="disponible"

        ).order_by("id")

    )

    if not creneaux_disponibles:

        raise Exception(

            "Aucun créneau disponible."

        )

    STATUTS=[

        "en_attente",

        "confirme",

        "refuse",

        "annule",

        "termine"

    ]

    DESCRIPTIONS=[

        "Nettoyage complet",

        "Réparation ordinateur",

        "Installation plomberie",

        "Mise aux normes électriques",

        "Entretien jardin",

        "Surveillance",

        "Coiffure",

        "Entretien climatiseur",

        "Peinture",

        "Transport"

    ]

    rdvs=[]

    nb=0

    index=0

    for client in clients:

        for j in range(8):

            creneau = creneaux_disponibles[index]

            index += 1

            if index >= len(creneaux_disponibles):

                index = 0

            statut = STATUTS[(j)%len(STATUTS)]

            description = DESCRIPTIONS[(j)%len(DESCRIPTIONS)]

            rdv,created = RendezVousModel.objects.get_or_create(

                client=client,

                creneau=creneau,

                defaults={

                    "description":description,

                    "statut":statut,

                    "confirmation":statut in ["confirme","termine"],

                    "traite_par":admin_mdl if statut in ["confirme","termine","refuse"] else None,

                    "motif_refus":"Créneau indisponible." if statut=="refuse" else ""

                }

            )

            if created:

                rdvs.append(rdv)

                nb += 1

                creneau.statut="reserve"

                creneau.save()

    print(f"Rendez-vous créés : {nb}")





    # ==========================================================
    # HISTORIQUE
    # ==========================================================

    print("\nCréation historique...")

    nb=0

    for rdv in rdvs:

        HistoriqueStatutModel.objects.get_or_create(

            rendezvous=rdv,

            ancien_statut="",

            nouveau_statut="en_attente",

            defaults={

                "change_par":rdv.client.utilisateur,

                "commentaire":"Création"

            }

        )

        if rdv.statut=="confirme":

            HistoriqueStatutModel.objects.get_or_create(

                rendezvous=rdv,

                ancien_statut="en_attente",

                nouveau_statut="confirme",

                defaults={

                    "change_par":admin_u,

                    "commentaire":"Confirmation"

                }

            )

        if rdv.statut=="termine":

            HistoriqueStatutModel.objects.get_or_create(

                rendezvous=rdv,

                ancien_statut="confirme",

                nouveau_statut="termine",

                defaults={

                    "change_par":admin_u,

                    "commentaire":"Terminé"

                }

            )

        nb+=1

    print(f"Historiques : {HistoriqueStatutModel.objects.count()}")



        # ==========================================================
    # PAIEMENTS
    # ==========================================================

    print("\nCréation des paiements...")

    MODES = [
        "mobile_money",
        "carte",
        "virement",
        "especes"
    ]

    MONTANTS = [
        5000,
        7500,
        10000,
        12000,
        15000,
        18000,
        20000,
        25000
    ]

    nb = 0

    rdvs_payables = RendezVousModel.objects.filter(
        statut__in=["confirme", "termine"]
    )

    for i, rdv in enumerate(rdvs_payables):

        paiement, created = PaiementModel.objects.get_or_create(

            rendezvous=rdv,

            defaults={

                "montant": Decimal(str(MONTANTS[i % len(MONTANTS)])),

                "mode_paiement": MODES[i % len(MODES)],

                "statut": "paye" if rdv.statut == "termine" else "en_attente",

                "reference_transaction":
                    f"PAY-{timezone.now().strftime('%Y%m%d')}-{rdv.id:04d}"

            }

        )

        if created:
            nb += 1

    print(f"Paiements créés : {nb}")



        # ==========================================================
    # NOTIFICATIONS
    # ==========================================================

    print("\nCréation des notifications...")

    nb = 0

    for rdv in rdvs:

        NotificationModel.objects.get_or_create(

            destinataire=rdv.client.utilisateur,

            titre="📅 Rendez-vous",

            message=f"Votre rendez-vous #{rdv.id} a été enregistré.",

            defaults={

                "type_notification":"rendezvous",

                "est_lue":False

            }

        )

        nb += 1

        if rdv.statut == "confirme":

            NotificationModel.objects.get_or_create(

                destinataire=rdv.client.utilisateur,

                titre="✅ Rendez-vous confirmé",

                message=f"Votre rendez-vous #{rdv.id} est confirmé.",

                defaults={

                    "type_notification":"rendezvous"

                }

            )

            nb += 1

        elif rdv.statut == "refuse":

            NotificationModel.objects.get_or_create(

                destinataire=rdv.client.utilisateur,

                titre="❌ Rendez-vous refusé",

                message=f"Votre rendez-vous #{rdv.id} a été refusé.",

                defaults={

                    "type_notification":"rendezvous"

                }

            )

            nb += 1

    NotificationModel.objects.get_or_create(

        destinataire=admin_u,

        titre="🎉 Base remplie",

        message="Le script seed.py a terminé avec succès.",

        defaults={

            "type_notification":"systeme"

        }

    )

    print(f"Notifications : {NotificationModel.objects.count()}")




        # ==========================================================
    # RÉSUMÉ
    # ==========================================================

    print("\n")
    print("=" * 60)
    print("           BASE DE DONNÉES REMPLIE")
    print("=" * 60)

    print(f"Utilisateurs    : {UtilisateurModel.objects.count()}")
    print(f"Clients         : {ClientModel.objects.count()}")
    print(f"Personnels      : {PersonnelModel.objects.count()}")
    print(f"Administrateurs : {AdministrateurModel.objects.count()}")

    print(f"Domaines        : {DomaineModel.objects.count()}")
    print(f"Entreprises     : {EntrepriseModel.objects.count()}")

    print(f"Avis            : {AvisModel.objects.count()}")

    print(f"Plages          : {PlageCreneauModel.objects.count()}")
    print(f"Créneaux        : {CreneauModel.objects.count()}")

    print(f"Rendez-vous     : {RendezVousModel.objects.count()}")
    print(f"Historiques     : {HistoriqueStatutModel.objects.count()}")

    print(f"Paiements       : {PaiementModel.objects.count()}")

    print(f"Notifications   : {NotificationModel.objects.count()}")

    print("=" * 60)

    print("\nCOMPTES DE CONNEXION\n")

    print("ADMIN")
    print("  Email : afizanoura@icloud.com")
    print("  Mot de passe : 123")

    print("\nCLIENTS")

    for c in clients:

        print(
            f"  {c.utilisateur.email}  / client123"
        )

    print("\nPERSONNELS")

    for p in personnels:

        print(
            f"  {p.utilisateur.email}  / personnel123"
        )

    print("\n✅ Script terminé avec succès.")


