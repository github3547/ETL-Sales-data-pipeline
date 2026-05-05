"""
query_db.py — Interactive query helper for the ETL pipeline database.
Run after pipeline.py to explore results and generate reports.
"""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "sales_pipeline.db"


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}\n"
            "Run  python pipeline.py  first."
        )
    return sqlite3.connect(DB_PATH)


def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def show_table(conn: sqlite3.Connection, table: str, n: int = 10) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {table} LIMIT {n}", conn)


def revenue_by_region(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT region,
               total_revenue,
               order_count,
               ROUND(avg_order_val, 2) AS avg_order_val
        FROM   dim_regions
        ORDER  BY total_revenue DESC
        """,
        conn,
    )


def top_products(conn: sqlite3.Connection, n: int = 5) -> pd.DataFrame:
    return pd.read_sql(
        f"""
        SELECT product,
               category,
               total_units_sold,
               ROUND(total_revenue, 2) AS total_revenue,
               order_count
        FROM   dim_products
        ORDER  BY total_revenue DESC
        LIMIT  {n}
        """,
        conn,
    )


def monthly_trend(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT order_year,
               order_month_nm AS month,
               total_revenue,
               order_count
        FROM   agg_monthly
        ORDER  BY order_year, order_month
        """,
        conn,
    )


def gap_summary(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM gap_analysis", conn)


# ─── CLI Report ──────────────────────────────────────────────────────────────

def print_section(title: str, df: pd.DataFrame) -> None:
    width = 60
    print(f"\n{'═' * width}")
    print(f"  {title}")
    print(f"{'═' * width}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    with connect() as conn:
        print("\n📦  Tables / Views in database:", list_tables(conn))

        print_section("📊  Gap Analysis Summary",      gap_summary(conn))
        print_section("🗺️   Revenue by Region",         revenue_by_region(conn))
        print_section("🏆  Top 5 Products by Revenue", top_products(conn, 5))
        print_section("📅  Monthly Revenue Trend",     monthly_trend(conn))
        print_section("🔎  Sample Fact Orders (10)",   show_table(conn, "fact_orders"))
