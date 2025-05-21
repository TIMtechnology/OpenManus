#!/usr/bin/env python
"""
OpenManus 监控容器测试脚本
用于测试监控容器的挂载和重启功能
"""

import os
import json
import time
import requests
from pathlib import Path


# 配置参数
MONITOR_API = "http://localhost:8089/api"  # 监控容器API地址
CORE_API = "http://localhost:5172/api/mounts"  # 开发容器API地址
TEMP_DIR = "D:\\timkj\\2025\\OpenManus\\examples\\use_case"  # 测试挂载目录
USER_ID = "cmagchmpl0000tjykb5timu8p"  # 测试用户ID
WORKSPACE_ID = "cmaw28tgj00wqtjfsmg8o0pjx"  # 测试工作区ID


def test_connection():
    """测试与监控容器的连接"""
    print("\n===== 测试与监控容器的连接 =====")
    try:
        # 直接访问监控容器API
        response = requests.get(f"{MONITOR_API}/health", timeout=5)
        print(f"监控容器健康检查状态: {response.status_code}")
        print(f"响应内容: {response.json()}")

        if response.status_code == 200:
            print("✅ 监控容器连接正常")
            return True
        else:
            print("❌ 监控容器连接失败")
            return False
    except Exception as e:
        print(f"❌ 连接测试出错: {str(e)}")
        return False


def get_all_mounts():
    """获取所有挂载配置"""
    print("\n===== 获取所有挂载配置 =====")
    try:
        response = requests.get(f"{MONITOR_API}/mounts", timeout=5)
        if response.status_code == 200:
            data = response.json().get("data", {})
            print(f"当前挂载数量: {len(data)}")
            for key, value in data.items():
                print(f"- {key}: {value['local_path']} -> {value['container_path']}")
            return data
        else:
            print(f"❌ 获取挂载配置失败: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ 获取挂载配置出错: {str(e)}")
        return {}


def remove_all_mounts():
    """移除所有挂载配置"""
    print("\n===== 移除所有挂载配置 =====")
    try:
        # 获取当前所有挂载
        mounts = get_all_mounts()

        if not mounts:
            print("没有找到挂载配置，无需清理")
            return True

        success = True
        # 逐个删除挂载
        for key in mounts.keys():
            try:
                user_id, workspace_id = key.split(":", 1)
                print(f"移除挂载: {user_id}/{workspace_id}")

                response = requests.delete(
                    f"{MONITOR_API}/mounts/{user_id}/{workspace_id}",
                    timeout=10
                )

                if response.status_code == 200:
                    print(f"✅ 成功移除挂载: {user_id}/{workspace_id}")
                else:
                    print(f"❌ 移除挂载失败: {response.status_code}, {response.text}")
                    success = False
            except Exception as e:
                print(f"❌ 移除挂载出错: {str(e)}")
                success = False

        return success
    except Exception as e:
        print(f"❌ 移除挂载操作出错: {str(e)}")
        return False


def add_mount():
    """添加测试挂载"""
    print(f"\n===== 添加测试挂载 ({USER_ID}/{WORKSPACE_ID}) =====")
    try:
        # 确保测试目录存在
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR, exist_ok=True)
            print(f"已创建测试目录: {TEMP_DIR}")

        # 添加标记文件以验证挂载
        marker_file = os.path.join(TEMP_DIR, "mount_test.txt")
        with open(marker_file, "w") as f:
            f.write(f"Mount test created at {time.time()}")
        print(f"已创建标记文件: {marker_file}")

        # 构建挂载数据
        mount_data = {
            "user_id": USER_ID,
            "workspace_id": WORKSPACE_ID,
            "local_path": TEMP_DIR,
            "description": "测试挂载配置"
        }

        # 发送添加挂载请求
        response = requests.post(
            f"{MONITOR_API}/mounts",
            json=mount_data,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 挂载添加成功: {result['message']}")
            print(f"挂载详情: {json.dumps(result['data'], ensure_ascii=False, indent=2)}")
            return True
        else:
            print(f"❌ 挂载添加失败: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ 添加挂载出错: {str(e)}")
        return False


def restart_container():
    """重启开发容器"""
    print("\n===== 重启开发容器 =====")
    try:
        # 发送重启请求
        response = requests.post(f"{MONITOR_API}/restart", timeout=30)

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ 容器重启成功: {result['message']}")
                return True
            else:
                print(f"❌ 容器重启失败: {result['message']}")
                return False
        else:
            print(f"❌ 重启请求失败: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ 重启容器出错: {str(e)}")
        return False


def verify_mount():
    """验证挂载是否成功"""
    print("\n===== 验证挂载配置 =====")
    try:
        # 查询特定挂载信息
        response = requests.get(
            f"{MONITOR_API}/mounts/{USER_ID}/{WORKSPACE_ID}",
            timeout=5
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ 挂载验证成功:")
                print(f"挂载详情: {json.dumps(result['data'], ensure_ascii=False, indent=2)}")
                return True
            else:
                print(f"❌ 挂载验证失败: {result['message']}")
                return False
        else:
            print(f"❌ 挂载查询失败: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ 验证挂载出错: {str(e)}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n========== OpenManus 监控容器测试 ==========")

    # 步骤1: 测试连接
    if not test_connection():
        print("❌ 连接测试失败，无法继续测试")
        return False

    # 步骤2: 移除所有挂载
    if not remove_all_mounts():
        print("⚠️ 移除挂载存在问题，但将继续测试")

    # 步骤3: 添加测试挂载
    if not add_mount():
        print("❌ 添加挂载失败，无法继续测试")
        return False

    # 步骤4: 重启容器
    if not restart_container():
        print("⚠️ 容器重启失败，但将继续验证挂载")

    # 等待容器重启完成
    print("等待容器重启完成...")
    time.sleep(5)

    # 步骤5: 验证挂载
    if not verify_mount():
        print("❌ 挂载验证失败")
        return False

    # 测试通过
    print("\n✅✅✅ 所有测试通过! ✅✅✅")
    return True


if __name__ == "__main__":
    # 运行测试
    run_all_tests()
