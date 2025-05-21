#!/usr/bin/env python
"""
OpenManus 监控容器
提供容器管理和挂载配置API
"""

from flask import Flask, request, jsonify
import os
import json
import yaml
import time
import logging
import threading
import docker
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("monitor")

# 应用配置
WORKSPACE_ROOT = "/workspace"
MOUNT_DATA_FILE = os.path.join(WORKSPACE_ROOT, "mount_data.json")
COMPOSE_FILE = "/app/docker-compose.dev.yml"
DEV_CONTAINER_NAME = "openmanus-core-dev"
CHECK_INTERVAL = 10  # 配置检查间隔（秒）
DEBUG_MODE = os.environ.get("DEBUG_MODE", "0") == "1"

# 创建Flask应用
app = Flask(__name__)

# Docker客户端
client = docker.from_env()

# 锁，用于保护数据文件操作
data_lock = threading.Lock()
restart_lock = threading.Lock()

def ensure_docker_compose():
    """确保docker compose已安装"""
    try:
        # 检查docker compose命令是否可用
        result = subprocess.run(["docker", "compose", "--version"],
                                capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Docker Compose已安装: {result.stdout.strip()}")
            return True

        # 检查docker-compose命令是否可用（旧版本）
        result = subprocess.run(["docker-compose", "--version"],
                               capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"旧版Docker Compose已安装: {result.stdout.strip()}")
            return True

        # Docker Compose 未安装，由于我们已在 Dockerfile 中安装了它
        # 这里应该不会执行到，但作为安全措施添加
        logger.warning("Docker Compose未检测到，但应已安装，请检查 Dockerfile 配置")

        # 在此处不尝试安装，因为可能会导致构建问题
        # 直接使用 docker API 作为备选方案
        return False

    except Exception as e:
        logger.error(f"检查Docker Compose时出错: {str(e)}")
        return False

def load_mount_data():
    """加载挂载数据"""
    with data_lock:
        try:
            if not os.path.exists(MOUNT_DATA_FILE):
                return {}

            with open(MOUNT_DATA_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载挂载数据失败: {str(e)}")
            return {}

def save_mount_data(data):
    """保存挂载数据"""
    with data_lock:
        try:
            os.makedirs(os.path.dirname(MOUNT_DATA_FILE), exist_ok=True)
            with open(MOUNT_DATA_FILE, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存挂载数据失败: {str(e)}")
            return False

def update_docker_compose():
    """更新docker-compose配置文件"""
    try:
        # 读取挂载数据
        mount_data = load_mount_data()

        # 读取docker-compose配置
        with open(COMPOSE_FILE, "r") as f:
            compose_data = yaml.safe_load(f)

        # 获取现有卷挂载
        volumes = compose_data["services"]["openmanus-core-dev"]["volumes"]

        # 分离系统挂载和用户挂载
        system_volumes = []
        user_volumes = []

        for volume in volumes:
            if ":/workspace/" in volume and not any(s in volume for s in ["/app/", "/config/", "docker.sock", "Dockerfile", "scripts"]):
                user_volumes.append(volume)
            else:
                system_volumes.append(volume)

        # 清空用户挂载，准备重建
        new_volumes = system_volumes.copy()

        # 根据挂载数据重建用户挂载
        for key, mount_info in mount_data.items():
            if ":" in key and "local_path" in mount_info:
                user_id, workspace_id = key.split(":", 1)
                local_path = mount_info["local_path"]
                target_path = f"/workspace/{user_id}/{workspace_id}"

                # 处理Windows路径，确保格式正确
                # 移除路径中可能存在的/app前缀
                if local_path.startswith("/app/"):
                    local_path = local_path[5:]  # 移除/app/前缀

                # 确保Windows路径格式正确（使用正斜杠）
                local_path = local_path.replace('\\', '/')

                # 创建挂载条目，不使用引号，让 docker-compose 处理
                mount_entry = f"{local_path}:{target_path}"

                logger.info(f"处理挂载点: {mount_entry}")

                if mount_entry not in new_volumes:
                    new_volumes.append(mount_entry)
                    logger.info(f"添加用户挂载点: {mount_entry}")

        # 更新docker-compose配置
        compose_data["services"]["openmanus-core-dev"]["volumes"] = new_volumes

        # 保存更新后的配置
        with open(COMPOSE_FILE, "w") as f:
            yaml.dump(compose_data, f, default_flow_style=False)

        logger.info("已更新docker-compose配置")
        return True
    except Exception as e:
        logger.error(f"更新docker-compose配置失败: {str(e)}")
        return False

def restart_dev_container():
    """使用宿主机 Docker 重启开发容器"""
    with restart_lock:
        try:
            logger.info(f"开始重启容器: {DEV_CONTAINER_NAME}")

            # 首先尝试使用 docker compose 命令
            # 由于我们通过卷挂载了 docker.sock，可以直接使用宿主机的 docker 命令
            docker_compose_exists = False

            # 检查 docker compose 命令
            try:
                result = subprocess.run(["docker", "compose", "version"],
                                       capture_output=True, text=True)
                if result.returncode == 0:
                    docker_compose_exists = True
                    compose_cmd = "docker compose"
                    logger.info(f"使用 docker compose 命令: {result.stdout.strip()}")
            except Exception:
                pass

            if not docker_compose_exists:
                # 尝试旧版 docker-compose
                try:
                    result = subprocess.run(["docker-compose", "--version"],
                                           capture_output=True, text=True)
                    if result.returncode == 0:
                        docker_compose_exists = True
                        compose_cmd = "docker-compose"
                        logger.info(f"使用 docker-compose 命令: {result.stdout.strip()}")
                except Exception:
                    pass

            if docker_compose_exists:
                # 使用 docker compose 重启容器
                compose_dir = os.path.dirname(COMPOSE_FILE)
                logger.info(f"在目录 {compose_dir} 中执行重启")

                # 构建 docker compose 命令
                compose_file_path = os.path.abspath(COMPOSE_FILE)
                compose_file_rel = os.path.basename(COMPOSE_FILE)
                logger.info(f"使用compose文件: {compose_file_rel}")

                # 正确使用 docker compose 命令重启单个容器
                # 首先尝试停止容器
                stop_cmd = f"cd {compose_dir} && {compose_cmd} -f {compose_file_rel} stop {DEV_CONTAINER_NAME}"
                logger.info(f"执行停止命令: {stop_cmd}")
                subprocess.run(stop_cmd, shell=True, capture_output=True, text=True)

                # 确保容器已停止
                try:
                    container = client.containers.get(DEV_CONTAINER_NAME)
                    if container.status != "exited":
                        logger.info("容器未完全停止，尝试强制停止")
                        container.stop(timeout=10)
                        time.sleep(2)
                except Exception as e:
                    logger.info(f"获取容器状态时出错: {str(e)}")

                # 然后移除容器
                rm_cmd = f"docker rm -f {DEV_CONTAINER_NAME} || true"
                logger.info(f"执行移除命令: {rm_cmd}")
                subprocess.run(rm_cmd, shell=True, capture_output=True, text=True)

                # 最后启动容器
                up_cmd = f"cd {compose_dir} && {compose_cmd} -f {compose_file_rel} up -d {DEV_CONTAINER_NAME}"
                logger.info(f"执行启动命令: {up_cmd}")

                result = subprocess.run(up_cmd, shell=True, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info(f"容器重启成功: {result.stdout}")
                    return True, "容器重启成功"
                else:
                    error_msg = f"容器启动失败: {result.stderr}"
                    logger.error(error_msg)
                    logger.info("尝试使用Docker API作为备选方案")
            else:
                logger.warning("未找到 docker compose 命令，使用 Docker API 重启容器")

            # 作为备选方案，使用Docker API重启容器
            try:
                # 先尝试移除现有容器
                try:
                    container = client.containers.get(DEV_CONTAINER_NAME)
                    container.stop(timeout=30)
                    container.remove(force=True)
                    logger.info(f"已移除现有容器: {DEV_CONTAINER_NAME}")
                except docker.errors.NotFound:
                    logger.info(f"未找到现有容器: {DEV_CONTAINER_NAME}")
                except Exception as e:
                    logger.warning(f"移除容器时出错: {str(e)}")

                # 使用 Docker Compose API 重启容器
                logger.info("尝试使用 Docker Compose API 重新创建容器")
                cmd = f"cd {compose_dir} && {compose_cmd} -f {compose_file_rel} up -d {DEV_CONTAINER_NAME}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info("使用Docker Compose API重启容器成功")
                    return True, "使用Docker Compose API重启容器成功"
                else:
                    logger.error(f"使用Docker Compose API重启容器失败: {result.stderr}")
                    return False, f"重启容器失败: {result.stderr}"

            except Exception as e:
                error_msg = f"重启容器失败: {str(e)}"
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"重启容器时发生错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

# API路由
@app.route("/api/health", methods=["GET"])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "container": "openmanus-monitor"
    })

@app.route("/api/mounts", methods=["GET"])
def get_mounts():
    """获取所有挂载配置"""
    return jsonify({
        "success": True,
        "data": load_mount_data()
    })

@app.route("/api/mounts/<user_id>/<workspace_id>", methods=["GET"])
def get_mount(user_id, workspace_id):
    """获取特定挂载配置"""
    mount_data = load_mount_data()
    key = f"{user_id}:{workspace_id}"

    if key in mount_data:
        return jsonify({
            "success": True,
            "data": {
                "user_id": user_id,
                "workspace_id": workspace_id,
                **mount_data[key]
            }
        })
    else:
        return jsonify({
            "success": False,
            "message": "未找到指定挂载配置"
        }), 404

@app.route("/api/mounts", methods=["POST"])
def add_mount():
    """添加挂载配置"""
    try:
        data = request.json

        # 验证必要字段
        if not all(k in data for k in ["user_id", "workspace_id", "local_path"]):
            return jsonify({
                "success": False,
                "message": "缺少必要字段"
            }), 400

        # 创建挂载键
        user_id = data["user_id"]
        workspace_id = data["workspace_id"]
        local_path = data["local_path"]
        description = data.get("description")

        key = f"{user_id}:{workspace_id}"

        # 保存到挂载数据
        mount_data = load_mount_data()
        mount_data[key] = {
            "local_path": local_path,
            "container_path": f"/workspace/{user_id}/{workspace_id}",
            "description": description,
            "created_at": datetime.now().isoformat()
        }

        if save_mount_data(mount_data):
            # 更新docker-compose配置
            update_docker_compose()

            return jsonify({
                "success": True,
                "message": "挂载配置已添加",
                "data": {
                    "user_id": user_id,
                    "workspace_id": workspace_id,
                    **mount_data[key]
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "保存挂载配置失败"
            }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"添加挂载配置时发生错误: {str(e)}"
        }), 500

@app.route("/api/mounts/<user_id>/<workspace_id>", methods=["DELETE"])
def remove_mount(user_id, workspace_id):
    """移除挂载配置"""
    try:
        mount_data = load_mount_data()
        key = f"{user_id}:{workspace_id}"

        if key in mount_data:
            del mount_data[key]

            if save_mount_data(mount_data):
                # 更新docker-compose配置
                update_docker_compose()

                return jsonify({
                    "success": True,
                    "message": "挂载配置已移除"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "保存更新后的挂载配置失败"
                }), 500
        else:
            return jsonify({
                "success": False,
                "message": "未找到指定挂载配置"
            }), 404

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"移除挂载配置时发生错误: {str(e)}"
        }), 500

