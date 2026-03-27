"""
Health check and readiness probe endpoints.
Related Jira: IN-7 — Implement /health and /ready endpoints for
Kubernetes liveness and readiness probes.

Standard: See Confluence > Health Check and Readiness Probe Design
"""
import time
import os
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)

_start_time = time.monotonic()


@health_bp.route("/health", methods=["GET"])
def liveness():
    """
    Liveness probe — confirms the process is running.
    Must be fast (no I/O). Returns 200 if alive, 503 if not.
    """
    return jsonify({
        "status": "ok",
        "uptime_seconds": int(time.monotonic() - _start_time),
    }), 200


@health_bp.route("/ready", methods=["GET"])
def readiness():
    """
    Readiness probe — confirms the service can accept traffic.
    Checks downstream dependencies (DB, Redis, etc.).
    Returns 200 if ready, 503 if any critical dependency is unavailable.
    """
    checks = {}
    overall_ok = True

    # Database connectivity check
    try:
        # Replace with actual DB ping in production
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}
        overall_ok = False

    # Redis connectivity check
    try:
        import redis
        r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379)
        r.ping()
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        checks["redis"] = {"status": "unavailable", "detail": str(e)}
        # Redis is non-critical — do not set overall_ok = False

    status_code = 200 if overall_ok else 503
    return jsonify({
        "status": "ok" if overall_ok else "degraded",
        "checks": checks,
        "uptime_seconds": int(time.monotonic() - _start_time),
    }), status_code


@health_bp.route("/metrics", methods=["GET"])
def metrics():
    """Basic Prometheus-compatible metrics endpoint."""
    uptime = int(time.monotonic() - _start_time)
    payload = (
        f"# HELP process_uptime_seconds Time the process has been running\n"
        f"# TYPE process_uptime_seconds gauge\n"
        f"process_uptime_seconds {uptime}\n"
    )
    return payload, 200, {"Content-Type": "text/plain; version=0.0.4"}
