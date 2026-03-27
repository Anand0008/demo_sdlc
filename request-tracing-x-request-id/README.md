# Request Tracing Standards — X-Request-ID

This module implements end-to-end request tracing using the
`X-Request-ID` header, as mandated by the Telomere Request
Tracing Standards Confluence page.

## How It Works

1. On every incoming request, the middleware checks for an `X-Request-ID` header.
2. If absent, it generates a new UUID v4.
3. The ID is stored in Flask's `g` object for use in log lines.
4. The same ID is echoed back in the response headers.

## Related Jira
- **IN-6**: Add X-Request-ID middleware for end-to-end request tracing
