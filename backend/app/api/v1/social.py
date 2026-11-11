"""Social-platform content and comment ingestion routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import ContainerDep
from app.models.social import (
    SocialFetchRequest,
    SocialFetchResponse,
    SocialPlatformListResponse,
)
from app.platforms.base import (
    PlatformAuthRequired,
    PlatformContentNotFound,
    PlatformDetectError,
    PlatformFetchError,
    SocialPlatformError,
)

router = APIRouter(prefix="/social", tags=["social"])


def _error_detail(exc: SocialPlatformError) -> dict[str, str]:
    detail = {
        "code": exc.code,
        "message": exc.message,
    }
    if exc.platform:
        detail["platform"] = exc.platform.value
    if exc.hint:
        detail["hint"] = exc.hint
    return detail


@router.get("/platforms", response_model=SocialPlatformListResponse)
async def social_platforms(container: ContainerDep) -> SocialPlatformListResponse:
    return container.social_service.platform_list()


@router.post("/fetch", response_model=SocialFetchResponse)
async def fetch_social_content(
    payload: SocialFetchRequest,
    container: ContainerDep,
) -> SocialFetchResponse:
    try:
        return await container.social_service.fetch(payload)
    except PlatformAuthRequired as exc:
        raise HTTPException(status_code=403, detail=_error_detail(exc)) from exc
    except PlatformDetectError as exc:
        raise HTTPException(status_code=400, detail=_error_detail(exc)) from exc
    except PlatformContentNotFound as exc:
        raise HTTPException(status_code=404, detail=_error_detail(exc)) from exc
    except PlatformFetchError as exc:
        raise HTTPException(status_code=502, detail=_error_detail(exc)) from exc
    except SocialPlatformError as exc:
        raise HTTPException(status_code=502, detail=_error_detail(exc)) from exc
