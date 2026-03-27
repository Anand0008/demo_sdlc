# Health Check & Readiness Probe Design

This module implements liveness and readiness endpoints for the service,
as defined in the Telomere Health Check Confluence page.

## Endpoints

| Endpoint   | Purpose                          | Related Jira |
|------------|----------------------------------|--------------|
| `GET /health` | Liveness — is the process alive? | IN-7 |
| `GET /ready`  | Readiness — can it serve traffic? | IN-7 |
| `GET /metrics` | Basic Prometheus-style metrics   | IN-7 |

## Design Decisions
- `/health` must respond in < 200ms (no DB calls)
- `/ready` checks DB connectivity and Redis availability
- Both return `{"status": "ok"}` or `{"status": "degraded", "checks": {...}}`
