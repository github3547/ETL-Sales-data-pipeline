"""
ETL Pipeline: Sales Data Processor
====================================
Extract → Clean → Transform → Load into SQLite

Author: Mohammad Khairul Jahan
"""

import pandas as pd
import sqlite3
import logging
import os
import re
from datetime import datetime
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────

BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
LOG_DIR    = BASE_DIR / "logs"
DB_PATH    = BASE_DIR / "sales_pipeline.db"
CSV_PATH   = DATA_DIR / "sales_data.csv"

LOG_DIR.mkdir(exist_ok=True)

# ─── Logging Setup ────────────────────────────────────────────────────────────

def setup_logger() -> logging.Logger:
    """Configure rotating file + console logger."""
    log_file = LOG_DIR / f"pipeline_{datetime.now():%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("etl_pipeline")


log = setup_logger()


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACT
# ═══════════════════════════════════════════════════════════════════════════════

def extract(csv_path: Path = CSV_PATH) -> pd.DataFrame:
    """
    Extract: Read raw CSV into a DataFrame.
    In production this could be: S3 bucket, REST API, FTP, or a database query.
    """
    log.info(f"[EXTRACT] Reading CSV from: {csv_path}")
    if not csv_path.exists():
        raise FileNotFoundError(f"Source file not found: {csv_path}")

    df = pd.read_csv(csv_path, dtype=str)   # Read everything as str first
    log.info(f"[EXTRACT] Loaded {len(df):,} rows × {len(df.columns)} columns")
    log.info(f"[EXTRACT] Columns: {list(df.columns)}")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# CLEAN
# ═══════════════════════════════════════════════════════════════════════════════

