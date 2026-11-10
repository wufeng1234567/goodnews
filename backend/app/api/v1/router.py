"""Aggregate v1 routers."""

from fastapi import APIRouter

from app.api.v1 import factcheck, graph, health, search

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(factcheck.router)
api_router.include_router(search.router)
api_router.include_router(graph.router)
