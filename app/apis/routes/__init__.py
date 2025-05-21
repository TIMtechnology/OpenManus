from fastapi import APIRouter

from app.apis.routes.tasks import router as tasks_router
from app.apis.routes.tools import router as tools_router
from app.apis.routes.mounts import router as mounts_router

router = APIRouter()

router.include_router(tools_router)
router.include_router(tasks_router)
router.include_router(mounts_router, prefix="/container", tags=["容器管理"])
