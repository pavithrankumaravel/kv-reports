from django.urls import path
from .views import *
from kvReportsApp.api_views import ReportDataAPI

urlpatterns = [
    # DRF endpoint for JSON report data: /TKG/api/<report_name>/
    path('api/<slug:report_name>/', ReportDataAPI.as_view(), {'business': 'tkg'}, name='tkgReportDataApi'),
    path('tkgHome/', tkgHome, name="tkgHome"),
    # OverAll
    path('tkgHome/tkgEntireStockReport/', tkgEntireStockReport, name="tkgEntireStockReport"),
    path('tkgHome/tkgEntireSaleReport/', tkgEntireSaleReport, name="tkgEntireSaleReport"),

    path('tkgHome/tkgChainStockReport/', tkgChainStockReport, name="tkgChainStockReport"),
    path('tkgHome/tkgMainChainStockReport/', tkgMainChainStockReport, name="tkgMainChainStockReport"),
    path('tkgHome/tkgBranchChainStockReport/', tkgBranchChainStockReport, name="tkgBranchChainStockReport"),
    path('tkgHome/tkgTrayChainStockReport/', tkgTrayChainStockReport, name="tkgTrayChainStockReport"),
    path('tkgHome/tkgProductWiseStockReport/', tkgProductWiseStockReport, name="tkgProductWiseStockReport"),
    path('tkgHome/tkgProSubGrsWiseStockReport/', tkgProSubGrsWiseStockReport, name="tkgProSubGrsWiseStockReport"),
    path('tkgHome/tkgSupProSubGrsWiseStockReport/', tkgSupProSubGrsWiseStockReport, name="tkgSupProSubGrsWiseStockReport"),
    path('tkgHome/tkgSupplierWiseSaleReport/', tkgSupplierWiseSaleReport, name="tkgSupplierWiseSaleReport"),
    path('tkgHome/tkgDateAndSupplierWiseChainSaleReport/', tkgDateAndSupplierWiseChainSaleReport, name="tkgDateAndSupplierWiseChainSaleReport"),

    # OwnerHand
    path('tkgHome/ownerHandTkgEntireStockReport/', ownerHandTkgEntireStockReport, name="ownerHandTkgEntireStockReport"),
    path('tkgHome/ownerHandtkgProductWiseStockReport/', ownerHandtkgProductWiseStockReport, name="ownerHandtkgProductWiseStockReport"),
    path('tkgHome/ownerHandTkgChainStockReport/', ownerHandTkgChainStockReport, name="ownerHandTkgChainStockReport"),
    path('tkgHome/ownerHandTkgProSubGrsWiseStockReport/', ownerHandTkgProSubGrsWiseStockReport, name="ownerHandTkgProSubGrsWiseStockReport"),
    path('tkgHome/ownerHandTkgSupProSubGrsWiseStockReport/', ownerHandTkgSupProSubGrsWiseStockReport, name="ownerHandTkgSupProSubGrsWiseStockReport"),
]
