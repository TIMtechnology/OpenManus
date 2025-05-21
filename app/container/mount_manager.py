import os
import json
import logging
import subprocess
import platform
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple

import docker
import yaml
from docker.errors import DockerException
from pydantic import BaseModel, Field, validator

from app.logger import logger
from app.config import config


class MountConfig(BaseModel):
    """工作区挂载配置模型"""

    user_id: str
    workspace_id: str
    local_path: str
    container_path: str = "/workspace"
    description: Optional[str] = None
    created_at: Optional[str] = None


class MountManager:
    """工作区目录挂载管理器"""

    def __init__(self):
        self.client = docker.from_env()
        self.mount_data_file = Path(config.workspace_root) / "mount_data.json"
        self.dev_container_name = "openmanus-core-dev"
        self.compose_file = Path(os.getcwd()) / "docker-compose.dev.yml"
        self._load_mount_data()

    def _load_mount_data(self):
        """加载挂载数据"""
        if not self.mount_data_file.exists():
            self.mount_data = {}
            self._save_mount_data()
        else:
            try:
                with open(self.mount_data_file, "r") as f:
                    self.mount_data = json.load(f)
            except Exception as e:
                logger.error(f"加载挂载数据失败: {str(e)}")
                self.mount_data = {}
                self._save_mount_data()

    def _save_mount_data(self):
        """保存挂载数据"""
        try:
            with open(self.mount_data_file, "w") as f:
                json.dump(self.mount_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存挂载数据失败: {str(e)}")

    def _get_mount_key(self, user_id: str, workspace_id: str) -> str:
        """获取挂载数据的键名"""
        return f"{user_id}:{workspace_id}"

    def get_mount_info(self, user_id: str, workspace_id: str) -> Optional[Dict]:
        """获取挂载信息"""
        key = self._get_mount_key(user_id, workspace_id)
        mount_info = self.mount_data.get(key)
        if mount_info:
            # 添加用户ID和工作区ID到结果中
            mount_info["user_id"] = user_id
            mount_info["workspace_id"] = workspace_id
        return mount_info

    def list_mounts(self) -> List[Dict]:
        """列出所有挂载信息"""
        result = []
        for key, mount_info in self.mount_data.items():
            if ":" in key:
                user_id, workspace_id = key.split(":", 1)
                result.append({
                    "user_id": user_id,
                    "workspace_id": workspace_id,
                    **mount_info
                })
        return result

    def add_mount(self, mount_config: MountConfig) -> bool:
        """添加新的挂载配置"""
        from datetime import datetime

        try:
            # 标准化路径格式
            local_path = str(Path(mount_config.local_path))

            # 创建挂载键
            key = self._get_mount_key(mount_config.user_id, mount_config.workspace_id)

            # 创建挂载配置
            mount_info = {
                "local_path": local_path,
                "container_path": mount_config.container_path,
                "description": mount_config.description,
                "created_at": datetime.now().isoformat()
            }

            # 保存挂载信息
            self.mount_data[key] = mount_info
            self._save_mount_data()

            return True
        except Exception as e:
            logger.error(f"添加挂载失败: {str(e)}")
            return False

    def remove_mount(self, user_id: str, workspace_id: str) -> bool:
        """移除挂载配置"""
        key = self._get_mount_key(user_id, workspace_id)
        if key in self.mount_data:
            del self.mount_data[key]
            self._save_mount_data()
            return True
        return False

    def restart_dev_container(self) -> bool:
        """重启开发容器 - 使用Docker Compose命令"""
        try:
            logger.info(f"重新启动开发容器: {self.dev_container_name}")

            # 使用docker-compose命令而不是Docker API
            # 这样可以保证完全按照docker-compose.dev.yml配置重新创建容器
            result = self._run_docker_compose_command("down")
            if not result[0]:
                logger.error(f"无法停止容器: {result[1]}")
                return False

            # 等待容器完全停止
            time.sleep(2)

            # 重新启动容器
            result = self._run_docker_compose_command("up -d")
            if not result[0]:
                logger.error(f"无法启动容器: {result[1]}")
                return False

            logger.info("容器重启成功")
            return True
        except Exception as e:
            logger.error(f"重启容器过程中发生错误: {str(e)}")
            return False

    def _run_docker_compose_command(self, cmd: str) -> Tuple[bool, str]:
        """运行docker-compose命令"""
        try:
            # 构建完整命令
            docker_compose_file = str(self.compose_file)
            full_cmd = f"docker-compose -f {docker_compose_file} {cmd}"

            logger.info(f"执行命令: {full_cmd}")

            # 执行命令
            process = subprocess.Popen(
                full_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 获取输出
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                logger.error(f"命令执行失败: {stderr}")
                return False, stderr

            return True, stdout
        except Exception as e:
            logger.error(f"执行docker-compose命令时发生错误: {str(e)}")
            return False, str(e)

    def apply_mount(self, user_id: str, workspace_id: str, local_path: str) -> bool:
        """应用挂载并重启容器"""
        try:
            # 配置挂载
            mount_config = MountConfig(
                user_id=user_id,
                workspace_id=workspace_id,
                local_path=local_path
            )

            # 添加挂载配置
            if not self.add_mount(mount_config):
                return False

            # 更新docker-compose配置
            self._update_docker_compose(user_id, workspace_id, local_path)

            # 重启容器
            return self.restart_dev_container()
        except Exception as e:
            logger.error(f"应用挂载时发生错误: {str(e)}")
            return False

    def _update_docker_compose(self, user_id: str, workspace_id: str, local_path: str):
        """更新docker-compose配置文件，添加新的挂载点"""
        docker_compose_path = self.compose_file

        try:
            # 读取现有的docker-compose.dev.yml
            with open(docker_compose_path, "r") as f:
                compose_data = yaml.safe_load(f)

            # 获取core-dev服务的volumes配置
            volumes = compose_data["services"]["openmanus-core-dev"]["volumes"]

            # 创建目标路径 - 使用 user_id/workspace_id 格式
            target_path = f"/workspace/{user_id}/{workspace_id}"

            # 检查是否已存在对应的挂载
            workspace_mount = f"{local_path}:{target_path}"

            # 移除现有的相同用户+工作区ID的挂载
            volumes = [v for v in volumes if not v.endswith(f":{target_path}")]

            # 添加新的挂载
            volumes.append(workspace_mount)

            # 更新volumes配置
            compose_data["services"]["openmanus-core-dev"]["volumes"] = volumes

            # 保存修改后的配置
            with open(docker_compose_path, "w") as f:
                yaml.dump(compose_data, f, default_flow_style=False)

            logger.info(f"已更新docker-compose配置，添加挂载: {workspace_mount}")

        except Exception as e:
            logger.error(f"更新docker-compose配置失败: {str(e)}")
            raise
