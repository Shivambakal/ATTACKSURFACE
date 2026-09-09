"""Health checks and provider status router."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models.base import utcnow
from app.models import User
from app.routers.deps import require_admin
from app.schemas import ProviderHealthOut
from app.services.provider_manager import get_provider_manager

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("")
@router.get("/", include_in_schema=False)
def basic_health() -> dict[str, str]:
    """Basic service health check."""
    return {
        "status": "ok",
        "timestamp": utcnow().isoformat(),
    }


@router.get("/providers", response_model=list[ProviderHealthOut])
async def provider_health(current_user: User = Depends(require_admin)) -> list[ProviderHealthOut]:
    """Check health of all registered providers. Credentials and secrets are NEVER exposed."""
    manager = get_provider_manager()
    results = await manager.health_check_all()

    return [
        ProviderHealthOut(
            name=r.name,
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
            error_summary=r.error_summary,
            recommended_fix=r.recommended_fix,
        )
        for r in results
    ]
