from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData
from pydantic import BaseModel, Field

from tool_alchemist_mcp.alchemist import Alchemist, ValidationError

# Create an MCP server
mcp = FastMCP("Tool Alchemist")
alchemist = Alchemist()


class ToolName(BaseModel):
    val: str = Field(pattern=r"^[a-zA-Z0-9 _-]+$")


@mcp.tool("CreateNewToolBoilerplate")
def build_boilerplate(name: ToolName) -> Path:
    """Create a new tool using the basic boilerplate.
    This should be done before any custom code is written by the agent.
    """
    try:
        tool_path = alchemist.create_new_tool(name.val)
        alchemist.add_tool_to_config(name.val)
        return tool_path
    except ValidationError as e:
        raise McpError(ErrorData(message=str(e), code=INTERNAL_ERROR))
    except Exception as e:
        raise McpError(
            ErrorData(message=f"Failed to create tool: {str(e)}", code=INTERNAL_ERROR)
        )


class GetToolPathResponse(BaseModel):
    root_path: Path = Field(description="The path at which the tool exists")
    server_path: Path = Field(description="The path where the server file lives")


@mcp.tool("GetToolPath")
def get_tool_path(tool_name: ToolName):
    """Given a tool_name, look up the tool so you can modify the server.py."""
    try:
        root = alchemist.get_tool_root_path(tool_name.val)
        server = alchemist.get_tool_server_path(tool_name.val)
        return GetToolPathResponse(root_path=root, server_path=server)
    except ValidationError as e:
        raise McpError(ErrorData(message=str(e), code=INTERNAL_ERROR))
    except Exception as e:
        raise McpError(
            ErrorData(message=f"Failed to get tool path: {str(e)}", code=INTERNAL_ERROR)
        )
