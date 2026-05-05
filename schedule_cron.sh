#!/usr/bin/env bash
# =============================================================================
# schedule_cron.sh — Register the ETL pipeline as a daily cron job (Linux/macOS)
# =============================================================================
# Usage:
#   chmod +x scripts/schedule_cron.sh
#   ./scripts/schedule_cron.sh
#
# This adds a cron entry that runs the pipeline every day at 06:00 AM.
# Edit the CRON_SCHEDULE variable to change the schedule.
# =============================================================================

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
CRON_SCHEDULE="0 6 * * *"                          # Daily at 06:00 AM
PIPELINE_DIR="$(cd "$(dirname "$0")/.." && pwd)"   # Absolute path to project
PYTHON_BIN="$(which python3)"
LOG_FILE="$PIPELINE_DIR/logs/cron.log"
CRON_CMD="$CRON_SCHEDULE cd $PIPELINE_DIR && $PYTHON_BIN pipeline.py >> $LOG_FILE 2>&1"

echo "──────────────────────────────────────────────"
echo "  ETL Pipeline Cron Scheduler"
echo "──────────────────────────────────────────────"
echo "  Project dir : $PIPELINE_DIR"
echo "  Python      : $PYTHON_BIN"
echo "  Schedule    : $CRON_SCHEDULE  (daily @ 06:00)"
echo "  Log file    : $LOG_FILE"
echo "──────────────────────────────────────────────"

mkdir -p "$PIPELINE_DIR/logs"

# Add cron job (avoid duplicate entries)
CURRENT_CRON="$(crontab -l 2>/dev/null || true)"
if echo "$CURRENT_CRON" | grep -qF "pipeline.py"; then
    echo "⚠️  A pipeline.py cron entry already exists — skipping."
else
    (echo "$CURRENT_CRON"; echo "$CRON_CMD") | crontab -
    echo "✅  Cron job registered successfully."
fi

echo ""
echo "  View current crontab : crontab -l"
echo "  Remove this job      : crontab -e  (then delete the line)"
echo ""

# ── Cron schedule quick-reference ───────────────────────────────────────────
cat <<'EOF'
Common cron schedules:
  "0 6 * * *"     → Daily at 06:00
  "*/30 * * * *"  → Every 30 minutes
  "0 6 * * 1"     → Every Monday at 06:00
  "0 6 1 * *"     → 1st of every month at 06:00
EOF
