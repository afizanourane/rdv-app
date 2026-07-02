"""
=============================================================
  rendezvous/presentation/schema.py

  Configuration de la documentation API (Swagger)
=============================================================
"""
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
)
from drf_spectacular.types import OpenApiTypes