"""
tests/test_pipeline.py — Unit tests for Extract, Clean, and Transform stages.
Run with:  python -m pytest tests/ -v
"""

import io
import sys
import pytest
import pandas as pd
from pathlib import Path

# Allow importing from parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline import clean, transform


# ─── Fixtures ─────────────────────────────────────────────────────────────────

SAMPLE_CSV = """order_id,customer_name,email,product,category,quantity,unit_price,order_date,region,status
1,Alice,alice@test.com,Laptop,Electronics,2,999.99,2024-01-15,NSW,completed
2,Bob,,Mouse,Electronics,3,29.99,2024-01-16,VIC,completed
3,Carol,carol@test.com,Chair,Furniture,1,299.00,2024/01/17,QLD,pending
4,Dave,dave@test.com,Desk,Furniture,-1,499.00,2024-01-18,SA,completed
5,Eve,eve@TEST.COM,Monitor,Electronics,1,449.00,2024-01-19,WA,cancelled
1,Alice,alice@test.com,Laptop,Electronics,2,999.99,2024-01-15,NSW,completed
"""


@pytest.fixture
def raw_df() -> pd.DataFrame:
    return pd.read_csv(io.StringIO(SAMPLE_CSV), dtype=str)


@pytest.fixture
def clean_df(raw_df) -> pd.DataFrame:
    return clean(raw_df)


# ─── Extract Tests ────────────────────────────────────────────────────────────

class TestExtract:
    def test_csv_loads(self, raw_df):
        assert len(raw_df) == 6

    def test_columns_present(self, raw_df):
        expected = {"order_id", "customer_name", "email", "product",
                    "quantity", "unit_price", "order_date", "status"}
        assert expected.issubset(set(raw_df.columns))


# ─── Clean Tests ──────────────────────────────────────────────────────────────

class TestClean:
    def test_removes_negative_quantity(self, clean_df):
        assert (clean_df["quantity"] > 0).all(), \
            "All quantities should be positive after cleaning"

    def test_removes_duplicate_order_ids(self, clean_df):
        assert clean_df["order_id"].nunique() == len(clean_df), \
            "No duplicate order_ids should remain"

    def test_email_lowercased(self, clean_df):
        emails = clean_df["email"].dropna()
        assert (emails == emails.str.lower()).all(), \
            "All emails should be lowercase"

    def test_missing_email_filled(self, clean_df):
        assert clean_df["email"].isna().sum() == 0, \
            "No null emails — should be replaced with placeholder"
        assert "unknown@noemail.com" in clean_df["email"].values

    def test_date_parsed(self, clean_df):
        assert pd.api.types.is_datetime64_any_dtype(clean_df["order_date"]), \
            "order_date should be datetime type"

    def test_slash_date_normalised(self, clean_df):
        """2024/01/17 (slash-separated) should parse correctly."""
        assert clean_df["order_date"].isna().sum() == 0

    def test_row_count_after_cleaning(self, clean_df):
        # 6 rows minus 1 duplicate (order_id=1) minus 1 negative qty = 4
        assert len(clean_df) == 4

    def test_status_lowercase(self, clean_df):
        assert clean_df["status"].str.lower().equals(clean_df["status"]), \
            "Status values should all be lowercase"


# ─── Transform Tests ──────────────────────────────────────────────────────────

class TestTransform:
    def test_total_price_calculated(self, clean_df):
        tables = transform(clean_df)
        fo = tables["fact_orders"]
        expected = (fo["quantity"] * fo["unit_price"]).round(2)
        pd.testing.assert_series_equal(fo["total_price"], expected, check_names=False)

    def test_is_high_value_flag(self, clean_df):
        tables = transform(clean_df)
        fo = tables["fact_orders"]
        high = fo[fo["is_high_value"] == 1]
        assert (high["total_price"] > 1000).all()

    def test_email_gap_flag(self, clean_df):
        tables = transform(clean_df)
        fo = tables["fact_orders"]
        assert "email_gap" in fo.columns
        assert fo["email_gap"].isin([0, 1]).all()

    def test_output_tables_exist(self, clean_df):
        tables = transform(clean_df)
        for expected in ["fact_orders", "dim_products", "dim_regions",
                         "agg_monthly", "gap_analysis"]:
            assert expected in tables, f"Missing table: {expected}"

    def test_dim_products_aggregation(self, clean_df):
        tables = transform(clean_df)
        dp = tables["dim_products"]
        assert "total_revenue" in dp.columns
        assert (dp["total_revenue"] >= 0).all()

    def test_gap_analysis_totals(self, clean_df):
        tables = transform(clean_df)
        ga = tables["gap_analysis"].iloc[0]
        assert ga["total_orders"] == len(clean_df)
        assert ga["missing_email_count"] >= 0

    def test_date_parts_extracted(self, clean_df):
        tables = transform(clean_df)
        fo = tables["fact_orders"]
        assert "order_year" in fo.columns
        assert "order_month" in fo.columns
        assert "order_month_nm" in fo.columns
        assert fo["order_year"].iloc[0] == 2024
