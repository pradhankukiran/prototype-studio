from __future__ import annotations

from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from .models import PrototypeProject


def get_project(_request: HttpRequest, slug: str, **extra_filters) -> PrototypeProject:
    return get_object_or_404(PrototypeProject, slug=slug, **extra_filters)


def get_project_with_prefetch(
    _request: HttpRequest, slug: str, prefetch_related: list[str] | None = None
) -> PrototypeProject:
    qs = PrototypeProject.objects.all()
    if prefetch_related:
        qs = qs.prefetch_related(*prefetch_related)
    return get_object_or_404(qs, slug=slug)
