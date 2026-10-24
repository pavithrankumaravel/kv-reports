from django.http import Http404, QueryDict
from django.db import DatabaseError, connections
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from decimal import Decimal, ROUND_HALF_UP
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from kvGPCApp import views as gpc_views
from kvGSNApp import views as gsn_views
from kvTKGApp import views as tkg_views
from . import views as shared_views
from .serializers import (
    AdminTimeSheetDeleteSerializer,
    AdminTimeSheetUpdateSerializer,
    EmployeeTimeSheetInputSerializer,
    EstimateDateRangeSerializer,
    GoldEstimateInputSerializer,
    GoldEstimateRecordSerializer,
    ReportIndexSerializer,
    ReportPayloadSerializer,
    SilverEstimateInputSerializer,
    SilverEstimateRecordSerializer,
)

def _copy_validated_data_to_post(request, validated_data, extra=None):
    post_data = QueryDict("", mutable=True)
    for key, value in validated_data.items():
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        post_data[key] = str(value)
    for key, value in (extra or {}).items():
        post_data[key] = str(value)
    request._request.POST = post_data


def _gold_estimate_less_values(values):
    owner_less_amount = (
        values["productWeight"] * values["ownerLessWastage"] * values["goldRate"] / Decimal("100")
        + values["ownerLessAmountDeduction"]
    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    hude = values["rAmount"] + values["chitAmount"] + values["digitalPayment"] + values["oldValue"]
    balance_paid = values["cashReceived"] - values["rAmount"]
    less_amount = (values["invoiceAmount"] + values["gst"]) - (hude - values["oldGoldPayment"])
    owner_less_difference = owner_less_amount - less_amount
    return hude, balance_paid, less_amount, owner_less_amount, owner_less_difference


def _estimate_range_sql(date_values):
    conditions, params = [], []
    from_date, from_time = date_values.get("fromDate"), date_values.get("fromTime")
    to_date, to_time = date_values.get("toDate"), date_values.get("toTime")
    if from_date and from_time:
        conditions.append("(EstimateDate > %s OR (EstimateDate = %s AND EstimateTime >= %s))")
        params.extend([from_date, from_date, from_time])
    elif from_date:
        conditions.append("EstimateDate >= %s")
        params.append(from_date)
    if to_date and to_time:
        conditions.append("(EstimateDate < %s OR (EstimateDate = %s AND EstimateTime <= %s))")
        params.extend([to_date, to_date, to_time])
    elif to_date:
        conditions.append("EstimateDate <= %s")
        params.append(to_date)
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    return where_clause, params


REPORTS = {
    "shared": {
        "ownerHandStockReport": shared_views.ownerHandStockReport,
        "trayPieceChainStockReport": shared_views.trayPieceChainStockReport,
        "ownerHandChainStockReport": shared_views.ownerHandChainStockReportData,
        "trayAndOwnerChainStockReport": shared_views.trayAndOwnerChainStockReport,
        "chainSizeReport": shared_views.chainSizeReport,
        "dateAndSupplierWiseChainSaleReport": shared_views.dateAndSupplierWiseChainSaleReport,
        "ornamentPurityFormReport": shared_views.ornamentPurityFormReport,
        "ornamentWastageMaster": shared_views.ornamentWastageMaster,
        "adminTimeSheetManagement": shared_views.adminTimeSheetApiAction,
    },
    "gpc": {
        "gpcEntireStockReport": gpc_views.gpcEntireStockReport,
        "gpcEntireSaleReport": gpc_views.gpcEntireSaleReport,
        "gpcChainStockReport": gpc_views.gpcChainStockReport,
        "gpcMainChainStockReport": gpc_views.gpcMainChainStockReport,
        "gpcBranchChainStockReport": gpc_views.gpcBranchChainStockReport,
        "gpcTrayChainStockReport": gpc_views.gpcTrayChainStockReport,
        "gpcProductWiseStockReport": gpc_views.gpcProductWiseStockReport,
        "gpcProSubGrsWiseStockReport": gpc_views.gpcProSubGrsWiseStockReport,
        "gpcSupProSubGrsWiseStockReport": gpc_views.gpcSupProSubGrsWiseStockReport,
        "gpcSupplierWiseSaleReport": gpc_views.gpcSupplierWiseSaleReport,
        "gpcDateAndSupplierWiseChainSaleReport": gpc_views.gpcDateAndSupplierWiseChainSaleReport,
        "ownerHandGpcEntireStockReport": gpc_views.ownerHandGpcEntireStockReport,
        "ownerHandGpcProductWiseStockReport": gpc_views.ownerHandGpcProductWiseStockReport,
        "ownerHandGpcChainStockReport": gpc_views.ownerHandGpcChainStockReport,
        "ownerHandGpcProSubGrsWiseStockReport": gpc_views.ownerHandGpcProSubGrsWiseStockReport,
        "ownerHandGpcSupProSubGrsWiseStockReport": gpc_views.ownerHandGpcSupProSubGrsWiseStockReport,
    },
    "tkg": {
        "tkgEntireStockReport": tkg_views.tkgEntireStockReport,
        "tkgEntireSaleReport": tkg_views.tkgEntireSaleReport,
        "tkgChainStockReport": tkg_views.tkgChainStockReport,
        "tkgMainChainStockReport": tkg_views.tkgMainChainStockReport,
        "tkgBranchChainStockReport": tkg_views.tkgBranchChainStockReport,
        "tkgTrayChainStockReport": tkg_views.tkgTrayChainStockReport,
        "tkgSupplierWiseSaleReport": tkg_views.tkgSupplierWiseSaleReport,
        "tkgDateAndSupplierWiseChainSaleReport": tkg_views.tkgDateAndSupplierWiseChainSaleReport,
        "tkgProductWiseStockReport": tkg_views.tkgProductWiseStockReport,
        "tkgProSubGrsWiseStockReport": tkg_views.tkgProSubGrsWiseStockReport,
        "tkgSupProSubGrsWiseStockReport": tkg_views.tkgSupProSubGrsWiseStockReport,
        "ownerHandTkgEntireStockReport": tkg_views.ownerHandTkgEntireStockReport,
        "ownerHandtkgProductWiseStockReport": tkg_views.ownerHandtkgProductWiseStockReport,
        "ownerHandTkgChainStockReport": tkg_views.ownerHandTkgChainStockReport,
        "ownerHandTkgProSubGrsWiseStockReport": tkg_views.ownerHandTkgProSubGrsWiseStockReport,
        "ownerHandTkgSupProSubGrsWiseStockReport": tkg_views.ownerHandTkgSupProSubGrsWiseStockReport,
    },
    "gsn": {
        "gsnEntireStockReport": gsn_views.gsnEntireStockReport,
        "gsnEntireSaleReport": gsn_views.gsnEntireSaleReport,
        "gsnProductWiseStockReport": gsn_views.gsnProductWiseStockReport,
        "gsnProSubGrsWiseStockReport": gsn_views.gsnProSubGrsWiseStockReport,
        "gsnSupProSubGrsWiseStockReport": gsn_views.gsnSupProSubGrsWiseStockReport,
        "gsnSupplierWiseSaleReport": gsn_views.gsnSupplierWiseSaleReport,
        "ownerHandGsnEntireStockReport": gsn_views.ownerHandGsnEntireStockReport,
        "ownerHandgsnProductWiseStockReport": gsn_views.ownerHandgsnProductWiseStockReport,
        "ownerHandGsnProSubGrsWiseStockReport": gsn_views.ownerHandGsnProSubGrsWiseStockReport,
        "ownerHandGsnSupProSubGrsWiseStockReport": gsn_views.ownerHandGsnSupProSubGrsWiseStockReport,
    },
}


class ReportAPIIndex(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        reports = [
            {
                "business": business,
                "name": report_name,
                "url": reverse("reportDataApi", kwargs={"business": business, "report_name": report_name}),
            }
            for business, business_reports in REPORTS.items()
            for report_name in business_reports
        ]
        serializer = ReportIndexSerializer({"reports": reports})
        return Response(serializer.data)


class ReportDataAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request, business, report_name):
        if business == "shared" and report_name == "ownerHandChainStockReport":
            payload = ReportPayloadSerializer({
                "report": report_name,
                "data": shared_views.get_owner_hand_chain_stock_report_data(),
            })
            return Response(payload.data)

        report_view = REPORTS.get(business, {}).get(report_name)
        if report_view is None:
            raise Http404("Report API was not found.")

        if business == "shared" and report_name in {"ornamentPurityFormReport", "ornamentWastageMaster"}:
            if not request.session.get("username"):
                return Response({"detail": "Authentication required."}, status=401)

        if report_name == "adminTimeSheetManagement" and "action" not in request.query_params:
            request._request.GET = request._request.GET.copy()
            request._request.GET["action"] = "getData"

        request._report_api_request = True
        return report_view(request)


@method_decorator(csrf_protect, name="dispatch")
class EmployeeTimeSheetAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if request.query_params.get("action") != "lastUpdate":
            return Response({"status": "invalid", "message": "Unsupported action."}, status=400)
        return shared_views.employeeTimeSheetApiAction(request)

    def post(self, request):
        serializer = EmployeeTimeSheetInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"status": "invalid", "errors": serializer.errors}, status=400)
        _copy_validated_data_to_post(request, serializer.validated_data)
        request._report_api_request = True
        return shared_views.employeeTimeSheetApiAction(request)


