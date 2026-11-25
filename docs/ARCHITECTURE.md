# Production Architecture & CI/CD Flow (Weeks 9–11)

## System Architecture
```
[User Browser]
      │
      ▼
[AWS ALB Ingress / Traefik Ingress]
      │
      ▼
[frontend-service (ClusterIP / NodePort)]
      │
      ▼
[Frontend Pods x2 (Unprivileged Nginx :8080)]
      │  (Reverse Proxy /api/*)
      ▼
[backend-service (ClusterIP :8000)]
      │
      ▼
[Backend Pods x2..6 (FastAPI :8000, HPA + PDB + /metrics)]
      ├──► [redis-service (ClusterIP :6379)] ──► Redis Pod (Live Visit Counter)
      └──► [postgres-headless (:5432)] ────────► PostgreSQL StatefulSet (PVC / AWS EBS)
```

## Production CI/CD Flow (Week 11)
```
GitHub Push
   │
   ▼
Jenkins Pipeline
   ├─► 1. Ruff Lint + Pytest (JUnit XML report)
   ├─► 2. Multi-stage Docker Build (Immutable tag: v<BUILD>-<GIT_SHA>)
   ├─► 3. Trivy Container Vulnerability Scan
   ├─► 4. Push Images to AWS ECR (with scan-on-push & lifecycle policy)
   ├─► 5. Fetch DB Secrets from AWS Systems Manager (SSM) Parameter Store
   ├─► 6. Kustomize Deploy + Zero-Downtime Rolling Update on AWS EKS
   ├─► 7. In-Cluster Smoke Test (/healthz, /readyz, /api/visits)
   └─► 8. Automatic Rollback (`kubectl rollout undo`) on Failure
```

## AWS CodePipeline Overview (Week 11)
While this project runs on Jenkins, `aws/buildspec.yml` provides the equivalent native AWS setup:
- **Source Stage**: AWS CodeConnections (GitHub).
- **Build Stage**: AWS CodeBuild executing `aws/buildspec.yml` (runs `pytest`, builds & pushes to ECR, pulls SSM parameters).
- **Deploy Stage**: CodeBuild or EKS Deploy action updating the EKS cluster with zero-downtime rolling updates.
