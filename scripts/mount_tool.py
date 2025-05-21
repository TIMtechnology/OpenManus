#!/usr/bin/env python
"""
OpenManus 挂载工具
用于快速执行挂载和卸载操作
"""

import argparse
import requests
import json
import sys
import os
import time


def main():
    """主函数"""
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='OpenManus 挂载工具')

    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # 挂载命令
    mount_parser = subparsers.add_parser('mount', help='挂载目录')
    mount_parser.add_argument('--user', '-u', required=True, help='用户ID')
    mount_parser.add_argument('--workspace', '-w', required=True, help='工作区ID')
    mount_parser.add_argument('--path', '-p', required=True, help='本地目录路径')
    mount_parser.add_argument('--desc', '-d', help='描述信息')
    mount_parser.add_argument('--api', '-a', default='http://localhost:8089/api', help='API地址')
    mount_parser.add_argument('--restart', '-r', action='store_true', help='是否重启容器')

    # 卸载命令
    unmount_parser = subparsers.add_parser('unmount', help='卸载目录')
    unmount_parser.add_argument('--user', '-u', required=True, help='用户ID')
    unmount_parser.add_argument('--workspace', '-w', required=True, help='工作区ID')
    unmount_parser.add_argument('--api', '-a', default='http://localhost:8089/api', help='API地址')
    unmount_parser.add_argument('--restart', '-r', action='store_true', help='是否重启容器')

    # 列表命令
    list_parser = subparsers.add_parser('list', help='列出挂载')
    list_parser.add_argument('--api', '-a', default='http://localhost:8089/api', help='API地址')

    # 重启命令
    restart_parser = subparsers.add_parser('restart', help='重启容器')
    restart_parser.add_argument('--api', '-a', default='http://localhost:8089/api', help='API地址')

    # 解析参数
    args = parser.parse_args()

    # 执行对应命令
    if args.command == 'mount':
        mount(args)
    elif args.command == 'unmount':
        unmount(args)
    elif args.command == 'list':
        list_mounts(args)
    elif args.command == 'restart':
        restart(args)
    else:
        parser.print_help()


def mount(args):
    """挂载目录"""
    print(f"挂载目录: {args.path}")
    print(f"用户: {args.user}")
    print(f"工作区: {args.workspace}")

    # 检查目录是否存在
    if not os.path.exists(args.path):
        print(f"错误: 目录 '{args.path}' 不存在")
        return 1

    # 构建请求数据
    data = {
        "user_id": args.user,
        "workspace_id": args.workspace,
        "local_path": args.path,
        "description": args.desc or f"通过挂载工具挂载于 {time.strftime('%Y-%m-%d %H:%M:%S')}"
    }

    try:
        # 发送请求
        response = requests.post(
            f"{args.api}/mounts",
            json=data,
            timeout=10
        )

        # 处理响应
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ 挂载成功!")
                if result.get('data'):
                    print(f"挂载详情: {result['data'].get('local_path')} -> {result['data'].get('container_path')}")

                # 如果需要重启容器
                if args.restart:
                    print("\n重启容器中...")
                    restart(args)

                return 0
            else:
                print(f"❌ 挂载失败: {result.get('message')}")
                return 1
        else:
            print(f"❌ 请求失败 ({response.status_code}): {response.text}")
            return 1
    except Exception as e:
        print(f"❌ 操作出错: {str(e)}")
        return 1


def unmount(args):
    """卸载目录"""
    print(f"卸载挂载: {args.user}/{args.workspace}")

    try:
        # 发送请求
        response = requests.delete(
            f"{args.api}/mounts/{args.user}/{args.workspace}",
            timeout=10
        )

        # 处理响应
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ 卸载成功!")

                # 如果需要重启容器
                if args.restart:
                    print("\n重启容器中...")
                    restart(args)

                return 0
            else:
                print(f"❌ 卸载失败: {result.get('message')}")
                return 1
        else:
            print(f"❌ 请求失败 ({response.status_code}): {response.text}")
            return 1
    except Exception as e:
        print(f"❌ 操作出错: {str(e)}")
        return 1


def list_mounts(args):
    """列出挂载"""
    print("获取挂载列表...")

    try:
        # 发送请求
        response = requests.get(
            f"{args.api}/mounts",
            timeout=10
        )

        # 处理响应
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                data = result.get('data', {})

                if not data:
                    print("没有找到任何挂载")
                    return 0

                print(f"找到 {len(data)} 个挂载:")
                print("-" * 80)
                for key, value in data.items():
                    print(f"挂载: {key}")
                    print(f"  本地路径: {value.get('local_path')}")
                    print(f"  容器路径: {value.get('container_path')}")
                    if value.get('description'):
                        print(f"  描述: {value.get('description')}")
                    if value.get('created_at'):
                        print(f"  创建时间: {value.get('created_at')}")
                    print("-" * 80)

                return 0
            else:
                print(f"❌ 获取失败: {result.get('message')}")
                return 1
        else:
            print(f"❌ 请求失败 ({response.status_code}): {response.text}")
            return 1
    except Exception as e:
        print(f"❌ 操作出错: {str(e)}")
        return 1


def restart(args):
    """重启容器"""
    print("重启容器...")

    try:
        # 发送请求
        response = requests.post(
            f"{args.api}/restart",
            timeout=30
        )

        # 处理响应
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ 容器重启成功!")
                return 0
            else:
                print(f"❌ 重启失败: {result.get('message')}")
                return 1
        else:
            print(f"❌ 请求失败 ({response.status_code}): {response.text}")
            return 1
    except Exception as e:
        print(f"❌ 操作出错: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
