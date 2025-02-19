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
DEFAULT_GOOSE_CONFIG_PATH = Path.home().joinpath(".config", "goose", "config.yaml")


class UVCommandNotFound(Exception):
    pass


class ValidationError(Exception): ...


def to_snake_case(val: str) -> str:
    return re.sub(r"[\s\-]+", "_", val.strip()).lower()


def to_kebob_case(val: str):
    return re.sub(r"[\s_]+", "-", val.strip()).lower()


class Alchemist:
    def __init__(
        self,
        data_path: Path | None = None,
        goose_config_path: Path | None = None,
        template_path: Path = TEMPLATE_PATH,
    ):
        # Use injected value, then environment variable, then default
        self.data_path = data_path or Path(
            os.getenv("TOOL_ALCHEMIST_MCP_DATA_PATH", DEFAULT_ALCHEMY_MCP_PATH)
        )
        self.goose_config_path = goose_config_path or Path(
            os.getenv("TOOL_ALCHEMIST_MCP_GOOSE_CONFIG_PATH", DEFAULT_GOOSE_CONFIG_PATH)
        )

        # Jinja2 environment setup
        self.template_env = Environment(loader=FileSystemLoader(template_path))

    def get_tool_root_path(self, name: str) -> Path:
        tool_path = self.data_path.joinpath(to_kebob_case(name))
        return tool_path

    def get_tool_server_path(self, name: str) -> Path:
        return self.get_tool_root_path(name).joinpath(
            "src", to_snake_case(name), "server.py"
        )

    def add_tool_to_config(self, name: str) -> None:
        tool_path = self.get_tool_root_path(name)
        tool_name_kebab = to_kebob_case(name)

        with open(self.goose_config_path, "r") as file:
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

        with open(self.goose_config_path, "w+") as file:
            yaml.dump(current_config, file, sort_keys=False)

    def create_new_tool(self, name: str, description: str | None = None) -> Path:
        self._check_uv_installed()
        name_in_kebab_case = to_kebob_case(name)
        name_in_snake_case = to_snake_case(name)

        tool_path = self.data_path.joinpath(name_in_kebab_case)
        self._uv_create(name, tool_path, description)

        server_file_path = tool_path.joinpath(
            "src", name_in_snake_case, SERVER_FILE_NAME
        )
        init_file_path = tool_path.joinpath("src", name_in_snake_case, "__init__.py")

        tool = self.template_env.get_template("tool.py.j2")
        tool_code = tool.render(name=name, name_in_snake_case=name_in_snake_case)

        init_template = self.template_env.get_template("init.py.j2")
        init_code = init_template.render(name_in_snake_case=name_in_snake_case)

        with open(server_file_path, "w+") as f:
            f.write(tool_code)
        with open(init_file_path, "w+") as f:
            f.write(init_code)

        return tool_path

    def _run_command(self, command: list[str], check: bool = True) -> None:
        subprocess.run(command, check=check)

    def _check_uv_installed(self) -> None:
        if not shutil.which("uv"):
            raise UVCommandNotFound(
                "The 'uv' command is not found. Please install it before proceeding."
            )

    def _uv_create(
        self,
        name: str,
        tool_path: Path,
        description: str | None = None,
    ):
        command = [
            "uv",
            "init",
            "--package",
            "--description",
            description or name,
            str(tool_path),
        ]
        self._run_command(command)

        command = ["uv", "add", "mcp", "--project", str(tool_path)]
        self._run_command(command)


if __name__ == "__main__":
    alchemist = Alchemist()
    print(alchemist.add_tool_to_config("my-tool"))
