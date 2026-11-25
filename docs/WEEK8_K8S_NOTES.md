# Week 8 Deliverable: Kubernetes Foundations Notes

## 1. Kubernetes Architecture Overview
- **Control Plane (Master Components)**:
  - `kube-apiserver`: Front-end REST API for all cluster operations (`kubectl` talks here).
  - `etcd`: Distributed key-value store holding all cluster state and configuration.
  - `kube-scheduler`: Assigns newly created Pods to eligible Worker Nodes based on CPU/memory requests.
  - `kube-controller-manager`: Runs reconciliation loops (ReplicaSet, Deployment, Node controllers) to maintain desired state.
- **Worker Node Components**:
  - `kubelet`: Node agent that ensures containers described in PodSpecs are running and healthy.
  - `kube-proxy`: Maintains network rules (iptables/IPVS) for Kubernetes Service routing.
  - **Container Runtime** (`containerd`): Pulls images and runs containers.

## 2. Core Workload Hierarchy
`Deployment` -> manages `ReplicaSet` -> maintains desired count of `Pods` -> runs `Containers`.

## 3. Week 8 Live Hands-On Commands (Nginx Assignment)
```bash
# Inspect cluster nodes
kubectl get nodes -o wide

# Deploy standalone Nginx with liveness & readiness probes
kubectl apply -f k8s/week8-basics/nginx-deployment.yaml

# Inspect Deployment, ReplicaSet, and Pods
kubectl get deploy,rs,pods -l app=nginx-basics
kubectl describe pod -l app=nginx-basics

# Test self-healing: delete one pod and watch ReplicaSet recreate it
kubectl delete pod -l app=nginx-basics --wait=false
kubectl get pods -l app=nginx-basics -w

# Clean up when finished
kubectl delete -f k8s/week8-basics/nginx-deployment.yaml
```
