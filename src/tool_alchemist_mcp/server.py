from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Tool Alchemist")


# Add an addition tool
@mcp.tool("CreateNewToolBoilerplate")
def build_boilerplate(name: str) -> int:
    """Create a new tool using the basic boilerplate.
    This should be done before any custom code is written by the agent.
    """
    return 0
