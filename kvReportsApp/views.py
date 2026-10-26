from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.views import redirect_to_login
from django.utils.http import url_has_allowed_host_and_scheme
from .api_utils import render
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_protect
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import ReportPayloadSerializer
from django.db import connection, connections
from collections import defaultdict
from .getFunction import round_to_even, round_for_without_chain, normalize_subproduct
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo 
from decimal import getcontext
import re
import random
import hashlib

# Create your views here.


def home(request):
    return render(request, "home.html")

def ownerHandStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    queryGPC = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM GPCJ2627.dbo.TagReceipt a
        JOIN GPCJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN GPCJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='' AND a.TagChkDate IS NULL;
    """

    queryTKG = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='' AND a.TagChkDate IS NULL;
    """

    with connection.cursor() as cursor:
        cursor.execute(queryGPC)
        rows = cursor.fetchall()
    columnsGPC = ["Product", "SubProduct", "TagNo", "GrsWt", "Pieces"]
    dataGPC = [dict(zip(columnsGPC, row)) for row in rows]

    with connection.cursor() as cursor:
        cursor.execute(queryTKG)
        rows = cursor.fetchall()
    columnsTKG = ["Product", "SubProduct", "TagNo", "GrsWt", "Pieces"]
    dataTKG = [dict(zip(columnsTKG, row)) for row in rows]
    
    data = dataGPC+dataTKG

    # ✅ Your filter selections
    selected_product = request.GET.get('product')
    selected_subproduct = request.GET.get('subproduct')
    selected_grswt = request.GET.getlist('grswt')

    # ✅ Unique products
    unique_products = sorted(set(d["Product"] for d in data if d["Product"]))

    # ✅ Unique subproducts based on selected product
    unique_subproducts = []
    if selected_product:
        filtered_for_sub = [d for d in data if d["Product"] == selected_product]
        unique_subproducts = sorted(set(d["SubProduct"] for d in filtered_for_sub if d["SubProduct"]))

    # ✅ Unique GrossWt values based on selected subproduct
    unique_grswts = []
    if selected_subproduct:
        if selected_product == "CHAIN":
            filtered_for_grswt = [
                d for d in data
                if d["SubProduct"] == selected_subproduct and
                d["GrsWt"] not in [None, ''] and
                str(d["GrsWt"]).replace('.', '', 1).isdigit()
            ]
            unique_grswts = sorted(set(round_to_even(float(d["GrsWt"])) for d in filtered_for_grswt))
        else:
            filtered_for_grswt = [
                d for d in data
                if d["SubProduct"] == selected_subproduct and
                d["GrsWt"] not in [None, ''] and
                str(d["GrsWt"]).replace('.', '', 1).isdigit()
            ]
            unique_grswts = sorted(set(round_for_without_chain(float(d["GrsWt"])) for d in filtered_for_grswt))

    # ✅ Show table only if all 3 filters applied
    show_table = selected_product and selected_subproduct and selected_grswt

    # ✅ Build tableData for template
    table_data = []
    if show_table:
        selected_grswt_nums = [float(g) for g in selected_grswt]
        matrix = defaultdict(lambda: defaultdict(int))

        for d in data:
            product = d["Product"]
            subproduct = d["SubProduct"]
            grswt = d["GrsWt"]

            if not (product and subproduct and grswt):
                continue
            if not str(grswt).replace('.', '', 1).isdigit():
                continue

            if product == "CHAIN":
                rounded_grswt = round_to_even(float(grswt))
            else:
                rounded_grswt = round_for_without_chain(float(grswt))

            if (product == selected_product and
                subproduct == selected_subproduct and
                rounded_grswt in selected_grswt_nums):
                matrix[subproduct][rounded_grswt] += 1

        # Build row-wise structured data
        for sub, grs_data in matrix.items():
            row_values = [grs_data.get(gw, 0) for gw in unique_grswts]
            total = sum(row_values)
            table_data.append({
                "sub": sub,
                "values": row_values,
                "total": total
            })

    return render(request, 'ownerHandStockReport.html', {
        'currentDateTime': formatted_time,
        'uniqueProducts': unique_products,
        'uniqueSubProducts': unique_subproducts,
        'uniqueGrsWt': unique_grswts,
        'selectedProduct': selected_product,
        'selectedSubProduct': selected_subproduct,
        'selectedGrsWt': selected_grswt,
        'tableData': table_data,   # ✅ simplified structured data
        'showTable': show_table,
    })

def trayPieceChainStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    queryGPC = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM GPCJ2627.dbo.TagReceipt a
        JOIN GPCJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN GPCJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='' AND a.TagChkDate IS NOT NULL AND b.ProName= 'CHAIN';
    """

    queryTKG = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='' AND a.TagChkDate IS NOT NULL AND b.ProName= 'CHAIN';
    """

    with connection.cursor() as cursor:
        cursor.execute(queryGPC)
        rows = cursor.fetchall()
    columnsGPC = ["ProName", "SubProName", "TagNo", "GrossWt", "Pieces"]
    dataGPC = [dict(zip(columnsGPC, row)) for row in rows]

    with connection.cursor() as cursor:
        cursor.execute(queryTKG)
        rows = cursor.fetchall()
    columnsTKG = ["ProName", "SubProName", "TagNo", "GrossWt", "Pieces"]
    dataTKG = [dict(zip(columnsTKG, row)) for row in rows]

    data = dataGPC+dataTKG

    # --- Build report like gpcChainStockReport ---
    # Unique Products
    unique_products = sorted(set(d["ProName"] for d in data if d["ProName"]))

    # Unique SubProducts
    unique_subproducts = sorted(set(d["SubProName"] for d in data if d["SubProName"]))

    # Unique Gross Weights (rounded to even)
    unique_grswts = sorted(set(
        round_to_even(float(d["GrossWt"]))
        for d in data
        if d["GrossWt"] not in [None, ''] and str(d["GrossWt"]).replace('.', '', 1).isdigit()
    ))

    # Matrix: SubProduct × GrossWt
    matrix = defaultdict(lambda: defaultdict(int))
    for d in data:
        sub = d["SubProName"]
        grs_wt = d["GrossWt"]
        if sub and grs_wt and str(grs_wt).replace('.', '', 1).isdigit():
            rounded_wt = round_to_even(float(grs_wt))
            matrix[sub][rounded_wt] += 1

    # Excluded subproducts
    excluded_subproducts = ["SORAI", "PLAIN MUGAPU", "STONE MUGAPU", "CASTING MUGAPU"]

    return render(request, 'trayPieceChainStockReport.html', {
        'currentDateTime': formatted_time,
        'rows': data,
        'uniqueProducts': unique_products,
        'uniqueSubProducts': unique_subproducts,
        'uniqueGrsWt': unique_grswts,
        'matrix': matrix,
        'excludedSubProducts': excluded_subproducts,
    })

def ownerHandChainStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    return render(request, 'ownerHandChainStockReport.html', {
        'currentDateTime': formatted_time,
    })


def employeeTimeSheetManagement(request):
    return render(request, "employeeTimeSheetManagement.html")


def adminTimeSheetManagement(request):
    return render(request, "adminTimeSheetManagement.html")


