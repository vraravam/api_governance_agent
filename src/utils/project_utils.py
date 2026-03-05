"""
Project structure and build tool detection utilities.
"""

from pathlib import Path
from typing import Tuple, Optional


class ProjectUtils:
    """Utility class for project detection and analysis"""

    @staticmethod
    def detect_build_tool(project_path: str) -> Tuple[bool, str]:
        """
        Detect if project is Java and which build tool it uses.

        Args:
          project_path: Path to project directory

        Returns:
          Tuple of (is_java_project, build_tool_name)
          build_tool_name will be "maven", "gradle", or "unknown"
        """
        root = Path(project_path)

        # Maven
        if (root / "pom.xml").exists():
            return True, "maven"

        # Gradle
        if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
            return True, "gradle"

        return False, "unknown"

    @staticmethod
    def is_maven_project(project_path: str) -> bool:
        """Check if project uses Maven"""
        return (Path(project_path) / "pom.xml").exists()

    @staticmethod
    def is_gradle_project(project_path: str) -> bool:
        """Check if project uses Gradle"""
        root = Path(project_path)
        return (root / "build.gradle").exists() or (root / "build.gradle.kts").exists()

    @staticmethod
    def is_java_project(project_path: str) -> bool:
        """Check if project is a Java project"""
        is_java, _ = ProjectUtils.detect_build_tool(project_path)
        return is_java

    @staticmethod
    def detect_project_type(project_path: str) -> str:
        """
        Detect overall project type.

        Args:
          project_path: Path to project directory

        Returns:
          Project type string: "java-maven", "java-gradle", "python", "node", "unknown"
        """
        root = Path(project_path)

        # Java projects
        if ProjectUtils.is_maven_project(project_path):
            return "java-maven"
        if ProjectUtils.is_gradle_project(project_path):
            return "java-gradle"

        # Python projects
        if any(
            [
                (root / "setup.py").exists(),
                (root / "pyproject.toml").exists(),
                (root / "requirements.txt").exists(),
                (root / "Pipfile").exists(),
            ]
        ):
            return "python"

        # Node projects
        if (root / "package.json").exists():
            return "node"

        return "unknown"

    @staticmethod
    def get_source_directories(project_path: str) -> list[str]:
        """
        Get typical source directories for a project.

        Args:
          project_path: Path to project directory

        Returns:
          List of source directory paths relative to project root
        """
        project_type = ProjectUtils.detect_project_type(project_path)

        if project_type.startswith("java"):
            return [
                "src/main/java",
                "src/test/java",
                "src/main/resources",
                "src/test/resources",
            ]
        elif project_type == "python":
            return [
                "src",
                "tests",
                "test",
            ]
        elif project_type == "node":
            return [
                "src",
                "lib",
                "test",
                "tests",
            ]
        else:
            return ["src", "test", "tests"]

    @staticmethod
    def get_build_directories(project_path: str) -> list[str]:
        """
        Get build output directories for a project.

        Args:
          project_path: Path to project directory

        Returns:
          List of build directory paths relative to project root
        """
        project_type = ProjectUtils.detect_project_type(project_path)

        if project_type == "java-maven":
            return ["target"]
        elif project_type == "java-gradle":
            return ["build", ".gradle"]
        elif project_type == "python":
            return ["build", "dist", "__pycache__", ".pytest_cache", ".tox"]
        elif project_type == "node":
            return ["node_modules", "dist", "build", ".next", "out"]
        else:
            return ["build", "target", "dist", "out"]

    @staticmethod
    def should_exclude_path(path: str, project_path: str) -> bool:
        """
        Check if a path should be excluded from analysis.

        Args:
          path: Path to check
          project_path: Project root path

        Returns:
          True if path should be excluded
        """
        # Get build directories for this project type
        build_dirs = ProjectUtils.get_build_directories(project_path)

        # Common exclusions
        exclude_patterns = build_dirs + [
            ".git",
            ".svn",
            ".hg",
            "__pycache__",
            ".pytest_cache",
            "venv",
            ".venv",
            "env",
            ".env",
        ]

        path_str = str(path)
        return any(pattern in path_str for pattern in exclude_patterns)

    @staticmethod
    def get_project_name(project_path: str) -> Optional[str]:
        """
        Try to extract project name from build files.

        Args:
          project_path: Path to project directory

        Returns:
          Project name if found, None otherwise
        """
        root = Path(project_path)

        # Try Maven pom.xml
        pom = root / "pom.xml"
        if pom.exists():
            try:
                import xml.etree.ElementTree as ET

                tree = ET.parse(pom)
                namespace = {"maven": "http://maven.apache.org/POM/4.0.0"}
                artifact_id = tree.find(".//maven:artifactId", namespace)
                if artifact_id is not None:
                    return artifact_id.text
            except:
                pass

        # Try package.json
        package_json = root / "package.json"
        if package_json.exists():
            try:
                from utils import FileUtils

                data = FileUtils.read_json(str(package_json))
                return data.get("name")
            except:
                pass

        # Try pyproject.toml
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                import toml

                data = toml.load(pyproject)
                return data.get("project", {}).get("name") or data.get("tool", {}).get(
                    "poetry", {}
                ).get("name")
            except:
                pass

        # Fallback to directory name
        return root.name
