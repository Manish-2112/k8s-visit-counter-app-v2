#!/usr/bin/env bash
# Week 11 Live Demo: Demonstrates Rolling Update -> Simulated Bad Release -> Rollback
set -euo pipefail

NS="visit-counter"

echo "=== 1. Current Rollout History ==="
kubectl -n "${NS}" rollout history deployment/backend

echo "=== 2. Simulating a broken image release (nginx:nonexistent-tag) ==="
kubectl -n "${NS}" set image deployment/backend backend=nginx:nonexistent-tag
kubectl -n "${NS}" annotate deployment/backend kubernetes.io/change-cause="Simulated broken release" --overwrite

echo "Waiting 15s to observe ImagePullBackOff while existing pods keep serving traffic (maxUnavailable: 0)..."
sleep 15
kubectl -n "${NS}" get pods -l app=backend

echo "=== 3. Executing Production Rollback ==="
kubectl -n "${NS}" rollout undo deployment/backend
kubectl -n "${NS}" rollout status deployment/backend --timeout=120s

echo "=== 4. Verified Healthy State After Rollback ==="
kubectl -n "${NS}" get pods -l app=backend