def get_owner_hand_chain_stock_report_data():
    query = """
        SELECT SubProName, GrossWt, SUM(ItemCount) AS ItemCount
        FROM (
            SELECT c.SubProName, a.GrossWt, COUNT_BIG(*) AS ItemCount
            FROM GPCJ2627.dbo.TagReceipt a
            JOIN GPCJMaster.dbo.Product b ON a.ProCode = b.ProCode
            JOIN GPCJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
            WHERE a.IssueType = '' AND a.TagChkDate IS NULL AND b.ProName = 'CHAIN'
            GROUP BY c.SubProName, a.GrossWt

            UNION ALL

            SELECT c.SubProName, a.GrossWt, COUNT_BIG(*) AS ItemCount
            FROM TKGJ2627.dbo.TagReceipt a
            JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
            JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
            WHERE a.IssueType = '' AND a.TagChkDate IS NULL AND b.ProName = 'CHAIN'
            GROUP BY c.SubProName, a.GrossWt
        ) AS StockCounts
        GROUP BY SubProName, GrossWt
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        grouped_rows = cursor.fetchall()

    unique_subproducts = set()
    unique_grswts = set()
    matrix = defaultdict(lambda: defaultdict(int))
    for subproduct, gross_weight, item_count in grouped_rows:
        if subproduct:
            unique_subproducts.add(subproduct)
        if gross_weight is None or not str(gross_weight).replace('.', '', 1).isdigit():
            continue

        rounded_weight = round_to_even(float(gross_weight))
        unique_grswts.add(rounded_weight)
        if subproduct and gross_weight:
            matrix[subproduct][rounded_weight] += int(item_count)

    excluded_subproducts = {"SORAI", "PLAIN MUGAPU", "STONE MUGAPU", "CASTING MUGAPU"}
    weights = sorted(unique_grswts)
    visible_subproducts = sorted(unique_subproducts - excluded_subproducts)
    report_rows = [{
        "subProduct": subproduct,
        "values": [matrix[subproduct].get(weight) or "" for weight in weights],
    } for subproduct in visible_subproducts]

    return {"weights": weights, "rows": report_rows}


@api_view(["GET"])
def ownerHandChainStockReportData(request):
    payload = ReportPayloadSerializer({
        "report": "ownerHandChainStockReport",
        "data": get_owner_hand_chain_stock_report_data(),
    })
    return Response(payload.data)

def get_chain_stock_data(db_prefix, tagchk_condition):
    query = f"""
        SELECT c.SubProName, a.GrossWt
        FROM {db_prefix}2627.dbo.TagReceipt a
        JOIN {db_prefix}Master.dbo.SubProduct c ON a.SubCode = c.SubCode
        JOIN {db_prefix}Master.dbo.Product b ON a.ProCode = b.ProCode
        WHERE a.IssueType = ''
          AND a.TagChkDate {tagchk_condition}
          AND b.ProName = 'CHAIN';
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()  # (SubProName, GrossWt)

