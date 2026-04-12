"""Request Validation and Size Limiting"""

import json

from fastapi import HTTPException, Request
from shared.logger import setup_logger
from starlette.middleware.base import BaseHTTPMiddleware

logger = setup_logger("request_validation")


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size"""

    def __init__(self, app, max_size: int = 1_048_576):  # 1MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")

            if content_length:
                content_length = int(content_length)
                if content_length > self.max_size:
                    logger.warning(
                        f"Request too large: {content_length} bytes from {request.client.host}"
                    )
                    return HTTPException(
                        413, f"Request body too large. Max size: {self.max_size} bytes"
                    )

        response = await call_next(request)
        return response


class ContentTypeValidationMiddleware(BaseHTTPMiddleware):
    """Validate Content-Type header"""

    ALLOWED_CONTENT_TYPES = {
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
    }

    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").split(";")[0].strip()

            if content_type and content_type not in self.ALLOWED_CONTENT_TYPES:
                logger.warning(
                    f"Invalid content-type: {content_type} from {request.client.host}"
                )
                raise HTTPException(415, f"Unsupported content type: {content_type}")

        response = await call_next(request)
        return response


async def validate_json_body(request: Request) -> dict:
    """Validate and parse JSON body safely"""
    try:
        body = await request.body()

        if len(body) == 0:
            return {}

        if len(body) > 1_048_576:  # 1MB
            raise HTTPException(413, "Request body too large")

        data = json.loads(body)

        if not isinstance(data, dict):
            raise HTTPException(400, "Request body must be a JSON object")

        return data

    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON from {request.client.host}: {e}")
        raise HTTPException(400, "Invalid JSON format")
    except Exception as e:
        logger.error(f"Error parsing request body: {e}")
        raise HTTPException(400, "Failed to parse request body")