def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean: Handle nulls, type coercion, format normalisation, and bad records.
    """
    log.info("[CLEAN] Starting data cleaning …")
    original_count = len(df)

    # 1. Strip whitespace from all string columns
    str_cols = df.select_dtypes("object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())

    # 2. Normalise email to lowercase
    df["email"] = df["email"].str.lower()

    # 3. Standardise order_date (handles both YYYY-MM-DD and YYYY/MM/DD)
    df["order_date"] = pd.to_datetime(
        df["order_date"].str.replace("/", "-"), errors="coerce"
    )

    # 4. Coerce numeric columns
    df["quantity"]   = pd.to_numeric(df["quantity"],   errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["order_id"]   = pd.to_numeric(df["order_id"],   errors="coerce")

    # 5. Drop rows with invalid / unparseable dates
    bad_dates = df["order_date"].isna()
    if bad_dates.any():
        log.warning(f"[CLEAN] Dropping {bad_dates.sum()} rows with invalid dates")
        df = df[~bad_dates]

    # 6. Drop rows with negative or zero quantity (data quality issue)
    bad_qty = df["quantity"] <= 0
    if bad_qty.any():
        log.warning(f"[CLEAN] Dropping {bad_qty.sum()} rows with invalid quantity")
        df = df[~bad_qty]

    # 7. Fill missing emails with a placeholder
    missing_email = df["email"].isna() | (df["email"] == "")
    df.loc[missing_email, "email"] = "unknown@noemail.com"
    log.info(f"[CLEAN] {missing_email.sum()} missing emails replaced with placeholder")

    # 8. Standardise status to title-case
    df["status"] = df["status"].str.lower().str.strip()

    # 9. Remove duplicate order IDs (keep first)
    dupes = df.duplicated(subset=["order_id"])
    if dupes.any():
        log.warning(f"[CLEAN] Removing {dupes.sum()} duplicate order_ids")
        df = df.drop_duplicates(subset=["order_id"], keep="first")

    cleaned_count = len(df)
    log.info(
        f"[CLEAN] Complete — {original_count - cleaned_count} rows removed, "
        f"{cleaned_count} rows retained"
    )
    return df.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSFORM
# ═══════════════════════════════════════════════════════════════════════════════

def transform(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Transform: Enrich and derive business metrics.
    Returns a dict of DataFrames ready for loading (star-schema style).
    """
    log.info("[TRANSFORM] Starting transformations …")

    # ── Derived columns ──────────────────────────────────────────────────────
    df["total_price"]    = (df["quantity"] * df["unit_price"]).round(2)
    df["order_year"]     = df["order_date"].dt.year
    df["order_month"]    = df["order_date"].dt.month
    df["order_month_nm"] = df["order_date"].dt.strftime("%B")
    df["order_week"]     = df["order_date"].dt.isocalendar().week.astype(int)
    df["is_high_value"]  = (df["total_price"] > 1000).astype(int)

    # ── Gap Analysis: flag orders with missing emails ─────────────────────────
    df["email_gap"] = (df["email"] == "unknown@noemail.com").astype(int)

    # ── Fact table: orders ────────────────────────────────────────────────────
    fact_orders = df[[
        "order_id", "customer_name", "email", "product", "category",
        "quantity", "unit_price", "total_price", "order_date",
        "region", "status", "order_year", "order_month",
        "order_month_nm", "order_week", "is_high_value", "email_gap",
    ]].copy()

    # ── Dimension: product summary ────────────────────────────────────────────
    dim_products = (
        df.groupby(["product", "category"])
        .agg(
            total_units_sold=("quantity",    "sum"),
            total_revenue   =("total_price", "sum"),
            order_count     =("order_id",    "count"),
            avg_unit_price  =("unit_price",  "mean"),
        )
        .round(2)
        .reset_index()
    )

    # ── Dimension: regional summary ───────────────────────────────────────────
    dim_regions = (
        df.groupby("region")
        .agg(
            total_revenue=("total_price", "sum"),
            order_count  =("order_id",    "count"),
            avg_order_val=("total_price", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )

    # ── Aggregate: monthly revenue trend ─────────────────────────────────────
    agg_monthly = (
        df[df["status"] != "cancelled"]
        .groupby(["order_year", "order_month", "order_month_nm"])
        .agg(
            total_revenue=("total_price", "sum"),
            order_count  =("order_id",    "count"),
        )
        .round(2)
        .reset_index()
        .sort_values(["order_year", "order_month"])
    )

    # ── Gap Analysis summary ──────────────────────────────────────────────────
    gap_analysis = pd.DataFrame([{
        "run_timestamp"        : datetime.now().isoformat(),
        "total_orders"         : len(df),
        "completed_orders"     : (df["status"] == "completed").sum(),
        "cancelled_orders"     : (df["status"] == "cancelled").sum(),
        "pending_orders"       : (df["status"] == "pending").sum(),
        "missing_email_count"  : df["email_gap"].sum(),
        "high_value_orders"    : df["is_high_value"].sum(),
        "total_revenue"        : round(df.loc[df["status"] != "cancelled", "total_price"].sum(), 2),
        "avg_order_value"      : round(df["total_price"].mean(), 2),
    }])

    log.info(f"[TRANSFORM] fact_orders   : {len(fact_orders):,} rows")
    log.info(f"[TRANSFORM] dim_products  : {len(dim_products):,} rows")
    log.info(f"[TRANSFORM] dim_regions   : {len(dim_regions):,} rows")
    log.info(f"[TRANSFORM] agg_monthly   : {len(agg_monthly):,} rows")
    log.info(f"[TRANSFORM] gap_analysis  : {len(gap_analysis):,} rows")

    return {
        "fact_orders"  : fact_orders,
        "dim_products" : dim_products,
        "dim_regions"  : dim_regions,
        "agg_monthly"  : agg_monthly,
        "gap_analysis" : gap_analysis,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LOAD
# ═══════════════════════════════════════════════════════════════════════════════

def load(tables: dict[str, pd.DataFrame], db_path: Path = DB_PATH) -> None:
    """
    Load: Persist all DataFrames into SQLite using replace strategy.
    Swap DB_PATH for a PostgreSQL connection string to go cloud-ready.
    """
    log.info(f"[LOAD] Connecting to database: {db_path}")

    with sqlite3.connect(db_path) as conn:
        for table_name, df in tables.items():
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            log.info(f"[LOAD] ✓ Wrote {len(df):,} rows → '{table_name}'")

        # Create a helpful view for BI / dashboards
        conn.execute("""
            CREATE VIEW IF NOT EXISTS vw_completed_orders AS
            SELECT *
            FROM fact_orders
            WHERE status = 'completed';
        """)

    log.info("[LOAD] All tables loaded successfully.")


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

def run_pipeline(csv_path: Path = CSV_PATH, db_path: Path = DB_PATH) -> bool:
    """
    Orchestrate Extract → Clean → Transform → Load.
    Returns True on success, False on failure.
    """
    log.info("=" * 60)
    log.info("  ETL PIPELINE STARTED")
    log.info(f"  Run timestamp: {datetime.now():%Y-%m-%d %H:%M:%S}")
    log.info("=" * 60)

    try:
        raw_df     = extract(csv_path)
        clean_df   = clean(raw_df)
        tables     = transform(clean_df)
        load(tables, db_path)

        log.info("=" * 60)
        log.info("  PIPELINE COMPLETED SUCCESSFULLY ✓")
        log.info("=" * 60)
        return True

    except Exception as exc:
        log.error(f"[PIPELINE] FAILED — {exc}", exc_info=True)
        return False


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    success = run_pipeline()
    exit(0 if success else 1)
