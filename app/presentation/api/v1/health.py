from fastapi import APIRouter, Response, status

from app.presentation.api.dependencies import ContainerDep

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness(container: ContainerDep) -> dict:
    """Process is up. Used by the orchestrator to decide on restarts."""
    return {"status": "ok", "instance": container.settings.instance_id}


@router.get("/ready")
async def readiness(container: ContainerDep, response: Response) -> dict:
    """Dependencies reachable. Used by the load balancer to route traffic."""
    checks = {
        "redis": await container.check_redis(),
        "database": await container.check_database(),
    }
    ready = all(checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if ready else "degraded",
        "instance": container.settings.instance_id,
        "checks": checks,
    }
