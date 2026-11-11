"""Offline tests for login-state persistence and expiry handling."""

from __future__ import annotations

import json
import time

from app.core.config import Settings
from app.models.social import SocialAuthState, SocialPlatform
from app.platforms.browser import cookie_header, storage_state_path
from app.services.social_auth import SocialAuthManager


def _write_state(settings: Settings, platform: SocialPlatform, expires: float) -> None:
    path = storage_state_path(settings, platform)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "cookies": [
                    {
                        "name": "SESSDATA",
                        "value": "test-cookie",
                        "domain": ".bilibili.com",
                        "path": "/",
                        "expires": expires,
                    }
                ],
                "origins": [],
            }
        ),
        encoding="utf-8",
    )


def test_auth_state_persistence_and_cookie_use(tmp_path):
    settings = Settings(social_state_dir=str(tmp_path))
    manager = SocialAuthManager(settings)
    assert manager.status(SocialPlatform.BILIBILI).state is SocialAuthState.NOT_LOGGED_IN

    _write_state(settings, SocialPlatform.BILIBILI, time.time() + 3600)
    manager._write_meta(
        SocialPlatform.BILIBILI,
        {"account_name": "测试账号", "last_login_at": "2026-11-11T00:00:00+00:00"},
    )
    status = manager.status(SocialPlatform.BILIBILI)
    assert status.state is SocialAuthState.LOGGED_IN
    assert status.account_name == "测试账号"
    assert "SESSDATA=test-cookie" in cookie_header(settings, SocialPlatform.BILIBILI)


def test_expired_cookie_is_reported(tmp_path):
    settings = Settings(social_state_dir=str(tmp_path))
    manager = SocialAuthManager(settings)
    _write_state(settings, SocialPlatform.XIAOHONGSHU, time.time() - 60)
    status = manager.status(SocialPlatform.XIAOHONGSHU)
    assert status.state is SocialAuthState.EXPIRED
    assert status.logged_in is False


async def test_logout_deletes_saved_state(tmp_path):
    settings = Settings(social_state_dir=str(tmp_path))
    manager = SocialAuthManager(settings)
    _write_state(settings, SocialPlatform.DOUYIN, time.time() + 3600)
    manager._write_meta(SocialPlatform.DOUYIN, {"account_name": "测试账号"})
    assert manager.status(SocialPlatform.DOUYIN).logged_in is True

    result = await manager.logout(SocialPlatform.DOUYIN)
    assert result.state is SocialAuthState.NOT_LOGGED_IN
    assert not storage_state_path(settings, SocialPlatform.DOUYIN).exists()
