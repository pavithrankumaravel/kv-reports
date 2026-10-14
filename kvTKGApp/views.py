from kvReportsApp.api_utils import render
from django.db import connection
from collections import defaultdict
from .getFunction import round_to_even, round_for_without_chain
from datetime import datetime
from zoneinfo import ZoneInfo 

# Create your views here.

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ GPC Overall Report ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def tkgHome(request):
    return render(request, "TKG/tkgHome.html")

def tkgEntireStockReport(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                d.DesignerName, 
                e.VendorName, 
                b.ProName, 
                c.SubProName, 
                a.TagNo, 
                a.GrossWt, 
                a.Pieces, 
                a.TagChkDate,
                f.CounterName
            FROM TKGJ2627.dbo.TagReceipt a
            JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
            JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
            LEFT JOIN TKGJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode  -- Changed to LEFT JOIN
            JOIN TKGJMaster.dbo.VendorMaster e ON a.AcctCode = e.AcctCode
			JOIN GPCJMaster.dbo.ProductCounter f ON a.CounterCode = f.CounterCode
            WHERE a.IssueType = '';
        """)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    datas = [dict(zip(columns, row)) for row in rows]

    branch_counters = [
        'KV BRANCH CHAINS',
        'KV BRANCH HARAM',
        'KV BRANCH NECKLACE',
        'KV BRANCH BRACELET',
        'KV BRANCH RINGS',
        'KV BRANCH THALIMANI',
        'KV BRANCH DOLLAR',
        'KV BRANCH HOOK',
        'KV BRANCH DOLLAR COIN',
        'KV BRANCH BACKCHAIN',
        'KV BRANCH EXTRA CHAIN',
        'KV BRANCH NANAL',
    ]

    for data in datas:
        if data["TagChkDate"]:
            if data["CounterName"] in branch_counters:
                data["TrayType"] = "Branch Office Tray"
            else:
                data["TrayType"] = "Main Branch Tray"
        else:
            data["TrayType"] = "Owner's Hand"

    return render(request, "TKG/tkgEntireStockReport.html", {
        "datas": datas
    })

def tkgEntireSaleReport(request):

    # -------------------- SALES --------------------
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                a.TranDate,
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
            WHERE a.CanceledIp = '0'
        """)
        sale_cols = [col[0] for col in cursor.description]
        sale_rows = cursor.fetchall()

    saleReport = [dict(zip(sale_cols, row)) for row in sale_rows]


    # -------------------- TAG RECEIPT --------------------
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                TagNo,
                GrossWt,
                RefTagNo
            FROM TKGJ2627.dbo.TagReceipt
            WHERE IssueType != ''
        """)
        tag_cols = [col[0] for col in cursor.description]
        tag_rows = cursor.fetchall()

    tagReport = [dict(zip(tag_cols, row)) for row in tag_rows]

    # Lookup table (TagNo -> row)
    tag_lookup = {tag['TagNo']: tag for tag in tagReport}


    # -------------------- ONE-TIME MATCH LOGIC --------------------
    properSaleReport = []

    for sale in saleReport:
        sale_tag = sale['TagNo']

        if sale_tag in tag_lookup:
            ref_tag = tag_lookup[sale_tag]['RefTagNo']

            # CASE 1: RefTagNo EMPTY → keep original
            if not ref_tag:
                properSaleReport.append(sale)

            # CASE 2: RefTagNo exists → REPLACE ONCE
            elif ref_tag in tag_lookup:
                sale['TagNo'] = ref_tag
                sale['GrossWt'] = tag_lookup[ref_tag]['GrossWt']
                properSaleReport.append(sale)

        else:
            # Safety fallback
            properSaleReport.append(sale)

    uniqueProperSaleReport = []
    seen = set()

    for d in properSaleReport:
        t = tuple(sorted(d.items()))
        if t not in seen:
            seen.add(t)
            uniqueProperSaleReport.append(d)

    # -------------------- RENDER --------------------
    return render(
        request,
        "TKG/tkgEntireSaleReport.html",
        {
            "datas": uniqueProperSaleReport
        }
    )

def tkgChainStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    query = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='' AND b.ProName= 'CHAIN';
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    data = [
        {"ProName": row[0], "SubProName": row[1], "TagNo": row[2], "GrossWt": row[3], "Pieces": row[4]}
        for row in rows
    ]

    subproducts = sorted(set(d["SubProName"] for d in data))
    gross_weights = sorted(set(
        round_to_even(float(d["GrossWt"]))
        for d in data if d["GrossWt"] not in [None, ""]
    ))

    # Build report matrix
    report = defaultdict(lambda: {gw: 0 for gw in gross_weights})

    for d in data:
        sub = d["SubProName"]
        gw = d["GrossWt"]
        pcs = d["Pieces"]
        if gw not in [None, ""]:
            rounded_wt = round_to_even(float(gw))
            report[sub][rounded_wt] += pcs

    # ✅ Add totals
    row_totals = {sub: sum(report[sub].values()) for sub in subproducts}
    col_totals = {gw: sum(report[sub][gw] for sub in subproducts) for gw in gross_weights}
    grand_total = sum(row_totals.values())

    return render(request, "TKG/tkgChainStockReport.html", {
        'currentDateTime': formatted_time,
        "subproducts": subproducts,
        "gross_weights": gross_weights,
        "report": report,
        "row_totals": row_totals,
        "col_totals": col_totals,
        "grand_total": grand_total,
    })

def tkgMainChainStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    query = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces, d.CounterName
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        JOIN TKGJMaster.dbo.ProductCounter d ON a.CounterCode = d.CounterCode
        WHERE a.IssueType='' AND b.ProName='CHAIN' AND d.CounterName NOT IN ('KV BRANCH CHAIN', 'KV BRANCH HOOK', 'KV BRANCH BANGLES', 'KV BRANCH EXTRA CHAIN');
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    data = [
        {"ProName": row[0], "SubProName": row[1], "TagNo": row[2], "GrossWt": row[3], "Pieces": row[4]}
        for row in rows
    ]

    subproducts = sorted(set(d["SubProName"] for d in data))
    gross_weights = sorted(set(
        round_to_even(float(d["GrossWt"]))
        for d in data if d["GrossWt"] not in [None, ""]
    ))

    # Build report matrix
    report = defaultdict(lambda: {gw: 0 for gw in gross_weights})

    for d in data:
        sub = d["SubProName"]
        gw = d["GrossWt"]
        pcs = d["Pieces"]
        if gw not in [None, ""]:
            rounded_wt = round_to_even(float(gw))
            report[sub][rounded_wt] += pcs

    # ✅ Add totals
    row_totals = {sub: sum(report[sub].values()) for sub in subproducts}
    col_totals = {gw: sum(report[sub][gw] for sub in subproducts) for gw in gross_weights}
    grand_total = sum(row_totals.values())

    return render(request, "TKG/tkgMainChainStockReport.html", {
        'data': data,
        'currentDateTime': formatted_time,
        "subproducts": subproducts,
        "gross_weights": gross_weights,
        "report": report,
        "row_totals": row_totals,
        "col_totals": col_totals,
        "grand_total": grand_total,
    })

def tkgBranchChainStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    query = """
        SELECT 
            b.ProName, 
            c.SubProName, 
            a.TagNo, 
            a.GrossWt, 
            a.Pieces, 
            d.CounterName
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b 
            ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c 
            ON a.SubCode = c.SubCode
        JOIN TKGJMaster.dbo.ProductCounter d 
            ON a.CounterCode = d.CounterCode
        WHERE 
            a.IssueType = ''
            AND b.ProName = 'CHAIN'
            AND (
                d.CounterName IN (
                    'KV BRANCH CHAINS', 
                    'KV BRANCH HARAM', 
                    'KV BRANCH NECKLACE', 
                    'KV BRANCH BRACELET', 
                    'KV BRANCH RINGS', 
                    'KV BRANCH THALIMANI', 
                    'KV BRANCH DOLLAR', 
                    'KV BRANCH HOOK', 
                    'KV BRANCH DOLLAR COIN', 
                    'KV BRANCH BACKCHAIN', 
                    'KV BRANCH EXTRA CHAIN', 
                    'KV BRANCH NANAL'
                )
            );
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    data = [
        {"ProName": row[0], "SubProName": row[1], "TagNo": row[2], "GrossWt": row[3], "Pieces": row[4]}
        for row in rows
    ]

    subproducts = sorted(set(d["SubProName"] for d in data))
    gross_weights = sorted(set(
        round_to_even(float(d["GrossWt"]))
        for d in data if d["GrossWt"] not in [None, ""]
    ))

    # Build report matrix
    report = defaultdict(lambda: {gw: 0 for gw in gross_weights})

    for d in data:
        sub = d["SubProName"]
        gw = d["GrossWt"]
        pcs = d["Pieces"]
        if gw not in [None, ""]:
            rounded_wt = round_to_even(float(gw))
            report[sub][rounded_wt] += pcs

    # ✅ Add totals
    row_totals = {sub: sum(report[sub].values()) for sub in subproducts}
    col_totals = {gw: sum(report[sub][gw] for sub in subproducts) for gw in gross_weights}
    grand_total = sum(row_totals.values())

    return render(request, "TKG/tkgBranchChainStockReport.html", {
        'data': data,
        'currentDateTime': formatted_time,
        "subproducts": subproducts,
        "gross_weights": gross_weights,
        "report": report,
        "row_totals": row_totals,
        "col_totals": col_totals,
        "grand_total": grand_total,
    })

def tkgTrayChainStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    query = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='' AND a.TagChkDate IS NOT NULL AND b.ProName= 'CHAIN';
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    columns = ["ProName", "SubProName", "TagNo", "GrossWt", "Pieces"]
    data = [dict(zip(columns, row)) for row in rows]

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

    return render(request, 'TKG/tkgTrayChainStockReport.html', {
        'currentDateTime': formatted_time,
        'rows': data,
        'uniqueProducts': unique_products,
        'uniqueSubProducts': unique_subproducts,
        'uniqueGrsWt': unique_grswts,
        'matrix': matrix,
        'excludedSubProducts': excluded_subproducts,
    })

def tkgSupplierWiseSaleReport(request):

    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    # ------------------ FILTERS ------------------
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    selected_supplier = request.GET.get('supplier')
    selected_product = request.GET.get('product')

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
        FROM TKGJ2627.dbo.Sales a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        JOIN TKGJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode
        WHERE a.CanceledIp = '0'
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
            FROM TKGJ2627.dbo.TagReceipt
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
    unique_suppliers = sorted(set(d["Supplier"] for d in data if d["Supplier"]))

    unique_products = []
    if selected_supplier:
        unique_products = sorted(
            set(d["Product"] for d in data if d["Supplier"] == selected_supplier)
        )

    # ------------------ SHOW TABLE ------------------
    show_table = bool(start_date and end_date and selected_supplier and selected_product)

    table_data = []
    unique_grswts = []

    if show_table:
        filtered = [
            d for d in data
            if d["Supplier"] == selected_supplier
            and d["Product"] == selected_product
            and d["GrossWt"] not in (None, '')
            and str(d["GrossWt"]).replace('.', '', 1).isdigit()
        ]

        # ------------------ APPLY ROUNDING ------------------
        rounded_data = []
        for d in filtered:
            gw = float(d["GrossWt"])

            if selected_product == "CHAIN":
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
    return render(request, 'TKG/tkgSupplierWiseSaleReport.html', {
        'currentDateTime': formatted_time,
        'uniqueSuppliers': unique_suppliers,
        'uniqueProducts': unique_products,
        'uniqueGrsWt': unique_grswts,
        'selectedSupplier': selected_supplier,
        'selectedProduct': selected_product,
        'startDate': start_date,
        'endDate': end_date,
        'tableData': table_data,
        'showTable': show_table,
        'totalRow': total_row,
    })

