"""
宿主机MCP服务工具 - 通过HTTP请求连接到宿主机MCP服务
"""

import os
import json
import logging
import aiohttp
from typing import Dict, List, Optional, Any, Tuple

from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.tool_collection import ToolCollection


class HostMCPClientTool(BaseTool):
    """代理宿主机上的MCP工具，通过HTTP请求调用"""

    client_id: str = ""
    original_name: str = ""
    host_address: str = ""
    host_port: int = 0
    server_name: str = ""

    async def execute(self, **kwargs) -> ToolResult:
        """调用宿主机上的MCP工具"""
        try:
            logger.info(f"通过HTTP调用宿主机工具: {self.original_name}")
            logger.info(f"参数: {json.dumps(kwargs, ensure_ascii=False)}")

            # 构建API请求URL和数据
            api_url = f"http://{self.host_address}:{self.host_port}/mcp/tools/{self.original_name}/call"

            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=kwargs) as response:
                    if response.status != 200:
                        error_msg = f"调用宿主机工具失败: HTTP {response.status}"
                        logger.error(error_msg)
                        return ToolResult(error=error_msg)

                    result_data = await response.json()

                    # 解析结果
                    content_str = ""
                    if "content" in result_data:
                        for item in result_data["content"]:
                            if item.get("type") == "text" and "text" in item:
                                content_str += item["text"]

                    is_error = result_data.get("isError", False)
                    if is_error:
                        return ToolResult(error=content_str or "调用出错，但未返回错误信息")

            logger.info(f"宿主机工具调用完成: {self.original_name}")
            return ToolResult(output=content_str or "No output returned.")
        except Exception as e:
            error_msg = f"调用宿主机工具失败: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            return ToolResult(error=error_msg)


class HostMCPTools(ToolCollection):
    """
    连接到宿主机上的MCP服务并提供工具集合
    """

    description: str = "宿主机MCP工具集合"
    host_address: str = ""
    host_port: int = 0

    def __init__(self, name: str = "host_mcp"):
        super().__init__()
        self.name = name
        self.host_address = os.environ.get("MCP_HOST_IP", "host.docker.internal")
        self.host_port = int(os.environ.get("MCP_HOST_PORT", "8001"))

        # 打印环境变量信息便于调试
        logger.info("=== 宿主机MCP工具初始化 ===")
        logger.info(f"环境变量 MCP_HOST_MODE: {os.environ.get('MCP_HOST_MODE', 'false')}")
        logger.info(f"环境变量 MCP_HOST_IP: {self.host_address}")
        logger.info(f"环境变量 MCP_HOST_PORT: {self.host_port}")
        logger.info(f"HTTP API端点: http://{self.host_address}:{self.host_port}/mcp/tools")

    async def connect(self) -> bool:
        """连接到宿主机MCP服务并获取工具列表"""
        try:
            logger.info(f"正在连接到宿主机MCP服务: http://{self.host_address}:{self.host_port}/mcp/tools")

            # 获取可用的工具列表
            await self._fetch_available_tools()

            logger.info(f"已连接到宿主机MCP服务，获取了 {len(self.tools)} 个工具")
            return True

        except Exception as e:
            logger.error(f"连接宿主机MCP服务失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def _fetch_available_tools(self) -> None:
        """获取宿主机上可用的MCP工具"""
        # 清空现有工具
        self.tools = tuple()
        self.tool_map = {}

        # 使用HTTP请求获取工具列表
        try:
            async with aiohttp.ClientSession() as session:
                # 使用/mcp/tools API获取所有工具
                tools_url = f"http://{self.host_address}:{self.host_port}/mcp/tools"
                async with session.get(tools_url) as response:
                    if response.status != 200:
                        logger.error(f"获取工具列表失败: HTTP {response.status}")
                        return

                    tools_response = await response.json()

                    # tools_response是一个字典，键是服务器名称，值是ListToolsResult对象
                    for server_name, server_tools in tools_response.items():
                        if "tools" not in server_tools:
                            continue

                        for tool in server_tools["tools"]:
                            # 使用mcp_服务名_工具名格式，保持命名一致
                            tool_name = f"mcp_{server_name}_{tool['name']}"

                            # 创建工具实例
                            host_tool = HostMCPClientTool(
                                name=tool_name,
                                description=tool.get("description", ""),
                                parameters=tool.get("inputSchema", {}),
                                original_name=tool["name"],
                                host_address=self.host_address,
                                host_port=self.host_port,
                                server_name=server_name
                            )

                            self.tool_map[tool_name] = host_tool

            self.tools = tuple(self.tool_map.values())
            logger.info(f"宿主机MCP服务提供的工具: {list(self.tool_map.keys())}")

        except Exception as e:
            logger.error(f"获取宿主机MCP工具列表失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    async def disconnect(self) -> None:
        """断开与宿主机MCP服务的连接（对于HTTP方式，只需清空工具列表）"""
        self.tools = tuple()
        self.tool_map = {}
        logger.info("已清空宿主机MCP工具列表")


# 创建单例实例
host_mcp_tools = HostMCPTools()
