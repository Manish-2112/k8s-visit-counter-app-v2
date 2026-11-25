# Production K8s Visit Counter & Guestbook (Weeks 8–11 DevOps Capstone)

A production-grade, 4-tier cloud-native application (**FastAPI + Unprivileged Nginx + Redis + PostgreSQL StatefulSet**) built to demonstrate end-to-end **Kubernetes (Weeks 8–10)** and **AWS + Jenkins CI/CD (Week 11)**.

## Repository Structure

- `backend/`: FastAPI API with JSON structured logging, Prometheus `/metrics`, `/healthz`, `/readyz`, `/api/load` (HPA demo), `pytest` suite, and multi-stage non-root `Dockerfile`.
- `frontend/`: Unprivileged Nginx (`:8080`) UI showing live Redis visit count, active Pod hostname, and App Version badge.
- `k8s/week8-basics/`: Standalone Nginx Deployment + probes for Week 8 Basics.
- `k8s/base/`: Production manifests (Namespace, ResourceQuota, LimitRange, ConfigMap, Secret, PostgreSQL StatefulSet + PVC, Redis, Backend/Frontend Deployments with zero-downtime `RollingUpdate`, HPA, PDB, NetworkPolicy).
- `k8s/overlays/`: Kustomize overlays for `aws-eks/` (ECR + ALB Ingress) and `local-k3s/` (Local Registry + NodePort/Traefik).
- `monitoring/`: Prometheus `ServiceMonitor` manifest.
- `aws/`: `eks-cluster.yaml` (`eksctl`), `setup-ecr-ssm.sh` (ECR + SSM Parameter Store), and `buildspec.yml` (CodePipeline/CodeBuild reference).
- `scripts/`: `load-test.sh` (triggers HPA live) and `rollback-test.sh` (simulates broken release + rollback).
- `docs/`: `WEEK8_K8S_NOTES.md`, `ARCHITECTURE.md`, and `LIVE_HANDS_ON_RUNBOOK.md`.
- `Jenkinsfile`: Parameterized production pipeline (Lint → Pytest + JUnit → Multi-stage Docker Build → Trivy Scan → ECR/Local Push → AWS SSM Secret Sync → EKS/K3s Rolling Deploy → Smoke Test → Auto-Rollback).

## Quick Start

See [`docs/LIVE_HANDS_ON_RUNBOOK.md`](docs/LIVE_HANDS_ON_RUNBOOK.md) for the complete Week 8 → Week 11 live demonstration commands.
