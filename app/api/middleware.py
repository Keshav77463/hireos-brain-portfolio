from starlette.responses import JSONResponse


class RequestLimitMiddleware:
    """Bound memory and multipart parser exposure, including chunked requests."""

    def __init__(self, app, maximum=3 * 1024 * 1024):
        self.app = app
        self.maximum = maximum

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope["method"] in ("POST", "PUT", "PATCH"):
            parts, size = [], 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > self.maximum:
                    response = JSONResponse(
                        {"detail": "Request body exceeds 3 MiB."}, status_code=413
                    )
                    return await response(scope, receive, send)
                parts.append(chunk)
                if not message.get("more_body"):
                    break
            delivered = False
            original_receive = receive

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": b"".join(parts), "more_body": False}
                return await original_receive()

            receive = replay

        async def headers(message):
            if message["type"] == "http.response.start":
                message["headers"].extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"x-frame-options", b"DENY"),
                        (b"cache-control", b"no-store"),
                    ]
                )
                if scope["path"] not in ("/docs", "/redoc", "/docs/oauth2-redirect"):
                    message["headers"].append(
                        (
                            b"content-security-policy",
                            b"default-src 'self'; script-src 'self'; style-src 'self'; "
                            b"object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
                        )
                    )
            await send(message)

        await self.app(scope, receive, headers)
