import pytest
from rest_framework.test import APIClient
from rendezvous.infrastructure.django_models.models import UtilisateurModel


@pytest.mark.django_db
def test_connexion_sans_2fa():

    client = APIClient()

    UtilisateurModel.objects.create_user(
        email="afiza@test.com",
        password="MotDePasse123",
        nom="Afiza",
        prenom="Nourane",
        deux_fa_active=False
    )

    response = client.post(
        "/api/auth/login/",
        {
            "email": "afiza@test.com",
            "password": "MotDePasse123"
        },
        format="json"
    )

    assert response.status_code == 200

    data = response.json()

    assert "access" in data
    assert "refresh" in data