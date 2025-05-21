from fastapi import APIRouter, Depends, HTTPException

from app.apis.models.mount import MountRequest, MountResponse, MountListResponse
from app.apis.services.mount_service import MountService
from app.logger import logger


router = APIRouter()


@router.post("/mount", response_model=MountResponse, summary="挂载本地文件夹到工作区")
async def mount_workspace(request: MountRequest):
    """
    挂载本地文件夹到工作区

    - **user_id**: 用户ID
    - **workspace_id**: 工作区ID
    - **local_path**: 本地文件夹绝对路径
    - **description**: 挂载描述信息（可选）

    挂载成功后，将重启开发容器以应用新的挂载配置
    """
    try:
        mount_service = MountService()
        result = mount_service.mount_workspace(
            user_id=request.user_id,
            workspace_id=request.workspace_id,
            local_path=request.local_path,
            description=request.description
        )

        return result
    except Exception as e:
        logger.error(f"处理挂载请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理挂载请求时发生错误: {str(e)}")


@router.delete("/mount/{user_id}/{workspace_id}", response_model=MountResponse, summary="卸载工作区挂载")
async def unmount_workspace(user_id: str, workspace_id: str):
    """
    卸载工作区挂载

    - **user_id**: 用户ID
    - **workspace_id**: 要卸载的工作区ID

    卸载成功后，将重启开发容器以应用新的挂载配置
    """
    try:
        mount_service = MountService()
        result = mount_service.unmount_workspace(user_id, workspace_id)

        return result
    except Exception as e:
        logger.error(f"处理卸载请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理卸载请求时发生错误: {str(e)}")


@router.get("/mounts", response_model=MountListResponse, summary="获取所有挂载信息")
async def list_mounts():
    """
    获取所有挂载信息列表
    """
    try:
        mount_service = MountService()
        result = mount_service.list_mounts()

        return result
    except Exception as e:
        logger.error(f"获取挂载列表时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取挂载列表时发生错误: {str(e)}")


@router.get("/mount/{user_id}/{workspace_id}", response_model=MountResponse, summary="获取指定工作区挂载信息")
async def get_mount_info(user_id: str, workspace_id: str):
    """
    获取指定工作区挂载信息

    - **user_id**: 用户ID
    - **workspace_id**: 工作区ID
    """
    try:
        mount_service = MountService()
        result = mount_service.get_mount_info(user_id, workspace_id)

        return result
    except Exception as e:
        logger.error(f"获取挂载信息时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取挂载信息时发生错误: {str(e)}")


@router.post("/restart-container", response_model=MountResponse, summary="重启开发容器")
async def restart_container():
    """
    重启开发容器

    用于手动触发容器重启，一般在挂载或卸载操作后自动执行
    """
    try:
        mount_service = MountService()
        result = mount_service.restart_container()

        return result
    except Exception as e:
        logger.error(f"重启容器时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重启容器时发生错误: {str(e)}")

# 测试接口 - 仅用于开发调试
@router.get("/test-monitor", response_model=MountResponse, summary="测试监控容器连接")
async def test_monitor_connection():
    """
    测试监控容器连接状态

    用于检查开发容器是否可以连接到监控容器
    """
    try:
        mount_service = MountService()
        result = mount_service.test_monitor_connection()

        return result
    except Exception as e:
        logger.error(f"测试监控容器连接时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"测试监控容器连接时发生错误: {str(e)}")
