"""
Capa de operaciones de Base de Datos y Lógica de Negocio para Ranocchio
"""
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime
from database import DB_PATH

MONTH_NAMES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

def get_month_label(date_str: str) -> str:
    """Convierte YYYY-MM-DD en ej. 'Septiembre 26'"""
    if not date_str:
        now = datetime.now()
        year_short = str(now.year)[2:]
        return f"{MONTH_NAMES_ES.get(now.month, '')} {year_short}"
    try:
        parts = date_str.strip().split("-")
        if len(parts) >= 2:
            y = int(parts[0])
            m = int(parts[1])
            year_short = str(y)[2:]
            return f"{MONTH_NAMES_ES.get(m, '')} {year_short}"
    except:
        pass
    return "Septiembre 26"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== SUMMARY & KPIS ====================

def get_dashboard_summary() -> Dict[str, Any]:
    conn = get_db()
    cur = conn.cursor()

    # Totales de ventas historicas
    sales_kpis = cur.execute("""
    SELECT 
        COUNT(*) as total_sales_count,
        COALESCE(SUM(total_sale), 0) as total_revenue,
        COALESCE(SUM(quantity), 0) as total_units_sold,
        COALESCE(SUM(total_cost), 0) as total_cost,
        COALESCE(SUM(commercial_margin_amount), 0) as total_margin_amount
    FROM sales
    """).fetchone()

    # Totales de gastos
    expenses_kpis = cur.execute("""
    SELECT 
        COUNT(*) as total_expenses_count,
        COALESCE(SUM(amount), 0) as total_expenses_amount,
        COALESCE(SUM(CASE WHEN category = 'Gasto Fijo' THEN amount ELSE 0 END), 0) as fixed_expenses,
        COALESCE(SUM(CASE WHEN category = 'Gasto Variable' THEN amount ELSE 0 END), 0) as variable_expenses
    FROM expenses
    """).fetchone()

    # Totales de stock
    stock_kpis = cur.execute("""
    SELECT 
        COUNT(*) as total_items_count,
        COALESCE(SUM(stock_total), 0) as total_stock_units,
        COALESCE(SUM(stock_value), 0) as total_stock_value,
        COALESCE(SUM(stock_cost), 0) as total_stock_cost,
        COALESCE(SUM(CASE WHEN stock_total <= min_stock AND stock_total > 0 THEN 1 ELSE 0 END), 0) as low_stock_count,
        COALESCE(SUM(CASE WHEN stock_total = 0 THEN 1 ELSE 0 END), 0) as out_of_stock_count
    FROM stock_items
    """).fetchone()

    # Top productos vendidos
    top_products = [dict(r) for r in cur.execute("""
    SELECT product_name, SUM(quantity) as units_sold, SUM(total_sale) as total_revenue
    FROM sales
    GROUP BY product_name
    ORDER BY total_revenue DESC
    LIMIT 6
    """).fetchall()]

    # Ventas por canal
    sales_by_channel = [dict(r) for r in cur.execute("""
    SELECT channel, COUNT(*) as count, SUM(total_sale) as total_revenue
    FROM sales
    GROUP BY channel
    ORDER BY total_revenue DESC
    """).fetchall()]

    # Ventas por medio de pago
    sales_by_payment = [dict(r) for r in cur.execute("""
    SELECT payment_method, COUNT(*) as count, SUM(total_sale) as total_revenue
    FROM sales
    GROUP BY payment_method
    ORDER BY total_revenue DESC
    """).fetchall()]

    # Gastos por rubro
    expenses_by_subcat = [dict(r) for r in cur.execute("""
    SELECT subcategory, SUM(amount) as total_amount
    FROM expenses
    GROUP BY subcategory
    ORDER BY total_amount DESC
    """).fetchall()]

    # Ultimas ventas
    recent_sales = [dict(r) for r in cur.execute("""
    SELECT id, date, customer, channel, product_name, quantity, total_sale, payment_method
    FROM sales
    ORDER BY date DESC, id DESC
    LIMIT 8
    """).fetchall()]

    # Alertas de stock bajo / reorder
    reorder_alerts = [dict(r) for r in cur.execute("""
    SELECT id, piece, model, print_design, size, stock_total, min_stock, status, action, unit_price
    FROM stock_items
    WHERE stock_total <= min_stock
    ORDER BY stock_total ASC
    LIMIT 8
    """).fetchall()]

    conn.close()

    total_revenue = sales_kpis["total_revenue"]
    total_expenses = expenses_kpis["total_expenses_amount"]
    net_operating_profit = total_revenue - total_expenses
    commercial_margin_pct = (sales_kpis["total_margin_amount"] / total_revenue * 100) if total_revenue > 0 else 0

    return {
        "sales": {
            "count": sales_kpis["total_sales_count"],
            "total_revenue": total_revenue,
            "total_units_sold": sales_kpis["total_units_sold"],
            "total_cost": sales_kpis["total_cost"],
            "commercial_margin_amount": sales_kpis["total_margin_amount"],
            "commercial_margin_pct": round(commercial_margin_pct, 1),
            "by_channel": sales_by_channel,
            "by_payment": sales_by_payment,
            "top_products": top_products,
            "recent": recent_sales
        },
        "expenses": {
            "count": expenses_kpis["total_expenses_count"],
            "total_amount": total_expenses,
            "fixed": expenses_kpis["fixed_expenses"],
            "variable": expenses_kpis["variable_expenses"],
            "by_subcategory": expenses_by_subcat
        },
        "stock": {
            "total_items": stock_kpis["total_items_count"],
            "total_units": stock_kpis["total_stock_units"],
            "total_value": stock_kpis["total_stock_value"],
            "total_cost": stock_kpis["total_stock_cost"],
            "low_stock_count": stock_kpis["low_stock_count"],
            "out_of_stock_count": stock_kpis["out_of_stock_count"],
            "alerts": reorder_alerts
        },
        "financial": {
            "net_profit": net_operating_profit,
            "profit_margin_pct": round((net_operating_profit / total_revenue * 100), 1) if total_revenue > 0 else 0
        }
    }

