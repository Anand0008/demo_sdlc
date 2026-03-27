"""
Security headers middleware for all API responses.
Related Jira: IN-8 — Add HSTS, Content-Security-Policy, and X-Frame-Options
headers to all API responses.

Standard: See Confluence > API Design Standards > Security Headers
"""
from flask import Flask


SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cache-Control": "no-store",
}


def apply_security_headers(app: Flask) -> None:
    """
    Register an after-request hook that injects security headers
    into every API response. Implements IN-8 requirements.
    """
    @app.after_request
    def add_security_headers(response):
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
