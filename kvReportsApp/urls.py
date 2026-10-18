from django.urls import path
from .views import *
from .api_views import GoldEstimateAPI, SilverEstimateAPI

urlpatterns = [
    path('', home, name="home"),
    path('ownerHandStockReport', ownerHandStockReport, name="ownerHandStockReport"),
    path('trayPieceChainStockReport', trayPieceChainStockReport, name="trayPieceChainStockReport"),
    path('ownerHandChainStockReport', ownerHandChainStockReport, name="ownerHandChainStockReport"),
    path('api/reports/owner-hand-chain-stock/', ownerHandChainStockReportData, name="ownerHandChainStockReportData"),
    path('trayAndOwnerChainStockReport', trayAndOwnerChainStockReport, name="trayAndOwnerChainStockReport"),
    path('chainSizeReport', chainSizeReport, name="chainSizeReport"),
    path('dateAndSupplierWiseChainSaleReport/', dateAndSupplierWiseChainSaleReport, name="dateAndSupplierWiseChainSaleReport"),


    # Login related pages:
    path('login/', login_view, name='login'),
    path('logout/', logout_view),


    # Purity related pages:
    path('ornamentWastageMaster/', ornamentWastageMaster, name="ornamentWastageMaster"),
    path('ornamentPurityFormReport/', ornamentPurityFormReport, name="ornamentPurityFormReport"),
    path('api/purity/wastage/', addOrnamentWastageMaster, name="addOrnamentWastageMaster"),
    path('api/purity/wastage/update/', updateOrnamentWastageMaster, name="updateOrnamentWastageMaster"),
    path("api/purity/products/", get_products, name="getProductsApi"),
    path("api/purity/ornaments/", get_ornaments, name="getOrnamentsApi"),
    path("api/purity/delete/", deleteOrnamentPurity, name="deleteOrnamentPurity"),
    path("api/purity/submit/", submitOrnamentPurityForm, name="submitOrnamentPurityForm"),


    # Office related pages:
    path("employeeTimeSheetManagement/", employeeTimeSheetManagement, name="employeeTimeSheetManagement"),
    path("adminTimeSheetManagement/", adminTimeSheetManagement, name="adminTimeSheetManagement"),

    # Estimate pages:
    path("goldEstimateForm/", goldEstimateForm, name="goldEstimateForm"),
    path("silverEstimateForm/", silverEstimateForm, name="silverEstimateForm"),
    path("goldEstimateReport/", goldEstimateReport, name="goldEstimateReport"),
    path("silverEstimateReport/", silverEstimateReport, name="silverEstimateReport"),
    path("api/estimates/gold/", GoldEstimateAPI.as_view(), name="goldEstimateCreateApi"),
    path("api/estimates/gold/<int:estimate_id>/", GoldEstimateAPI.as_view(), name="goldEstimateDetailApi"),
    path("api/estimates/silver/", SilverEstimateAPI.as_view(), name="silverEstimateCreateApi"),
    path("api/estimates/silver/<int:estimate_id>/", SilverEstimateAPI.as_view(), name="silverEstimateDetailApi"),
]
