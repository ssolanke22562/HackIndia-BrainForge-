# Incident Postmortem: Database Connection Pool Exhaustion (INC-8821)

**Date of Incident:** 2026-09-14 14:22 UTC  
**Severity:** P1 - High  
**Duration:** 28 minutes  
**Impact:** 4.2% of API requests returned HTTP 500 Internal Server Error during peak traffic spike.

## Executive Summary
A sudden 300% spike in concurrent `/ask` RAG queries caused SQLite connection pool starvation. Because background vector search was executing nested uncommitted read locks without `busy_timeout` backoff, worker threads hung waiting for database access.

## Root Cause Analysis
1. `SQLAlchemy` engine pool size was configured to default `pool_size=5, max_overflow=10`.
2. Several long-running graph traversal queries were executing on the main SQLite thread rather than using read-only connection replicas.
3. WAL journal mode was enabled, but `PRAGMA busy_timeout` was omitted, causing instant `sqlite3.OperationalError: database is locked` exceptions after 100ms.

## Remediation Steps Taken
- [x] Configured SQLite PRAGMA: `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000; PRAGMA synchronous=NORMAL;`
- [x] Increased connection pool limits in `backend/config.py`: `pool_size=20, max_overflow=30`.
- [x] Separated FAISS vector indexing into an in-memory lock-free snapshot with background sync.
- [x] Added Prometheus latency telemetry alerts for query durations exceeding 500ms.
