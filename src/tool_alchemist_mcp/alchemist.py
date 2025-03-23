import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

import yaml
import jinja2
from jinja2 import Environment, FileSystemLoader

# Constants for file paths and names
DEFAULT_ALCHEMY_MCP_PATH = Path.home().joinpath(".local/share/tool-alchemist-mcp/")
SERVER_FILE_NAME = "server.py"
TEMPLATE_PATH = Path(__file__).parent.joinpath("templates")
DEFAULT_GOOSE_CONFIG_PATH = Path.home().joinpath(".config", "goose", "config.yaml")


class UVCommandNotFound(Exception):
    """Raised when the UV package manager is not found on the system."""
    pass


class ValidationError(Exception):
    """Raised when validation of inputs fails."""
    pass


class Alchemist:
    """
    A class to create and manage Goose extensions/tools.
    
    The Alchemist class provides functionality to create new tool boilerplate,
    manage their configuration in Goose, and handle dependencies.
    It uses the UV package manager for project creation and dependency management.
    """
    
    @staticmethod
    def to_snake_case(val: str) -> str:
        """
        Convert a string to snake_case format.
        
        Args:
            val: The string to convert
            
        Returns:
            The snake_case formatted string
        """
        return re.sub(r"[\s\-]+", "_", val.strip()).lower()
    
    @staticmethod
    def to_kebob_case(val: str) -> str:
        """
        Convert a string to kebob-case format.
        
        Args:
            val: The string to convert
            
        Returns:
            The kebob-case formatted string
        """
        return re.sub(r"[\s_]+", "-", val.strip()).lower()
    
    @staticmethod
    def validate_tool_name(name: str) -> bool:
        """
        Validate that a tool name contains only allowed characters.
        
        Args:
            name: The name to validate
            
        Returns:
            True if the name is valid
            
        Raises:
            ValidationError: If the name contains invalid characters
        """
        if not name or not re.match(r"^[a-zA-Z0-9 _-]+$", name):
            raise ValidationError(
                "Tool name must contain only letters, numbers, spaces, underscores, and hyphens"
            )
        return True
    
    def __init__(
        self,
        data_path: Optional[Path] = None,
        goose_config_path: Optional[Path] = None,
        template_path: Path = TEMPLATE_PATH,
    ):
        """
        Initialize a new Alchemist instance.
        
        Args:
            data_path: Path where tools will be stored. If None, uses environment 
                       variable TOOL_ALCHEMIST_MCP_DATA_PATH or default.
            goose_config_path: Path to the Goose config file. If None, uses environment 
                             variable TOOL_ALCHEMIST_MCP_GOOSE_CONFIG_PATH or default.
            template_path: Path to the templates directory. Defaults to TEMPLATE_PATH.
        """
        # Use injected value, then environment variable, then default
        self.data_path = data_path or Path(
            os.getenv("TOOL_ALCHEMIST_MCP_DATA_PATH", str(DEFAULT_ALCHEMY_MCP_PATH))
        )
        self.goose_config_path = goose_config_path or Path(
            os.getenv("TOOL_ALCHEMIST_MCP_GOOSE_CONFIG_PATH", str(DEFAULT_GOOSE_CONFIG_PATH))
        )

        # Jinja2 environment setup
        self.template_env = Environment(loader=FileSystemLoader(template_path))

    def get_tool_root_path(self, name: str) -> Path:
        """
        Get the root path for a tool.
        
        Args:
            name: The name of the tool
            
        Returns:
            Path object for the tool's root directory
        """
        tool_path = self.data_path.joinpath(self.to_kebob_case(name))
        return tool_path

    def get_tool_server_path(self, name: str) -> Path:
        """
        Get the path to the server.py file for a tool.
        
        Args:
            name: The name of the tool
            
        Returns:
            Path object for the tool's server.py file
        """
        return self.get_tool_root_path(name).joinpath(
            "src", self.to_snake_case(name), SERVER_FILE_NAME
        )

    def add_tool_to_config(self, name: str) -> None:
        """
        Add a tool to the Goose configuration file.
        
        Args:
            name: The name of the tool to add
        
        Raises:
            ValidationError: If the tool name is invalid
            IOError: If there are issues reading or writing the config file
        """
        self.validate_tool_name(name)
        tool_path = self.get_tool_root_path(name)
        tool_name_kebab = self.to_kebob_case(name)

        try:
            with open(self.goose_config_path, "r") as file:
                current_config = yaml.safe_load(file) or {"extensions": {}}
                
            # Ensure extensions section exists
            if "extensions" not in current_config:
                current_config["extensions"] = {}

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
        except (IOError, yaml.YAMLError) as e:
            raise IOError(f"Failed to update Goose config file: {e}")

    def add_dependency(self, name: str, deps: List[str]) -> None:
        """
        Add dependencies to a tool using the UV package manager.
        
        Args:
            name: The name of the tool
            deps: List of dependency names to add
            
        Raises:
            ValidationError: If the tool name is invalid
            UVCommandNotFound: If UV is not installed
            subprocess.SubprocessError: If the UV command fails
        """
        self.validate_tool_name(name)
        self._check_uv_installed()
        tool_path = self.get_tool_root_path(name)
        cmd = ["uv", "add", *deps, "--project", str(tool_path)]
        try:
            self._run_command(cmd)
        except subprocess.SubprocessError as e:
            raise subprocess.SubprocessError(f"Failed to add dependencies {deps}: {e}")

    def create_new_tool(self, name: str, description: str | None = None) -> Path:
        """
        Create a new tool with boilerplate code.
        
        Args:
            name: The name of the tool to create
            description: Optional description for the tool
            
        Returns:
            Path to the created tool directory
            
        Raises:
            ValidationError: If the tool name is invalid
            UVCommandNotFound: If UV is not installed
            subprocess.SubprocessError: If the tool creation fails
            IOError: If there are issues writing the template files
        """
        self.validate_tool_name(name)
        self._check_uv_installed()
        name_in_kebab_case = self.to_kebob_case(name)
        name_in_snake_case = self.to_snake_case(name)

        tool_path = self.data_path.joinpath(name_in_kebab_case)
        self._uv_create(name, tool_path, description)

        server_file_path = tool_path.joinpath(
            "src", name_in_snake_case, SERVER_FILE_NAME
        )
        init_file_path = tool_path.joinpath("src", name_in_snake_case, "__init__.py")

        try:
            tool = self.template_env.get_template("tool.py.j2")
            tool_code = tool.render(name=name, name_in_snake_case=name_in_snake_case)

            init_template = self.template_env.get_template("init.py.j2")
            init_code = init_template.render(name_in_snake_case=name_in_snake_case)

            # Ensure parent directories exist
            server_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(server_file_path, "w+") as f:
                f.write(tool_code)
            with open(init_file_path, "w+") as f:
                f.write(init_code)
        except (IOError, jinja2.exceptions.TemplateError) as e:
            raise IOError(f"Failed to create tool files: {e}")

        return tool_path

    def _run_command(self, command: list[str], check: bool = True) -> None:
        """
        Run a shell command.
        
        Args:
            command: List of command arguments
            check: Whether to check the return code
            
        Raises:
            subprocess.SubprocessError: If the command fails and check is True
        """
        subprocess.run(command, check=check)

    def _check_uv_installed(self) -> None:
        """
        Check if the UV package manager is installed.
        
        Raises:
            UVCommandNotFound: If UV is not installed
        """
        if not shutil.which("uv"):
            raise UVCommandNotFound(
                "The 'uv' command is not found. Please install it before proceeding."
            )

    def _uv_create(
        self,
        name: str,
        tool_path: Path,
        description: str | None = None,
    ) -> None:
        """
        Initialize a new Python project using UV.
        
        Args:
            name: The name of the tool
            tool_path: Path where the tool will be created
            description: Optional description for the tool
            
        Raises:
            subprocess.SubprocessError: If the UV commands fail
        """
        # Create the directory if it doesn't exist
        tool_path.parent.mkdir(parents=True, exist_ok=True)
        
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
    # Example usage
    alchemist = Alchemist()
    print(f"Tool Alchemist initialized with data path: {alchemist.data_path}")
    print(f"Goose config path: {alchemist.goose_config_path}")
    print("To create a new tool, use: alchemist.create_new_tool('tool-name', 'description')")
