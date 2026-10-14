from django.urls import path
from .views import *
from kvReportsApp.api_views import ReportDataAPI

urlpatterns = [
    # DRF endpoint for JSON report data: /GPC/api/<report_name>/
    path('api/<slug:report_name>/', ReportDataAPI.as_view(), {'business': 'gpc'}, name='gpcReportDataApi'),
    path('gpcHome/', gpcHome, name="gpcHome"),
    # OverAll
    path('gpcHome/gpcEntireStockReport/', gpcEntireStockReport, name="gpcEntireStockReport"),
    path('gpcHome/gpcEntireSaleReport/', gpcEntireSaleReport, name="gpcEntireSaleReport"),

    path('gpcHome/gpcChainStockReport/', gpcChainStockReport, name="gpcChainStockReport"),
    path('gpcHome/gpcMainChainStockReport/', gpcMainChainStockReport, name="gpcMainChainStockReport"),
    path('gpcHome/gpcBranchChainStockReport/', gpcBranchChainStockReport, name="gpcBranchChainStockReport"),
    path('gpcHome/gpcTrayChainStockReport/', gpcTrayChainStockReport, name="gpcTrayChainStockReport"),
    path('gpcHome/gpcProductWiseStockReport/', gpcProductWiseStockReport, name="gpcProductWiseStockReport"),
    path('gpcHome/gpcProSubGrsWiseStockReport/', gpcProSubGrsWiseStockReport, name="gpcProSubGrsWiseStockReport"),
    path('gpcHome/gpcSupProSubGrsWiseStockReport/', gpcSupProSubGrsWiseStockReport, name="gpcSupProSubGrsWiseStockReport"),
    path('gpcHome/gpcSupplierWiseSaleReport/', gpcSupplierWiseSaleReport, name="gpcSupplierWiseSaleReport"),
    path('gpcHome/gpcDateAndSupplierWiseChainSaleReport/', gpcDateAndSupplierWiseChainSaleReport, name="gpcDateAndSupplierWiseChainSaleReport"),

    # OwnerHand
    path('gpcHome/ownerHandGpcEntireStockReport/', ownerHandGpcEntireStockReport, name="ownerHandGpcEntireStockReport"),
    path('gpcHome/ownerHandGpcProductWiseStockReport/', ownerHandGpcProductWiseStockReport, name="ownerHandGpcProductWiseStockReport"),
    path('gpcHome/ownerHandGpcChainStockReport/', ownerHandGpcChainStockReport, name="ownerHandGpcChainStockReport"),
    path('gpcHome/ownerHandGpcProSubGrsWiseStockReport/', ownerHandGpcProSubGrsWiseStockReport, name="ownerHandGpcProSubGrsWiseStockReport"),
    path('gpcHome/ownerHandGpcSupProSubGrsWiseStockReport/', ownerHandGpcSupProSubGrsWiseStockReport, name="ownerHandGpcSupProSubGrsWiseStockReport"),

]