# ==================== SALES CRUD ====================

def list_sales(limit: int = 100, month: Optional[str] = None, channel: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT * FROM sales WHERE 1=1"
    params = []

    if month and month != "all":
        query += " AND month_label = ?"
        params.append(month)
    if channel and channel != "all":
        query += " AND channel = ?"
        params.append(channel)
    if search:
        query += " AND (customer LIKE ? OR product_name LIKE ? OR details LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])

    query += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)

    rows = [dict(r) for r in cur.execute(query, params).fetchall()]
    conn.close()
    return rows

def create_sale(data: Dict[str, Any]) -> Any:
    conn = get_db()
    cur = conn.cursor()

    month_label = data.get("month_label") or get_month_label(data.get("date", ""))
    date_val = data.get("date")
    customer = data.get("customer", "")
    channel = data.get("channel", "SHOWROOM")
    order_type = data.get("order_type", "Minorista")
    payment_method = data.get("payment_method", "Efectivo")
    order_code = data.get("order_code") or f"ORD-{datetime.now().strftime('%y%m%d%H%M%S')}"

    # CASO 1: Varios productos en la misma orden para la misma clienta
    items = data.get("items")
    if items and len(items) > 0:
        created_records = []
        shipping_total = float(data.get("shipping", 0))
        for idx, item in enumerate(items):
            # Dict o Pydantic model
            if hasattr(item, "model_dump"):
                item_dict = item.model_dump()
            elif isinstance(item, dict):
                item_dict = item
            else:
                item_dict = dict(item)

            prod_name = item_dict.get("product_name", "Prenda")
            qty = int(item_dict.get("quantity", 1))
            unit_price = float(item_dict.get("unit_price", 0))
            billed = qty * unit_price
            # El envio se asocia al primer item del pedido
            item_shipping = shipping_total if idx == 0 else 0.0
            total_sale = billed + item_shipping
            
            unit_cost = float(item_dict.get("unit_cost", 0))
            if unit_cost == 0:
                p_row = cur.execute("SELECT base_cost FROM products WHERE name = ? COLLATE NOCASE", (prod_name,)).fetchone()
                if p_row and p_row[0]:
                    unit_cost = float(p_row[0])

            total_cost = qty * unit_cost
            margin_amt = total_sale - total_cost
            margin_pct = (margin_amt / total_sale) if total_sale > 0 else 0
            item_details = item_dict.get("details", "") or data.get("details", "")

            cur.execute("""
            INSERT INTO sales
            (month_label, date, customer, channel, product_name, order_type, quantity, unit_price, billed, shipping, total_sale, payment_method, unit_cost, total_cost, commercial_margin_amount, commercial_margin_pct, details, order_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                month_label, date_val, customer, channel, prod_name, order_type,
                qty, unit_price, billed, item_shipping, total_sale, payment_method,
                unit_cost, total_cost, margin_amt, margin_pct, item_details, order_code
            ))
            created_records.append(cur.lastrowid)

        conn.commit()
        last_row = dict(cur.execute("SELECT * FROM sales WHERE id = ?", (created_records[0],)).fetchone())
        last_row["multiple_items_count"] = len(created_records)
        last_row["order_code"] = order_code
        conn.close()
        return last_row

    # CASO 2: Venta por lote / Consignación global o producto individual
    is_bulk = data.get("is_bulk", False)
    qty = int(data.get("quantity", 1))
    unit_price = float(data.get("unit_price", 0))
    shipping = float(data.get("shipping", 0))

    if is_bulk:
        total_sale = float(data.get("total_sale") or data.get("billed") or 0)
        billed = total_sale
        unit_price = (total_sale / qty) if qty > 0 else total_sale
    else:
        billed = data.get("billed")
        if billed is None or billed <= 0:
            billed = qty * unit_price
        else:
            billed = float(billed)
        total_sale = billed + shipping

    unit_cost = float(data.get("unit_cost", 0))
    if unit_cost == 0 and not is_bulk:
        p_row = cur.execute("SELECT base_cost FROM products WHERE name = ? COLLATE NOCASE", (data.get("product_name"),)).fetchone()
        if p_row and p_row[0]:
            unit_cost = float(p_row[0])

    total_cost = qty * unit_cost
    margin_amt = total_sale - total_cost
    margin_pct = (margin_amt / total_sale) if total_sale > 0 else 0

    cur.execute("""
    INSERT INTO sales
    (month_label, date, customer, channel, product_name, order_type, quantity, unit_price, billed, shipping, total_sale, payment_method, unit_cost, total_cost, commercial_margin_amount, commercial_margin_pct, details, order_code)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        month_label,
        date_val,
        customer,
        channel,
        data.get("product_name", "Lote Consignación"),
        order_type,
        qty,
        unit_price,
        billed,
        shipping,
        total_sale,
        payment_method,
        unit_cost,
        total_cost,
        margin_amt,
        margin_pct,
        data.get("details", ""),
        order_code
    ))
    new_id = cur.lastrowid

    # Descontar stock opcional si corresponde
    if data.get("deduct_stock") and data.get("stock_item_id"):
        cur.execute("""
        UPDATE stock_items 
        SET stock_total = MAX(0, stock_total - ?),
            sold_qty = sold_qty + ?,
            stock_value = MAX(0, stock_total - ?) * unit_price,
            stock_cost = MAX(0, stock_total - ?) * unit_cost
        WHERE id = ?
        """, (qty, qty, qty, qty, data["stock_item_id"]))

    conn.commit()
    row = dict(cur.execute("SELECT * FROM sales WHERE id = ?", (new_id,)).fetchone())
    conn.close()
    return row

