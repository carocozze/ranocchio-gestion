"""
Modelos de datos Pydantic para la API de Ranocchio
"""
from pydantic import BaseModel, Field
from typing import Optional, List

class SaleItem(BaseModel):
    product_name: str
    quantity: int = 1
    unit_price: float
    unit_cost: Optional[float] = 0.0
    details: Optional[str] = ""

class SaleCreate(BaseModel):
    date: str
    month_label: Optional[str] = None
    customer: Optional[str] = ""
    channel: str = "SHOWROOM" # SHOWROOM, WHATSAPP, INSTAGRAM, CONSIGNACION, TIENDA NUBE, FERIA
    order_type: str = "Minorista" # Minorista, Consignacion, oferton, Mayorista
    payment_method: str = "Efectivo"
    shipping: Optional[float] = 0.0
    order_code: Optional[str] = None
    # Modo clasico (un solo producto) o Lote
    product_name: Optional[str] = "Prendas Ranocchio"
    quantity: Optional[int] = 1
    unit_price: Optional[float] = 0.0
    billed: Optional[float] = None
    total_sale: Optional[float] = None
    unit_cost: Optional[float] = 0.0
    details: Optional[str] = ""
    is_bulk: Optional[bool] = False
    deduct_stock: Optional[bool] = False
    stock_item_id: Optional[int] = None
    # Modo varios productos para la misma clienta
    items: Optional[List[SaleItem]] = None

class SaleUpdate(BaseModel):
    date: str
    month_label: Optional[str] = None
    customer: Optional[str] = ""
    channel: str = "SHOWROOM"
    product_name: str
    order_type: str = "Minorista"
    quantity: int = 1
    unit_price: float
    billed: Optional[float] = None
    shipping: Optional[float] = 0.0
    total_sale: Optional[float] = None
    payment_method: str = "Efectivo"
    unit_cost: Optional[float] = 0.0
    details: Optional[str] = ""
    order_code: Optional[str] = None

class BatchDeleteRequest(BaseModel):
    ids: List[int]


class ExpenseCreate(BaseModel):
    date: Optional[str] = ""
    month_label: Optional[str] = None
    category: str # "Gasto Fijo" o "Gasto Variable"
    subcategory: str # Showroom, Administrativos, Marketing, Viaticos, Ferias, Producto, Packaging, Otros
    detail: str
    invoice_number: Optional[str] = ""
    amount: float
    payment_method: Optional[str] = "Efectivo"
    notes: Optional[str] = ""

class ExpenseUpdate(ExpenseCreate):
    pass

class StockItemCreate(BaseModel):
    piece: str
    model: str
    print_design: Optional[str] = ""
    season: str = "Nueva Temporada"
    size: str
    production_qty: Optional[int] = 0
    stock_total: int = 0
    consignment_qty: Optional[int] = 0
    showroom_qty: Optional[int] = 0
    tiendanube_qty: Optional[int] = 0
    sold_qty: Optional[int] = 0
    min_stock: int = 3
    status: Optional[str] = "in Stock"
    action: Optional[str] = "Mantener"
    unit_price: float = 0.0
    unit_cost: float = 0.0

class StockItemUpdate(StockItemCreate):
    pass

class StockAdjust(BaseModel):
    adjustment: int # e.g. +1, -1, +5
    channel: Optional[str] = "showroom" # showroom, tiendanube, consignment

class PricingSimulationRequest(BaseModel):
    base_cost: float
    markup: float = 3.0 # Multiplicador sobre costo
    target_net_profit: Optional[float] = None
    vat_rate: float = 0.21 # 21% IVA comisiones
    list_price_card: float # Precio lista tarjeta / cuotas
    discount_cash_pct: float = 0.20 # 20% desc en efectivo/transf
    discount_bolsera_pct: float = 0.40 # 40% consignacion/bolsera

class FixedCostItemCreate(BaseModel):
    segment: str
    item_name: str
    periodicity: str = "mensual"
    multiplier: float = 12
    unit_value: float
    annual_total: Optional[float] = None
    notes: Optional[str] = ""

class RecipeCreate(BaseModel):
    product_name: str
    fabric_and_design_cost: float = 0.0
    labor_cost: float = 0.0
    notions_cost: float = 0.0
    packaging_cost: float = 1600.5
    notes: Optional[str] = ""

class MonthlyPnlUpdate(BaseModel):
    month_label: str
    investment_usd: Optional[float] = 0.0
    fx_rate: Optional[float] = 0.0
    investment_pesos: Optional[float] = 0.0
    sales_revenue: Optional[float] = 0.0
    var_expense_product: Optional[float] = 0.0
    var_expense_packaging: Optional[float] = 0.0
    var_expense_other: Optional[float] = 0.0
    fixed_expense_showroom: Optional[float] = 0.0
    fixed_expense_admin: Optional[float] = 0.0
    fixed_expense_marketing: Optional[float] = 0.0
    fixed_expense_travel: Optional[float] = 0.0
    fixed_expense_fairs: Optional[float] = 0.0
    fixed_expense_other: Optional[float] = 0.0
