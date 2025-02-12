import os
import shutil  # Import shutil for command checking
import subprocess
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

DEFAULT_ALCHEMY_MCP_PATH = Path.home().joinpath(".local/share/tool-alchemist-mcp/")


class UVCommandNotFound(Exception):
    pass


# Convert kebab-case to snake_case
def kebab_to_snake(name: str) -> str:
    return name.replace("-", "_")


class Alchemist:
    def __init__(self):
        self.data_path = DEFAULT_ALCHEMY_MCP_PATH
        if custom_data_path := os.getenv("TOOL_ALCHEMIST_MCP_DATA_PATH"):
            self.data_path = Path(custom_data_path)

        # Jinja2 environment setup
        self.template_env = Environment(
            loader=FileSystemLoader("src/tool_alchemist_mcp/templates")
        )

    def create_new_tool(self, name: str, description: str | None = None):
        # Check if 'uv' command exists
        if not shutil.which("uv"):
            raise UVCommandNotFound(
                "The 'uv' command is not found. Please install it before proceeding."
            )

        name_in_kebab_case = name.lower().replace(" ", "-")
        name_in_snake_case = kebab_to_snake(name_in_kebab_case)

        # Step 1: Create boilerplate in the data path
        tool_path = self.data_path.joinpath(name_in_kebab_case)
        tool_path.mkdir(parents=True, exist_ok=True)

        # Step 2: Create the package
        command = [
            "uv",
            "init",
            "--package",
            "--description",
            description or name,
            name_in_kebab_case,
        ]
        subprocess.run(command, check=True)

        # Step 3: Create and render template for server.py
        server_file_path = tool_path.joinpath("src", name_in_snake_case, "server.py")
        server_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Load and render the Jinja2 template
        template = self.template_env.get_template("tool.py.jinja")
        rendered_code = template.render(name=name)

        # Write the rendered code to server.py
        with open(server_file_path, "w") as f:
            f.write(rendered_code)

        print(f"Successfully created tool '{name}' at {tool_path}")


if __name__ == "__main__":
    alchemist = Alchemist()
    alchemist.create_new_tool("Example Tool", "An example tool description.")
