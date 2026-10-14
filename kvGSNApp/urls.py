from django.urls import path
from .views import *
from kvReportsApp.api_views import ReportDataAPI

urlpatterns = [
    # DRF endpoint for JSON report data: /GSN/api/<report_name>/
    path('api/<slug:report_name>/', ReportDataAPI.as_view(), {'business': 'gsn'}, name='gsnReportDataApi'),
    path('gsnHome/', gsnHome, name="gsnHome"),
    # OverAll
    path('gsnHome/gsnEntireStockReport/', gsnEntireStockReport, name="gsnEntireStockReport"),
    path('gsnHome/gsnEntireSaleReport/', gsnEntireSaleReport, name="gsnEntireSaleReport"),

    path('gsnHome/gsnProductWiseStockReport/', gsnProductWiseStockReport, name="gsnProductWiseStockReport"),
    path('gsnHome/gsnProSubGrsWiseStockReport/', gsnProSubGrsWiseStockReport, name="gsnProSubGrsWiseStockReport"),
    path('gsnHome/gsnSupProSubGrsWiseStockReport/', gsnSupProSubGrsWiseStockReport, name="gsnSupProSubGrsWiseStockReport"),
    path('gsnHome/gsnSupplierWiseSaleReport/', gsnSupplierWiseSaleReport, name="gsnSupplierWiseSaleReport"),

    # OwnerHand
    path('gsnHome/ownerHandGsnEntireStockReport/', ownerHandGsnEntireStockReport, name="ownerHandGsnEntireStockReport"),
    path('gsnHome/ownerHandgsnProductWiseStockReport/', ownerHandgsnProductWiseStockReport, name="ownerHandgsnProductWiseStockReport"),
    path('gsnHome/ownerHandGsnProSubGrsWiseStockReport/', ownerHandGsnProSubGrsWiseStockReport, name="ownerHandGsnProSubGrsWiseStockReport"),
    path('gsnHome/ownerHandGsnSupProSubGrsWiseStockReport/', ownerHandGsnSupProSubGrsWiseStockReport, name="ownerHandGsnSupProSubGrsWiseStockReport"),
]