def trayAndOwnerChainStockReportOg(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    formatted_time = datetime.now(indian_zone).strftime("%d-%m-%Y %I.%M%p")

    # ---- FETCH DATA ----
    tray_rows = (
        get_chain_stock_data("GPCJ", "IS NOT NULL") +
        get_chain_stock_data("TKGJ", "IS NOT NULL")
    )

    owner_rows = (
        get_chain_stock_data("GPCJ", "IS NULL") +
        get_chain_stock_data("TKGJ", "IS NULL")
    )

    # ---- UNIQUE GROSS WEIGHTS ----
    all_weights = set()
    for _, wt in tray_rows + owner_rows:
        if wt and str(wt).replace('.', '', 1).isdigit():
            all_weights.add(round_to_even(float(wt)))

    unique_grswts = sorted(all_weights)

    # ---- MATRIX ----
    matrix = defaultdict(lambda: defaultdict(lambda: {"tray": 0, "owner": 0}))

    for sub, wt in tray_rows:
        if wt and str(wt).replace('.', '', 1).isdigit():
            matrix[sub][round_to_even(float(wt))]["tray"] += 1

    for sub, wt in owner_rows:
        if wt and str(wt).replace('.', '', 1).isdigit():
            matrix[sub][round_to_even(float(wt))]["owner"] += 1

    excluded_subproducts = {
        "SORAI", "PLAIN MUGAPU", "STONE MUGAPU", "CASTING MUGAPU"
    }

    unique_subproducts = sorted(set(matrix.keys()) - excluded_subproducts)

    # ---- ROW GRAND TOTALS ----
    row_grand_totals = {}
    for sub, wt_data in matrix.items():
        row_grand_totals[sub] = sum(
            counts["tray"] + counts["owner"]
            for counts in wt_data.values()
        )

    # ---- COLUMN TOTALS ----
    column_totals = defaultdict(lambda: {"tray": 0, "owner": 0, "total": 0})
    overall_grand_total = 0

    for sub, wt_data in matrix.items():
        for wt, counts in wt_data.items():
            tray = counts["tray"]
            owner = counts["owner"]
            total = tray + owner

            column_totals[wt]["tray"] += tray
            column_totals[wt]["owner"] += owner
            column_totals[wt]["total"] += total

            overall_grand_total += total

    return render(request, "trayAndOwnerChainStockReport.html", {
        "currentDateTime": formatted_time,
        "uniqueSubProducts": unique_subproducts,
        "uniqueGrsWt": unique_grswts,
        "matrix": matrix,
        "rowGrandTotals": row_grand_totals,
        "columnTotals": column_totals,
        "overallGrandTotal": overall_grand_total,
    })

def trayAndOwnerChainStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    formatted_time = datetime.now(indian_zone).strftime("%d-%m-%Y %I.%M%p")

    # ---------------- FETCH DATA ----------------
    tray_rows = (
        get_chain_stock_data("GPCJ", "IS NOT NULL") +
        get_chain_stock_data("TKGJ", "IS NOT NULL")
    )

    owner_rows = (
        get_chain_stock_data("GPCJ", "IS NULL") +
        get_chain_stock_data("TKGJ", "IS NULL")
    )

    # ---------------- UNIQUE WEIGHTS ----------------
    weights = set()
    for _, wt in tray_rows + owner_rows:
        if wt and str(wt).replace('.', '', 1).isdigit():
            weights.add(round_to_even(float(wt)))

    unique_grswts = sorted(weights)

    # ---------------- MATRIX ----------------
    matrix = defaultdict(lambda: defaultdict(lambda: {
        "sale": 0,
        "tray": 0,
        "owner": 0,
        "total": 0
    }))

    for sub, wt in tray_rows:
        if wt and str(wt).replace('.', '', 1).isdigit():
            matrix[sub][round_to_even(float(wt))]["tray"] += 1

    for sub, wt in owner_rows:
        if wt and str(wt).replace('.', '', 1).isdigit():
            matrix[sub][round_to_even(float(wt))]["owner"] += 1

    # ---------------- EXCLUDE SUB PRODUCTS ----------------
    excluded = {"SORAI", "PLAIN MUGAPU", "STONE MUGAPU", "CASTING MUGAPU"}
    unique_subproducts = sorted(set(matrix.keys()) - excluded)

    # ---------------- ROW TOTALS ----------------
    row_grand_totals = {}
    for sub in unique_subproducts:
        total = 0
        for wt in unique_grswts:
            cell = matrix[sub][wt]
            cell["total"] = cell["tray"] + cell["owner"]
            total += cell["total"]
        row_grand_totals[sub] = total

    # ---------------- COLUMN TOTALS ----------------
    column_totals = defaultdict(lambda: {
        "sale": 0,
        "tray": 0,
        "owner": 0,
        "total": 0
    })

    overall_grand_total = 0

    for sub in unique_subproducts:
        for wt in unique_grswts:
            cell = matrix[sub][wt]
            column_totals[wt]["tray"] += cell["tray"]
            column_totals[wt]["owner"] += cell["owner"]
            column_totals[wt]["total"] += cell["total"]
            overall_grand_total += cell["total"]

    return render(request, "trayAndOwnerChainStockReport.html", {
        "currentDateTime": formatted_time,
        "uniqueSubProducts": unique_subproducts,
        "uniqueGrsWt": unique_grswts,
        "matrix": matrix,
        "rowGrandTotals": row_grand_totals,
        "columnTotals": column_totals,
        "overallGrandTotal": overall_grand_total,
    })

def dateAndSupplierWiseChainSaleReportOld(request):

    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    # ------------------ FILTERS ------------------
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    selected_supplier = request.GET.get('supplier')

    # ------------------ SALES ------------------
    sales_query = """
        SELECT
            CAST(a.TranDate AS DATE),
            d.DesignerName,
            b.ProName,
            c.SubProName,
            a.GrossWt,
            a.TagNo,
            a.Pieces
        FROM GPCJ2627.dbo.Sales a
        JOIN GPCJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN GPCJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        JOIN GPCJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode
        WHERE a.CanceledIp = '0' AND b.ProName = 'CHAIN'
    """

    params = []

    if start_date:
        sales_query += " AND CAST(a.TranDate AS DATE) >= %s"
        params.append(start_date)

    if end_date:
        sales_query += " AND CAST(a.TranDate AS DATE) <= %s"
        params.append(end_date)

    with connection.cursor() as cursor:
        cursor.execute(sales_query, params)
        sale_rows = cursor.fetchall()

    saleReport = [{
        "TranDate": r[0],
        "Supplier": r[1],
        "Product": r[2],
        "SubProduct": r[3],
        "GrossWt": r[4],
        "TagNo": r[5],
        "Pieces": r[6],
    } for r in sale_rows]

    # ------------------ TAG RECEIPT ------------------
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                TagNo,
                GrossWt,
                RefTagNo
            FROM GPCJ2627.dbo.TagReceipt
            WHERE IssueType != ''
        """)
        tag_rows = cursor.fetchall()

    tag_lookup = {
        r[0]: {"GrossWt": r[1], "RefTagNo": r[2]}
        for r in tag_rows
    }

    # ------------------ APPLY SAME LOGIC (ONE-TIME) ------------------
    properSaleReport = []

    for sale in saleReport:
        sale_tag = sale["TagNo"]

        if sale_tag in tag_lookup:
            ref_tag = tag_lookup[sale_tag]["RefTagNo"]

            if not ref_tag:
                properSaleReport.append(sale)

            elif ref_tag in tag_lookup:
                sale["TagNo"] = ref_tag
                sale["GrossWt"] = tag_lookup[ref_tag]["GrossWt"]
                properSaleReport.append(sale)
        else:
            properSaleReport.append(sale)

    # ------------------ REMOVE DUPLICATES ------------------
    unique_data = []
    seen = set()

    for d in properSaleReport:
        key = tuple(sorted(d.items()))
        if key not in seen:
            seen.add(key)
            unique_data.append(d)

    data = unique_data

    # ------------------ FILTER DROPDOWNS ------------------
    
    # Supplier depends ONLY on date range
    unique_suppliers = []
    if start_date and end_date:
        unique_suppliers = sorted(
            set(d["Supplier"] for d in data if d["Supplier"])
        )

    # ------------------ SHOW TABLE ------------------
    show_table = bool(start_date and end_date and selected_supplier)


    table_data = []
    unique_grswts = []

    if show_table:
        filtered = [
            d for d in data
            if (selected_supplier == "ALL" or d["Supplier"] == selected_supplier)
            and d["GrossWt"] not in (None, '')
            and str(d["GrossWt"]).replace('.', '', 1).isdigit()
        ]

        # ------------------ APPLY ROUNDING ------------------
        rounded_data = []
        for d in filtered:
            gw = float(d["GrossWt"])

            if d["Product"] == "CHAIN":
                rounded_gw = round_to_even(gw)
            else:
                rounded_gw = round_for_without_chain(gw)

            rounded_data.append({
                "SubProduct": d["SubProduct"],
                "GrossWt": rounded_gw,
                "Pieces": d["Pieces"] or 0
            })

        # ------------------ GROSS WT COLUMNS ------------------
        unique_grswts = sorted(set(d["GrossWt"] for d in rounded_data))

        # ------------------ MATRIX ------------------
        matrix = defaultdict(lambda: defaultdict(int))

        for d in rounded_data:
            matrix[d["SubProduct"]][d["GrossWt"]] += d["Pieces"]

        for sub, gw_data in matrix.items():
            row_values = [gw_data.get(gw, 0) for gw in unique_grswts]
            table_data.append({
                "sub": sub,
                "values": row_values,
                "total": sum(row_values)
            })

    # ------------------ TOTAL ROW ------------------
    total_row = None

    if show_table and table_data:
        col_totals = [0] * len(unique_grswts)
        grand_total = 0

        for row in table_data:
            for i, val in enumerate(row["values"]):
                col_totals[i] += val
                grand_total += val

        total_row = {
            "sub": "TOTAL",
            "values": col_totals,
            "total": grand_total
        }

    # ------------------ RENDER ------------------
    return render(request, 'dateAndSupplierWiseChainSaleReport.html', {
        'currentDateTime': formatted_time,
        'uniqueSuppliers': unique_suppliers,
        'uniqueGrsWt': unique_grswts,
        'selectedSupplier': selected_supplier,
        'startDate': start_date,
        'endDate': end_date,
        'tableData': table_data,
        'showTable': show_table,
        'totalRow': total_row,
    })

def chainSizeReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    queryGPC = """
        SELECT c.SubProName, a.GrossWt
        FROM GPCJ2627.dbo.TagReceipt a
        JOIN GPCJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN GPCJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='' AND b.ProName='CHAIN' AND (c.SubProName LIKE '18"%' OR c.SubProName LIKE '20"%' OR c.SubProName LIKE '23"%');
    """

    queryTKG = """
        SELECT c.SubProName, a.GrossWt
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='' AND b.ProName='CHAIN' AND (c.SubProName LIKE '18"%' OR c.SubProName LIKE '20"%' OR c.SubProName LIKE '23"%');
    """

    with connection.cursor() as cursor:
        cursor.execute(queryGPC)
        rows = cursor.fetchall()
    columnsGPC = ["SubProName", "GrossWt"]
    dataGPC = [dict(zip(columnsGPC, row)) for row in rows]

    with connection.cursor() as cursor:
        cursor.execute(queryTKG)
        rows = cursor.fetchall()
    columnsTKG = ["SubProName", "GrossWt"]
    dataTKG = [dict(zip(columnsTKG, row)) for row in rows]

    data = dataGPC + dataTKG

    # ---------- Process & Clean Data ----------
    processed_data = []

    for item in data:
        full_name = item["SubProName"].strip()

        # Extract size + name (handles: 23", 23", 23 , 23MUGAPU etc.)
        match = re.match(r'^(\d+)"?\s*(.*)', full_name)

        if match:
            size = match.group(1)
            name = match.group(2).strip()
        else:
            size = ""
            name = full_name

        # Apply rounding
        original_weight = float(item["GrossWt"])
        rounded_weight = round_to_even(original_weight)

        processed_data.append({
            "SubProName": name,
            "Size": size,
            "GrossWt": rounded_weight
        })

    # ---------- Group by (SubProduct, Size) ----------
    grouped = defaultdict(list)

    for item in processed_data:
        key = (item["SubProName"], item["Size"])
        grouped[key].append(item["GrossWt"])

    final_data = []

    for (name, size), weights in grouped.items():

        # Remove duplicates and sort ascending
        unique_sorted_weights = sorted(set(weights))

        final_data.append({
            "SubProName": name,
            "Size": size,
            # Multi-line format instead of comma separated
            "GrossWt": unique_sorted_weights
        })


    # Optional: sort by Size then SubProduct
    final_data = sorted(final_data, key=lambda x: (x["Size"], x["SubProName"]))

    return render(request, 'chainSizeReport.html', {
        'currentDateTime': formatted_time,
        'rows': final_data,
    })

def dateAndSupplierWiseChainSaleReport(request):

    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    # ------------------ FILTERS ------------------

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    selected_supplier = request.GET.get('supplier')

    params = []

    # ================== GPC SALES ==================

    sales_query_gpc = """
        SELECT
            CAST(a.TranDate AS DATE),
            d.DesignerName,
            b.ProName,
            c.SubProName,
            a.GrossWt,
            a.TagNo,
            a.Pieces
        FROM GPCJ2627.dbo.Sales a
        JOIN GPCJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN GPCJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        JOIN GPCJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode
        WHERE a.CanceledIp = '0' AND b.ProName = 'CHAIN'
    """

    # ================== TKG SALES ==================

    sales_query_tkg = """
        SELECT
            CAST(a.TranDate AS DATE),
            d.DesignerName,
            b.ProName,
            c.SubProName,
            a.GrossWt,
            a.TagNo,
            a.Pieces
        FROM TKGJ2627.dbo.Sales a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        JOIN TKGJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode
        WHERE a.CanceledIp = '0' AND b.ProName = 'CHAIN'
    """

    if start_date:
        sales_query_gpc += " AND CAST(a.TranDate AS DATE) >= %s"
        sales_query_tkg += " AND CAST(a.TranDate AS DATE) >= %s"
        params.append(start_date)

    if end_date:
        sales_query_gpc += " AND CAST(a.TranDate AS DATE) <= %s"
        sales_query_tkg += " AND CAST(a.TranDate AS DATE) <= %s"
        params.append(end_date)

    # Execute GPC
    with connection.cursor() as cursor:
        cursor.execute(sales_query_gpc, params)
        gpc_rows = cursor.fetchall()

    # Execute TKG
    with connection.cursor() as cursor:
        cursor.execute(sales_query_tkg, params)
        tkg_rows = cursor.fetchall()

    # Combine rows
    all_rows = gpc_rows + tkg_rows

    saleReport = [{
        "TranDate": r[0],
        "Supplier": r[1],
        "Product": r[2],
        "SubProduct": r[3],
        "GrossWt": r[4],
        "TagNo": r[5],
        "Pieces": r[6],
    } for r in all_rows]

    # ================== TAG RECEIPT (GPC + TKG) ==================

    tag_lookup = {}

    # GPC TagReceipt
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT TagNo, GrossWt, RefTagNo
            FROM GPCJ2627.dbo.TagReceipt
            WHERE IssueType != ''
        """)
        for r in cursor.fetchall():
            tag_lookup[r[0]] = {"GrossWt": r[1], "RefTagNo": r[2]}

    # TKG TagReceipt
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT TagNo, GrossWt, RefTagNo
            FROM TKGJ2627.dbo.TagReceipt
            WHERE IssueType != ''
        """)
        for r in cursor.fetchall():
            tag_lookup[r[0]] = {"GrossWt": r[1], "RefTagNo": r[2]}

    # ================== APPLY TAG LOGIC ==================

    properSaleReport = []

    for sale in saleReport:
        sale_tag = sale["TagNo"]

        if sale_tag in tag_lookup:
            ref_tag = tag_lookup[sale_tag]["RefTagNo"]

            if not ref_tag:
                properSaleReport.append(sale)

            elif ref_tag in tag_lookup:
                sale["TagNo"] = ref_tag
                sale["GrossWt"] = tag_lookup[ref_tag]["GrossWt"]
                properSaleReport.append(sale)
        else:
            properSaleReport.append(sale)

    # ================== REMOVE DUPLICATES ==================

    unique_data = []
    seen = set()

    for d in properSaleReport:
        key = tuple(sorted(d.items()))
        if key not in seen:
            seen.add(key)
            unique_data.append(d)

    data = unique_data

    # ================== SUPPLIER DROPDOWN ==================

    unique_suppliers = []
    if start_date and end_date:
        unique_suppliers = sorted(
            set(d["Supplier"] for d in data if d["Supplier"])
        )

    # ================== SHOW TABLE ==================

    show_table = bool(start_date and end_date and selected_supplier)

    table_data = []
    unique_grswts = []
    total_row = None

    if show_table:

        filtered = [
            d for d in data
            if (selected_supplier == "ALL" or d["Supplier"] == selected_supplier)
            and d["GrossWt"] not in (None, '')
            and str(d["GrossWt"]).replace('.', '', 1).isdigit()
        ]

        rounded_data = []
        for d in filtered:
            gw = float(d["GrossWt"])
            rounded_gw = round_to_even(gw)

            rounded_data.append({
                "SubProduct": d["SubProduct"],
                "GrossWt": rounded_gw,
                "Pieces": d["Pieces"] or 0
            })

        unique_grswts = sorted(set(d["GrossWt"] for d in rounded_data))

        matrix = defaultdict(lambda: defaultdict(int))

        for d in rounded_data:
            matrix[d["SubProduct"]][d["GrossWt"]] += d["Pieces"]

        for sub, gw_data in matrix.items():
            row_values = [gw_data.get(gw, 0) for gw in unique_grswts]

            table_data.append({
                "sub": sub,
                "values": row_values,
                "total": sum(row_values)
            })

        if table_data:
            col_totals = [0] * len(unique_grswts)
            grand_total = 0

            for row in table_data:
                for i, val in enumerate(row["values"]):
                    col_totals[i] += val
                    grand_total += val

            total_row = {
                "sub": "TOTAL",
                "values": col_totals,
                "total": grand_total
            }

    return render(request, 'dateAndSupplierWiseChainSaleReport.html', {
        'currentDateTime': formatted_time,
        'uniqueSuppliers': unique_suppliers,
        'uniqueGrsWt': unique_grswts,
        'selectedSupplier': selected_supplier,
        'startDate': start_date,
        'endDate': end_date,
        'tableData': table_data,
        'showTable': show_table,
        'totalRow': total_row,
    })



# ------------------------------ Ornament Purity ------------------------------
def _require_purity_session(request):
    if not request.session.get("username"):
        return Response({"detail": "Authentication required."}, status=401)
    return None


def login_view(request):
    next_url = request.POST.get("next") or request.GET.get("next", "")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        query = """
        SELECT * FROM CustomReport.dbo.LoginTable
        WHERE LoginUserName = %s AND LoginPassWord = %s
        """

        with connection.cursor() as cursor:
            cursor.execute(query, [username, password])
            user = cursor.fetchone()

        if user:
            # Store session
            request.session['username'] = username
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('ornamentPurityFormReport')
        else:
            return render(request, "login.html", {"error": "Invalid credentials", "next": next_url})

    return render(request, "login.html", {"next": next_url})

def logout_view(request):
    request.session.flush()
    return redirect('/login/')


def ornamentWastageMaster(request):

    # 🔒 Check session
    if not request.session.get('username'):
        return redirect_to_login(request.get_full_path(), login_url=reverse('login'))
    
    with connection.cursor() as cursor:
        cursor.execute("""SELECT * FROM CustomReport.dbo.OrnamentWastageMaster;""")
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    data = [dict(zip(columns, row)) for row in rows]

    designers = sorted({d["DesignerName"] for d in data if d.get("DesignerName")})

    return render(request, "ornamentWastageMaster.html", {
        "cursor": cursor,
        "datas": data,
        "designers": designers,
    })

# AJAX → Save purity data
@api_view(["POST"])
@csrf_protect
def addOrnamentWastageMaster(request):
    auth_error = _require_purity_session(request)
    if auth_error:
        return auth_error

    if request.method == "POST":

        DesignerName = request.POST.get("DesignerName")
        ProductName = request.POST.get("ProductName")
        OrnamentName = request.POST.get("OrnamentName")
        FromGrossWt = request.POST.get("FromGrossWt")
        ToGrossWt = request.POST.get("ToGrossWt")
        WastagePercent = request.POST.get("WastagePercent")
        WastageGram = request.POST.get("WastageGram")
        MakingCharge = request.POST.get("MakingCharge")

        try:
            from_weight = float(FromGrossWt)
            to_weight = float(ToGrossWt)
        except (TypeError, ValueError):
            return Response({"error": "Enter valid from and to gross weights"}, status=400)
        if from_weight < 0 or to_weight < from_weight:
            return Response({"error": "From Gross Weight must be non-negative and no greater than To Gross Weight"}, status=400)

        query = """
        INSERT INTO CustomReport.dbo.OrnamentWastageMaster
        (DesignerName, ProductName, OrnamentName, FromGrossWt, ToGrossWt,
         WastagePercentageValue, WastageGramValue, MakingCharge)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """

        with connection.cursor() as cursor:
            cursor.execute(query, [
                DesignerName,
                ProductName,
                OrnamentName,
                from_weight,
                to_weight,
                WastagePercent if WastagePercent else None,
                WastageGram if WastageGram else None,
                MakingCharge if MakingCharge else None
            ])

        return Response({"status": "success"})

@api_view(["POST"])
@csrf_protect
def updateOrnamentWastageMaster(request):
    auth_error = _require_purity_session(request)
    if auth_error:
        return auth_error

    try:
        wastage_id = int(request.POST.get("WastageID"))
        from_weight = float(request.POST.get("FromGrossWt"))
        to_weight = float(request.POST.get("ToGrossWt"))
    except (TypeError, ValueError):
        return Response({"error": "Enter a valid row ID and gross-weight range"}, status=400)

    if from_weight < 0 or to_weight < from_weight:
        return Response({"error": "From Gross Weight must be non-negative and no greater than To Gross Weight"}, status=400)

    query = """
        UPDATE CustomReport.dbo.OrnamentWastageMaster
        SET DesignerName = %s,
            ProductName = %s,
            OrnamentName = %s,
            FromGrossWt = %s,
            ToGrossWt = %s,
            WastagePercentageValue = %s,
            WastageGramValue = %s,
            MakingCharge = %s
        WHERE WastageID = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [
            request.POST.get("DesignerName"),
            request.POST.get("ProductName"),
            request.POST.get("OrnamentName"),
            from_weight,
            to_weight,
            request.POST.get("WastagePercent") or None,
            request.POST.get("WastageGram") or None,
            request.POST.get("MakingCharge") or None,
            wastage_id,
        ])
        if cursor.rowcount == 0:
            return Response({"error": "Wastage record was not found"}, status=404)

    return Response({"status": "success"})

