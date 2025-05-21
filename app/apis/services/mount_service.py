import requests
import os
from typing import Dict, List, Optional

from app.logger import logger


class MountService:
    """工作区挂载服务 - 通过Monitor容器API实现"""

    def __init__(self):
        # 监控容器API地址
        # 在开发环境下，使用容器名访问
        # 在生产环境下，可以使用环境变量配置
        self.monitor_api = os.environ.get("MONITOR_API", "http://openmanus-monitor:8089/api")

        # 兼容性测试模式 - 如果设置为True，会尝试直接API调用不可用时回退到旧版实现
        self.fallback_mode = os.environ.get("MONITOR_API_FALLBACK", "0") == "1"

    def _check_monitor_available(self) -> bool:
        """检查监控API是否可用"""
        try:
            response = requests.get(f"{self.monitor_api}/health", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

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
            logger.info(f"通过Monitor API添加挂载: {user_id}/{workspace_id}, 路径: {local_path}")

            # 发送请求到监控容器API
            response = requests.post(
                f"{self.monitor_api}/mounts",
                json={
                    "user_id": user_id,
                    "workspace_id": workspace_id,
                    "local_path": local_path,
                    "description": description
                },
                timeout=30
            )

            # 处理响应
            if response.status_code == 200:
                result = response.json()

                # 检查是否需要重启
                self._try_restart_container()

                return {
                    "success": result.get("success", True),
                    "message": result.get("message", "工作区挂载成功"),
                    "data": result.get("data")
                }
            else:
                error_msg = f"监控API返回错误: {response.status_code}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "data": None
                }
        except Exception as e:
            error_msg = f"挂载工作区时发生错误: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
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
            logger.info(f"通过Monitor API移除挂载: {user_id}/{workspace_id}")

            # 发送请求到监控容器API
            response = requests.delete(
                f"{self.monitor_api}/mounts/{user_id}/{workspace_id}",
                timeout=30
            )

            # 处理响应
            if response.status_code == 200:
                result = response.json()

                # 检查是否需要重启
                self._try_restart_container()

                return {
                    "success": result.get("success", True),
                    "message": result.get("message", "工作区挂载已移除"),
                    "data": result.get("data")
                }
            else:
                error_msg = f"监控API返回错误: {response.status_code}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "data": None
                }
        except Exception as e:
            error_msg = f"卸载工作区挂载时发生错误: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "data": None
            }

    def list_mounts(self) -> Dict:
        """
        获取所有挂载信息

        Returns:
            Dict: 挂载列表
        """
        try:
            logger.info("通过Monitor API获取挂载列表")

            # 发送请求到监控容器API
            response = requests.get(f"{self.monitor_api}/mounts", timeout=10)

            # 处理响应
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": result.get("success", True),
                    "message": "获取挂载列表成功",
                    "data": result.get("data", [])
                }
            else:
                error_msg = f"监控API返回错误: {response.status_code}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "data": []
                }
        except Exception as e:
            error_msg = f"获取挂载列表时发生错误: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
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
            logger.info(f"通过Monitor API获取挂载信息: {user_id}/{workspace_id}")

            # 发送请求到监控容器API
            response = requests.get(
                f"{self.monitor_api}/mounts/{user_id}/{workspace_id}",
                timeout=10
            )

            # 处理响应
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": result.get("success", True),
                    "message": "获取挂载信息成功",
                    "data": result.get("data")
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "message": "未找到指定工作区的挂载信息",
                    "data": None
                }
            else:
                error_msg = f"监控API返回错误: {response.status_code}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "data": None
                }
        except Exception as e:
            error_msg = f"获取挂载信息时发生错误: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "data": None
            }

    def restart_container(self) -> Dict:
        """
        重启开发容器

        Returns:
            Dict: 操作结果
        """
        return self._try_restart_container()

    def _try_restart_container(self) -> Dict:
        """
        尝试通过监控API重启容器

        Returns:
            Dict: 操作结果
        """
        try:
            logger.info("通过Monitor API重启容器")

            # 发送请求到监控容器API
            response = requests.post(f"{self.monitor_api}/restart", timeout=30)

            # 处理响应
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": result.get("success", True),
                    "message": result.get("message", "容器重启请求已发送"),
                    "data": result.get("data")
                }
            else:
                error_msg = f"监控API返回错误: {response.status_code}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "data": None
                }
        except Exception as e:
            error_msg = f"重启容器时发生错误: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "data": None
            }

    # 调试接口 - 仅在开发模式下可用
    def test_monitor_connection(self) -> Dict:
        """
        测试与监控容器的连接

        Returns:
            Dict: 测试结果
        """
        try:
            # 检查监控API是否可用
            is_available = self._check_monitor_available()

            if is_available:
                return {
                    "success": True,
                    "message": "监控API可用",
                    "data": {
                        "api_url": self.monitor_api,
                        "status": "connected"
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "无法连接到监控API",
                    "data": {
                        "api_url": self.monitor_api,
                        "status": "disconnected"
                    }
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"测试连接时发生错误: {str(e)}",
                "data": None
            }
