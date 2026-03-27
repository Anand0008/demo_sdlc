"""
X-Request-ID middleware for end-to-end distributed request tracing.
Related Jira: IN-6 — Add X-Request-ID header to all requests and responses.

Standard: See Confluence > Request Tracing Standards — X-Request-ID
"""
import uuid
import logging
from flask import Flask, g, request

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


def _get_or_generate_request_id() -> str:
    """Return incoming X-Request-ID or generate a new UUID v4."""
    incoming = request.headers.get(REQUEST_ID_HEADER)
    if incoming and len(incoming) <= 64:  # Validate length to prevent header injection
        return incoming
    return str(uuid.uuid4())


def apply_request_id(app: Flask) -> None:
    """
    Register before/after request hooks to:
    1. Parse or generate X-Request-ID before the request is handled.
    2. Echo the X-Request-ID in the response headers.
    3. Inject the request ID into every log line via a log filter.
    """

    @app.before_request
    def set_request_id():
        g.request_id = _get_or_generate_request_id()
        logger.debug("request_started", extra={"request_id": g.request_id})

    @app.after_request
    def echo_request_id(response):
        request_id = getattr(g, "request_id", "unknown")
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class RequestIdFilter(logging.Filter):
    """
    Logging filter that injects the current request ID into every log record.
    Attach to your root logger so all log lines carry the trace ID.

    Usage:
        import logging
        from request_tracing_x_request_id.middleware import RequestIdFilter
        logging.getLogger().addFilter(RequestIdFilter())
    """
    def filter(self, record):
        record.request_id = getattr(g, "request_id", "no-request-context")
        return True
