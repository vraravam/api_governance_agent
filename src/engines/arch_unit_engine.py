import os
import subprocess
import requests
import json
from pathlib import Path
from typing import List, Dict, Optional
from utils.logger import logger


class ArchUnitEngine:
    """
    Engine to run ArchUnit tests against a Java project.
    Manages dependencies (JARs), compilation, and execution.
    """

    ARCHUNIT_VERSION = "1.2.1"
    SLF4J_VERSION = "2.0.9"

    JARS = {
        "archunit": f"https://repo1.maven.org/maven2/com/tngtech/archunit/archunit/{ARCHUNIT_VERSION}/archunit-{ARCHUNIT_VERSION}.jar",
        "slf4j-api": f"https://repo1.maven.org/maven2/org/slf4j/slf4j-api/{SLF4J_VERSION}/slf4j-api-{SLF4J_VERSION}.jar",
        "slf4j-simple": f"https://repo1.maven.org/maven2/org/slf4j/slf4j-simple/{SLF4J_VERSION}/slf4j-simple-{SLF4J_VERSION}.jar",
    }

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.resources_dir = Path(__file__).parent.parent.parent / "resources" / "java"
        self.lib_dir = self.resources_dir / "lib"
        self.runner_src = self.resources_dir / "ArchUnitRunner.java"

        self.lib_dir.mkdir(parents=True, exist_ok=True)

    def _download_jars(self):
        """Download necessary JARs if missing"""
        for name, url in self.JARS.items():
            filename = url.split("/")[-1]
            filepath = self.lib_dir / filename
            if not filepath.exists():
                logger.info(f"Downloading {name}...")
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                except Exception as e:
                    logger.error(f"Failed to download {name}: {e}")
                    raise

    def _get_classpath(self) -> str:
        """Construct classpath for Java execution"""
        jars = list(self.lib_dir.glob("*.jar"))
        classpath_elements = [str(j) for j in jars]
        classpath_elements.append(str(self.resources_dir))  # For compiled runner class
        # Use platform-specific classpath separator: ; on Windows, : on Unix
        separator = ";" if os.name == "nt" else ":"
        return separator.join(classpath_elements)

    def _compile_runner(self):
        """Compile the Java runner"""
        classpath = self._get_classpath()
        cmd = ["javac", "-cp", classpath, str(self.runner_src)]

        logger.info(f"Compiling ArchUnitRunner: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Compilation failed: {result.stderr}")
            raise RuntimeError("Failed to compile ArchUnitRunner")

    def _find_compiled_classes_dir(self) -> Path:
        """
        Find the compiled classes directory for the project.

        Priority:
        1. Gradle: build/classes/java/main
        2. Maven: target/classes
        3. Fallback to project root (ArchUnit will import source files)

        Returns:
            Path to compiled classes directory, or project root if not found
        """
        # Gradle structure
        gradle_main = self.project_path / "build" / "classes" / "java" / "main"
        if gradle_main.exists() and gradle_main.is_dir():
            logger.info(f"✅ Found Gradle compiled classes: {gradle_main}")
            return gradle_main

        # Maven structure
        maven_classes = self.project_path / "target" / "classes"
        if maven_classes.exists() and maven_classes.is_dir():
            logger.info(f"✅ Found Maven compiled classes: {maven_classes}")
            return maven_classes

        # Fallback: ArchUnit can import from source, but test filtering may not work
        logger.warning(
            f"⚠️  Compiled classes not found. Using project root: {self.project_path}"
        )
        logger.warning(
            "⚠️  ArchUnit will scan source files. Run 'gradle build' or 'mvn compile' first for better results."
        )
        return self.project_path

    def _resolve_java_file_path(
        self, filename: str, violation_message: str
    ) -> Optional[Path]:
        """
        Resolve a Java filename to its full path in the project.

        Strategies:
        1. Extract FQCN from message and map to file path
        2. Search in common source directories
        3. Recursively search entire project

        Args:
            filename: Short filename like "CodingViolations.java"
            violation_message: Full violation message containing class names

        Returns:
            Path object if file found, None otherwise
        """
        import re

        # Strategy 1: Extract FQCN (Fully Qualified Class Name) from message
        # Pattern: <com.example.package.ClassName> or <com.example.package.ClassName$InnerClass>
        class_match = re.search(r"<([\w\.]+)>", violation_message)
        if class_match:
            fqcn = class_match.group(1)

            # Handle inner classes: com.example.MyClass$Inner -> com.example.MyClass
            if "$" in fqcn:
                fqcn = fqcn.split("$")[0]

            # Convert FQCN to path: com.example.MyClass -> com/example/MyClass.java
            rel_path = fqcn.replace(".", "/") + ".java"

            # Search in common Java source directories
            common_source_dirs = [
                "src/main/java",  # Maven/Gradle main
                "src/test/java",  # Maven/Gradle test
                "src",  # Simple structure
                "test",  # Simple test structure
                "java",  # Alternative structure
                "",  # Root level
            ]

            for src_dir in common_source_dirs:
                if src_dir:
                    full_path = self.project_path / src_dir / rel_path
                else:
                    full_path = self.project_path / rel_path

                if full_path.exists():
                    logger.debug(f"Resolved {filename} -> {full_path}")
                    return full_path

        # Strategy 2: Direct search in common directories
        for src_dir in ["src/main/java", "src/test/java", "src", "test", "com", ""]:
            search_root = self.project_path / src_dir if src_dir else self.project_path
            if search_root.exists():
                matches = list(search_root.rglob(filename))
                if matches:
                    # If multiple matches, prefer ones in src/main/java
                    for match in matches:
                        # Use Path.parts to be platform-independent
                        if (
                            "src" in match.parts
                            and "main" in match.parts
                            and "java" in match.parts
                        ):
                            logger.debug(
                                f"Resolved {filename} -> {match} (preferred main source)"
                            )
                            return match
                    # Otherwise return first match
                    logger.debug(f"Resolved {filename} -> {matches[0]}")
                    return matches[0]

        # Strategy 3: Recursive search as last resort
        matches = list(self.project_path.rglob(filename))
        if matches:
            # Prefer files not in build/target directories
            for match in matches:
                # Use Path.parts to be platform-independent
                match_parts = match.parts
                excluded = any(
                    excl in match_parts
                    for excl in ["target", "build", ".gradle", "node_modules"]
                )
                if not excluded:
                    logger.debug(f"Resolved {filename} -> {match} (recursive search)")
                    return match
            # If all are in build dirs, just return first
            logger.debug(f"Resolved {filename} -> {matches[0]} (in build dir)")
            return matches[0]

        # Could not resolve
        logger.warning(f"Could not resolve file path for {filename}")
        logger.debug(f"Searched in: {self.project_path}")
        logger.debug(f"Message excerpt: {violation_message[:200]}")
        return None

    def run_scan(self) -> List[Dict]:
        """Run the ArchUnit scan"""
        self._download_jars()
        self._compile_runner()

        # Find compiled classes directory (build/classes/java/main or target/classes)
        classes_dir = self._find_compiled_classes_dir()

        classpath = self._get_classpath()
        # Add project classes to classpath? No, ArchUnit imports them via path argument.
        # But we need the runner in the classpath.

        cmd = [
            "java",
            "-cp",
            classpath,
            "ArchUnitRunner",
            str(classes_dir),  # Pass compiled classes dir, not project root
        ]

        cmd_str = " ".join(cmd)
        logger.info(f"Running ArchUnit scan on: {classes_dir}")
        logger.info(f"Command: {cmd_str}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"ArchUnit run failed: {result.stderr}")
            # Even if it fails, we might have partial output or it might be a crash
            return []

        # Parse JSON output
        output = result.stdout
        try:
            start_marker = "---JSON-START---"
            end_marker = "---JSON-END---"

            if start_marker in output and end_marker in output:
                json_str = output.split(start_marker)[1].split(end_marker)[0]
                violations = json.loads(json_str)

                # Add metadata and parse location
                # IMPORTANT: Never skip violations - always include them in the report
                all_violations = []
                for v in violations:
                    v["engine"] = "archunit"
                    # Use severity from Java runner if available (0=Critical, 1=Warning)
                    if "severity" in v:
                        v["severity"] = int(v["severity"])
                    else:
                        v["severity"] = 1

                    # Parse location from message - try multiple patterns
                    import re

                    message = v.get("message", "")

                    # Pattern 1: "... in (FileName.java:123)"
                    loc_match = re.search(r"in \(([^/\\:]+\.java):(\d+)\)", message)

                    # Pattern 2: "(FileName.java:123)" anywhere in message
                    if not loc_match:
                        loc_match = re.search(r"\(([^/\\:]+\.java):(\d+)\)", message)

                    # Pattern 3: "FileName.java:123" (without parentheses)
                    if not loc_match:
                        loc_match = re.search(r"([^/\\:\s]+\.java):(\d+)", message)

                    if loc_match:
                        filename = loc_match.group(1)
                        line = int(loc_match.group(2))

                        logger.debug(f"Parsed location: {filename}:{line} from message")

                        # Resolve full path using improved strategies
                        resolved_path = self._resolve_java_file_path(filename, message)

                        if resolved_path:
                            # Best case: We have file path and line number
                            v["file"] = str(resolved_path)
                            v["source"] = str(resolved_path)
                            v["line"] = line
                            logger.debug(
                                f"✅ Resolved {filename}:{line} -> {resolved_path}"
                            )
                        else:
                            # We have line number but couldn't resolve full path
                            # Still include the violation with partial info
                            v["file"] = filename  # Just the filename, not full path
                            v["source"] = filename
                            v["line"] = line
                            logger.warning(
                                f"⚠️ Could not resolve full path for {filename}:{line}, using filename only"
                            )
                    else:
                        # No location found in message - include violation without line number
                        # Extract class name from message as fallback for file field
                        class_match = re.search(r"<([^>]+)>", message)
                        if class_match:
                            class_name = class_match.group(1)
                            # Extract simple class name (last part after dot)
                            simple_name = class_name.split(".")[-1]
                            v["file"] = f"{simple_name}.java"
                            v["source"] = f"{simple_name}.java"
                        else:
                            v["file"] = "Unknown location"
                            v["source"] = "Unknown location"

                        # Don't set line field at all - omit it from the violation
                        # This is better than showing null or 0
                        if "line" in v:
                            del v["line"]
                        logger.debug(
                            "⚠️ No file location found in message, using class name fallback"
                        )

                    # ALWAYS add the violation to the list
                    all_violations.append(v)

                logger.info(
                    f"Processed {len(all_violations)} ArchUnit violations (all included in report)"
                )
                return all_violations
            else:
                logger.warning("No JSON output found from ArchUnitRunner")
                return []
        except Exception as e:
            logger.error(f"Failed to parse ArchUnit output: {e}")
            return []
