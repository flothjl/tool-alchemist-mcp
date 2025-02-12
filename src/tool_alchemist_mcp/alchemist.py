import os
from pathlib import Path

DEFAULT_ALCHEMY_MCP_PATH = Path.home().joinpath(".local/share/")


class Alchemist:
    def __init__(self):
        self.data_path = DEFAULT_ALCHEMY_MCP_PATH
        if custom_data_path := os.getenv("TOOL_ALCHEMIST_MCP_DATA_PATH"):
            self.data_path = Path(custom_data_path)

    def create_new_tool(self, name: str, description: str | None = None):
        """
        Must accomplish the following:
            1. boiler plate should be created in self.custom_data_path directory
            2. package should be created using uv init --package --description <description or name> <name-in-kabob-case>
            3. boiler plate should be added to <name-in-kabob-case>/src/<name_in_snake_case>/server.py
        """


if __name__ == "__main__":
    print(DEFAULT_ALCHEMY_MCP_PATH)
