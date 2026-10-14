from django.shortcuts import render as django_render
from rest_framework.response import Response

from .serializers import ReportPayloadSerializer


def render(request, template_name, context=None, *args, **kwargs):
    """Render report HTML normally, or serialize the same report context for API requests."""
    if getattr(request, "_report_api_request", False):
        data = dict(context or {})
        # Cursor objects are not report data and cannot be serialized.
        data.pop("cursor", None)
        payload = ReportPayloadSerializer({"report": template_name, "data": data}).data
        return Response(payload)

    return django_render(request, template_name, context, *args, **kwargs)
