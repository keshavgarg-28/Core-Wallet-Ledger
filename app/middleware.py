from time import perf_counter

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.logger import get_logger

logger = get_logger(__name__)


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = perf_counter()
        logger.info("Request started: %s %s", request.method, request.url.path)

        try:
            response = await call_next(request)
        except HTTPException as exc:
            duration_ms = (perf_counter() - start_time) * 1000
            logger.warning(
                "HTTP exception: %s %s status=%s detail=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                exc.status_code,
                exc.detail,
                duration_ms,
            )
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        except RequestValidationError as exc:
            duration_ms = (perf_counter() - start_time) * 1000
            logger.warning(
                "Validation exception: %s %s errors=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                exc.errors(),
                duration_ms,
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": exc.errors()},
            )
        except Exception:
            duration_ms = (perf_counter() - start_time) * 1000
            logger.exception(
                "Unhandled exception: %s %s duration_ms=%.2f",
                request.method,
                request.url.path,
                duration_ms,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error."},
            )

        duration_ms = (perf_counter() - start_time) * 1000
        logger.info(
            "Request completed: %s %s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