@api_view(["POST"])
@csrf_protect
def deleteOrnamentWastageMaster(request):
    auth_error = _require_purity_session(request)
    if auth_error:
        return auth_error

    try:
        wastage_id = int(request.data.get("WastageID"))
    except (TypeError, ValueError):
        return Response({"error": "A valid wastage record ID is required"}, status=400)

    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM CustomReport.dbo.OrnamentWastageMaster WHERE WastageID = %s",
            [wastage_id],
        )
        if cursor.rowcount == 0:
            return Response({"error": "Wastage record was not found"}, status=404)

    return Response({"status": "success"})
    
def ornamentPurityFormReport(request):

    # 🔒 Check session
    if not request.session.get('username'):
        return redirect_to_login(request.get_full_path(), login_url=reverse('login'))

    # Fetch designer and ornament master data
    query1 = """
        SELECT DesignerName, ProductName, OrnamentName, FromGrossWt, ToGrossWt,
               WastagePercentageValue, WastageGramValue
        FROM CustomReport.dbo.OrnamentWastageMaster
    """

    with connection.cursor() as cursor:
        cursor.execute(query1)
        rows = cursor.fetchall()

    data1 = []
    for row in rows:
        data1.append({
            "DesignerName": row[0],
            "ProductName": row[1],
            "OrnamentName": row[2],
            "FromGrossWt": row[3],
            "ToGrossWt": row[4],
            "WastagePercentageValue": row[5],
            "WastageGramValue": row[6],
        })

    # Fetch saved purity records
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM CustomReport.dbo.OrnamentPurity")
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    data2 = [dict(zip(columns, row)) for row in rows]

    designers = sorted({d["DesignerName"] for d in data1})

    products = sorted({d["ProductName"] for d in data1})

    context = {
        "datas": data2,
        "designers": designers,
        "products": products
    }

    return render(request, "ornamentPurityFormReport.html", context)

