from typing import Dict, List, Optional

from app.container.mount_manager import MountManager, MountConfig
from app.logger import logger


class MountService:
    """工作区挂载服务"""

    def __init__(self):
        self.mount_manager = MountManager()

    def mount_workspace(self, user_id: str, workspace_id: str, local_path: str, description: Optional[str] = None) -> Dict:
        """
        挂载本地文件夹到工作区

        Args:
            user_id: 用户ID
            workspace_id: 工作区ID
            local_path: 本地文件夹绝对路径
            description: 挂载描述信息

        Returns:
            Dict: 操作结果
        """
        try:
            # 应用挂载并重启容器
            success = self.mount_manager.apply_mount(user_id, workspace_id, local_path)

            if success:
                # 获取最新挂载信息
                mount_info = self.mount_manager.get_mount_info(user_id, workspace_id)

                return {
                    "success": True,
                    "message": "工作区挂载成功",
                    "data": mount_info
                }
            else:
                return {
                    "success": False,
                    "message": "工作区挂载失败",
                    "data": None
                }
        except Exception as e:
            logger.error(f"挂载工作区时发生错误: {str(e)}")
            return {
                "success": False,
                "message": f"挂载工作区时发生错误: {str(e)}",
                "data": None
            }

    def unmount_workspace(self, user_id: str, workspace_id: str) -> Dict:
        """
        卸载工作区挂载

        Args:
            user_id: 用户ID
            workspace_id: 工作区ID

        Returns:
            Dict: 操作结果
        """
        try:
            # 移除挂载配置
            success = self.mount_manager.remove_mount(user_id, workspace_id)

            if success:
                # 重启容器以应用变更
                restart_success = self.mount_manager.restart_dev_container()

                return {
                    "success": restart_success,
                    "message": "工作区挂载卸载成功" if restart_success else "卸载配置成功，但容器重启失败",
                    "data": None
                }
            else:
                return {
                    "success": False,
                    "message": "未找到指定工作区的挂载配置",
                    "data": None
                }
        except Exception as e:
            logger.error(f"卸载工作区挂载时发生错误: {str(e)}")
            return {
                "success": False,
                "message": f"卸载工作区挂载时发生错误: {str(e)}",
                "data": None
            }

    def list_mounts(self) -> Dict:
        """
        获取所有挂载信息

        Returns:
            Dict: 挂载列表
        """
        try:
            mount_list = self.mount_manager.list_mounts()

            return {
                "success": True,
                "message": "获取挂载列表成功",
                "data": mount_list
            }
        except Exception as e:
            logger.error(f"获取挂载列表时发生错误: {str(e)}")
            return {
                "success": False,
                "message": f"获取挂载列表时发生错误: {str(e)}",
                "data": []
            }

    def get_mount_info(self, user_id: str, workspace_id: str) -> Dict:
        """
        获取指定工作区挂载信息

        Args:
            user_id: 用户ID
            workspace_id: 工作区ID

        Returns:
            Dict: 挂载信息
        """
        try:
            mount_info = self.mount_manager.get_mount_info(user_id, workspace_id)

            if mount_info:
                return {
                    "success": True,
                    "message": "获取挂载信息成功",
                    "data": mount_info
                }
            else:
                return {
                    "success": False,
                    "message": "未找到指定工作区的挂载信息",
                    "data": None
                }
        except Exception as e:
            logger.error(f"获取挂载信息时发生错误: {str(e)}")
            return {
                "success": False,
                "message": f"获取挂载信息时发生错误: {str(e)}",
                "data": None
            }

    def restart_container(self) -> Dict:
        """
        重启开发容器

        Returns:
            Dict: 操作结果
        """
        try:
            success = self.mount_manager.restart_dev_container()

            return {
                "success": success,
                "message": "容器重启成功" if success else "容器重启失败",
                "data": None
            }
        except Exception as e:
            logger.error(f"重启容器时发生错误: {str(e)}")
            return {
                "success": False,
                "message": f"重启容器时发生错误: {str(e)}",
                "data": None
            }
