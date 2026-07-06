"""
config/urls.py
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from rendezvous.presentation.views.auth_views import (
    LoginView,
    LogoutView,
    ChangerMotDePasseView,
    
    
)


from rendezvous.presentation.views.views import (
    
    DemanderResetMotDePasseView,
    ResetMotDePasseView,
    ValiderTokenResetView,
    
)


# Swagger
schema_view = get_schema_view(
    openapi.Info(
        title="API Rendez-vous",
        default_version='v1',
        description="API de gestion de rendez-vous",
        contact=openapi.Contact(email="admin@rendezvous.cm"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [

    # Admin Django
    path('admin/', admin.site.urls),

    # ── Authentification JWT ──────────────────────────────────
    path('api/auth/login/',
         LoginView.as_view(), name='login'),

    path('api/auth/logout/',
         LogoutView.as_view(), name='logout'),

    path('api/auth/changer-mot-de-passe/',
         ChangerMotDePasseView.as_view(), name='changer-mot-de-passe'),

    path('api/auth/refresh/',
         TokenRefreshView.as_view(), name='token-refresh'),

    # ── Toutes les autres routes ──────────────────────────────
    path('api/', include('rendezvous.presentation.urls')),

    # ── Documentation Swagger ─────────────────────────────────
    re_path(r'^api/docs/$',
            schema_view.with_ui('swagger', cache_timeout=0),
            name='swagger-ui'),
    re_path(r'^api/redoc/$',
            schema_view.with_ui('redoc', cache_timeout=0),
            name='redoc'),


     # _______Reintialisation mot passe_______
     path('api/auth/demander-reset/',
     DemanderResetMotDePasseView.as_view(), name='demander-reset'),

     path('api/auth/reset-password/',
     ResetMotDePasseView.as_view(), name='reset-password'),

     path('api/auth/valider-token/',
     ValiderTokenResetView.as_view(), name='valider-token'),


     

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)