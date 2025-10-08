#!/bin/bash
#
# Wrapper script for cron jobs
# Provides proper logging and error handling
#

set -euo pipefail

LOG_DIR="/home/user/local-analytics/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/pipeline_$TIMESTAMP.log"

cd /home/user/local-analytics

echo "=== Pipeline started at $(date) ===" | tee -a "$LOG_FILE"

if make all 2>&1 | tee -a "$LOG_FILE"; then
    echo "[OK] Pipeline succeeded" | tee -a "$LOG_FILE"
else
    echo "[FAIL] Pipeline failed" | tee -a "$LOG_FILE"
    # Optional: Send notification
    # curl -X POST your-webhook-url -d "Pipeline failed, check $LOG_FILE"
    exit 1
fi
