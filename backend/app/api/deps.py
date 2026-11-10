"""FastAPI dependency helpers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.bootstrap import AppContainer


def get_container(request: Request) -> AppContainer:
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise RuntimeError("application container is not initialized")
    return container


# Using Annotated avoids calling Depends() in argument defaults (Ruff B008) and
# is the modern FastAPI style.
ContainerDep = Annotated[AppContainer, Depends(get_container)]
