"""
Path resolution and file search utilities.
"""

from pathlib import Path
from typing import List, Optional
import re


class PathUtils:
    """Utility class for path operations and file searching"""

    @staticmethod
    def find_files(
        root_dir: str,
        pattern: str,
        recursive: bool = True,
        exclude_patterns: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        Find files matching a glob pattern.

        Args:
          root_dir: Root directory to search
          pattern: Glob pattern (e.g., "*.java", "**/Test*.java")
          recursive: Whether to search recursively
          exclude_patterns: List of patterns to exclude (e.g., ["target/", "build/"])

        Returns:
          List of matching Path objects
        """
        root = Path(root_dir)
        if not root.exists():
            return []

        # Use rglob for recursive, glob for non-recursive
        search_fn = root.rglob if recursive else root.glob
        matches = list(search_fn(pattern))

        # Apply exclusion filters
        if exclude_patterns:
            filtered = []
            for match in matches:
                match_str = str(match)
                if not any(excl in match_str for excl in exclude_patterns):
                    filtered.append(match)
            return filtered

        return matches

    @staticmethod
    def find_java_files(root_dir: str, exclude_build_dirs: bool = True) -> List[Path]:
        """
        Find all Java source files in a directory.

        Args:
          root_dir: Root directory to search
          exclude_build_dirs: Whether to exclude build/target directories

        Returns:
          List of Java file paths
        """
        exclude_patterns = (
            ["target/", "build/", ".gradle/", "node_modules/"]
            if exclude_build_dirs
            else None
        )
        return PathUtils.find_files(
            root_dir, "**/*.java", exclude_patterns=exclude_patterns
        )

    @staticmethod
    def find_test_files_for_class(project_root: str, class_name: str) -> List[Path]:
        """
        Find test files for a given class name.

        Args:
          project_root: Project root directory
          class_name: Name of the class (without .java extension)

        Returns:
          List of test file paths
        """
        root = Path(project_root)
        test_files = []

        # Remove common suffixes to get base name
        base_name = (
            class_name.replace("Controller", "")
            .replace("Service", "")
            .replace("Repository", "")
        )

        # Common test patterns
        patterns = [
            f"**/{class_name}Test.java",
            f"**/{class_name}Tests.java",
            f"**/{class_name}TestCase.java",
            f"**/{class_name}IT.java",
            f"**/{class_name}IntegrationTest.java",
            f"**/{base_name}ControllerTest.java",
            f"**/{base_name}ControllerTests.java",
        ]

        for pattern in patterns:
            matches = PathUtils.find_files(project_root, pattern)
            for match in matches:
                # Verify it's in a test directory
                if "/test/" in str(match) or "/tests/" in str(match):
                    if match not in test_files:
                        test_files.append(match)

        return test_files

    @staticmethod
    def resolve_java_file_path(project_root: str, class_fqcn: str) -> Optional[Path]:
        """
        Resolve a fully qualified class name to its source file path.

        Args:
          project_root: Project root directory
          class_fqcn: Fully qualified class name (e.g., "com.example.MyClass")

        Returns:
          Path to source file or None if not found
        """
        root = Path(project_root)

        # Handle inner classes
        if "$" in class_fqcn:
            class_fqcn = class_fqcn.split("$")[0]

        # Convert FQCN to relative path
        rel_path = class_fqcn.replace(".", "/") + ".java"

        # Check common source directories
        source_dirs = ["src/main/java", "src/test/java", "src", "test", "java", ""]

        for src_dir in source_dirs:
            full_path = root / src_dir / rel_path if src_dir else root / rel_path
            if full_path.exists():
                return full_path

        # Fallback: search recursively
        filename = class_fqcn.split(".")[-1] + ".java"
        matches = PathUtils.find_files(
            str(root),
            f"**/{filename}",
            exclude_patterns=["target/", "build/", ".gradle/"],
        )

        if matches:
            # Prefer files in src/main/java
            for match in matches:
                if "src/main/java" in str(match):
                    return match
            # Otherwise return first match
            return matches[0]

        return None

    @staticmethod
    def find_compiled_classes_dir(project_root: str) -> Path:
        """
        Find the compiled classes directory (Maven or Gradle).

        Args:
          project_root: Project root directory

        Returns:
          Path to compiled classes directory, or project root if not found
        """
        root = Path(project_root)

        # Gradle
        gradle_main = root / "build" / "classes" / "java" / "main"
        if gradle_main.exists():
            return gradle_main

        # Maven
        maven_classes = root / "target" / "classes"
        if maven_classes.exists():
            return maven_classes

        # Fallback to project root
        return root

    @staticmethod
    def extract_fqcn_from_message(message: str) -> Optional[str]:
        """
        Extract fully qualified class name from violation message.

        Args:
          message: Violation message containing class references

        Returns:
          FQCN if found, None otherwise
        """
        # Pattern: <com.example.package.ClassName>
        match = re.search(r"<([\w\.]+)>", message)
        if match:
            fqcn = match.group(1)
            # Handle inner classes
            if "$" in fqcn:
                fqcn = fqcn.split("$")[0]
            return fqcn
        return None

    @staticmethod
    def get_relative_path(path: str, base: str) -> str:
        """
        Get relative path from base directory.

        Args:
          path: Full or relative path
          base: Base directory

        Returns:
          Relative path string
        """
        try:
            return str(Path(path).relative_to(Path(base)))
        except ValueError:
            # Path is not relative to base
            return str(path)

    @staticmethod
    def is_build_artifact(path: str) -> bool:
        """
        Check if path is in a build artifact directory.

        Args:
          path: Path to check

        Returns:
          True if path is in build/target/node_modules etc.
        """
        exclude_patterns = [
            "target/",
            "build/",
            ".gradle/",
            "node_modules/",
            "dist/",
            "out/",
        ]
        path_str = str(path)
        return any(pattern in path_str for pattern in exclude_patterns)
