from pathlib import Path
from typing import Tuple, List, Optional
from utils import FileUtils, ProjectUtils


class ProjectDetector:
    """Detects projects and locates OpenAPI specifications"""

    SPEC_LOCATIONS = [
        # YAML files
        "src/main/resources/openapi.yaml",
        "src/main/resources/openapi.yml",
        "src/main/resources/swagger.yaml",
        "src/main/resources/swagger.yml",
        "src/main/resources/api/openapi.yaml",
        "openapi.yaml",
        "sample-openapi.yaml",
        "openapi.yml",
        "swagger.yaml",
        "swagger.yml",
        "api/openapi.yaml",
        "docs/openapi.yaml",
        # JSON files
        "src/main/resources/openapi.json",
        "src/main/resources/swagger.json",
        "src/main/resources/api/openapi.json",
        "openapi.json",
        "swagger.json",
        "api/openapi.json",
        "docs/openapi.json",
    ]

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def is_java_project(self) -> Tuple[bool, str]:
        """Check if directory contains a Java project"""
        return ProjectUtils.detect_build_tool(str(self.project_path))

    def find_openapi_specs(self) -> List[Path]:
        """Locate all OpenAPI specification files (YAML and JSON)"""
        specs = []

        # Check standard locations
        for location in self.SPEC_LOCATIONS:
            spec_path = self.project_path / location
            if spec_path.exists():
                specs.append(spec_path)

        # Recursive search for additional YAML specs
        for spec_file in self.project_path.rglob("*openapi*.yaml"):
            if spec_file not in specs and self._is_valid_spec_location(spec_file):
                specs.append(spec_file)

        for spec_file in self.project_path.rglob("*swagger*.yaml"):
            if spec_file not in specs and self._is_valid_spec_location(spec_file):
                specs.append(spec_file)

        # Recursive search for JSON specs
        for spec_file in self.project_path.rglob("*openapi*.json"):
            if spec_file not in specs and self._is_valid_spec_location(spec_file):
                specs.append(spec_file)

        for spec_file in self.project_path.rglob("*swagger*.json"):
            if spec_file not in specs and self._is_valid_spec_location(spec_file):
                specs.append(spec_file)

        return specs

    def _is_valid_spec_location(self, path: Path) -> bool:
        """Filter out build artifacts (but allow test directories for sample specs)"""
        return not ProjectUtils.should_exclude_path(str(path), str(self.project_path))

    def validate_spec_syntax(self, spec_path: Path) -> Tuple[bool, Optional[str]]:
        """Validate that the spec is valid YAML/JSON and contains OpenAPI content"""
        try:
            # Parse based on file extension
            data, file_format = FileUtils.read_spec_file(str(spec_path))

            # Handle case where data is None or not a dict
            if not isinstance(data, dict):
                return (
                    False,
                    f"Invalid {file_format.upper()}: Expected object/dict at root, got {type(data).__name__}",
                )

            # Basic OpenAPI structure validation
            if "openapi" not in data and "swagger" not in data:
                return (
                    False,
                    "Not a valid OpenAPI/Swagger specification (missing 'openapi' or 'swagger' field)",
                )

            return True, None

        except ValueError as e:
            # Handle JSON/YAML parsing errors
            error_msg = str(e)
            if "yaml" in error_msg.lower():
                # YAML syntax warning - might be caught by Spectral
                return True, f"YAML syntax warning: {error_msg}"
            else:
                return False, f"Syntax error: {error_msg}"
        except Exception as e:
            # If we can't read the file at all, fail
            return False, f"Error reading file: {str(e)}"
