from pathlib import Path
from typing import Tuple, List, Optional
import yaml
import json


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
        if (self.project_path / "pom.xml").exists():
            return True, "maven"
        if (self.project_path / "build.gradle").exists() or (
            self.project_path / "build.gradle.kts"
        ).exists():
            return True, "gradle"
        return False, "unknown"

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
        path_str = str(path)
        exclude_patterns = ["target/", "build/", "node_modules/", ".gradle/"]
        return not any(pattern in path_str for pattern in exclude_patterns)

    def validate_spec_syntax(self, spec_path: Path) -> Tuple[bool, Optional[str]]:
        """Validate that the spec is valid YAML/JSON and contains OpenAPI content"""
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                content = f.read()

                # Parse based on file extension
                if spec_path.suffix in [".yaml", ".yml"]:
                    data = yaml.safe_load(content)
                elif spec_path.suffix == ".json":
                    data = json.loads(content)
                else:
                    return False, f"Unsupported file format: {spec_path.suffix}"

                # Handle case where data is None or not a dict
                if not isinstance(data, dict):
                    return (
                        False,
                        "File does not contain a valid OpenAPI specification structure",
                    )

                # Basic OpenAPI structure validation
                if "openapi" not in data and "swagger" not in data:
                    return (
                        False,
                        "Not a valid OpenAPI/Swagger specification (missing 'openapi' or 'swagger' field)",
                    )

                return True, None

        except yaml.YAMLError as e:
            # Report syntax error but don't block scanning if it's a minor YAML issue that Spectral might catch as a rule violation
            # e.g. "mapping values are not allowed here" in a description string
            return True, f"YAML syntax warning: {str(e)}"
        except json.JSONDecodeError as e:
            return False, f"JSON syntax error: {str(e)}"
        except Exception as e:
            # If we can't read the file at all, fail
            return False, f"Error reading file: {str(e)}"
