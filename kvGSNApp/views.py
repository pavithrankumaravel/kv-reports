from kvReportsApp.api_utils import render
from django.db import connection
from collections import defaultdict
from .getFunction import round_to_even, round_for_without_chain
from datetime import datetime
from zoneinfo import ZoneInfo 

# Create your views here.

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ GSN Overall Report ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def gsnHome(request):
    return render(request, "GSN/gsnHome.html")

def gsnEntireStockReport(request):
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
            FROM GSNJ2627.dbo.TagReceipt a
            JOIN GSNJMaster.dbo.Product b ON a.ProCode = b.ProCode
            JOIN GSNJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
            LEFT JOIN GSNJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode  -- Changed to LEFT JOIN
            JOIN GSNJMaster.dbo.VendorMaster e ON a.AcctCode = e.AcctCode
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

    return render(request, "GSN/gsnEntireStockReport.html", {
        "datas": datas
    })

def gsnEntireSaleReport(request):

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                a.TranDate,
                d.DesignerName, 
                b.ProName, 
                c.SubProName, 
                a.TagNo, 
                a.GrossWt, 
                a.Pieces
            FROM GSNJ2627.dbo.Sales a
            JOIN GSNJMaster.dbo.Product b 
                ON a.ProCode = b.ProCode
            JOIN GSNJMaster.dbo.SubProduct c 
                ON a.SubCode = c.SubCode
            JOIN GSNJMaster.dbo.DesignerMaster d 
                ON a.DesCode = d.DesignerCode
            WHERE a.CanceledIp = '0'
        """)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    data = [dict(zip(columns, row)) for row in rows]

    return render(request, "GSN/gsnEntireSaleReport.html", {"cursor": cursor, "datas": data})

def gsnProductWiseStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    selected_product = request.GET.get("product")

    query = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM GSNJ2627.dbo.TagReceipt a
        JOIN GSNJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN GSNJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
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

    return render(request, "GSN/gsnProductWiseStockReport.html", context)

def gsnProSubGrsWiseStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    # 🔹 Run SQL query instead of ORM
    query = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM GSNJ2627.dbo.TagReceipt a
        JOIN GSNJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN GSNJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
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

    return render(request, 'GSN/gsnProSubGrsWiseStockReport.html', {
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

def gsnSupProSubGrsWiseStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")
 
    # 🔹 SQL Query: Added Vendor Join
    query = """
        SELECT d.DesignerName, b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM GSNJ2627.dbo.TagReceipt a
        JOIN GSNJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN GSNJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        JOIN GSNJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode
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
 
    return render(request, 'GSN/gsnSupProSubGrsWiseStockReport.html', {
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

def gsnSupplierWiseSaleReport(request):
    # ------------------ Date Time ------------------
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    # ------------------ READ FILTERS ------------------
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    selected_supplier = request.GET.get('supplier')
    selected_product = request.GET.get('product')

    # ------------------ BASE QUERY (AS GIVEN) ------------------
    query = """
        SELECT
            CAST(a.TranDate AS DATE) AS TranDate,
            d.DesignerName,
            b.ProName,
            c.SubProName,
            a.TagNo,
            a.GrossWt,
            a.Pieces
        FROM GSNJ2627.dbo.Sales a
        JOIN GSNJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN GSNJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        JOIN GSNJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode
        WHERE 1 = 1
    """

    params = []

    if start_date:
        query += " AND CAST(a.TranDate AS DATE) >= %s"
        params.append(start_date)

    if end_date:
        query += " AND CAST(a.TranDate AS DATE) <= %s"
        params.append(end_date)

    # ------------------ EXECUTE QUERY ------------------
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    # ------------------ NORMALIZE DATA ------------------
    data = [{
        "Supplier": r[1],
        "Product": r[2],
        "SubProduct": r[3],
        "TagNo": r[4],
        "GrossWt": r[5],
        "Pieces": r[6],
    } for r in rows]

    # ------------------ FILTER DROPDOWNS ------------------
    unique_suppliers = sorted(set(d["Supplier"] for d in data if d["Supplier"]))

    unique_products = []
    if selected_supplier:
        unique_products = sorted(
            set(d["Product"] for d in data if d["Supplier"] == selected_supplier)
        )

    # ------------------ TABLE DATA ------------------
    show_table = bool(start_date and end_date and selected_supplier and selected_product)

    table_data = []
    if show_table:
        matrix = defaultdict(int)

        for d in data:
            if (
                d["Supplier"] == selected_supplier and
                d["Product"] == selected_product
            ):
                # Counting Pieces (better for Sales)
                matrix[d["SubProduct"]] += d["Pieces"]

        for sub, total in matrix.items():
            table_data.append({
                "sub": sub,
                "total": total
            })

    # ------------------ RENDER ------------------
    return render(request, 'GSN/gsnSupplierWiseSaleReportOld.html', {
        'currentDateTime': formatted_time,
        'uniqueSuppliers': unique_suppliers,
        'uniqueProducts': unique_products,
        'selectedSupplier': selected_supplier,
        'selectedProduct': selected_product,
        'startDate': start_date,
        'endDate': end_date,
        'tableData': table_data,
        'showTable': show_table,
    })
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ GSN Owner Hand Report ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def ownerHandGsnEntireStockReport(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT d.DesignerName, b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
            FROM GSNJ2627.dbo.TagReceipt a
            JOIN GSNJMaster.dbo.Product b ON a.ProCode = b.ProCode
            JOIN GSNJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
            JOIN GSNJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode
            WHERE a.IssueType='' AND a.TagChkDate IS NULL;
        """)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    data = [dict(zip(columns, row)) for row in rows]

    return render(request, "GSN/ownerHandGsnEntireStockReport.html", {"cursor": cursor, "datas": data})

def ownerHandgsnProductWiseStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    selected_product = request.GET.get("product")

    query = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM GSNJ2627.dbo.TagReceipt a
        JOIN GSNJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN GSNJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
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

    return render(request, "GSN/ownerHandGsnProductWiseStockReport.html", context)

def ownerHandGsnProSubGrsWiseStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")

    # 🔹 Run SQL query instead of ORM
    query = """
        SELECT b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM GSNJ2627.dbo.TagReceipt a
        JOIN GSNJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN GSNJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
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

    return render(request, 'GSN/ownerHandGsnProSubGrsWiseStockReport.html', {
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

def ownerHandGsnSupProSubGrsWiseStockReport(request):
    indian_zone = ZoneInfo("Asia/Kolkata")
    current_datetime = datetime.now(indian_zone)
    formatted_time = current_datetime.strftime("%d-%m-%Y %I.%M%p")
 
    # 🔹 SQL Query: Added Vendor Join
    query = """
        SELECT d.DesignerName, b.ProName, c.SubProName, a.TagNo, a.GrossWt, a.Pieces
        FROM GSNJ2627.dbo.TagReceipt a
        JOIN GSNJMaster.dbo.Product b ON a.ProCode = b.ProCode
        JOIN GSNJMaster.dbo.SubProduct c ON a.SubCode = c.SubCode
        JOIN GSNJMaster.dbo.DesignerMaster d ON a.DesCode = d.DesignerCode
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
 
    return render(request, 'GSN/ownerHandGsnSupProSubGrsWiseStockReport.html', {
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