@method_decorator(csrf_protect, name="dispatch")
class AdminTimeSheetAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        request._request.GET = request._request.GET.copy()
        request._request.GET["action"] = "getData"
        return shared_views.adminTimeSheetApiAction(request)

    def post(self, request):
        action = request.data.get("action")
        if action == "delete":
            serializer = AdminTimeSheetDeleteSerializer(data=request.data)
        elif action == "update":
            serializer = AdminTimeSheetUpdateSerializer(data=request.data)
        else:
            return Response({"status": "invalid", "message": "Unsupported action."}, status=400)
        if not serializer.is_valid():
            return Response({"status": "invalid", "errors": serializer.errors}, status=400)
        _copy_validated_data_to_post(request, serializer.validated_data, {"action": action})
        request._report_api_request = True
        return shared_views.adminTimeSheetApiAction(request)


@method_decorator(csrf_protect, name="dispatch")
class GoldEstimateAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request, estimate_id=None):
        if estimate_id is not None:
            return Response({"detail": "Method not allowed."}, status=405)
        date_filter = EstimateDateRangeSerializer(data=request.query_params)
        date_filter.is_valid(raise_exception=True)
        date_values = date_filter.validated_data
        where_clause, params = _estimate_range_sql(date_values)
        columns = (
            "GoldEstimateID, EstimateDate, EstimateTime, KPadNo, Item, ProductWeight, "
            "OwnerLessWastage, OwnerLessAmountDeduction, GoldRate, OwnerLessAmount, "
            "OwnerLessDifference, InvoiceAmount, GST, "
            "RAmount, OldGoldPayment, CashReceived, DigitalPayment, ChitAmount, OldOrnament, "
            "OldKDye, OldOtherDye, OldValue, Hude, BalancePaid, LessAmount, Remarks"
        )
        try:
            with connections["custom_report"].cursor() as cursor:
                cursor.execute(f"""
                    SELECT TOP (2000) {columns}
                    FROM CustomReport.dbo.GoldEstimate
                    {where_clause}
                    ORDER BY EstimateDate DESC, GoldEstimateID DESC
                """, params)
                rows = cursor.fetchall()
        except DatabaseError:
            return Response({"detail": "Could not read CustomReport.dbo.GoldEstimate. Check the table and Django server log."}, status=503)
        keys = (
            "id", "date", "time", "kPadNo", "item", "productWeight", "ownerLessWastage",
            "ownerLessAmountDeduction", "goldRate", "ownerLessAmount", "ownerLessDifference",
            "invoiceAmount", "gst", "rAmount",
            "oldGoldPayment", "cashReceived", "digitalPayment", "chitAmount", "oldOrnament",
            "oldKDye", "oldOtherDye", "oldValue", "hude", "balancePaid", "lessAmount", "remarks",
        )
        records = [dict(zip(keys, row)) for row in rows]
        return Response({"results": GoldEstimateRecordSerializer(records, many=True).data})

    def post(self, request, estimate_id=None):
        if estimate_id is not None:
            return Response({"detail": "Method not allowed."}, status=405)
        serializer = GoldEstimateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        hude, balance_paid, less_amount, owner_less_amount, owner_less_difference = _gold_estimate_less_values(values)
        params = [
            values["date"], values["time"], hude, values["kPadNo"].strip().upper(), values["item"],
            values["productWeight"], values["ownerLessWastage"],
            values["ownerLessAmountDeduction"], values["goldRate"],
            owner_less_amount, owner_less_difference,
            values["invoiceAmount"], values["gst"], values["rAmount"], values["oldGoldPayment"],
            values["cashReceived"], values["digitalPayment"], values["chitAmount"],
            values["oldOrnament"], values["oldKDye"], values["oldOtherDye"], values["oldValue"],
            values["remarks"].strip() or "No Remarks", balance_paid, less_amount,
        ]
        with connections["custom_report"].cursor() as cursor:
            cursor.execute("""
                INSERT INTO CustomReport.dbo.GoldEstimate
                    (EstimateDate, EstimateTime, Hude, KPadNo, Item, ProductWeight,
                     OwnerLessWastage, OwnerLessAmountDeduction, GoldRate, OwnerLessAmount,
                     OwnerLessDifference, InvoiceAmount, GST,
                     RAmount, OldGoldPayment, CashReceived, DigitalPayment, ChitAmount,
                     OldOrnament, OldKDye, OldOtherDye, OldValue, Remarks, BalancePaid, LessAmount)
                OUTPUT INSERTED.GoldEstimateID
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, params)
            estimate_id = cursor.fetchone()[0]
        return Response({"status": "success", "id": estimate_id}, status=201)

    def put(self, request, estimate_id=None):
        if estimate_id is None:
            return Response({"detail": "An estimate ID is required."}, status=405)
        if estimate_id < 1:
            return Response({"detail": "A valid estimate ID is required."}, status=400)
        serializer = GoldEstimateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        hude, balance_paid, less_amount, owner_less_amount, owner_less_difference = _gold_estimate_less_values(values)
        params = [
            values["date"], values["time"], hude, values["kPadNo"].strip().upper(), values["item"],
            values["productWeight"], values["ownerLessWastage"],
            values["ownerLessAmountDeduction"], values["goldRate"],
            owner_less_amount, owner_less_difference,
            values["invoiceAmount"], values["gst"], values["rAmount"], values["oldGoldPayment"],
            values["cashReceived"], values["digitalPayment"], values["chitAmount"],
            values["oldOrnament"], values["oldKDye"], values["oldOtherDye"], values["oldValue"],
            values["remarks"].strip() or "No Remarks", balance_paid, less_amount, estimate_id,
        ]
        with connections["custom_report"].cursor() as cursor:
            cursor.execute("""
                UPDATE CustomReport.dbo.GoldEstimate
                SET EstimateDate = %s, EstimateTime = %s, Hude = %s, KPadNo = %s, Item = %s,
                    ProductWeight = %s, OwnerLessWastage = %s,
                    OwnerLessAmountDeduction = %s, GoldRate = %s,
                    OwnerLessAmount = %s, OwnerLessDifference = %s,
                    InvoiceAmount = %s, GST = %s, RAmount = %s, OldGoldPayment = %s,
                    CashReceived = %s, DigitalPayment = %s, ChitAmount = %s, OldOrnament = %s,
                    OldKDye = %s, OldOtherDye = %s, OldValue = %s, Remarks = %s,
                    BalancePaid = %s, LessAmount = %s
                OUTPUT INSERTED.GoldEstimateID
                WHERE GoldEstimateID = %s
            """, params)
            row = cursor.fetchone()
        if not row:
            return Response({"detail": "Gold estimate not found."}, status=404)
        return Response({"status": "success", "id": row[0]})

    def delete(self, request, estimate_id=None):
        if estimate_id is None:
            return Response({"detail": "An estimate ID is required."}, status=405)
        if estimate_id < 1:
            return Response({"detail": "A valid estimate ID is required."}, status=400)
        with connections["custom_report"].cursor() as cursor:
            cursor.execute("""
                DELETE FROM CustomReport.dbo.GoldEstimate
                OUTPUT DELETED.GoldEstimateID
                WHERE GoldEstimateID = %s
            """, [estimate_id])
            row = cursor.fetchone()
        if not row:
            return Response({"detail": "Gold estimate not found."}, status=404)
        return Response({"status": "success", "id": row[0]})


@method_decorator(csrf_protect, name="dispatch")
class SilverEstimateAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request, estimate_id=None):
        if estimate_id is not None:
            return Response({"detail": "Method not allowed."}, status=405)
        date_filter = EstimateDateRangeSerializer(data=request.query_params)
        date_filter.is_valid(raise_exception=True)
        date_values = date_filter.validated_data
        where_clause, params = _estimate_range_sql(date_values)
        columns = (
            "SilverEstimateID, EstimateDate, EstimateTime, KPadNo, NetValue, CashReceived, "
            "OldSilverPayment, DigitalPayment, ChitAmount, KSheetWeight, PhysicalWeight, "
            "OldGoldValue, BalancePaid, Remarks"
        )
        try:
            with connections["custom_report"].cursor() as cursor:
                cursor.execute(f"""
                    SELECT TOP (2000) {columns}
                    FROM CustomReport.dbo.SilverEstimate
                    {where_clause}
                    ORDER BY EstimateDate DESC, SilverEstimateID DESC
                """, params)
                rows = cursor.fetchall()
        except DatabaseError:
            return Response({"detail": "Could not read CustomReport.dbo.SilverEstimate. Check the table and Django server log."}, status=503)
        keys = (
            "id", "date", "time", "kPadNo", "netValue", "cashReceived", "oldSilverPayment",
            "digitalPayment", "chitAmount", "kSheetWeight", "physicalWeight", "oldGoldValue",
            "balancePaid", "remarks",
        )
        records = [dict(zip(keys, row)) for row in rows]
        return Response({"results": SilverEstimateRecordSerializer(records, many=True).data})

    def post(self, request, estimate_id=None):
        if estimate_id is not None:
            return Response({"detail": "Method not allowed."}, status=405)
        serializer = SilverEstimateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        balance_paid = values["cashReceived"] - values["netValue"]
        params = [
            values["date"], values["time"], values["kPadNo"].strip().upper(), values["netValue"],
            values["cashReceived"], values["oldSilverPayment"], values["digitalPayment"],
            values["chitAmount"], values["kSheetWeight"], values["physicalWeight"],
            values["oldGoldValue"], values["remarks"].strip() or "No Remarks", balance_paid,
        ]
        with connections["custom_report"].cursor() as cursor:
            cursor.execute("""
                INSERT INTO CustomReport.dbo.SilverEstimate
                    (EstimateDate, EstimateTime, KPadNo, NetValue, CashReceived, OldSilverPayment,
                     DigitalPayment, ChitAmount, KSheetWeight, PhysicalWeight, OldGoldValue,
                     Remarks, BalancePaid)
                OUTPUT INSERTED.SilverEstimateID
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, params)
            estimate_id = cursor.fetchone()[0]
        return Response({"status": "success", "id": estimate_id}, status=201)

    def put(self, request, estimate_id=None):
        if estimate_id is None:
            return Response({"detail": "An estimate ID is required."}, status=405)
        if estimate_id < 1:
            return Response({"detail": "A valid estimate ID is required."}, status=400)
        serializer = SilverEstimateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        balance_paid = values["cashReceived"] - values["netValue"]
        params = [
            values["date"], values["time"], values["kPadNo"].strip().upper(), values["netValue"],
            values["cashReceived"], values["oldSilverPayment"], values["digitalPayment"],
            values["chitAmount"], values["kSheetWeight"], values["physicalWeight"],
            values["oldGoldValue"], values["remarks"].strip() or "No Remarks", balance_paid, estimate_id,
        ]
        with connections["custom_report"].cursor() as cursor:
            cursor.execute("""
                UPDATE CustomReport.dbo.SilverEstimate
                SET EstimateDate = %s, EstimateTime = %s, KPadNo = %s, NetValue = %s,
                    CashReceived = %s, OldSilverPayment = %s, DigitalPayment = %s, ChitAmount = %s,
                    KSheetWeight = %s, PhysicalWeight = %s, OldGoldValue = %s, Remarks = %s,
                    BalancePaid = %s
                OUTPUT INSERTED.SilverEstimateID
                WHERE SilverEstimateID = %s
            """, params)
            row = cursor.fetchone()
        if not row:
            return Response({"detail": "Silver estimate not found."}, status=404)
        return Response({"status": "success", "id": row[0]})

    def delete(self, request, estimate_id=None):
        if estimate_id is None:
            return Response({"detail": "An estimate ID is required."}, status=405)
        if estimate_id < 1:
            return Response({"detail": "A valid estimate ID is required."}, status=400)
        with connections["custom_report"].cursor() as cursor:
            cursor.execute("""
                DELETE FROM CustomReport.dbo.SilverEstimate
                OUTPUT DELETED.SilverEstimateID
                WHERE SilverEstimateID = %s
            """, [estimate_id])
            row = cursor.fetchone()
        if not row:
            return Response({"detail": "Silver estimate not found."}, status=404)
        return Response({"status": "success", "id": row[0]})
