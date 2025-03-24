import os
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml
from jinja2 import FileSystemLoader

from tool_alchemist_mcp.alchemist import (
    DEFAULT_ALCHEMY_MCP_PATH,
    DEFAULT_GOOSE_CONFIG_PATH,
    TEMPLATE_PATH,
    Alchemist,
    UVCommandNotFound,
    ValidationError,
)


def print_directory_tree(path, indent=""):
    """Prints the directory tree starting from the given path."""
    if not path.exists():
        print(f"{indent} [!] Path not found: {path}")
        return

    print(f"{indent} {path.name}/")
    indent += "  "

    for item in os.listdir(path):
        item_path = path / item
        if item_path.is_dir():
            print_directory_tree(item_path, indent)
        else:
            print(f"{indent} {item}")


class AlchemistTestable(Alchemist):
    def __init__(
        self, override_check_uv_installed=True, override_run_cmd=True, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.executed_commands = []
        self.override_check_uv_installed = override_check_uv_installed
        self.override_run_cmd = override_run_cmd

    def _run_command(self, command: list[str], check: bool = True) -> None:
        """Overrides `_run_command` to avoid actually running subprocesses."""
        if self.override_run_cmd:
            self.executed_commands.append(
                command
            )  # Store commands instead of executing
            return
        super()._run_command(command, check)

    def _check_uv_installed(self) -> None:
        """Overrides `_check_uv_installed` to avoid relying on `shutil.which`."""
        if self.override_check_uv_installed:
            return
        super()._check_uv_installed()

    def _uv_create(
        self,
        name: str,
        tool_path: Path,
        description: str | None = None,
    ) -> None:
        tool_path.mkdir(parents=True, exist_ok=True)

        (tool_path / "pyproject.toml").write_text(
            f"[project]\ndescription = '{description}'\n"
        )

        (tool_path / "src").mkdir()
        (tool_path / "src" / self.to_snake_case(name)).mkdir()
        (tool_path / "src" / self.to_snake_case(name) / "server.py").touch()
        print_directory_tree(tool_path)


@pytest.fixture
def fake_data_path(tmp_path) -> Path:
    """Creates a temporary directory to act as the data path for testing."""
    return tmp_path / "data"


@pytest.fixture
def fake_goose_config_path(tmp_path) -> Path:
    """Creates a temporary goose config file for testing."""
    config_file = tmp_path / "goose_config.yaml"
    config_file.write_text("extensions: {}")
    return config_file


@pytest.fixture
def fake_template_path(tmp_path) -> Path:
    """Creates a temporary directory to store fake templates."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "tool.py.j2").write_text("server template content: {{ name }}")
    (template_dir / "init.py.j2").write_text(
        "__init__ template content: {{ name_in_snake_case }}"
    )
    return template_dir


@pytest.fixture
def alchemist(fake_data_path, fake_goose_config_path, fake_template_path) -> Alchemist:
    """
    Returns an Alchemist instance with injected paths
    so we don't rely on environment variables or actual defaults.
    """
    return AlchemistTestable(
        data_path=fake_data_path,
        goose_config_path=fake_goose_config_path,
        template_path=fake_template_path,
    )


def test_constructor_defaults(monkeypatch):
    """
    Test that the constructor uses environment variables or defaults
    when arguments are not provided.
    """
    monkeypatch.delenv("TOOL_ALCHEMIST_MCP_DATA_PATH", raising=False)
    monkeypatch.delenv("TOOL_ALCHEMIST_MCP_GOOSE_CONFIG_PATH", raising=False)

    alch = Alchemist()
    assert alch.data_path == Path(DEFAULT_ALCHEMY_MCP_PATH)
    assert alch.goose_config_path == Path(DEFAULT_GOOSE_CONFIG_PATH)

    assert isinstance(alch.template_env.loader, FileSystemLoader)
    assert alch.template_env.loader.searchpath == [str(TEMPLATE_PATH)]


def test_constructor_with_injected_paths(
    fake_data_path, fake_goose_config_path, fake_template_path
):
    """
    Test that providing paths to the constructor overrides environment variables.
    """
    alch = Alchemist(
        data_path=fake_data_path,
        goose_config_path=fake_goose_config_path,
        template_path=fake_template_path,
    )
    assert alch.data_path == fake_data_path
    assert alch.goose_config_path == fake_goose_config_path
    assert isinstance(alch.template_env.loader, FileSystemLoader)
    assert alch.template_env.loader.searchpath == [str(fake_template_path)]


def test_get_tool_root_path(alchemist):
    tool_name = "MyTool"
    root_path = alchemist.get_tool_root_path(tool_name)
    expected = alchemist.data_path / "mytool"
    assert root_path == expected


def test_get_tool_server_path(alchemist):
    tool_name = "MyTool"
    server_path = alchemist.get_tool_server_path(tool_name)
    expected = alchemist.data_path / "mytool" / "src" / "mytool" / "server.py"
    assert server_path == expected


def test_validate_tool_name_valid():
    """Test that validate_tool_name accepts valid names"""
    alch = Alchemist()
    assert alch.validate_tool_name("valid-name") is True
    assert alch.validate_tool_name("valid_name") is True
    assert alch.validate_tool_name("Valid Name 123") is True


def test_validate_tool_name_invalid():
    """Test that validate_tool_name rejects invalid names"""
    alch = Alchemist()
    with pytest.raises(ValidationError):
        alch.validate_tool_name("invalid@name")
    with pytest.raises(ValidationError):
        alch.validate_tool_name("")
    with pytest.raises(ValidationError):
        alch.validate_tool_name("name with $ symbol")


def test_to_snake_case():
    """Test the to_snake_case static method"""
    alch = Alchemist()
    assert alch.to_snake_case("Hello World") == "hello_world"
    assert alch.to_snake_case("hello-world") == "hello_world"
    assert alch.to_snake_case("Hello-World") == "hello_world"
    assert alch.to_snake_case(" Spaces  Around ") == "spaces_around"


def test_to_kebob_case():
    """Test the to_kebob_case static method"""
    alch = Alchemist()
    assert alch.to_kebob_case("Hello World") == "hello-world"
    assert alch.to_kebob_case("hello_world") == "hello-world"
    assert alch.to_kebob_case("Hello_World") == "hello-world"
    assert alch.to_kebob_case(" Spaces  Around ") == "spaces-around"


def test_add_tool_to_config(alchemist):
    """
    Test that add_tool_to_config modifies the config file as expected.
    """
    tool_name = "AwesomeTool"
    tool_kebab_case = "awesometool"

    alchemist.add_tool_to_config(tool_name)

    with open(alchemist.goose_config_path, "r") as f:
        resulting_config = yaml.safe_load(f)

    assert tool_kebab_case in resulting_config["extensions"]
    assert resulting_config["extensions"][tool_kebab_case]["cmd"] == "uvx"


def test_create_new_tool_uv_not_found():
    """
    Test that create_new_tool raises UVCommandNotFound if 'uv' is not available.
    """
    alch = AlchemistTestable(False, False)
    with patch("shutil.which", return_value=None):
        with pytest.raises(UVCommandNotFound):
            alch.create_new_tool("SomeTool")


def test_create_new_tool_success(alchemist):
    """
    Test that create_new_tool calls the right commands and writes template files.
    """
    tool_name = "Some Tool"
    tool_path = alchemist.data_path / "some-tool"
    server_file_path = tool_path / "src" / "some_tool" / "server.py"
    init_file_path = tool_path / "src" / "some_tool" / "__init__.py"

    created_tool_path = alchemist.create_new_tool(tool_name, "A description")

    assert created_tool_path == tool_path

    assert server_file_path.exists()
    assert init_file_path.exists()

    server_file_content = server_file_path.read_text()
    assert "server template content: Some Tool" in server_file_content

    init_file_content = init_file_path.read_text()
    assert "__init__ template content: some_tool" in init_file_content


def test_check_uv_installed_when_present():
    """
    Confirms _check_uv_installed does not raise if 'uv' is found.
    """
    alch = AlchemistTestable(False, False)
    with patch("shutil.which", return_value="/usr/local/bin/uv"):
        alch._check_uv_installed()


def test_check_uv_installed_when_missing():
    """
    Confirms _check_uv_installed raises if 'uv' is missing.
    """
    alch = AlchemistTestable(False, False)
    with patch("shutil.which", return_value=None):
        with pytest.raises(UVCommandNotFound):
            alch._check_uv_installed()