# AJAX → Get products based on Designer
@api_view(["GET"])
def get_products(request):
    auth_error = _require_purity_session(request)
    if auth_error:
        return auth_error

    designer = request.query_params.get("designer")

    query = """
        SELECT DISTINCT ProductName
        FROM CustomReport.dbo.OrnamentWastageMaster
        WHERE DesignerName = %s
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [designer])
        rows = cursor.fetchall()

    products = [row[0] for row in rows]

    return Response({"products": products})

# AJAX → Get ornaments based on Designer + Product
@api_view(["GET"])
def get_ornaments(request):
    auth_error = _require_purity_session(request)
    if auth_error:
        return auth_error

    designer = request.query_params.get("designer")
    product = request.query_params.get("product")

    query = """
        SELECT DISTINCT OrnamentName
        FROM CustomReport.dbo.OrnamentWastageMaster
        WHERE DesignerName = %s AND ProductName = %s
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [designer, product])
        rows = cursor.fetchall()

    ornaments = [row[0] for row in rows]

    return Response({"ornaments": ornaments})

@api_view(["POST"])
@csrf_protect
def deleteOrnamentPurity(request):
    auth_error = _require_purity_session(request)
    if auth_error:
        return auth_error

    if request.method == "POST":

        processing_date = request.data.get("date")
        processing_time = request.data.get("time")

        query = """
        DELETE FROM CustomReport.dbo.OrnamentPurity
        WHERE ProcessingDate = %s
        AND ProcessingTime = %s
        """

        with connection.cursor() as cursor:
            cursor.execute(query, [processing_date, processing_time])

        return Response({"status": "success"})

