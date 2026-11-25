# Live Hands-On Demo Runbook (Weeks 8–11)

Use this checklist when demonstrating the project live or capturing deliverables/screenshots.

## Week 8: Kubernetes Basics

1. `kubectl get nodes -o wide`
2. `kubectl apply -f k8s/week8-basics/nginx-deployment.yaml`
3. `kubectl get deploy,rs,pods,svc -l app=nginx-basics`
4. `kubectl describe pod -l app=nginx-basics` (highlight Liveness/Readiness probes & resource limits)

## Week 9: Multi-Tier App (Services, Ingress, ConfigMap, Secret, Namespace, Quotas)

1. Deploy via Kustomize (`local-k3s` or `aws-eks`):

   ```bash
   kubectl apply -k k8s/overlays/local-k3s/
   ```

2. Verify namespace isolation, quotas, ConfigMap, Secret, Services, and Ingress:

   ```bash
   kubectl get all,cm,secret,ingress,resourcequota,netpol -n visit-counter
   ```

3. Open the UI and click **Refresh Counter** repeatedly to show live load-balancing across backend pods.

## Week 10: Advanced K8s (StatefulSet, PVC, HPA, Rolling Updates, Monitoring)

1. **StatefulSet + PVC Persistence**:
   - Post a guestbook note in the UI.
   - Delete the PostgreSQL StatefulSet pod: `kubectl delete pod postgres-0 -n visit-counter`
   - Wait for `postgres-0` to recreate with the **same pod name** and **same PVC**; refresh UI to prove the note persisted.
2. **HPA Autoscaling Live Demo**:
   - Terminal 1: `kubectl get hpa,pods -n visit-counter -w`
   - Terminal 2: `bash scripts/load-test.sh http://<APP_HOST>:30080 12 90`
   - Watch CPU cross 50% and backend replicas scale from 2 up to 6.
3. **Monitoring**:
   - Verify Prometheus metrics directly: `curl http://<APP_HOST>:30080/api/visits` and inside cluster `curl http://backend-service:8000/metrics`.
   - Check live resource consumption: `kubectl top nodes` and `kubectl top pods -n visit-counter`.
   - (Optional) Apply `monitoring/servicemonitor.yaml` if `kube-prometheus-stack` is installed.

## Week 11: End-to-End AWS Integration (ECR, EKS, SSM, Jenkins, Rollback)

1. Provision ECR + SSM Parameter Store: `bash aws/setup-ecr-ssm.sh`
2. Provision EKS Cluster: `eksctl create cluster -f aws/eks-cluster.yaml`
3. Update `AWS_ACCOUNT_ID` in `Jenkinsfile` and `k8s/overlays/aws-eks/kustomization.yaml`.
4. Trigger Jenkins Pipeline with `DEPLOY_TARGET=aws-eks`, `ACTION=deploy`.
5. Validate live app URL from `kubectl get ingress -n visit-counter`.
6. **Live Rollback Test**:
   - Either run `bash scripts/rollback-test.sh` OR trigger Jenkins Pipeline with `ACTION=rollback`.
   - Verify the version badge in the UI reverts cleanly with zero downtime.
