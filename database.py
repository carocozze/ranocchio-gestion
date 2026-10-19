"""
Script de importacion y creacion de base de datos SQLite para Ranocchio.
Parsea los datos originales del Excel del usuario y los carga en ranocchio.db
"""
import sqlite3
import re
from datetime import datetime

DB_PATH = "ranocchio.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Habilitar claves foraneas y WAL mode para rapidez y concurrencia
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")

    # 1. Tabla de Productos estandar
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        base_cost REAL DEFAULT 0,
        suggested_price REAL DEFAULT 0,
        notes TEXT,
        is_active INTEGER DEFAULT 1
    );
    """)

    # 2. Tabla de Ventas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month_label TEXT,
        date TEXT NOT NULL,
        customer TEXT,
        channel TEXT NOT NULL,
        product_name TEXT NOT NULL,
        order_type TEXT DEFAULT 'Minorista',
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price REAL NOT NULL DEFAULT 0,
        billed REAL DEFAULT 0,
        shipping REAL DEFAULT 0,
        total_sale REAL NOT NULL DEFAULT 0,
        payment_method TEXT,
        unit_cost REAL DEFAULT 0,
        total_cost REAL DEFAULT 0,
        commercial_margin_amount REAL DEFAULT 0,
        commercial_margin_pct REAL DEFAULT 0,
        details TEXT,
        order_code TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Tabla de Gastos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month_label TEXT,
        date TEXT,
        category TEXT NOT NULL,          -- 'Gasto Fijo' o 'Gasto Variable'
        subcategory TEXT NOT NULL,       -- 'Showroom', 'Administrativos', 'Viaticos', 'Producto', 'Packaging', 'Marketing', 'Ferias', 'Otros'
        detail TEXT NOT NULL,
        invoice_number TEXT,
        amount REAL NOT NULL,
        payment_method TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Tabla de Stock / Inventario
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        piece TEXT NOT NULL,             -- Entera nena, Body, Bikini, Nene, Remera UV, Poncho
        model TEXT NOT NULL,             -- Pocky, Sofia, Lucy, Francisca, Lupe, etc.
        print_design TEXT,               -- Amapola Rosa, etc.
        season TEXT DEFAULT 'Anteriores', -- Nueva Temporada, Anteriores
        size TEXT NOT NULL,              -- 1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, S, M, L
        production_qty INTEGER DEFAULT 0,
        stock_total INTEGER DEFAULT 0,
        consignment_qty INTEGER DEFAULT 0,
        showroom_qty INTEGER DEFAULT 0,
        tiendanube_qty INTEGER DEFAULT 0,
        sold_qty INTEGER DEFAULT 0,
        min_stock INTEGER DEFAULT 3,
        status TEXT DEFAULT 'in Stock',  -- 'in Stock', 're Order', 'Agotado'
        action TEXT DEFAULT 'Mantener',  -- 'Mantener', 'Agotar', 'Re comprar'
        unit_price REAL DEFAULT 0,
        stock_value REAL DEFAULT 0,
        unit_cost REAL DEFAULT 0,
        stock_cost REAL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. Tabla de Presupuesto Costos Fijos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fixed_costs_budget (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        segment TEXT NOT NULL,           -- Showroom, Ferias, Administrativo, Marketing
        item_name TEXT NOT NULL,
        periodicity TEXT,                -- mensual, diaria, etc.
        multiplier REAL DEFAULT 1,
        unit_value REAL DEFAULT 0,
        annual_total REAL DEFAULT 0,
        notes TEXT
    );
    """)

    # 6. Tabla de Escandallos de Fabricación (Costos Variables)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS variable_cost_recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT UNIQUE NOT NULL,
        fabric_and_design_cost REAL DEFAULT 0,
        labor_cost REAL DEFAULT 0,
        notions_cost REAL DEFAULT 0,
        packaging_cost REAL DEFAULT 1600.5,
        total_cost REAL DEFAULT 0,
        sales_units_ref INTEGER DEFAULT 0,
        total_budget_ref REAL DEFAULT 0,
        notes TEXT
    );
    """)

    # 7. Tabla de Reglas de Precios / Calculadora
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pricing_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT UNIQUE NOT NULL,
        base_cost REAL NOT NULL,
        desired_markup REAL DEFAULT 3.0,
        base_cash_price REAL,
        suggested_launch_price REAL,
        consignation_price REAL,
        wholesale_price REAL,
        list_price_card REAL NOT NULL,
        previous_year_price REAL,
        vat_commission_rate REAL DEFAULT 0.21,
        notes TEXT
    );
    """)

    # 8. Tabla de Benchmarks de Competencia
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS competitor_benchmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT NOT NULL,
        product_name TEXT NOT NULL,
        product_type TEXT,
        gender_segment TEXT,
        store_category TEXT,
        list_price REAL DEFAULT 0,
        promo_price REAL DEFAULT 0,
        has_promo INTEGER DEFAULT 0,
        discount_pct REAL DEFAULT 0,
        promo_detail TEXT,
        payment_terms TEXT,
        availability TEXT DEFAULT 'Disponible',
        link TEXT,
        updated_at TEXT
    );
    """)

    # 9. Tabla de P&L Mensual Consolidado
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS monthly_pnl (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month_label TEXT UNIQUE NOT NULL, -- 'Marzo 26', 'Abril 26', etc.
        month_order INTEGER,
        investment_usd REAL DEFAULT 0,
        fx_rate REAL DEFAULT 0,
        investment_pesos REAL DEFAULT 0,
        sales_revenue REAL DEFAULT 0,
        total_revenue REAL DEFAULT 0,
        var_expense_product REAL DEFAULT 0,
        var_expense_packaging REAL DEFAULT 0,
        var_expense_other REAL DEFAULT 0,
        total_var_expense REAL DEFAULT 0,
        fixed_expense_showroom REAL DEFAULT 0,
        fixed_expense_admin REAL DEFAULT 0,
        fixed_expense_marketing REAL DEFAULT 0,
        fixed_expense_travel REAL DEFAULT 0,
        fixed_expense_fairs REAL DEFAULT 0,
        fixed_expense_other REAL DEFAULT 0,
        total_fixed_expense REAL DEFAULT 0,
        total_expenses REAL DEFAULT 0,
        net_profit REAL DEFAULT 0,
        net_margin_pct REAL DEFAULT 0
    );
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
