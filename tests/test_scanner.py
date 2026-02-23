"""
Unit tests for scanner modules using pytest.
Tests GovernanceScanner, ProjectDetector, and related functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scanner.project_detector import ProjectDetector


class TestProjectDetector:
    """Test ProjectDetector functionality"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Create and clean up temporary project directory"""
        self.temp_dir = tempfile.mkdtemp()
        yield
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_detect_maven_project(self):
        """Test Maven project detection"""
        pom = Path(self.temp_dir) / "pom.xml"
        pom.write_text("<project></project>")

        detector = ProjectDetector(self.temp_dir)
        is_java, tool = detector.is_java_project()

        assert is_java
        assert tool == "maven"

    def test_detect_gradle_project(self):
        """Test Gradle project detection"""
        build = Path(self.temp_dir) / "build.gradle"
        build.write_text("// gradle")

        detector = ProjectDetector(self.temp_dir)
        is_java, tool = detector.is_java_project()

        assert is_java
        assert tool == "gradle"

    def test_detect_no_java_project(self):
        """Test non-Java project detection"""
        detector = ProjectDetector(self.temp_dir)
        is_java, tool = detector.is_java_project()

        assert not is_java
        assert tool == "unknown"

    def test_find_openapi_specs_empty(self):
        """Test finding specs in empty directory"""
        detector = ProjectDetector(self.temp_dir)
        specs = detector.find_openapi_specs()

        assert len(specs) == 0

    def test_find_openapi_specs_yaml(self):
        """Test finding YAML OpenAPI specs"""
        spec_dir = Path(self.temp_dir) / "src" / "main" / "resources"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0\ninfo:\n  title: Test\n")

        detector = ProjectDetector(self.temp_dir)
        specs = detector.find_openapi_specs()

        assert len(specs) > 0
        assert any("openapi.yaml" in str(s) for s in specs)

    def test_find_openapi_specs_json(self):
        """Test finding JSON OpenAPI specs"""
        spec_file = Path(self.temp_dir) / "openapi.json"
        spec_file.write_text('{"openapi": "3.0.0", "info": {"title": "Test"}}')

        detector = ProjectDetector(self.temp_dir)
        specs = detector.find_openapi_specs()

        assert len(specs) > 0
        assert any("openapi.json" in str(s) for s in specs)

    def test_validate_spec_syntax_valid_yaml(self):
        """Test validating valid YAML spec"""
        spec_file = Path(self.temp_dir) / "openapi.yaml"
        spec_file.write_text("openapi: '3.0.0'\ninfo:\n  title: Test API\n")

        detector = ProjectDetector(self.temp_dir)
        is_valid, error = detector.validate_spec_syntax(spec_file)

        assert is_valid

    def test_validate_spec_syntax_valid_json(self):
        """Test validating valid JSON spec"""
        spec_file = Path(self.temp_dir) / "openapi.json"
        spec_file.write_text('{"openapi": "3.0.0", "info": {"title": "Test"}}')

        detector = ProjectDetector(self.temp_dir)
        is_valid, error = detector.validate_spec_syntax(spec_file)

        assert is_valid

    # def test_validate_spec_syntax_missing_openapi_field(self):
    #   """Test validating spec without openapi field"""
    #   spec_file = Path(self.temp_dir) / "invalid.yaml"
    #   spec_file.write_text("info:\n  title: Test\n")

    #   detector = ProjectDetector(self.temp_dir)
    #   is_valid, error = detector.validate_spec_syntax(spec_file)

    #   assert not is_valid
    #   assert "openapi" in error.lower()

    def test_is_valid_spec_location(self):
        """Test spec location validation"""
        detector = ProjectDetector(self.temp_dir)

        # Valid locations
        assert detector._is_valid_spec_location(Path("src/main/resources/openapi.yaml"))
        assert detector._is_valid_spec_location(Path("api/openapi.json"))

        # Invalid locations (build artifacts)
        assert not detector._is_valid_spec_location(Path("target/openapi.yaml"))
        assert not detector._is_valid_spec_location(Path("build/openapi.json"))
