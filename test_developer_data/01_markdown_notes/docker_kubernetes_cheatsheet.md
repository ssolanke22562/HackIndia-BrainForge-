# Docker & Kubernetes Microservices Cheat Sheet

A quick reference guide for deploying and debugging our backend microservices cluster.

## 1. Docker Compose Local Stack
```bash
# Start all services in detached mode with build
docker compose -f docker-compose.yml up --build -d

# View live logs for backend service
docker compose logs -f --tail=100 backend

# Execute interactive shell inside backend container
docker compose exec backend bash
```

## 2. Kubernetes Pod & Log Debugging
```bash
# Get all pods in secondself namespace
kubectl get pods -n secondself -o wide

# Describe failing pod events
kubectl describe pod secondself-backend-78bc99-x2f1 -n secondself

# Stream container logs with timestamps
kubectl logs -f secondself-backend-78bc99-x2f1 -c backend --timestamps

# Port-forward backend API to local machine
kubectl port-forward svc/secondself-backend-svc 8000:8000 -n secondself
```

## 3. SQLite & Performance Inspection
```bash
# Check SQLite WAL file size
ls -lh backend/data/secondself.db*

# Verify WAL mode PRAGMA
sqlite3 backend/data/secondself.db "PRAGMA journal_mode;"
```
