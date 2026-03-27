"""
Utilities for propagating X-Request-ID to downstream service calls.

When calling another internal service, always forward the current
request ID so the trace can be correlated across services.
"""
import requests as http_client
from flask import g


def get_propagation_headers() -> dict:
    """
    Returns a dict containing the current X-Request-ID for forwarding
    to downstream HTTP calls.
    """
    request_id = getattr(g, "request_id", None)
    if request_id:
        return {"X-Request-ID": request_id}
    return {}


def traced_get(url: str, **kwargs) -> http_client.Response:
    """HTTP GET with automatic X-Request-ID propagation."""
    headers = {**kwargs.pop("headers", {}), **get_propagation_headers()}
    return http_client.get(url, headers=headers, **kwargs)


def traced_post(url: str, **kwargs) -> http_client.Response:
    """HTTP POST with automatic X-Request-ID propagation."""
    headers = {**kwargs.pop("headers", {}), **get_propagation_headers()}
    return http_client.post(url, headers=headers, **kwargs)
