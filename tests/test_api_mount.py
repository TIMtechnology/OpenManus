#!/usr/bin/env python
"""
OpenManus API挂载测试脚本
使用OpenManus API接口进行挂载测试
"""

import requests
import json
import time
import os

# 配置参数
API_URL = "http://localhost:5172/api/mounts"
TEMP_DIR = "D:\\timkj\\2025\\OpenManus\\examples\\use_case"
USER_ID = "cmagchmpl0000tjykb5timu8p"
WORKSPACE_ID = "cmaw28tgj00wqtjfsmg8o0pjx"


def main():
    """主函数"""
    print("=====================================================")
    print("OpenManus API挂载测试")
    print("=====================================================")

    # 1. 测试连接
    print("\n>>> 测试API连接...")
    try:
        response = requests.get(f"{API_URL}/test-monitor")
        if response.status_code == 200:
            result = response.json()
            print(f"连接状态: {result['success']}")
            print(f"消息: {result['message']}")
            if 'data' in result and result['data']:
                print(f"监控API地址: {result['data'].get('api_url')}")
                print(f"状态: {result['data'].get('status')}")
        else:
            print(f"连接测试失败: {response.status_code}")
            return
    except Exception as e:
        print(f"连接测试出错: {str(e)}")
        return

    # 2. 获取当前挂载列表
    print("\n>>> 获取当前挂载列表...")
    try:
        response = requests.get(f"{API_URL}/mounts")
        result = response.json()
        if result.get("success"):
            mount_list = result.get("data", [])
            print(f"当前挂载数量: {len(mount_list)}")
            for mount in mount_list:
                print(f"- {mount.get('user_id')}/{mount.get('workspace_id')}: {mount.get('local_path')}")
        else:
            print(f"获取挂载列表失败: {result.get('message')}")
    except Exception as e:
        print(f"获取挂载列表出错: {str(e)}")

    # 3. 检查并移除现有挂载
    print(f"\n>>> 检查并移除现有挂载 ({USER_ID}/{WORKSPACE_ID})...")
    try:
        response = requests.get(f"{API_URL}/mount/{USER_ID}/{WORKSPACE_ID}")
        result = response.json()

        if result.get("success"):
            print(f"找到现有挂载: {USER_ID}/{WORKSPACE_ID}")
            print(f"正在移除...")

            # 移除挂载
            response = requests.delete(f"{API_URL}/mount/{USER_ID}/{WORKSPACE_ID}")
            result = response.json()

            if result.get("success"):
                print(f"挂载移除成功: {result.get('message')}")
            else:
                print(f"挂载移除失败: {result.get('message')}")
        else:
            print(f"未找到挂载 {USER_ID}/{WORKSPACE_ID}，无需移除")
    except Exception as e:
        print(f"移除挂载出错: {str(e)}")

    # 4. 创建测试目录和文件
    print(f"\n>>> 准备测试目录 ({TEMP_DIR})...")
    try:
        # 确保目录存在
        os.makedirs(TEMP_DIR, exist_ok=True)

        # 创建测试文件
        test_file = os.path.join(TEMP_DIR, "test_api_mount.txt")
        with open(test_file, "w") as f:
            f.write(f"API Mount Test\nCreated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        print(f"已创建测试文件: {test_file}")
    except Exception as e:
        print(f"准备测试目录出错: {str(e)}")
        return

    # 5. 添加挂载
    print(f"\n>>> 添加挂载 ({USER_ID}/{WORKSPACE_ID})...")
    try:
        # 准备挂载数据
        mount_data = {
            "user_id": USER_ID,
            "workspace_id": WORKSPACE_ID,
            "local_path": TEMP_DIR,
            "description": "API挂载测试"
        }

        # 发送挂载请求
        response = requests.post(
            f"{API_URL}/mount",
            json=mount_data
        )

        result = response.json()
        if result.get("success"):
            print(f"挂载添加成功: {result.get('message')}")
            if result.get('data'):
                print(f"挂载路径: {result['data'].get('local_path')} -> {result['data'].get('container_path')}")
        else:
            print(f"挂载添加失败: {result.get('message')}")
            return
    except Exception as e:
        print(f"添加挂载出错: {str(e)}")
        return

    # 6. 重启容器
    print("\n>>> 重启容器...")
    try:
        response = requests.post(f"{API_URL}/restart-container")

        result = response.json()
        if result.get("success"):
            print(f"容器重启成功: {result.get('message')}")
        else:
            print(f"容器重启失败: {result.get('message')}")
    except Exception as e:
        print(f"重启容器出错: {str(e)}")

    # 7. 等待容器重启完成
    print("\n>>> 等待容器重启完成...")
    time.sleep(5)

    # 8. 验证挂载
    print(f"\n>>> 验证挂载 ({USER_ID}/{WORKSPACE_ID})...")
    try:
        response = requests.get(f"{API_URL}/mount/{USER_ID}/{WORKSPACE_ID}")

        result = response.json()
        if result.get("success"):
            print(f"验证成功，挂载已生效")
            print(f"挂载详情:")
            mount_info = result.get("data", {})
            print(f"- 用户ID: {mount_info.get('user_id')}")
            print(f"- 工作区ID: {mount_info.get('workspace_id')}")
            print(f"- 本地路径: {mount_info.get('local_path')}")
            print(f"- 容器路径: {mount_info.get('container_path')}")
            print(f"- 描述: {mount_info.get('description')}")
            print(f"- 创建时间: {mount_info.get('created_at')}")
        else:
            print(f"挂载验证失败: {result.get('message')}")
    except Exception as e:
        print(f"验证挂载出错: {str(e)}")

    # 测试完成
    print("\n=====================================================")
    print("测试完成!")
    print("=====================================================")


if __name__ == "__main__":
    main()
