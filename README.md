# 🔄 ETL Sales Data Pipeline

[![ETL Pipeline CI](https://github.com/YOUR_USERNAME/etl-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/etl-pipeline/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-style **Extract → Clean → Transform → Load** pipeline built with Python, pandas, and SQLite. Designed to demonstrate core data engineering skills relevant to **Canberra APS / government data roles** including gap analysis, ETL orchestration, data quality checks, and scheduler integration.

---

## 📐 Architecture

```
data/sales_data.csv
        │
        ▼
┌───────────────┐
│   EXTRACT     │  Read CSV (swappable: S3, API, FTP, DB)
└──────┬────────┘
       │
       ▼
┌───────────────┐
│    CLEAN      │  Nulls · type coercion · deduplication · date normalisation
└──────┬────────┘
       │
       ▼
┌───────────────┐
│  TRANSFORM    │  Derived metrics · star-schema tables · gap analysis
└──────┬────────┘
       │
       ▼
┌───────────────┐
│    LOAD       │  SQLite (swap for PostgreSQL / BigQuery in prod)
└───────────────┘
        │
        └── sales_pipeline.db
               ├── fact_orders
               ├── dim_products
               ├── dim_regions
               ├── agg_monthly
               └── gap_analysis
```

---

## 🗂️ Project Structure

```
etl_pipeline/
├── pipeline.py              # Main ETL orchestrator (Extract→Clean→Transform→Load)
├── query_db.py              # Query helper & CLI report generator
├── requirements.txt
├── data/
│   └── sales_data.csv       # Sample dataset (25 rows)
├── logs/                    # Auto-created; daily log files written here
├── tests/
│   └── test_pipeline.py     # pytest unit tests (17 tests)
├── scripts/
│   ├── schedule_cron.sh     # Linux/macOS cron registration
│   └── schedule_windows.ps1 # Windows Task Scheduler registration
└── .github/
    └── workflows/
        └── ci.yml           # GitHub Actions CI (test + run + verify)
```

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/etl-pipeline.git
cd etl-pipeline
pip install -r requirements.txt
```

### 2. Run the pipeline

```bash
python pipeline.py
```

**Sample output:**
```
2024-01-30 09:00:01 | INFO     | ============================================================
2024-01-30 09:00:01 | INFO     |   ETL PIPELINE STARTED
2024-01-30 09:00:01 | INFO     | [EXTRACT] Loaded 25 rows × 10 columns
2024-01-30 09:00:01 | INFO     | [CLEAN]   2 rows removed, 23 rows retained
2024-01-30 09:00:01 | INFO     | [TRANSFORM] fact_orders : 23 rows
2024-01-30 09:00:01 | INFO     | [LOAD] ✓ Wrote 23 rows → 'fact_orders'
2024-01-30 09:00:01 | INFO     |   PIPELINE COMPLETED SUCCESSFULLY ✓
```

### 3. Query results

```bash
python query_db.py
```

### 4. Run tests

```bash
python -m pytest tests/ -v
```

---

## ⚙️ Scheduling

### Linux / macOS (cron)

```bash
chmod +x scripts/schedule_cron.sh
./scripts/schedule_cron.sh        # Registers daily @ 06:00
```

Or manually add to crontab (`crontab -e`):

```
0 6 * * * cd /path/to/etl_pipeline && python3 pipeline.py >> logs/cron.log 2>&1
```

### Windows (Task Scheduler)

```powershell
# Run as Administrator
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\schedule_windows.ps1
```

---

## 🔧 Data Cleaning Rules

| Check | Action |
|---|---|
| Negative / zero quantity | Drop row |
| Invalid / unparseable date | Drop row |
| Duplicate `order_id` | Keep first occurrence |
| Missing email | Replace with `unknown@noemail.com` |
| Date format `YYYY/MM/DD` | Normalise to `YYYY-MM-DD` |
| Email casing | Force lowercase |
| Whitespace in strings | Strip leading/trailing |

---

## 📊 Output Tables (Star Schema)

| Table | Description |
|---|---|
| `fact_orders` | Cleaned + enriched order records |
| `dim_products` | Product-level revenue & unit aggregates |
| `dim_regions` | Regional revenue summary |
| `agg_monthly` | Monthly revenue trend (excluding cancelled) |
| `gap_analysis` | Pipeline run metadata + data quality KPIs |

---

## ☁️ Cloud / PostgreSQL Migration

Swap the SQLite connection in `pipeline.py` for PostgreSQL in one line:

```python
# SQLite (default)
conn = sqlite3.connect("sales_pipeline.db")

# PostgreSQL (production)
from sqlalchemy import create_engine
engine = create_engine("postgresql://user:pass@host:5432/dbname")
df.to_sql("fact_orders", engine, if_exists="replace", index=False)
```

For AWS / Azure cloud, replace the `extract()` function with an S3 or Blob Storage read:

```python
import boto3, io
s3  = boto3.client("s3")
obj = s3.get_object(Bucket="my-bucket", Key="sales_data.csv")
df  = pd.read_csv(io.BytesIO(obj["Body"].read()))
```

---

## 🧪 CI/CD

GitHub Actions runs on every push:
1. Install dependencies  
2. Run all pytest unit tests  
3. Execute pipeline end-to-end  
4. Verify all database tables were created  
5. Upload logs as build artifacts  

---

## 📌 Skills Demonstrated

- **ETL / Data Pipeline Design** — modular Extract, Clean, Transform, Load stages  
- **Gap Analysis** — missing data detection, quality KPIs, audit trail  
- **Data Transformation** — derived metrics, star-schema output, aggregations  
- **Testing** — 17 pytest unit tests covering each stage  
- **Scheduling** — cron (Linux/macOS) and Task Scheduler (Windows)  
- **CI/CD** — GitHub Actions workflow  
- **Cloud-ready** — SQLite swappable for PostgreSQL, BigQuery, or S3-backed sources  

---

## 📄 License

MIT — free to use, adapt, and extend.
