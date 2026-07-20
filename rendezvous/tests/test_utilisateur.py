import pytest
from rendezvous.infrastructure.django_models.models import UtilisateurModel

@pytest.mark.django_db
def test_creation_utilisateur():

    utilisateur = UtilisateurModel.objects.create_user(
        email="afiza@test.com",
        password="MotDePasse123",
        nom="Nourane",
        prenom="Afiza"
    )

    assert utilisateur.email == "afiza@test.com"
    assert utilisateur.nom == "Nourane"
    assert utilisateur.prenom == "Afiza"
    assert utilisateur.role == "client"
    assert utilisateur.is_active is True
@pytest.mark.django_db
def test_mot_de_passe_est_hache():

    utilisateur = UtilisateurModel.objects.create_user(
        email="ali@test.com",
        password="MonSecret123",
        nom="Ali",
        prenom="Ahmed"
    )

    assert utilisateur.check_password("MonSecret123")
    assert not utilisateur.check_password("MauvaisMotDePasse")