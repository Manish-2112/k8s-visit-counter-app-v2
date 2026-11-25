#!/usr/bin/env bash
# Week 10 Live Demo: Generates concurrent CPU load against /api/load to trigger HPA scaling
set -euo pipefail

TARGET_URL="${1:-http://localhost:30080}"
CONCURRENCY="${2:-12}"
DURATION_SEC="${3:-90}"

echo "Starting load test against ${TARGET_URL}/api/load (${CONCURRENCY} workers for ${DURATION_SEC}s)..."
echo "In another terminal, watch HPA live with: kubectl get hpa,pods -n visit-counter -w"

END=$((SECONDS + DURATION_SEC))
worker() {
  while [ $SECONDS -lt $END ]; do
    curl -s "${TARGET_URL}/api/load?iterations=350000" >/dev/null || true
  done
}

for _ in $(seq 1 "$CONCURRENCY"); do
  worker &
done

wait
echo "Load test complete. Watch HPA scale back down after the 60s stabilization window."
