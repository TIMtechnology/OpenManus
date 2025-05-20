import logging
import sys
import os


logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stderr)])

import argparse
import asyncio
import atexit
import json
import websockets
import subprocess
from inspect import Parameter, Signature
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from app.logger import logger
from app.tool.base import BaseTool
from app.tool.bash import Bash
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.terminate import Terminate


class MCPServer:
    """MCP Server implementation with tool registration and management."""

    def __init__(self, name: str = "openmanus"):
        self.server = FastMCP(name)
        self.tools: Dict[str, BaseTool] = {}
        self.host_mode = os.environ.get("MCP_HOST_MODE", "false").lower() == "true"
        self.host_address = os.environ.get("MCP_HOST_IP", "host.docker.internal")
        self.host_port = int(os.environ.get("MCP_HOST_PORT", "8001"))

        # 初始化日志
        logger.info("============ MCP服务器初始化 ============")
        logger.info(f"宿主机模式: {'启用' if self.host_mode else '禁用'}")
        if self.host_mode:
            logger.info(f"宿主机地址: {self.host_address}")
            logger.info(f"宿主机端口: {self.host_port}")
            logger.info(f"宿主机MCP API端点: http://{self.host_address}:{self.host_port}/mcp/tools")
        logger.info("=========================================")

        # Initialize standard tools
        self.tools["bash"] = Bash()
        self.tools["browser"] = BrowserUseTool()
        self.tools["editor"] = StrReplaceEditor()
        self.tools["terminate"] = Terminate()

    def register_tool(self, tool: BaseTool, method_name: Optional[str] = None) -> None:
        """Register a tool with parameter validation and documentation."""
        tool_name = method_name or tool.name
        tool_param = tool.to_param()
        tool_function = tool_param["function"]

        # Define the async function to be registered
        async def tool_method(**kwargs):
            logger.info(f"Executing {tool_name}: {kwargs}")

            # 检查是否需要在宿主机上执行
            if self.host_mode and tool_name.startswith("mcp_"):
                # 解析MCP服务器名称和工具名称
                parts = tool_name.split("_", 2)
                if len(parts) >= 3:
                    server_name = parts[1]
                    original_tool_name = parts[2]
                    # 通过HTTP调用宿主机MCP服务
                    result = await self._execute_via_http(server_name, original_tool_name, kwargs)
                    logger.info(f"Host MCP Result of {tool_name}: {result}")
                    return result

            # 普通执行
            result = await tool.execute(**kwargs)
            logger.info(f"Result of {tool_name}: {result}")

            # Handle different types of results
            if hasattr(result, "model_dump"):
                return json.dumps(result.model_dump())
            elif isinstance(result, dict):
                return json.dumps(result)
            return result

        # Set method metadata
        tool_method.__name__ = tool_name
        tool_method.__doc__ = self._build_docstring(tool_function)
        tool_method.__signature__ = self._build_signature(tool_function)

        # Store parameter schema (important for tools that access it programmatically)
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])
        tool_method._parameter_schema = {
            param_name: {
                "description": param_details.get("description", ""),
                "type": param_details.get("type", "any"),
                "required": param_name in required_params,
            }
            for param_name, param_details in param_props.items()
        }

        # Register with server
        self.server.tool()(tool_method)
        logger.info(f"Registered tool: {tool_name}")

    async def _execute_via_http(self, server_name: str, tool_name: str, params: Dict) -> str:
        """通过HTTP请求执行宿主机上的MCP工具"""
        import aiohttp

        try:
            logger.info(f"通过HTTP调用宿主机MCP工具: {tool_name} - 服务器: {server_name}")

            # 构建API请求URL和数据
            api_url = f"http://{self.host_address}:{self.host_port}/mcp/tools/{tool_name}/call"
            logger.info(f"请求URL: {api_url}")

            # 使用aiohttp发送请求
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        error_msg = f"调用宿主机工具失败: HTTP {response.status}: {error_text}"
                        logger.error(error_msg)
                        return error_msg

                    # 解析响应结果
                    result_data = await response.json()

                    # 处理结果
                    content_str = ""
                    if "content" in result_data:
                        for item in result_data["content"]:
                            if item.get("type") == "text" and "text" in item:
                                content_str += item["text"]

                    # 检查是否有错误
                    is_error = result_data.get("isError", False)
                    if is_error:
                        error_msg = f"宿主机工具执行错误: {content_str}"
                        logger.error(error_msg)
                        return error_msg

            logger.info(f"HTTP工具调用完成: {tool_name}")
            return content_str or "No output returned."

        except Exception as e:
            logger.error(f"HTTP调用宿主机工具失败: {str(e)}")
            import traceback
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            return f"HTTP调用宿主机工具失败: {str(e)}"

    def _build_docstring(self, tool_function: dict) -> str:
        """Build a formatted docstring from tool function metadata."""
        description = tool_function.get("description", "")
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])

        # Build docstring (match original format)
        docstring = description
        if param_props:
            docstring += "\n\nParameters:\n"
            for param_name, param_details in param_props.items():
                required_str = (
                    "(required)" if param_name in required_params else "(optional)"
                )
                param_type = param_details.get("type", "any")
                param_desc = param_details.get("description", "")
                docstring += (
                    f"    {param_name} ({param_type}) {required_str}: {param_desc}\n"
                )

        return docstring

    def _build_signature(self, tool_function: dict) -> Signature:
        """Build a function signature from tool function metadata."""
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])

        parameters = []

        # Follow original type mapping
        for param_name, param_details in param_props.items():
            param_type = param_details.get("type", "")
            default = Parameter.empty if param_name in required_params else None

            # Map JSON Schema types to Python types (same as original)
            annotation = Any
            if param_type == "string":
                annotation = str
            elif param_type == "integer":
                annotation = int
            elif param_type == "number":
                annotation = float
            elif param_type == "boolean":
                annotation = bool
            elif param_type == "object":
                annotation = dict
            elif param_type == "array":
                annotation = list

            # Create parameter with same structure as original
            param = Parameter(
                name=param_name,
                kind=Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation,
            )
            parameters.append(param)

        return Signature(parameters=parameters)

    async def cleanup(self) -> None:
        """Clean up server resources."""
        logger.info("Cleaning up resources")

        # Follow original cleanup logic - only clean browser tool
        if "browser" in self.tools and hasattr(self.tools["browser"], "cleanup"):
            await self.tools["browser"].cleanup()

    def register_all_tools(self) -> None:
        """Register all tools with the server."""
        for tool in self.tools.values():
            self.register_tool(tool)

    def run(self, transport: str = "stdio") -> None:
        """Run the MCP server."""
        # Register all tools
        self.register_all_tools()

        # Register cleanup function (match original behavior)
        atexit.register(lambda: asyncio.run(self.cleanup()))

        # Start server (with same logging as original)
        logger.info(f"Starting OpenManus server ({transport} mode)")
        self.server.run(transport=transport)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="OpenManus MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio"],
        default="stdio",
        help="Communication method: stdio or http (default: stdio)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # 设置宿主机模式环境变量
    if args.host_mode:
        os.environ["MCP_HOST_MODE"] = "true"

    # Create and run server (maintaining original flow)
    server = MCPServer()
    server.run(transport=args.transport)