def update_sale(sale_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()

    month_label = data.get("month_label") or get_month_label(data.get("date", ""))
    qty = int(data.get("quantity", 1))
    unit_price = float(data.get("unit_price", 0))
    shipping = float(data.get("shipping", 0))
    
    billed = data.get("billed")
    if billed is None or billed <= 0:
        billed = qty * unit_price
    else:
        billed = float(billed)

    total_sale = billed + shipping
    unit_cost = float(data.get("unit_cost", 0))
    total_cost = qty * unit_cost
    margin_amt = total_sale - total_cost
    margin_pct = (margin_amt / total_sale) if total_sale > 0 else 0

    cur.execute("""
    UPDATE sales SET
        month_label = ?,
        date = ?,
        customer = ?,
        channel = ?,
        product_name = ?,
        order_type = ?,
        quantity = ?,
        unit_price = ?,
        billed = ?,
        shipping = ?,
        total_sale = ?,
        payment_method = ?,
        unit_cost = ?,
        total_cost = ?,
        commercial_margin_amount = ?,
        commercial_margin_pct = ?,
        details = ?
    WHERE id = ?
    """, (
        month_label,
        data.get("date"),
        data.get("customer", ""),
        data.get("channel", "SHOWROOM"),
        data.get("product_name"),
        data.get("order_type", "Minorista"),
        qty,
        unit_price,
        billed,
        shipping,
        total_sale,
        data.get("payment_method", "Efectivo"),
        unit_cost,
        total_cost,
        margin_amt,
        margin_pct,
        data.get("details", ""),
        sale_id
    ))
    conn.commit()
    row = cur.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def delete_sale(sale_id: int) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def batch_delete_sales(sale_ids: List[int]) -> int:
    if not sale_ids:
        return 0
    conn = get_db()
    cur = conn.cursor()
    placeholders = ",".join(["?"] * len(sale_ids))
    cur.execute(f"DELETE FROM sales WHERE id IN ({placeholders})", sale_ids)
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


# ==================== EXPENSES CRUD ====================

def list_expenses(limit: int = 150, month: Optional[str] = None, category: Optional[str] = None, subcategory: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if month and month != "all":
        query += " AND month_label = ?"
        params.append(month)
    if category and category != "all":
        query += " AND category = ?"
        params.append(category)
    if subcategory and subcategory != "all":
        query += " AND subcategory = ?"
        params.append(subcategory)
    if search:
        query += " AND (detail LIKE ? OR payment_method LIKE ? OR notes LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])

    query += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)

    rows = [dict(r) for r in cur.execute(query, params).fetchall()]
    conn.close()
    return rows

def create_expense(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db()
    cur = conn.cursor()

    month_label = data.get("month_label") or get_month_label(data.get("date", ""))
    amount = float(data.get("amount", 0))

    cur.execute("""
    INSERT INTO expenses
    (month_label, date, category, subcategory, detail, invoice_number, amount, payment_method, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        month_label,
        data.get("date", ""),
        data.get("category", "Gasto Fijo"),
        data.get("subcategory", "Otros"),
        data.get("detail", ""),
        data.get("invoice_number", ""),
        amount,
        data.get("payment_method", "Efectivo"),
        data.get("notes", "")
    ))
    new_id = cur.lastrowid
    conn.commit()
    row = dict(cur.execute("SELECT * FROM expenses WHERE id = ?", (new_id,)).fetchone())
    conn.close()
    return row

def update_expense(expense_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    month_label = data.get("month_label") or get_month_label(data.get("date", ""))

    cur.execute("""
    UPDATE expenses SET
        month_label = ?,
        date = ?,
        category = ?,
        subcategory = ?,
        detail = ?,
        invoice_number = ?,
        amount = ?,
        payment_method = ?,
        notes = ?
    WHERE id = ?
    """, (
        month_label,
        data.get("date", ""),
        data.get("category", "Gasto Fijo"),
        data.get("subcategory", "Otros"),
        data.get("detail", ""),
        data.get("invoice_number", ""),
        float(data.get("amount", 0)),
        data.get("payment_method", "Efectivo"),
        data.get("notes", ""),
        expense_id
    ))
    conn.commit()
    row = cur.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def delete_expense(expense_id: int) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# ==================== STOCK CRUD ====================

def list_stock(piece: Optional[str] = None, status: Optional[str] = None, season: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT * FROM stock_items WHERE 1=1"
    params = []

    if piece and piece != "all":
        query += " AND piece = ?"
        params.append(piece)
    if status and status != "all":
        query += " AND status = ?"
        params.append(status)
    if season and season != "all":
        query += " AND season = ?"
        params.append(season)
    if search:
        query += " AND (model LIKE ? OR print_design LIKE ? OR piece LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])

    query += " ORDER BY piece ASC, model ASC, size ASC"
    rows = [dict(r) for r in cur.execute(query, params).fetchall()]
    conn.close()
    return rows

def create_stock_item(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db()
    cur = conn.cursor()

    stock_total = int(data.get("stock_total", 0))
    min_stock = int(data.get("min_stock", 3))
    unit_price = float(data.get("unit_price", 0))
    unit_cost = float(data.get("unit_cost", 0))

    # Auto status
    status = "in Stock" if stock_total > min_stock else ("re Order" if stock_total > 0 else "Agotado")
    action = data.get("action") or ("Mantener" if stock_total > min_stock else "Re comprar")

    stock_val = stock_total * unit_price
    stock_cost = stock_total * unit_cost

    cur.execute("""
    INSERT INTO stock_items
    (piece, model, print_design, season, size, production_qty, stock_total, consignment_qty, showroom_qty, tiendanube_qty, sold_qty, min_stock, status, action, unit_price, stock_value, unit_cost, stock_cost)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("piece"),
        data.get("model"),
        data.get("print_design", ""),
        data.get("season", "Nueva Temporada"),
        str(data.get("size")),
        int(data.get("production_qty", stock_total)),
        stock_total,
        int(data.get("consignment_qty", 0)),
        int(data.get("showroom_qty", stock_total)),
        int(data.get("tiendanube_qty", 0)),
        int(data.get("sold_qty", 0)),
        min_stock,
        status,
        action,
        unit_price,
        stock_val,
        unit_cost,
        stock_cost
    ))
    new_id = cur.lastrowid
    conn.commit()
    row = dict(cur.execute("SELECT * FROM stock_items WHERE id = ?", (new_id,)).fetchone())
    conn.close()
    return row

def update_stock_item(item_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()

    stock_total = int(data.get("stock_total", 0))
    min_stock = int(data.get("min_stock", 3))
    unit_price = float(data.get("unit_price", 0))
    unit_cost = float(data.get("unit_cost", 0))

    status = "in Stock" if stock_total > min_stock else ("re Order" if stock_total > 0 else "Agotado")
    action = data.get("action") or ("Mantener" if stock_total > min_stock else "Re comprar")

    cur.execute("""
    UPDATE stock_items SET
        piece = ?,
        model = ?,
        print_design = ?,
        season = ?,
        size = ?,
        production_qty = ?,
        stock_total = ?,
        consignment_qty = ?,
        showroom_qty = ?,
        tiendanube_qty = ?,
        sold_qty = ?,
        min_stock = ?,
        status = ?,
        action = ?,
        unit_price = ?,
        stock_value = ?,
        unit_cost = ?,
        stock_cost = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (
        data.get("piece"),
        data.get("model"),
        data.get("print_design", ""),
        data.get("season", "Nueva Temporada"),
        str(data.get("size")),
        int(data.get("production_qty", 0)),
        stock_total,
        int(data.get("consignment_qty", 0)),
        int(data.get("showroom_qty", 0)),
        int(data.get("tiendanube_qty", 0)),
        int(data.get("sold_qty", 0)),
        min_stock,
        status,
        action,
        unit_price,
        stock_total * unit_price,
        unit_cost,
        stock_total * unit_cost,
        item_id
    ))
    conn.commit()
    row = cur.execute("SELECT * FROM stock_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def adjust_stock_qty(item_id: int, delta: int, channel: str = "showroom") -> Optional[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM stock_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        conn.close()
        return None

    current = dict(row)
    new_total = max(0, current["stock_total"] + delta)
    min_stock = current["min_stock"]
    status = "in Stock" if new_total > min_stock else ("re Order" if new_total > 0 else "Agotado")

    sh = current["showroom_qty"]
    tn = current["tiendanube_qty"]
    co = current["consignment_qty"]
    if channel == "showroom":
        sh = max(0, sh + delta)
    elif channel == "tiendanube":
        tn = max(0, tn + delta)
    elif channel == "consignment":
        co = max(0, co + delta)

    val = new_total * current["unit_price"]
    cost = new_total * current["unit_cost"]

    cur.execute("""
    UPDATE stock_items SET
        stock_total = ?,
        showroom_qty = ?,
        tiendanube_qty = ?,
        consignment_qty = ?,
        status = ?,
        stock_value = ?,
        stock_cost = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (new_total, sh, tn, co, status, val, cost, item_id))

    conn.commit()
    updated = dict(cur.execute("SELECT * FROM stock_items WHERE id = ?", (item_id,)).fetchone())
    conn.close()
    return updated

def delete_stock_item(item_id: int) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM stock_items WHERE id = ?", (item_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# ==================== PRICING SIMULATOR ====================

def calculate_pricing_breakdown(
    base_cost: float,
    markup: float = 3.0,
    list_price_card: float = 90000.0,
    vat_rate: float = 0.21,
    discount_cash_pct: float = 0.20,
    discount_bolsera_pct: float = 0.40
) -> Dict[str, Any]:
    """
    Calcula el desglose financiero exacto por medio de pago tal como en el Excel de Ranocchio.
    """
    # Ganancia neta objetivo sobre costo
    target_profit = base_cost * markup
    base_cash_target = base_cost + target_profit # Costo + Ganancia deseada

    methods = [
        {
            "id": "cash",
            "name": "Efectivo / Transferencia",
            "fee_trans_pct": 0.0,
            "cft_pct": 0.0,
            "discount_pct": discount_cash_pct,
            "claim": f"{int(discount_cash_pct*100)}% Off",
            "description": "Cobro directo sin intermediación ni costo financiero.",
            "is_cash_type": True
        },
        {
            "id": "mp_qr_wallet",
            "name": "Mercado Pago - QR Dinero en Cuenta",
            "fee_trans_pct": 0.008, # 0.8%
            "cft_pct": 0.0,
            "discount_pct": discount_cash_pct,
            "claim": f"{int(discount_cash_pct*100)}% Off",
            "description": "Arancel por procesamiento con saldo en billetera virtual.",
            "is_cash_type": True
        },
        {
            "id": "mp_qr_debit",
            "name": "Mercado Pago - Débito / QR",
            "fee_trans_pct": 0.015, # 1.5%
            "cft_pct": 0.0191,     # 1.91%
            "discount_pct": discount_cash_pct,
            "claim": f"{int(discount_cash_pct*100)}% Off",
            "description": "Arancel tarjeta débito + costo de acreditación en el acto.",
            "is_cash_type": True
        },
        {
            "id": "mp_credit_1",
            "name": "Mercado Pago - Crédito 1 Pago (Inmediato)",
            "fee_trans_pct": 0.018, # 1.8%
            "cft_pct": 0.0480,     # 4.8%
            "discount_pct": 0.0,
            "claim": "Tarjeta 1 pago",
            "description": "Arancel tarjeta crédito + costo por acreditación inmediata.",
            "is_cash_type": False
        },
        {
            "id": "mp_credit_3",
            "name": "Mercado Pago - 3 Cuotas (Inmediato)",
            "fee_trans_pct": 0.018, # 1.8%
            "cft_pct": 0.1319,     # 13.19%
            "discount_pct": 0.0,
            "claim": "3 Cuotas sin interés",
            "description": "Arancel tarjeta + financiamiento de 3 cuotas inmediato.",
            "is_cash_type": False
        },
        {
            "id": "mp_credit_6",
            "name": "Mercado Pago - 6 Cuotas (Inmediato)",
            "fee_trans_pct": 0.018, # 1.8%
            "cft_pct": 0.2400,     # 24.0%
            "discount_pct": 0.0,
            "claim": "6 Cuotas sin interés",
            "description": "Arancel tarjeta + financiamiento de 6 cuotas inmediato.",
            "is_cash_type": False
        },
        {
            "id": "bolsera",
            "name": "Consignación / Bolsera",
            "fee_trans_pct": 0.0,
            "cft_pct": 0.0,
            "discount_pct": discount_bolsera_pct,
            "claim": f"{int(discount_bolsera_pct*100)}% bolsera",
            "description": "Venta por consignación con comisión acordada.",
            "is_cash_type": False
        }
    ]

    breakdown = []
    for m in methods:
        # Precio de venta para el cliente
        if m["is_cash_type"]:
            # Aplica descuento de pago contado sobre el precio de lista
            suggested_price = list_price_card * (1.0 - m["discount_pct"])
        elif m["id"] == "bolsera":
            suggested_price = list_price_card * (1.0 - m["discount_pct"])
        else:
            suggested_price = list_price_card

        base_commission_rate = m["fee_trans_pct"] + m["cft_pct"]
        vat_commission_rate = base_commission_rate * vat_rate
        total_commission_pct = base_commission_rate + vat_commission_rate

        platform_fee_amount = suggested_price * total_commission_pct
        net_revenue = suggested_price - platform_fee_amount
        net_profit = net_revenue - base_cost
        margin_on_sale_pct = (net_profit / suggested_price) if suggested_price > 0 else 0

        breakdown.append({
            "id": m["id"],
            "name": m["name"],
            "description": m["description"],
            "claim": m["claim"],
            "suggested_price": round(suggested_price, 2),
            "fee_trans_pct": round(m["fee_trans_pct"] * 100, 2),
            "cft_pct": round(m["cft_pct"] * 100, 2),
            "total_commission_pct": round(total_commission_pct * 100, 2),
            "platform_fee_amount": round(platform_fee_amount, 2),
            "net_revenue": round(net_revenue, 2),
            "base_cost": round(base_cost, 2),
            "net_profit": round(net_profit, 2),
            "margin_on_sale_pct": round(margin_on_sale_pct * 100, 2),
            "is_viable": net_profit > 0
        })

    return {
        "parameters": {
            "base_cost": base_cost,
            "markup": markup,
            "target_profit": target_profit,
            "base_cash_target": base_cash_target,
            "list_price_card": list_price_card,
            "vat_rate_pct": vat_rate * 100
        },
        "breakdown": breakdown
    }

# ==================== P&L MENSUAL ====================

def get_monthly_pnl_data() -> List[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    # Obtenemos los meses registrados en monthly_pnl
    pnl_rows = [dict(r) for r in cur.execute("SELECT * FROM monthly_pnl ORDER BY month_order ASC").fetchall()]

    # Tambien calculamos los datos dinamicos reales desde las tablas de sales y expenses para comparar
    sales_by_month = {
        r["month_label"]: r["total"] 
        for r in cur.execute("SELECT month_label, SUM(total_sale) as total FROM sales GROUP BY month_label").fetchall()
    }
    expenses_by_month = {
        r["month_label"]: r["total"] 
        for r in cur.execute("SELECT month_label, SUM(amount) as total FROM expenses GROUP BY month_label").fetchall()
    }

    # Fusionamos
    result = []
    for row in pnl_rows:
        m = row["month_label"]
        dyn_sales = sales_by_month.get(m, 0)
        dyn_exp = expenses_by_month.get(m, 0)
        
        # Si la fila tiene ingresos cargados los usamos, o si no los dinamicos
        final_sales = row["sales_revenue"] if row["sales_revenue"] > 0 else dyn_sales
        final_exp = row["total_expenses"] if row["total_expenses"] > 0 else dyn_exp

        net = final_sales - final_exp
        pct = (net / final_sales * 100) if final_sales > 0 else 0

        item = dict(row)
        item["calculated_sales"] = dyn_sales
        item["calculated_expenses"] = dyn_exp
        item["effective_sales"] = final_sales
        item["effective_expenses"] = final_exp
        item["effective_net"] = net
        item["effective_margin_pct"] = round(pct, 1)
        result.append(item)

    conn.close()
    return result

# ==================== COST STRUCTURES ====================

def get_cost_structures() -> Dict[str, Any]:
    conn = get_db()
    cur = conn.cursor()
    fixed = [dict(r) for r in cur.execute("SELECT * FROM fixed_costs_budget ORDER BY segment, id").fetchall()]
    variables = [dict(r) for r in cur.execute("SELECT * FROM variable_cost_recipes ORDER BY total_cost DESC").fetchall()]
    pricing_rules = [dict(r) for r in cur.execute("SELECT * FROM pricing_rules ORDER BY id").fetchall()]
    benchmarks = [dict(r) for r in cur.execute("SELECT * FROM competitor_benchmarks ORDER BY brand, product_name").fetchall()]
    conn.close()

    total_fixed_monthly = sum(r["unit_value"] for r in fixed if r["periodicity"] == "mensual")
    total_fixed_annual = sum(r["annual_total"] for r in fixed if r["annual_total"])

    return {
        "fixed_items": fixed,
        "fixed_total_monthly": total_fixed_monthly,
        "fixed_total_annual": total_fixed_annual,
        "variable_recipes": variables,
        "pricing_rules": pricing_rules,
        "competitor_benchmarks": benchmarks
    }
