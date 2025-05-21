import os
import unittest
import tempfile
import shutil
from pathlib import Path

import requests
import pytest

# API 基础URL，根据您的实际配置修改
BASE_URL = "http://localhost:5172/container"


class TestMountAPI(unittest.TestCase):
    """挂载管理API测试用例"""

    def setUp(self):
        """测试前准备工作"""
        # 使用真实的本地目录，确保宿主机上存在
        self.temp_dir = "D:\\timkj\\2025\\OpenManus\\examples\\use_case"
        self.user_id = "cmagchmpl0000tjykb5timu8p"
        self.workspace_id = "cmaw28tgj00wqtjfsmg8o0pjx"

        # 确保测试目录存在
        os.makedirs(self.temp_dir, exist_ok=True)

        # 创建测试文件
        test_file_path = os.path.join(self.temp_dir, "test.txt")
        with open(test_file_path, "w") as f:
            f.write("This is a test file for mount testing.")

    def tearDown(self):
        """测试后清理工作"""
        # 卸载测试工作区
        try:
            response = requests.delete(f"{BASE_URL}/mount/{self.user_id}/{self.workspace_id}")
            print(f"卸载清理响应: {response.json()}")
        except Exception as e:
            print(f"卸载清理时出错: {str(e)}")

        # 删除测试文件，但不删除目录
        try:
            test_file_path = os.path.join(self.temp_dir, "test.txt")
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
        except Exception as e:
            print(f"删除测试文件时出错: {str(e)}")

    def test_mount_and_unmount(self):
        """测试挂载和卸载功能"""
        # 1. 挂载本地目录
        mount_data = {
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "local_path": self.temp_dir,
            "description": "测试挂载本地目录"
        }

        response = requests.post(f"{BASE_URL}/mount", json=mount_data)
        print(f"挂载响应: {response.json()}")

        assert response.status_code == 200
        assert response.json()["success"] is True

        # 2. 获取挂载信息
        response = requests.get(f"{BASE_URL}/mount/{self.user_id}/{self.workspace_id}")
        print(f"获取挂载信息响应: {response.json()}")

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["data"]["user_id"] == self.user_id
        assert response.json()["data"]["workspace_id"] == self.workspace_id

        # 3. 获取挂载列表
        response = requests.get(f"{BASE_URL}/mounts")
        print(f"获取挂载列表响应: {response.json()}")

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert len(response.json()["data"]) > 0

        # 4. 卸载工作区
        response = requests.delete(f"{BASE_URL}/mount/{self.user_id}/{self.workspace_id}")
        print(f"卸载响应: {response.json()}")

        assert response.status_code == 200
        assert response.json()["success"] is True

        # 5. 确认卸载成功
        response = requests.get(f"{BASE_URL}/mount/{self.user_id}/{self.workspace_id}")
        print(f"卸载后获取信息响应: {response.json()}")

        assert response.status_code == 200
        assert response.json()["success"] is False  # 应该找不到挂载信息


def test_restart_container():
    """测试重启容器功能"""
    response = requests.post(f"{BASE_URL}/restart-container")
    print(f"重启容器响应: {response.json()}")

    assert response.status_code == 200
    assert "success" in response.json()


if __name__ == "__main__":
    # 运行测试
    unittest.main()