def tkgDateAndSupplierWiseChainSaleReport(request):

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
        FROM TKGJ2627.dbo.Sales a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        JOIN TKGJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode
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
            FROM TKGJ2627.dbo.TagReceipt
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
    return render(request, 'TKG/tkgDateAndSupplierWiseChainSaleReport.html', {
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

def tkgProductWiseStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    selected_product = request.GET.get("product")

    query = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='';
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    data = [
        {
            "ProName": row[0],
            "SubProName": row[1],
            "TagNo": row[2],
            "GrossWt": row[3],
            "Pieces": row[4],
        }
        for row in rows
    ]

    # All unique products
    unique_products = sorted(set(d["ProName"] for d in data))

    # Apply filter if product is selected
    if selected_product:
        data = [d for d in data if d["ProName"] == selected_product]

    # Pivot-style report
    subproducts = sorted(set(d["SubProName"] for d in data))

    # Apply rounding function depending on product
    if selected_product == "CHAIN":
        gross_weights = sorted(set(
            round_to_even(float(d["GrossWt"]))
            for d in data if d["GrossWt"] not in [None, ""]
        ))
    else:
        gross_weights = sorted(set(
            round_for_without_chain(float(d["GrossWt"]))
            for d in data if d["GrossWt"] not in [None, ""]
        ))

    # Initialize matrix with rounded weights
    report = defaultdict(lambda: {gw: 0 for gw in gross_weights})

    # Fill the matrix
    for d in data:
        sub = d["SubProName"]
        gw = d["GrossWt"]
        pcs = d["Pieces"]

        if gw not in [None, ""]:
            if selected_product == "CHAIN":
                rounded_wt = round_to_even(float(gw))
            else:
                rounded_wt = round_for_without_chain(float(gw))

            report[sub][rounded_wt] += pcs

    # Totals
    row_totals = {sub: sum(report[sub].values()) for sub in subproducts}
    col_totals = {gw: sum(report[sub][gw] for sub in subproducts) for gw in gross_weights}
    grand_total = sum(row_totals.values())

    context = {
        'currentDateTime': formatted_time,
        "uniqueProducts": unique_products,
        "selectedProduct": selected_product,
        "subproducts": subproducts,
        "gross_weights": gross_weights,
        "report": report,
        "row_totals": row_totals,
        "col_totals": col_totals,
        "grand_total": grand_total,
    }

    return render(request, "TKG/tkgProductWiseStockReport.html", context)

def tkgProSubGrsWiseStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    # 🔹 Run SQL query instead of ORM
    query = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='';
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    # Convert rows to list of dicts
    data = [
        {
            "Product": row[0],
            "SubProduct": row[1],
            "TagNo": row[2],
            "GrsWt": row[3],
            "Pieces": row[4],
        }
        for row in rows
    ]

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

    return render(request, 'TKG/tkgProSubGrsWiseStockReport.html', {
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

def tkgSupProSubGrsWiseStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")
 
    # 🔹 SQL Query: Added Vendor Join
    query = """
        SELECT d.DesignerName, b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        JOIN TKGJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode
        WHERE a.IssueType='';
    """
 
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
 
    # 🔹 Convert SQL result into list of dicts
    data = [
        {
            "Supplier": row[0],
            "Product": row[1],
            "SubProduct": row[2],
            "TagNo": row[3],
            "GrsWt": row[4],
            "Pieces": row[5],
        }
        for row in rows
    ]
 
    # ✅ Read filters from request
    selected_supplier = request.GET.get('supplier')
    selected_product = request.GET.get('product')
    selected_subproduct = request.GET.get('subproduct')
    selected_grswt = request.GET.getlist('grswt')
 
    # 1) Unique suppliers (always available)
    unique_suppliers = sorted(set(d["Supplier"] for d in data if d["Supplier"]))
 
    # 2) Products must depend on selected supplier ONLY
    unique_products = []
    if selected_supplier:
        filtered_by_supplier = [d for d in data if d["Supplier"] == selected_supplier]
        unique_products = sorted(set(d["Product"] for d in filtered_by_supplier if d["Product"]))
 
    # 3) SubProducts depend on selected supplier AND selected product
    unique_subproducts = []
    if selected_supplier and selected_product:
        filtered_by_sup_prod = [
            d for d in data
            if d["Supplier"] == selected_supplier and d["Product"] == selected_product
        ]
        unique_subproducts = sorted(set(d["SubProduct"] for d in filtered_by_sup_prod if d["SubProduct"]))
 
    # 4) Gross weights depend on supplier + product + subproduct
    unique_grswts = []
    if selected_supplier and selected_product and selected_subproduct:
        filtered_for_grswt = [
            d for d in data
            if d["Supplier"] == selected_supplier and
               d["Product"] == selected_product and
               d["SubProduct"] == selected_subproduct and
               d["GrsWt"] not in [None, ''] and
               str(d["GrsWt"]).replace('.', '', 1).isdigit()
        ]
        if selected_product == "CHAIN":
            unique_grswts = sorted(set(round_to_even(float(d["GrsWt"])) for d in filtered_for_grswt))
        else:
            unique_grswts = sorted(set(round_for_without_chain(float(d["GrsWt"])) for d in filtered_for_grswt))
 
    # Show table only when all four filters applied
    show_table = bool(selected_supplier and selected_product and selected_subproduct and selected_grswt)
 
    table_data = []
    if show_table:
        # convert selected grswt values to floats for comparison
        try:
            selected_grswt_nums = [float(g) for g in selected_grswt]
        except ValueError:
            selected_grswt_nums = []
 
        matrix = defaultdict(lambda: defaultdict(int))
 
        for d in data:
            supplier = d["Supplier"]
            product = d["Product"]
            subproduct = d["SubProduct"]
            grswt = d["GrsWt"]
 
            if not (supplier and product and subproduct and grswt):
                continue
            if not str(grswt).replace('.', '', 1).isdigit():
                continue
 
            if product == "CHAIN":
                rounded_grswt = round_to_even(float(grswt))
            else:
                rounded_grswt = round_for_without_chain(float(grswt))
 
            if (supplier == selected_supplier and
                product == selected_product and
                subproduct == selected_subproduct and
                rounded_grswt in selected_grswt_nums):
                matrix[subproduct][rounded_grswt] += 1
 
        # Build rows ordered by unique_grswts
        for sub, grs_data in matrix.items():
            row_values = [grs_data.get(gw, 0) for gw in unique_grswts]
            total = sum(row_values)
            table_data.append({
                "sub": sub,
                "values": row_values,
                "total": total
            })
 
    return render(request, 'TKG/tkgSupProSubGrsWiseStockReport.html', {
        'currentDateTime': formatted_time,
        'uniqueSuppliers': unique_suppliers,
        'uniqueProducts': unique_products,
        'uniqueSubProducts': unique_subproducts,
        'uniqueGrsWt': unique_grswts,
        'selectedSupplier': selected_supplier,
        'selectedProduct': selected_product,
        'selectedSubProduct': selected_subproduct,
        'selectedGrsWt': selected_grswt,
        'tableData': table_data,
        'showTable': show_table,
    })


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ GPC Owner Hand Report ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def ownerHandTkgEntireStockReport(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT d.DesignerName, b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
            FROM TKGJ2627.dbo.TagReceipt a
            JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
            JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
            JOIN TKGJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode
            WHERE a.IssueType='' AND a.TagChkDate IS NULL;
        """)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    data = [dict(zip(columns, row)) for row in rows]

    return render(request, "TKG/ownerHandTkgEntireStockReport.html", {"cursor": cursor, "datas": data})

def ownerHandtkgProductWiseStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    selected_product = request.GET.get("product")

    query = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='' AND a.TagChkDate IS NULL;
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    data = [
        {
            "ProName": row[0],
            "SubProName": row[1],
            "TagNo": row[2],
            "GrossWt": row[3],
            "Pieces": row[4],
        }
        for row in rows
    ]

    # All unique products
    unique_products = sorted(set(d["ProName"] for d in data))

    # Apply filter if product is selected
    if selected_product:
        data = [d for d in data if d["ProName"] == selected_product]

    # Pivot-style report
    subproducts = sorted(set(d["SubProName"] for d in data))

    # Apply rounding function depending on product
    if selected_product == "CHAIN":
        gross_weights = sorted(set(
            round_to_even(float(d["GrossWt"]))
            for d in data if d["GrossWt"] not in [None, ""]
        ))
    else:
        gross_weights = sorted(set(
            round_for_without_chain(float(d["GrossWt"]))
            for d in data if d["GrossWt"] not in [None, ""]
        ))

    # Initialize matrix with rounded weights
    report = defaultdict(lambda: {gw: 0 for gw in gross_weights})

    # Fill the matrix
    for d in data:
        sub = d["SubProName"]
        gw = d["GrossWt"]
        pcs = d["Pieces"]

        if gw not in [None, ""]:
            if selected_product == "CHAIN":
                rounded_wt = round_to_even(float(gw))
            else:
                rounded_wt = round_for_without_chain(float(gw))

            report[sub][rounded_wt] += pcs

    # Totals
    row_totals = {sub: sum(report[sub].values()) for sub in subproducts}
    col_totals = {gw: sum(report[sub][gw] for sub in subproducts) for gw in gross_weights}
    grand_total = sum(row_totals.values())

    context = {
        'currentDateTime': formatted_time,
        "uniqueProducts": unique_products,
        "selectedProduct": selected_product,
        "subproducts": subproducts,
        "gross_weights": gross_weights,
        "report": report,
        "row_totals": row_totals,
        "col_totals": col_totals,
        "grand_total": grand_total,
    }

    return render(request, "TKG/ownerHandTkgProductWiseStockReport.html", context)

def ownerHandTkgChainStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    query = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='' AND a.TagChkDate IS NULL AND b.ProName= 'CHAIN';
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    columns = ["ProName", "SubProName", "TagNo", "GrossWt", "Pieces"]
    data = [dict(zip(columns, row)) for row in rows]

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

    return render(request, 'TKG/ownerHandTkgChainStockReport.html', {
        'currentDateTime': formatted_time,
        'rows': data,
        'uniqueProducts': unique_products,
        'uniqueSubProducts': unique_subproducts,
        'uniqueGrsWt': unique_grswts,
        'matrix': matrix,
        'excludedSubProducts': excluded_subproducts,
    })

def ownerHandTkgProSubGrsWiseStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    # 🔹 Run SQL query instead of ORM
    query = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        WHERE a.IssueType='' AND a.TagChkDate IS NULL;
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    # Convert rows to list of dicts
    data = [
        {
            "Product": row[0],
            "SubProduct": row[1],
            "TagNo": row[2],
            "GrsWt": row[3],
            "Pieces": row[4],
        }
        for row in rows
    ]

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

    return render(request, 'TKG/ownerHandTkgProSubGrsWiseStockReport.html', {
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

def ownerHandTkgSupProSubGrsWiseStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")
 
    # 🔹 SQL Query: Added Vendor Join
    query = """
        SELECT d.DesignerName, b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM TKGJ2627.dbo.TagReceipt a
        JOIN TKGJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN TKGJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        JOIN TKGJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode
        WHERE a.IssueType='' AND a.TagChkDate IS NULL;
    """
 
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
 
    # 🔹 Convert SQL result into list of dicts
    data = [
        {
            "Supplier": row[0],
            "Product": row[1],
            "SubProduct": row[2],
            "TagNo": row[3],
            "GrsWt": row[4],
            "Pieces": row[5],
        }
        for row in rows
    ]
 
    # ✅ Read filters from request
    selected_supplier = request.GET.get('supplier')
    selected_product = request.GET.get('product')
    selected_subproduct = request.GET.get('subproduct')
    selected_grswt = request.GET.getlist('grswt')
 
    # 1) Unique suppliers (always available)
    unique_suppliers = sorted(set(d["Supplier"] for d in data if d["Supplier"]))
 
    # 2) Products must depend on selected supplier ONLY
    unique_products = []
    if selected_supplier:
        filtered_by_supplier = [d for d in data if d["Supplier"] == selected_supplier]
        unique_products = sorted(set(d["Product"] for d in filtered_by_supplier if d["Product"]))
 
    # 3) SubProducts depend on selected supplier AND selected product
    unique_subproducts = []
    if selected_supplier and selected_product:
        filtered_by_sup_prod = [
            d for d in data
            if d["Supplier"] == selected_supplier and d["Product"] == selected_product
        ]
        unique_subproducts = sorted(set(d["SubProduct"] for d in filtered_by_sup_prod if d["SubProduct"]))
 
    # 4) Gross weights depend on supplier + product + subproduct
    unique_grswts = []
    if selected_supplier and selected_product and selected_subproduct:
        filtered_for_grswt = [
            d for d in data
            if d["Supplier"] == selected_supplier and
               d["Product"] == selected_product and
               d["SubProduct"] == selected_subproduct and
               d["GrsWt"] not in [None, ''] and
               str(d["GrsWt"]).replace('.', '', 1).isdigit()
        ]
        if selected_product == "CHAIN":
            unique_grswts = sorted(set(round_to_even(float(d["GrsWt"])) for d in filtered_for_grswt))
        else:
            unique_grswts = sorted(set(round_for_without_chain(float(d["GrsWt"])) for d in filtered_for_grswt))
 
    # Show table only when all four filters applied
    show_table = bool(selected_supplier and selected_product and selected_subproduct and selected_grswt)
 
    table_data = []
    if show_table:
        # convert selected grswt values to floats for comparison
        try:
            selected_grswt_nums = [float(g) for g in selected_grswt]
        except ValueError:
            selected_grswt_nums = []
 
        matrix = defaultdict(lambda: defaultdict(int))
 
        for d in data:
            supplier = d["Supplier"]
            product = d["Product"]
            subproduct = d["SubProduct"]
            grswt = d["GrsWt"]
 
            if not (supplier and product and subproduct and grswt):
                continue
            if not str(grswt).replace('.', '', 1).isdigit():
                continue
 
            if product == "CHAIN":
                rounded_grswt = round_to_even(float(grswt))
            else:
                rounded_grswt = round_for_without_chain(float(grswt))
 
            if (supplier == selected_supplier and
                product == selected_product and
                subproduct == selected_subproduct and
                rounded_grswt in selected_grswt_nums):
                matrix[subproduct][rounded_grswt] += 1
 
        # Build rows ordered by unique_grswts
        for sub, grs_data in matrix.items():
            row_values = [grs_data.get(gw, 0) for gw in unique_grswts]
            total = sum(row_values)
            table_data.append({
                "sub": sub,
                "values": row_values,
                "total": total
            })
 
    return render(request, 'TKG/ownerHandTkgSupProSubGrsWiseStockReport.html', {
        'currentDateTime': formatted_time,
        'uniqueSuppliers': unique_suppliers,
        'uniqueProducts': unique_products,
        'uniqueSubProducts': unique_subproducts,
        'uniqueGrsWt': unique_grswts,
        'selectedSupplier': selected_supplier,
        'selectedProduct': selected_product,
        'selectedSubProduct': selected_subproduct,
        'selectedGrsWt': selected_grswt,
        'tableData': table_data,
        'showTable': show_table,
    })

