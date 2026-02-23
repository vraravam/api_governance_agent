"""
File utility functions for reading, writing, and managing various file formats.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


class FileUtils:
    """Utility class for file operations"""

    @staticmethod
    def read_json(file_path: str) -> Dict[str, Any]:
        """
        Read and parse a JSON file.

        Args:
          file_path: Path to JSON file

        Returns:
          Parsed JSON as dictionary

        Raises:
          FileNotFoundError: If file doesn't exist
          json.JSONDecodeError: If JSON is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def read_json_safe(
        file_path: str, default: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Read JSON file, returning default value if file not found or invalid.

        Args:
          file_path: Path to JSON file
          default: Default value to return on error (empty dict if None)

        Returns:
          Parsed JSON or default value
        """
        if default is None:
            default = {}

        try:
            return FileUtils.read_json(file_path)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    @staticmethod
    def write_json(file_path: str, data: Dict[str, Any], indent: int = 2):
        """
        Write data to JSON file.

        Args:
          file_path: Path to output file
          data: Data to write
          indent: JSON indentation level
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)

    @staticmethod
    def read_yaml(file_path: str) -> Dict[str, Any]:
        """
        Read and parse a YAML file.

        Args:
          file_path: Path to YAML file

        Returns:
          Parsed YAML as dictionary

        Raises:
          FileNotFoundError: If file doesn't exist
          yaml.YAMLError: If YAML is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @staticmethod
    def read_yaml_safe(
        file_path: str, default: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Read YAML file, returning default value if file not found or invalid.

        Args:
          file_path: Path to YAML file
          default: Default value to return on error (empty dict if None)

        Returns:
          Parsed YAML or default value
        """
        if default is None:
            default = {}

        try:
            return FileUtils.read_yaml(file_path)
        except (FileNotFoundError, yaml.YAMLError):
            return default

    @staticmethod
    def write_yaml(file_path: str, data: Dict[str, Any]):
        """
        Write data to YAML file.

        Args:
          file_path: Path to output file
          data: Data to write
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False)

    @staticmethod
    def read_spec_file(file_path: str) -> Tuple[Dict[str, Any], str]:
        """
        Read OpenAPI spec file (JSON or YAML).

        Args:
          file_path: Path to spec file

        Returns:
          Tuple of (parsed_data, file_format)
          file_format is either "json" or "yaml"

        Raises:
          ValueError: If file format is not supported
          FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)

        if path.suffix == ".json":
            return FileUtils.read_json(file_path), "json"
        elif path.suffix in [".yaml", ".yml"]:
            return FileUtils.read_yaml(file_path), "yaml"
        else:
            raise ValueError(f"Unsupported spec format: {path.suffix}")

    @staticmethod
    def read_text(file_path: str) -> str:
        """
        Read text file content.

        Args:
          file_path: Path to text file

        Returns:
          File content as string
        """
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def write_text(file_path: str, content: str):
        """
        Write content to text file.

        Args:
          file_path: Path to output file
          content: Text content to write
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def ensure_dir(dir_path: str) -> Path:
        """
        Ensure directory exists, creating it if necessary.

        Args:
          dir_path: Path to directory

        Returns:
          Path object for the directory
        """
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
