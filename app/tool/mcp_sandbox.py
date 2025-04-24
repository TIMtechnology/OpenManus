import time
from contextlib import AsyncExitStack
from typing import Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from app.config import config
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.tool_collection import ToolCollection


class MCPToolCallSandboxHost:
    """A context manager for handling multiple MCP client connections.

    This class is responsible for:
    1. Maintaining multiple MCP client connections
    2. Managing client lifecycles
    3. Providing CRUD operations for clients
    """

    def __init__(self):
        # Dictionary to store multiple client connections
        # key: client_id, value: MCPSandboxClients instance
        self.clients: Dict[str, MCPSandboxClients] = {}

    async def add_sse_client(
        self, client_id: str, server_url: str
    ) -> "MCPSandboxClients":
        """Add a new SSE-based MCP client connection running in a sandbox.

        Args:
            client_id: Unique identifier for the client
            server_url: URL of the MCP server

        Returns:
            MCPSandboxClients: The newly created sandboxed client instance

        Raises:
            ValueError: If client_id already exists
        """
        if client_id in self.clients:
            raise ValueError(f"Client ID '{client_id}' already exists")

        client = MCPSandboxClients(client_id=client_id)
        await client.connect_sse(server_url=server_url)
        self.clients[client_id] = client
        return client

    async def add_stdio_client(
        self,
        client_id: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> "MCPSandboxClients":
        """Add a new STDIO-based MCP client connection running in a sandbox.

        Args:
            client_id: Unique identifier for the client
            command: Command to execute
            args: List of command arguments

        Returns:
            MCPSandboxClients: The newly created sandboxed client instance

        Raises:
            ValueError: If client_id already exists
        """
        if client_id in self.clients:
            raise ValueError(f"Client ID '{client_id}' already exists")

        client = MCPSandboxClients(client_id=client_id)
        await client.connect_stdio(command=command, args=args or [], env=env or {})
        self.clients[client_id] = client
        return client

    def get_client(self, client_id: str) -> Optional["MCPSandboxClients"]:
        """Retrieve a specific MCP client.

        Args:
            client_id: Unique identifier for the client

        Returns:
            Optional[Union[MCPClients, MCPSandboxClients]]: The client instance if found, None otherwise
        """
        return self.clients.get(client_id)

    async def remove_client(self, client_id: str) -> bool:
        """Remove and disconnect a specific MCP client connection.

        Args:
            client_id: Unique identifier for the client

        Returns:
            bool: True if client was found and removed, False otherwise
        """
        if client := self.clients.pop(client_id, None):
            await client.disconnect()
            return True
        return False

    async def disconnect_all(self) -> None:
        """Disconnect all MCP client connections."""
        client_ids = list(self.clients.keys())
        # If the list is not reversed, there would be error when disconnecting the client.
        # such like `Attempted to exit a cancel scope that isn't the current tasks's current cancel scope`
        # I don't know why should reverse the list, but it works,
        # if you know the reason, please let me know. Thanks!
        # by author @iheytang
        client_ids.reverse()
        for client_id in client_ids:
            await self.get_client(client_id).disconnect()

    def list_clients(self) -> List[str]:
        """Get a list of all client IDs.

        Returns:
            List[str]: List of all connected client IDs
        """
        return list(self.clients.keys())

    def get_client_count(self) -> int:
        """Get the current number of connected clients.

        Returns:
            int: Number of clients
        """
        return len(self.clients)


class MCPSandboxClientTool(BaseTool):
    """Represents a tool proxy that can be called on the MCP server from the client side, running in a sandbox."""

    session: Optional[ClientSession] = None
    client_id: str = ""

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool by making a remote call to the MCP server."""
        if not self.session:
            return ToolResult(error="Not connected to MCP server")

        try:
            # Remove client_id prefix from tool name before calling server
            server_tool_name = (
                self.name[len(self.client_id) + 1 :] if self.client_id else self.name
            )
            result = await self.session.call_tool(server_tool_name, kwargs)
            content_str = ", ".join(
                item.text for item in result.content if isinstance(item, TextContent)
            )
            return ToolResult(output=content_str or "No output returned.")
        except Exception as e:
            return ToolResult(error=f"Error executing tool: {str(e)}")


class MCPSandboxClients(ToolCollection):
    """
    A collection of tools that connects to an MCP server within a container and manages available tools.
    """

    session: Optional[ClientSession] = None
    exit_stack: AsyncExitStack = None
    description: str = "MCP client tools running in container for server interaction"
    client_id: str = ""

    # Container management
    container_name: Optional[str] = None
    # source container name, it's HeyFuns core container

    def __init__(self, client_id: str):
        super().__init__()  # Initialize with empty tools list
        self.name = f"mcp-{client_id}"  # Keep name for backward compatibility
        self.client_id = client_id
        self.exit_stack = AsyncExitStack()

        # Always create a new container but use cached images
        # Generate a container name with timestamp to ensure uniqueness
        timestamp = int(time.time())
        container_name = f"heyfuns-sandbox-{timestamp}-{''.join(c if c.isalnum() else '-' for c in self.client_id)}"
        self.container_name = container_name

    def _get_command_type(self, command: str) -> str:
        """Determine the type of command (uvx/npx/docker)."""
        if command.startswith("uvx"):
            return "uvx"
        elif command.startswith("npx"):
            return "npx"
        elif command.startswith("docker"):
            return "docker"
        else:
            raise ValueError(f"Unsupported command type: {command}")

    def _convert_to_docker_command(
        self, parameters: StdioServerParameters
    ) -> StdioServerParameters:
        """Convert any command to unified docker command format and return StdioServerParameters.

        Args:
            command: The original command to execute
            args: List of command arguments

        Returns:
            StdioServerParameters: Parameters for stdio transport
        """
        command_type = self._get_command_type(parameters.command)

        # Build a unified docker command
        docker_command = "docker"

        logger.info(f"Creating new container: {self.container_name}")

        # For docker commands, use the original parameters directly
        if command_type == "docker":
            docker_args = ["run"]

            if "--rm" not in parameters.args:
                docker_args.append("--rm")
            if "-i" not in parameters.args:
                docker_args.append("-i")

            docker_args.extend(["-v", f"{config.host_workspace_root}:/workspace"])
            docker_args.extend([parameters.command, *parameters.args])

            return StdioServerParameters(
                command=docker_command,
                args=docker_args,
                env=parameters.env,
            )

        # Otherwise create a new container with --rm flag to ensure cleanup
        docker_args = ["run", "--rm", "-i", "--name", self.container_name]

        # Add volume mounts for package caches to persist between container runs
        if command_type == "uvx":
            # Map Python package cache directories
            docker_args.extend(
                [
                    "-v",
                    "heyfuns-pip-cache:/root/.cache/pip",
                    "-v",
                    "heyfuns-uv-cache:/root/.cache/uv",
                ]
            )
        elif command_type == "npx":
            # Map npm package cache directories
            docker_args.extend(
                [
                    "-v",
                    "heyfuns-npm-cache:/root/.npm",
                    "-v",
                    "heyfuns-yarn-cache:/usr/local/share/.cache/yarn",
                ]
            )

        # Add workspace directory mount
        docker_args.extend(["-v", f"{config.host_workspace_root}:/workspace"])

        # Add environment variables to docker command
        env_vars = {
            "PYTHONUNBUFFERED": "1",  # Ensure Python output is not buffered
            "TERM": "dumb",  # Use dumb terminal type
            "PS1": "$ ",  # Set a simple prompt
            "PROMPT_COMMAND": "",  # Disable prompt command
            "UV_INDEX_URL": "https://mirrors.aliyun.com/pypi/simple/",
            "NPM_REGISTRY": "https://registry.npmmirror.com",
        }
        for key, value in env_vars.items():
            docker_args.extend(["-e", f"{key}={value}"])

        # Add custom environment variables from parameters
        for key, value in parameters.env.items():
            docker_args.extend(["-e", f"{key}={value}"])

        # Set different images and commands based on command type
        if command_type == "uvx":
            docker_args.extend(
                [
                    "iheytang/heyfuns-sandbox-uvenv:latest",
                    "bash",
                    "-c",
                    f"{parameters.command} {' '.join(parameters.args)}",
                ]
            )
        elif command_type == "npx":
            docker_args.extend(
                [
                    "iheytang/heyfuns-sandbox-nodejs:latest",
                    "bash",
                    "-c",
                    f"{parameters.command} {' '.join(parameters.args)}",
                ]
            )

        return StdioServerParameters(
            command=docker_command,
            args=docker_args,
        )

    async def connect_stdio(
        self, command: str, args: List[str], env: Dict[str, str]
    ) -> None:
        """Connect to an MCP server using stdio transport within a container."""
        if not command:
            raise ValueError("Server command is required.")
        if self.session:
            await self.disconnect()

        # Convert to unified docker command parameters
        server_params = self._convert_to_docker_command(
            StdioServerParameters(command=command, args=args, env=env)
        )
        # Use stdio_client provided by mcp library
        try:
            s = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.session = await self.exit_stack.enter_async_context(ClientSession(*s))
        except Exception as e:
            logger.error(f"Error creating stdio client {self.client_id}: {e}")
            raise

        # Directly call the initialization method
        await self._initialize_and_list_tools()

    async def connect_sse(self, server_url: str) -> None:
        """Connect to an MCP server using SSE transport."""
        if not server_url:
            raise ValueError("Server URL is required.")
        if self.session:
            await self.disconnect()

        # Use AsyncExitStack to manage async context
        try:
            s = await self.exit_stack.enter_async_context(sse_client(url=server_url))
            self.session = await self.exit_stack.enter_async_context(ClientSession(*s))
        except Exception as e:
            logger.error(f"Error creating sse client {self.client_id}: {e}")
            raise

        # Fetch available tools from MCP server
        await self._initialize_and_list_tools()

    async def _initialize_and_list_tools(self) -> None:
        """Initialize session and populate tool map."""
        if not self.session:
            raise RuntimeError("Session not initialized.")

        logger.info("Initializing MCP session...")
        try:
            await self.session.initialize()
            logger.info("MCP session initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MCP session: {e}")
            await self.disconnect()
            raise RuntimeError(f"Failed to initialize MCP session: {e}")

        logger.info("Fetching available tools from MCP server...")
        try:
            response = await self.session.list_tools()
            logger.info(f"Received tool list response: {response}")

            # Clear existing tools
            self.tools = tuple()
            self.tool_map = {}

            # Add client_id prefix to tool name
            for tool in response.tools:
                prefixed_name = f"{self.client_id}-{tool.name}"
                server_tool = MCPSandboxClientTool(
                    name=prefixed_name,
                    description=tool.description,
                    parameters=tool.inputSchema,
                    session=self.session,
                    client_id=self.client_id,
                )
                self.tool_map[prefixed_name] = server_tool
                logger.info(f"Added tool: {prefixed_name}")

            self.tools = tuple(self.tool_map.values())
            logger.info(
                f"Connected to server with tools (via container): {[tool.name for tool in response.tools]}"
            )
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            await self.disconnect()
            raise RuntimeError(f"Failed to list tools: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the MCP server and clean up resources."""
        if self.session and self.exit_stack:
            await self.exit_stack.aclose()
            self.session = None
            self.tools = tuple()
            self.tool_map = {}
