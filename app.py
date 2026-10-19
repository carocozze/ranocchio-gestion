"""
FastAPI Server principal para Ranocchio Gestión & Automatización
"""
import os
import io
import socket
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any

import crud
import models
import export_service
from database import DB_PATH, init_db

app = FastAPI(title="Ranocchio Gestión & Automatización", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

# ==================== SUMMARY & NETWORK ====================

@app.get("/api/network-info")
def network_info():
    ip = get_local_ip()
    port = int(os.environ.get("PORT", 8000))
    pub_url = None
    pub_file = os.path.join(os.path.dirname(__file__), "public_url.txt")
    if os.path.exists(pub_file):
        try:
            with open(pub_file, "r", encoding="utf-8") as f:
                pub_url = f.read().strip()
        except:
            pass

    return {
        "local_ip": ip,
        "port": port,
        "local_url": f"http://localhost:{port}",
        "network_url": f"http://{ip}:{port}",
        "public_url": pub_url,
        "share_url": pub_url if pub_url else f"http://{ip}:{port}",
        "brand": "Ranocchio Swimwear"
    }


@app.get("/api/summary")
def get_summary():
    return crud.get_dashboard_summary()

# ==================== SALES API ====================

@app.get("/api/sales")
def list_sales(
    limit: int = 200,
    month: Optional[str] = None,
    channel: Optional[str] = None,
    search: Optional[str] = None
):
    return crud.list_sales(limit=limit, month=month, channel=channel, search=search)

@app.post("/api/sales")
def create_sale(sale: models.SaleCreate):
    return crud.create_sale(sale.model_dump())

@app.put("/api/sales/{sale_id}")
def update_sale(sale_id: int, sale: models.SaleUpdate):
    updated = crud.update_sale(sale_id, sale.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return updated

@app.delete("/api/sales/{sale_id}")
def delete_sale(sale_id: int):
    ok = crud.delete_sale(sale_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return {"success": True, "message": "Venta eliminada correctamente"}

@app.post("/api/sales/batch-delete")
def batch_delete_sales(req: models.BatchDeleteRequest):
    count = crud.batch_delete_sales(req.ids)
    return {"success": True, "deleted_count": count, "message": f"{count} ventas eliminadas correctamente"}


# ==================== EXPENSES API ====================

@app.get("/api/expenses")
def list_expenses(
    limit: int = 300,
    month: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    search: Optional[str] = None
):
    return crud.list_expenses(limit=limit, month=month, category=category, subcategory=subcategory, search=search)

@app.post("/api/expenses")
def create_expense(expense: models.ExpenseCreate):
    return crud.create_expense(expense.model_dump())

@app.put("/api/expenses/{expense_id}")
def update_expense(expense_id: int, expense: models.ExpenseUpdate):
    updated = crud.update_expense(expense_id, expense.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return updated

@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int):
    ok = crud.delete_expense(expense_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return {"success": True, "message": "Gasto eliminado correctamente"}

# ==================== STOCK API ====================

@app.get("/api/stock")
def list_stock(
    piece: Optional[str] = None,
    status: Optional[str] = None,
    season: Optional[str] = None,
    search: Optional[str] = None
):
    return crud.list_stock(piece=piece, status=status, season=season, search=search)

@app.post("/api/stock")
def create_stock_item(item: models.StockItemCreate):
    return crud.create_stock_item(item.model_dump())

@app.put("/api/stock/{item_id}")
def update_stock_item(item_id: int, item: models.StockItemUpdate):
    updated = crud.update_stock_item(item_id, item.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Artículo de stock no encontrado")
    return updated

@app.patch("/api/stock/{item_id}/adjust")
def adjust_stock(item_id: int, adj: models.StockAdjust):
    updated = crud.adjust_stock_qty(item_id, adj.adjustment, adj.channel)
    if not updated:
        raise HTTPException(status_code=404, detail="Artículo de stock no encontrado")
    return updated

@app.delete("/api/stock/{item_id}")
def delete_stock_item(item_id: int):
    ok = crud.delete_stock_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    return {"success": True, "message": "Artículo eliminado correctamente"}

# ==================== PRICING SIMULATOR ====================

@app.post("/api/pricing/simulate")
def simulate_pricing(req: models.PricingSimulationRequest):
    return crud.calculate_pricing_breakdown(
        base_cost=req.base_cost,
        markup=req.markup,
        list_price_card=req.list_price_card,
        vat_rate=req.vat_rate,
        discount_cash_pct=req.discount_cash_pct,
        discount_bolsera_pct=req.discount_bolsera_pct
    )

@app.get("/api/pricing/rules")
def get_pricing_rules():
    costs = crud.get_cost_structures()
    return costs["pricing_rules"]

# ==================== P&L API ====================

@app.get("/api/pnl")
def get_pnl():
    return crud.get_monthly_pnl_data()

# ==================== COSTS & BENCHMARKS ====================

@app.get("/api/costs")
def get_costs():
    return crud.get_cost_structures()

@app.get("/api/products")
def list_products():
    conn = crud.get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY name").fetchall()]
    conn.close()
    return rows

@app.get("/api/competitors")
def get_competitors():
    conn = crud.get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM competitor_benchmarks ORDER BY brand, product_name").fetchall()]
    conn.close()
    return rows

# ==================== EXPORT EXCEL ====================

@app.get("/api/export/excel")
def download_excel():
    output = export_service.generate_full_excel()
    filename = "Ranocchio_Gestion_Completa.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ==================== FRONTEND ROOT ====================

@app.get("/", response_class=HTMLResponse)
def index():
    # Servir la plantilla HTML principal
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Ranocchio Sistema de Gestión - Cargando...</h1>")
