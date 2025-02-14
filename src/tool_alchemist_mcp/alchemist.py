import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

DEFAULT_ALCHEMY_MCP_PATH = Path.home().joinpath(".local/share/tool-alchemist-mcp/")
SERVER_FILE_NAME = "server.py"
TEMPLATE_PATH = Path(__file__).parent.joinpath("templates")
GOOSE_CONFIG_PATH = Path.home().joinpath(".config", "goose", "config.yaml")


class UVCommandNotFound(Exception):
    pass


class ValidationError(Exception): ...


# Convert kebab-case to snake_case
def to_snake_case(val: str) -> str:
    return re.sub(r"[\s\-]+", "_", val.strip()).lower()


def to_kebob_case(val: str):
    return re.sub(r"[\s_]+", "-", val.strip()).lower()


class Alchemist:
    def __init__(self):
        self.data_path = DEFAULT_ALCHEMY_MCP_PATH
        if custom_data_path := os.getenv("TOOL_ALCHEMIST_MCP_DATA_PATH"):
            self.data_path = Path(custom_data_path)

        # Jinja2 environment setup
        self.template_env = Environment(loader=FileSystemLoader(TEMPLATE_PATH))

    def get_tool_root_path(self, name: str) -> Path:
        tool_path = self.data_path.joinpath(to_kebob_case(name))
        return tool_path

    def get_tool_server_path(self, name: str) -> Path:
        return self.get_tool_root_path(name).joinpath(
            "src", to_snake_case(name), "server.py"
        )

    def add_tool_to_config(self, name: str):
        tool_path = self.get_tool_root_path(name)
        tool_name_kebab = to_kebob_case(name)
        with open(GOOSE_CONFIG_PATH, "r") as file:
            current_config = yaml.safe_load(file)
        new_extension = {
            "args": ["--from", str(tool_path), tool_name_kebab],
            "cmd": "uvx",
            "enabled": True,
            "envs": {},
            "name": tool_name_kebab,
            "type": "stdio",
        }
        current_config["extensions"][tool_name_kebab] = new_extension

        with open(GOOSE_CONFIG_PATH, "w+") as file:
            yaml.dump(current_config, file, sort_keys=False)

    def create_new_tool(self, name: str, description: str | None = None) -> Path:
        if not shutil.which("uv"):
            raise UVCommandNotFound(
                "The 'uv' command is not found. Please install it before proceeding."
            )

        name_in_kebab_case = to_kebob_case(name)
        name_in_snake_case = to_snake_case(name)

        tool_path = self.data_path.joinpath(name_in_kebab_case)

        command = [
            "uv",
            "init",
            "--package",
            "--description",
            description or name,
            tool_path,
        ]
        subprocess.run(command, check=True)

        command = ["uv", "add", "mcp", "--project", tool_path]
        subprocess.run(command, check=True)

        server_file_path = tool_path.joinpath(
            "src", name_in_snake_case, SERVER_FILE_NAME
        )
        init_file_path = tool_path.joinpath("src", name_in_snake_case, "__init__.py")

        tool = self.template_env.get_template("tool.py.j2")
        tool_code = tool.render(name=name, name_in_snake_case=name_in_snake_case)

        init = self.template_env.get_template("init.py.j2")
        init_code = init.render(name_in_snake_case=name_in_snake_case)

        with open(server_file_path, "w+") as f:
            f.write(tool_code)
        with open(init_file_path, "w+") as f:
            f.write(init_code)

        return tool_path


if __name__ == "__main__":
    alchemist = Alchemist()
    print(alchemist.add_tool_to_config("my-tool"))
