"""Social-platform content, comment and account-session routes."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import ContainerDep
from app.models.social import (
    SocialAuthActionRequest,
    SocialAuthStatus,
    SocialAuthStatusListResponse,
    SocialFetchRequest,
    SocialFetchResponse,
    SocialJobCreateRequest,
    SocialJobStatus,
    SocialPlatform,
    SocialPlatformListResponse,
    SocialReplyResponse,
)
from app.platforms.base import (
    PlatformAuthRequired,
    PlatformContentNotFound,
    PlatformDetectError,
    PlatformFetchError,
    SocialPlatformError,
)
from app.services.social_export import export_result

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


@router.get("/auth/status", response_model=SocialAuthStatusListResponse)
async def social_auth_status(container: ContainerDep) -> SocialAuthStatusListResponse:
    return container.social_auth_manager.status_all()


@router.post("/auth/login", response_model=SocialAuthStatus)
async def social_auth_login(
    payload: SocialAuthActionRequest,
    container: ContainerDep,
) -> SocialAuthStatus:
    return await container.social_auth_manager.start_login(payload.platform)


@router.post("/auth/logout", response_model=SocialAuthStatus)
async def social_auth_logout(
    payload: SocialAuthActionRequest,
    container: ContainerDep,
) -> SocialAuthStatus:
    return await container.social_auth_manager.logout(payload.platform)


@router.post("/auth/refresh", response_model=SocialAuthStatus)
async def social_auth_refresh(
    payload: SocialAuthActionRequest,
    container: ContainerDep,
) -> SocialAuthStatus:
    return await container.social_auth_manager.refresh(payload.platform)


@router.get("/comments/replies", response_model=SocialReplyResponse)
async def social_comment_replies(
    container: ContainerDep,
    platform: Annotated[SocialPlatform, Query()],
    content_id: Annotated[str, Query(min_length=1, max_length=200)],
    root_id: Annotated[str, Query(min_length=1, max_length=200)],
    max_comments: Annotated[int, Query(ge=1, le=50_000)] = 50_000,
) -> SocialReplyResponse:
    if platform is not SocialPlatform.BILIBILI:
        raise HTTPException(
            status_code=501,
            detail={
                "code": "reply_api_unsupported",
                "message": "该平台请通过全量评论任务获取完整子回复。",
            },
        )
    adapter = container.social_service.adapter_for(platform)
    replies = await adapter.fetch_root_replies(
        content_id=content_id,
        root_id=root_id,
        max_comments=max_comments,
    )
    return SocialReplyResponse(
        root_id=root_id,
        replies=replies,
        total_fetched=len(replies),
        has_more=False,
    )


@router.post("/jobs", response_model=SocialJobStatus, status_code=status.HTTP_202_ACCEPTED)
async def create_social_job(
    payload: SocialJobCreateRequest,
    container: ContainerDep,
) -> SocialJobStatus:
    try:
        return await container.social_job_service.create(payload)
    except PlatformDetectError as exc:
        raise HTTPException(status_code=400, detail=_error_detail(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "job_unavailable", "message": str(exc)},
        ) from exc


@router.get("/jobs/{job_id}", response_model=SocialJobStatus)
async def social_job_status(job_id: str, container: ContainerDep) -> SocialJobStatus:
    job = await container.social_job_service.status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="评论任务不存在")
    return job


@router.get("/jobs/{job_id}/export")
async def export_social_job(
    job_id: str,
    container: ContainerDep,
    format: Annotated[str, Query(pattern="^(xlsx|md|txt|excel|markdown|text)$")] = "xlsx",
) -> Response:
    job = await container.social_job_service.status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="评论任务不存在")
    if job.state.value != "completed":
        raise HTTPException(status_code=409, detail="评论任务尚未完成")
    result = await container.social_job_service.result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="任务结果不存在")
    try:
        exported = export_result(result, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    suffix = exported.filename.rsplit(".", 1)[-1]
    return Response(
        content=exported.content,
        media_type=exported.media_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename=goodnews-export.{suffix}; "
                f"filename*=UTF-8''{quote(exported.filename)}"
            ),
        },
    )


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
