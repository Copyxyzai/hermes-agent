"""Version 1 API router."""

from fastapi import APIRouter

from hermes_api.api.v1.routes.chat import router as chat_router
from hermes_api.api.v1.routes.sessions import router as sessions_router
from hermes_api.api.v1.routes.toolsets import router as toolsets_router

router = APIRouter(prefix="/api/v1")
router.include_router(chat_router)
router.include_router(sessions_router)
router.include_router(toolsets_router)
