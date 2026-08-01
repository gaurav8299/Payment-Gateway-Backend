import platform
import sys

from common.response import APIResponse
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """
    Health Check endpoint verifying system status (Database, Redis, API).
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="System Health Check",
        description="Verifies operational status of Database, Redis Cache, and Gateway Service.",
        responses={200: dict},
    )
    def get(self, request):
        db_healthy = True
        redis_healthy = True
        db_error = None
        redis_error = None

        # Check Database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
        except Exception as e:
            db_healthy = False
            db_error = str(e)

        # Check Redis Cache
        try:
            cache.set("health_check_ping", "pong", timeout=5)
            redis_pong = cache.get("health_check_ping")
            if redis_pong != "pong":
                redis_healthy = False
                redis_error = "Cache read/write mismatch"
        except Exception as e:
            redis_healthy = False
            redis_error = str(e)

        status_code = 200 if (db_healthy and redis_healthy) else 503

        data = {
            "status": "healthy" if status_code == 200 else "degraded",
            "services": {
                "database": {
                    "status": "up" if db_healthy else "down",
                    "error": db_error,
                },
                "redis": {
                    "status": "up" if redis_healthy else "down",
                    "error": redis_error,
                },
            },
        }

        return APIResponse.success(
            data=data,
            message="Health check evaluated successfully",
            status_code=status_code,
        )


class ReadinessCheckView(APIView):
    """
    Readiness Check — indicates whether the service is ready to accept traffic.
    Checks database connectivity and cache availability.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Readiness Check",
        description="Returns 200 if DB and Redis are reachable; 503 otherwise.",
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
            cache.set("readiness_ping", "ok", timeout=5)
            if cache.get("readiness_ping") != "ok":
                raise Exception("Redis read/write mismatch")
        except Exception as e:
            return APIResponse.error(
                message=f"Service not ready: {e}",
                code="SERVICE_UNAVAILABLE",
                status_code=503,
            )

        return APIResponse.success(data={"ready": True}, message="Service is ready.")


class LivenessCheckView(APIView):
    """
    Liveness Check — indicates the application process is alive.
    Always returns 200 if the Django process is running.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Liveness Check",
        description="Returns 200 if the application process is alive.",
    )
    def get(self, request):
        return APIResponse.success(data={"alive": True}, message="Service is alive.")


class VersionInfoView(APIView):
    """
    System Info / Version API returning application metadata.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="System Version Info",
        description="Returns application version, Python version, Django version, and platform.",
    )
    def get(self, request):
        import django

        data = {
            "app_name": "Payment Gateway API",
            "version": getattr(settings, "SPECTACULAR_SETTINGS", {}).get(
                "VERSION", "1.0.0"
            ),
            "python_version": sys.version,
            "django_version": django.__version__,
            "platform": platform.platform(),
            "debug_mode": settings.DEBUG,
        }
        return APIResponse.success(data=data, message="System info retrieved.")
