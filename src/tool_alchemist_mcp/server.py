from pathlib import Path
from typing import List

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData
from pydantic import BaseModel, Field

from tool_alchemist_mcp.alchemist import Alchemist, ValidationError

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
    """Given a tool_name, look up the tool so you can modify the codebase"""
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


class AddDepsRequest(BaseModel):
    tool_name: ToolName = Field(description="Name of tool to add dependencies to")
    deps: List[str] = Field(description="list of dependencies you want to add")


@mcp.tool("AddDependency")
def add_deps(req: AddDepsRequest):
    """Given a tool_name, find the mcp tool and `uv add` depdendencies"""
    alchemist.add_dependency(name=req.tool_name.val, deps=req.deps)


@mcp.resource(
    uri="llmcontext://mcpdocs",
    description="Get instructions on how to write mcp servers using the latest python sdk",
)
def get_mcp_docs():
    return httpx.get(
        "https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/refs/heads/main/README.md"
    ).text