@app.route("/api/restart", methods=["GET"])
def restart_container():
    """重启开发容器"""
    try:
        success, message = restart_dev_container()

        return jsonify({
            "success": success,
            "message": message
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"重启容器时发生错误: {str(e)}"
        }), 500

@app.route("/api/debug/apply", methods=["POST"])
def debug_apply_changes():
    """调试接口：应用配置变更并重启容器"""
    if not DEBUG_MODE:
        return jsonify({
            "success": False,
            "message": "调试模式未启用"
        }), 403

    try:
        # 更新docker-compose配置
        update_success = update_docker_compose()

        # 重启容器
        restart_success, message = restart_dev_container()

        return jsonify({
            "success": update_success and restart_success,
            "message": f"配置更新: {'成功' if update_success else '失败'}, 容器重启: {message}"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"应用变更时发生错误: {str(e)}"
        }), 500

@app.route("/api/debug/stats", methods=["GET"])
def debug_container_stats():
    """调试接口：获取容器状态"""
    if not DEBUG_MODE:
        return jsonify({
            "success": False,
            "message": "调试模式未启用"
        }), 403

    try:
        container = client.containers.get(DEV_CONTAINER_NAME)

        return jsonify({
            "success": True,
            "data": {
                "id": container.id,
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else str(container.image.id)
            }
        })

    except docker.errors.NotFound:
        return jsonify({
            "success": False,
            "message": f"容器 {DEV_CONTAINER_NAME} 不存在"
        }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取容器状态时发生错误: {str(e)}"
        }), 500

# 启动应用
if __name__ == "__main__":
    # 确保挂载数据文件存在
    if not os.path.exists(MOUNT_DATA_FILE):
        save_mount_data({})
        logger.info("已创建空的挂载数据文件")

    # 调试信息
    if DEBUG_MODE:
        logger.info("调试模式已启用")

    logger.info(f"监控服务启动于 http://0.0.0.0:8089")
    app.run(host="0.0.0.0", port=8089)