# AJAX → Save purity data
@api_view(["POST"])
@csrf_protect
def submitOrnamentPurityForm(request):
    auth_error = _require_purity_session(request)
    if auth_error:
        return auth_error

    if request.method == "POST":

        DesignerName = request.data.get("DesignerName")
        ProductName = request.data.get("ProductName")
        OrnamentName = request.data.get("OrnamentName")
        Pieces = int(request.data.get("Pieces"))
        GrossWt = float(request.data.get("GrossWt"))
        ReceiptPurity = float(request.data.get("ReceiptPurity"))

        query = """
        SELECT TOP 1 FromGrossWt, ToGrossWt, WastagePercentageValue, WastageGramValue
        FROM CustomReport.dbo.OrnamentWastageMaster
        WHERE DesignerName = %s
        AND ProductName = %s
        AND OrnamentName = %s
        AND FromGrossWt <= %s
        AND ToGrossWt >= %s
        ORDER BY (ToGrossWt - FromGrossWt) ASC
        """

        with connection.cursor() as cursor:
            cursor.execute(query, [DesignerName, ProductName, OrnamentName, GrossWt, GrossWt])
            row = cursor.fetchone()

        if row is None:
            return Response({"error": "No wastage rule found"}, status=400)

        wastage_percent = row[2]
        wastage_gram = row[3]

        getcontext().prec = 3

        if (DesignerName == 'KOSALAM') and (ProductName == 'CHAIN'):
            if wastage_percent is None:
                print(float(wastage_gram))
                Weight = GrossWt + float(wastage_gram)
                Purity = round(Weight * 0.92, 3)
            else:
                Weight = GrossWt + (GrossWt * float(wastage_percent))
                Purity = round(Weight * 0.92, 3)
        else:
            Purity = round(GrossWt * float(wastage_percent), 3)

        print(Purity)

        # purity = Weight * 0.92

        if Purity != ReceiptPurity:
            status = "Unmatched"
        else:
            status = "Matched"

        processing_date = datetime.now().date()
        processing_time = datetime.now().time()

        insert_query = """
        INSERT INTO CustomReport.dbo.OrnamentPurity
        (ProcessingDate, ProcessingTime, DesignerName, ProductName, OrnamentName, Pieces, GrossWt, ReceiptPurity, Status, Purity)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        with connection.cursor() as cursor:
            cursor.execute(insert_query, [
                processing_date,
                processing_time,
                DesignerName,
                ProductName,
                OrnamentName,
                Pieces,
                GrossWt,
                ReceiptPurity,
                status,
                Purity
            ])

        return Response({"status": "success", "Purity": Purity})



# ------------------------------ Office Pages ------------------------------
def employeeTimeSheetApiAction(request):
    if request.method == "GET" and request.GET.get("action") == "lastUpdate":
        employee = (request.GET.get("employee") or "").strip()
        if not employee:
            return Response({"status": "invalid", "message": "Employee is required."}, status=400)

        with connections['custom_report'].cursor() as cursor:
            cursor.execute("""
                SELECT TOP 1 [Date], LeaveType, ToTime
                FROM CustomReport.dbo.TimeSheet
                WHERE Employee = %s
                ORDER BY [Date] DESC, ID DESC
            """, [employee])
            row = cursor.fetchone()

        if not row:
            return Response({"status": "empty"})

        last_date, leave_type, to_time = row
        return Response({
            "status": "success",
            "date": last_date.strftime("%d-%m-%Y") if hasattr(last_date, "strftime") else str(last_date),
            "leaveType": leave_type,
            "toTime": to_time.strftime("%H:%M") if hasattr(to_time, "strftime") else (str(to_time)[:5] if to_time else ""),
        })

    if request.method == "POST":
        date_value = request.POST.get("date", "").strip()
        employee = request.POST.get("employee", "").strip()
        leave_type = request.POST.get("leaveType", "").strip()
        work = request.POST.get("work", "").strip()
        from_time = request.POST.get("fromTime", "").strip()
        to_time = request.POST.get("toTime", "").strip()
        total_hours = request.POST.get("totalHours", "").strip()

        if not all((date_value, employee)) or leave_type not in {"None", "Half Day", "Full Day"}:
            return Response({"status": "invalid", "message": "Date, employee, and a valid leave type are required."}, status=400)

        try:
            sheet_date = datetime.strptime(date_value, "%Y-%m-%d").date()
            now_india = datetime.now(ZoneInfo("Asia/Kolkata"))
            if sheet_date > now_india.date():
                return Response({"status": "future"})
            if leave_type == "Full Day":
                from_time = to_time = None
                work = ""
                total_hours = "00:00"
            else:
                if leave_type == "Half Day":
                    work = ""
                start_time = datetime.strptime(from_time, "%H:%M").time()
                end_time = datetime.strptime(to_time, "%H:%M").time()
                datetime.strptime(total_hours, "%H:%M")
                if leave_type == "None" and not work:
                    raise ValueError
                end_datetime = datetime.combine(sheet_date, end_time)
                if end_time <= start_time:
                    end_datetime += timedelta(days=1)
                if end_datetime > now_india.replace(tzinfo=None):
                    return Response({"status": "future"})
        except ValueError:
            return Response({"status": "invalid", "message": "Enter valid date, times, and work description."}, status=400)

        with connections['custom_report'].cursor() as cursor:
            if from_time and to_time:
                cursor.execute("""
                    SELECT FromTime, ToTime
                    FROM CustomReport.dbo.TimeSheet
                    WHERE Employee = %s AND [Date] = %s
                      AND FromTime IS NOT NULL AND ToTime IS NOT NULL
                """, [employee, sheet_date])
                new_start = start_time.hour * 60 + start_time.minute
                new_end = end_time.hour * 60 + end_time.minute
                if new_end <= new_start:
                    new_end += 24 * 60
                for existing_start, existing_end in cursor.fetchall():
                    old_start = existing_start.hour * 60 + existing_start.minute
                    old_end = existing_end.hour * 60 + existing_end.minute
                    if old_end <= old_start:
                        old_end += 24 * 60
                    if new_start < old_end and old_start < new_end:
                        return Response({"status": "overlap"})

            cursor.execute("""
                INSERT INTO CustomReport.dbo.TimeSheet
                    ([Date], Employee, LeaveType, WorkDescription, FromTime, ToTime, TotalHours, CreatedAt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, GETDATE())
            """, [sheet_date, employee, leave_type, work, from_time, to_time, total_hours])

        return Response({"status": "success"})

    return Response({"status": "invalid", "message": "Unsupported request."}, status=400)

def adminTimeSheetApiAction(request):
    if request.method == "POST" and request.POST.get("action") == "delete":
        entry_id = request.POST.get("id", "").strip()
        if not entry_id.isdigit():
            return Response({"status": "invalid", "message": "A valid record ID is required."}, status=400)

        with connections['custom_report'].cursor() as cursor:
            cursor.execute(
                "DELETE FROM CustomReport.dbo.TimeSheet WHERE ID = %s",
                [int(entry_id)],
            )
            if cursor.rowcount == 0:
                return Response({"status": "not_found", "message": "Timesheet entry was not found."}, status=404)

        return Response({"status": "success"})

    if request.method == "POST" and request.POST.get("action") == "update":
        entry_id = request.POST.get("id", "").strip()
        date_value = request.POST.get("date", "").strip()
        employee = request.POST.get("employee", "").strip()
        leave_type = request.POST.get("leaveType", "").strip()
        work = request.POST.get("work", "").strip()
        from_time = request.POST.get("fromTime", "").strip()
        to_time = request.POST.get("toTime", "").strip()

        if not entry_id.isdigit() or not date_value or not employee or leave_type not in {"None", "Half Day", "Full Day"}:
            return Response({"status": "invalid", "message": "Date, employee, leave type, and record ID are required."}, status=400)

        try:
            sheet_date = datetime.strptime(date_value, "%Y-%m-%d").date()
            if from_time or to_time:
                if not from_time or not to_time:
                    raise ValueError
                start_time = datetime.strptime(from_time, "%H:%M").time()
                end_time = datetime.strptime(to_time, "%H:%M").time()
                start_minutes = start_time.hour * 60 + start_time.minute
                end_minutes = end_time.hour * 60 + end_time.minute
                if end_minutes <= start_minutes:
                    end_minutes += 24 * 60
                duration = end_minutes - start_minutes
                total_hours = f"{duration // 60:02d}:{duration % 60:02d}"
            else:
                from_time = to_time = None
                total_hours = "00:00"
        except ValueError:
            return Response({"status": "invalid", "message": "Enter valid date, times, and work description."}, status=400)

        with connections['custom_report'].cursor() as cursor:
            cursor.execute("""
                SELECT FromTime, ToTime
                FROM CustomReport.dbo.TimeSheet
                WHERE Employee = %s AND [Date] = %s AND ID <> %s
                  AND FromTime IS NOT NULL AND ToTime IS NOT NULL
            """, [employee, sheet_date, int(entry_id)])
            if from_time and to_time:
                new_start = start_time.hour * 60 + start_time.minute
                new_end = end_time.hour * 60 + end_time.minute
                if new_end <= new_start:
                    new_end += 24 * 60
                for existing_start, existing_end in cursor.fetchall():
                    old_start = existing_start.hour * 60 + existing_start.minute
                    old_end = existing_end.hour * 60 + existing_end.minute
                    if old_end <= old_start:
                        old_end += 24 * 60
                    if new_start < old_end and old_start < new_end:
                        return Response({"status": "overlap"})

            cursor.execute("""
                UPDATE CustomReport.dbo.TimeSheet
                SET [Date] = %s, Employee = %s, LeaveType = %s,
                    WorkDescription = %s, FromTime = %s, ToTime = %s, TotalHours = %s
                WHERE ID = %s
            """, [sheet_date, employee, leave_type, work, from_time, to_time, total_hours, int(entry_id)])
            if cursor.rowcount == 0:
                return Response({"status": "not_found", "message": "Timesheet entry was not found."}, status=404)

        return Response({"status": "success"})

    if request.method == "GET" and request.GET.get("action") == "getData":
        from_date = request.GET.get("fromDate", "").strip()
        to_date = request.GET.get("toDate", "").strip()
        employee = request.GET.get("employee", "").strip()
        try:
            start_date = datetime.strptime(from_date, "%Y-%m-%d").date() if from_date else None
            end_date = datetime.strptime(to_date, "%Y-%m-%d").date() if to_date else None
        except ValueError:
            return Response({"status": "invalid", "data": []}, status=400)
        if start_date and end_date and start_date > end_date:
            return Response({"status": "invalid", "data": []}, status=400)

        conditions = []
        params = []
        if start_date:
            conditions.append("[Date] >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("[Date] <= %s")
            params.append(end_date)
        if employee:
            conditions.append("Employee = %s")
            params.append(employee)
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        with connections['custom_report'].cursor() as cursor:
            cursor.execute(f"""
                SELECT ID, [Date], Employee, LeaveType, WorkDescription, FromTime, ToTime, TotalHours
                FROM CustomReport.dbo.TimeSheet
                {where_clause}
                ORDER BY [Date], ID
            """, params)
            rows = cursor.fetchall()

        data = [{
            "id": row[0],
            "date": row[1].strftime("%d-%m-%Y") if hasattr(row[1], "strftime") else str(row[1]),
            "isoDate": row[1].strftime("%Y-%m-%d") if hasattr(row[1], "strftime") else str(row[1]),
            "employee": row[2] or "",
            "leaveType": row[3] or "",
            "work": row[4] or "",
            "fromTime": row[5].strftime("%H:%M") if hasattr(row[5], "strftime") else (str(row[5])[:5] if row[5] else ""),
            "toTime": row[6].strftime("%H:%M") if hasattr(row[6], "strftime") else (str(row[6])[:5] if row[6] else ""),
            "totalHours": row[7] or "00:00",
        } for row in rows]
        return Response({"status": "success", "data": data})

    return Response({"status": "invalid", "message": "Unsupported request."}, status=400)

def goldEstimateForm(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    return render(request, 'goldEstimateForm.html', {
        'currentDateTime': formatted_time,
    })

def silverEstimateForm(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    return render(request, 'silverEstimateForm.html', {
        'currentDateTime': formatted_time,
    })


def goldEstimateReport(request):
    columns = [
        {"label": "Date", "key": "date"}, {"label": "Time", "key": "time"},
        {"label": "K Pad No.", "key": "kPadNo"}, {"label": "Item", "key": "item"},
        {"label": "Product Weight", "key": "productWeight"},
        {"label": "Owner Less Wastage (%)", "key": "ownerLessWastage"},
        {"label": "Owner Less Amount Deduction", "key": "ownerLessAmountDeduction"},
        {"label": "Gold Rate", "key": "goldRate"},
        {"label": "Invoice Amount", "key": "invoiceAmount"}, {"label": "GST", "key": "gst"},
        {"label": "R Amount", "key": "rAmount"}, {"label": "Old Gold Payment", "key": "oldGoldPayment"},
        {"label": "Cash Received", "key": "cashReceived"}, {"label": "GPay / Card / NEFT", "key": "digitalPayment"},
        {"label": "Chit Amount", "key": "chitAmount"}, {"label": "Old Ornament (g)", "key": "oldOrnament"},
        {"label": "Old K Dye (g)", "key": "oldKDye"}, {"label": "Old Other Dye (g)", "key": "oldOtherDye"},
        {"label": "Old Value", "key": "oldValue"}, {"label": "Balance Paid", "key": "balancePaid"}, 
        {"label": "Less Amount", "key": "lessAmount"},
        {"label": "Owner Less Amount", "key": "ownerLessAmount"},
        {"label": "Owner Less Difference", "key": "ownerLessDifference", "format": "signedDifference"},
        {"label": "Remarks", "key": "remarks"},
        {"label": "Action", "key": "actions"},
    ]
    item_choices = [
        "Bangle", "Bracelet", "Chain", "Coin", "Dollar", "Ring", "Thalimani",
        "Neclace", "Nanal", "Haram", "Stud", "Pesary", "Extra", "Others",
    ]
    edit_fields = [
        {"label": "Date", "key": "date", "type": "date"},
        {"label": "Time", "key": "time", "type": "time", "step": "1"},
        {"label": "K Pad No.", "key": "kPadNo", "type": "text"},
        {"label": "Item", "key": "item", "type": "select", "options": item_choices},
        {"label": "Product Weight", "key": "productWeight", "type": "number", "step": "0.001"},
        {"label": "Owner Less Wastage (%)", "key": "ownerLessWastage", "type": "number", "step": "0.0001"},
        {"label": "Owner Less Amount Deduction", "key": "ownerLessAmountDeduction", "type": "number", "step": "0.01"},
        {"label": "Gold Rate", "key": "goldRate", "type": "number", "step": "0.01"},
        {"label": "Invoice Amount", "key": "invoiceAmount", "type": "number", "step": "0.01"},
        {"label": "GST", "key": "gst", "type": "number", "step": "0.01"},
        {"label": "R Amount", "key": "rAmount", "type": "number", "step": "0.01"},
        {"label": "Old Gold Payment", "key": "oldGoldPayment", "type": "number", "step": "0.01"},
        {"label": "Cash Received", "key": "cashReceived", "type": "number", "step": "0.01"},
        {"label": "GPay / Card / NEFT", "key": "digitalPayment", "type": "number", "step": "0.01"},
        {"label": "Chit Amount", "key": "chitAmount", "type": "number", "step": "0.01"},
        {"label": "Old Ornament (g)", "key": "oldOrnament", "type": "number", "step": "0.001"},
        {"label": "Old K Dye (g)", "key": "oldKDye", "type": "number", "step": "0.001"},
        {"label": "Old Other Dye (g)", "key": "oldOtherDye", "type": "number", "step": "0.001"},
        {"label": "Old Value", "key": "oldValue", "type": "number", "step": "0.01"},
        {"label": "Remarks", "key": "remarks", "type": "text"},
    ]
    total_columns = [
        {"label": "R Amount", "key": "rAmount", "decimals": 2},
        {"label": "Old Gold Payment", "key": "oldGoldPayment", "decimals": 2},
        {"label": "GPay / Card / NEFT", "key": "digitalPayment", "decimals": 2},
        {"label": "Chit Amount", "key": "chitAmount", "decimals": 2},
        {"label": "Old Ornament (g)", "key": "oldOrnament", "decimals": 3},
        {"label": "Old K Dye (g)", "key": "oldKDye", "decimals": 3},
        {"label": "Old Other Dye (g)", "key": "oldOtherDye", "decimals": 3},
        {"label": "Old Value", "key": "oldValue", "decimals": 2},
    ]
    return render(request, "estimateReport.html", {
        "reportTitle": "Gold Estimate Report",
        "reportTheme": "gold",
        "apiUrl": reverse("goldEstimateCreateApi"),
        "columns": columns,
        "editFields": edit_fields,
        "totalColumns": total_columns,
    })


def silverEstimateReport(request):
    columns = [
        {"label": "Date", "key": "date"}, {"label": "Time", "key": "time"},
        {"label": "K Pad No.", "key": "kPadNo"}, {"label": "Net Value", "key": "netValue"},
        {"label": "Cash Received", "key": "cashReceived"}, {"label": "Old Silver Payment", "key": "oldSilverPayment"},
        {"label": "GPay / Card / NEFT", "key": "digitalPayment"}, {"label": "Chit Amount", "key": "chitAmount"},
        {"label": "K Sheet Weight (g)", "key": "kSheetWeight"}, {"label": "Physical Weight (g)", "key": "physicalWeight"},
        {"label": "Old Gold Value", "key": "oldGoldValue"}, {"label": "Balance Paid", "key": "balancePaid"},
        {"label": "Remarks", "key": "remarks"}, {"label": "Action", "key": "actions"},
    ]
    edit_fields = [
        {"label": "Date", "key": "date", "type": "date"},
        {"label": "Time", "key": "time", "type": "time", "step": "1"},
        {"label": "K Pad No.", "key": "kPadNo", "type": "text"},
        {"label": "Net Value", "key": "netValue", "type": "number", "step": "0.01"},
        {"label": "Cash Received", "key": "cashReceived", "type": "number", "step": "0.01"},
        {"label": "Old Silver Payment", "key": "oldSilverPayment", "type": "number", "step": "0.01"},
        {"label": "GPay / Card / NEFT", "key": "digitalPayment", "type": "number", "step": "0.01"},
        {"label": "Chit Amount", "key": "chitAmount", "type": "number", "step": "0.01"},
        {"label": "K Sheet Weight (g)", "key": "kSheetWeight", "type": "number", "step": "0.001"},
        {"label": "Physical Weight (g)", "key": "physicalWeight", "type": "number", "step": "0.001"},
        {"label": "Old Gold Value", "key": "oldGoldValue", "type": "number", "step": "0.01"},
        {"label": "Remarks", "key": "remarks", "type": "text"},
    ]
    total_columns = [
        {"label": "Net Value", "key": "netValue", "decimals": 2},
        {"label": "Old Silver Payment", "key": "oldSilverPayment", "decimals": 2},
        {"label": "GPay / Card / NEFT", "key": "digitalPayment", "decimals": 2},
        {"label": "K Sheet Weight", "key": "kSheetWeight", "decimals": 3},
        {"label": "Physical Weight", "key": "physicalWeight", "decimals": 3},
        {"label": "Old Gold Value", "key": "oldGoldValue", "decimals": 2},
        {"label": "Remarks (numeric only)", "key": "remarks", "decimals": 2, "numericOnly": True},
    ]
    return render(request, "estimateReport.html", {
        "reportTitle": "Silver Estimate Report",
        "reportTheme": "silver",
        "apiUrl": reverse("silverEstimateCreateApi"),
        "columns": columns,
        "editFields": edit_fields,
        "totalColumns": total_columns,
    })
