"""
Unit tests for utility modules using pytest.
Tests FileUtils, ProcessUtils, PathUtils, ViolationUtils, ReportUtils, ProjectUtils.
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import (
    FileUtils,
    ProcessUtils,
    PathUtils,
    ViolationUtils,
    ReportUtils,
    ProjectUtils,
)


class TestFileUtils:
    """Test FileUtils functionality"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Create and clean up temporary directory for tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_json = os.path.join(self.temp_dir, "test.json")
        self.test_yaml = os.path.join(self.temp_dir, "test.yaml")
        self.test_text = os.path.join(self.temp_dir, "test.txt")
        yield
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_read_write_json(self):
        """Test JSON read and write operations"""
        test_data = {"key": "value", "count": 42, "items": [1, 2, 3]}
        FileUtils.write_json(self.test_json, test_data)
        loaded = FileUtils.read_json(self.test_json)
        assert loaded == test_data

    def test_read_json_nonexistent(self):
        """Test reading nonexistent JSON file raises error"""
        with pytest.raises(FileNotFoundError):
            FileUtils.read_json("/nonexistent/file.json")

    def test_read_json_safe(self):
        """Test safe JSON reading with default"""
        result = FileUtils.read_json_safe("/nonexistent/file.json", {"default": True})
        assert result == {"default": True}

    def test_read_write_yaml(self):
        """Test YAML read and write operations"""
        test_data = {"key": "value", "nested": {"a": 1, "b": 2}}
        FileUtils.write_yaml(self.test_yaml, test_data)
        loaded = FileUtils.read_yaml(self.test_yaml)
        assert loaded == test_data

    def test_read_write_text(self):
        """Test text file operations"""
        test_content = "Hello\nWorld\n"
        FileUtils.write_text(self.test_text, test_content)
        loaded = FileUtils.read_text(self.test_text)
        assert loaded == test_content

    def test_ensure_dir(self):
        """Test directory creation"""
        new_dir = os.path.join(self.temp_dir, "subdir", "nested")
        result = FileUtils.ensure_dir(new_dir)
        assert result.exists()
        assert result.is_dir()

    def test_read_spec_file_json(self):
        """Test reading JSON spec file"""
        spec_data = {"openapi": "3.0.0", "info": {"title": "Test"}}
        FileUtils.write_json(self.test_json, spec_data)
        data, fmt = FileUtils.read_spec_file(self.test_json)
        assert data == spec_data
        assert fmt == "json"

    def test_read_spec_file_yaml(self):
        """Test reading YAML spec file"""
        spec_data = {"openapi": "3.0.0", "info": {"title": "Test"}}
        FileUtils.write_yaml(self.test_yaml, spec_data)
        data, fmt = FileUtils.read_spec_file(self.test_yaml)
        assert data == spec_data
        assert fmt == "yaml"


class TestProcessUtils:
    """Test ProcessUtils functionality"""

    def test_run_command_success(self):
        """Test successful command execution"""

    def test_run_command_success(self):
        """Test successful command execution"""
        result = ProcessUtils.run_command(["echo", "test"])
        assert result.success
        assert "test" in result.stdout

    def test_run_command_failure(self):
        """Test failed command execution"""
        result = ProcessUtils.run_command_safe(["false"])
        assert not result.success

    def test_check_binary_exists_true(self):
        """Test binary existence check - positive"""
        assert ProcessUtils.check_binary_exists("python3")

    def test_check_binary_exists_false(self):
        """Test binary existence check - negative"""
        assert not ProcessUtils.check_binary_exists("nonexistent_binary_12345")

    def test_get_binary_path(self):
        """Test getting binary path"""
        path = ProcessUtils.get_binary_path("python3")
        assert path is not None
        assert os.path.exists(path)

    def test_get_binary_version(self):
        """Test getting binary version"""
        version = ProcessUtils.get_binary_version("python3")
        assert version is not None
        assert isinstance(version, str)


class TestPathUtils:
    """Test PathUtils functionality"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up and clean up test directory structure"""
        self.temp_dir = tempfile.mkdtemp()
        # Create test files
        os.makedirs(os.path.join(self.temp_dir, "src", "main", "java"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "src", "test", "java"), exist_ok=True)

        # Create Java files
        self.main_file = os.path.join(self.temp_dir, "src", "main", "java", "User.java")
        self.test_file = os.path.join(
            self.temp_dir, "src", "test", "java", "UserTest.java"
        )

        with open(self.main_file, "w") as f:
            f.write("public class User {}")
        with open(self.test_file, "w") as f:
            f.write("public class UserTest {}")

        yield
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_find_files(self):
        """Test finding files by pattern"""
        files = PathUtils.find_files(self.temp_dir, "*.java", recursive=True)
        assert len(files) > 0
        java_files = [f for f in files if str(f).endswith(".java")]
        assert len(java_files) == 2

    def test_find_java_files(self):
        """Test finding Java files"""
        files = PathUtils.find_java_files(self.temp_dir)
        assert len(files) == 2

    def test_find_test_files_for_class(self):
        """Test finding test files for a class"""
        tests = PathUtils.find_test_files_for_class(self.temp_dir, "User")
        assert len(tests) > 0
        test_names = [t.name for t in tests]
        assert "UserTest.java" in test_names

    def test_extract_fqcn_from_message(self):
        """Test extracting FQCN from message"""
        message = "Class <com.example.MyClass> violates rule"
        fqcn = PathUtils.extract_fqcn_from_message(message)
        assert fqcn == "com.example.MyClass"

    def test_get_relative_path(self):
        """Test getting relative path"""
        full_path = os.path.join(self.temp_dir, "src", "main", "User.java")
        rel = PathUtils.get_relative_path(full_path, self.temp_dir)
        assert "src" in rel
        assert self.temp_dir not in rel

    def test_is_build_artifact(self):
        """Test build artifact detection"""
        assert PathUtils.is_build_artifact("target/classes/User.class")
        assert PathUtils.is_build_artifact("build/libs/app.jar")
        assert not PathUtils.is_build_artifact("src/main/java/User.java")


class TestViolationUtils:
    """Test ViolationUtils functionality"""

    def test_normalize_spectral_violation(self):
        """Test normalizing Spectral violation"""
        raw = {
            "code": "test-rule",
            "message": "Test message",
            "severity": 1,
            "path": ["paths", "/users"],
            "range": {"start": {"line": 10}},
            "source": "test.yaml",
        }

        normalized = ViolationUtils.normalize_spectral_violation(raw)
        assert normalized["rule"] == "test-rule"
        assert normalized["engine"] == "spectral"
        assert normalized["type"] == "api"

    def test_normalize_archunit_violation(self):
        """Test normalizing ArchUnit violation"""
        raw = {
            "rule": "arch-rule",
            "violation": "Test violation",
            "file": "User.java",
            "class": "com.example.User",
            "severity": "ERROR",
        }

        normalized = ViolationUtils.normalize_archunit_violation(raw)
        assert normalized["rule"] == "arch-rule"
        assert normalized["engine"] == "archunit"
        assert normalized["type"] == "architecture"

    def test_group_by_severity(self):
        """Test grouping violations by severity"""
        violations = [
            {"rule": "r1", "severity": 0},
            {"rule": "r2", "severity": 1},
            {"rule": "r3", "severity": 0},
        ]

        groups = ViolationUtils.group_by_severity(violations)
        assert len(groups[0]) == 2
        assert len(groups[1]) == 1

    def test_group_by_rule(self):
        """Test grouping violations by rule"""
        violations = [
            {"rule": "rule1", "message": "m1"},
            {"rule": "rule2", "message": "m2"},
            {"rule": "rule1", "message": "m3"},
        ]

        groups = ViolationUtils.group_by_rule(violations)
        assert len(groups["rule1"]) == 2
        assert len(groups["rule2"]) == 1

    def test_count_by_severity(self):
        """Test counting violations by severity"""
        violations = [
            {"severity": 0},
            {"severity": 1},
            {"severity": 0},
            {"severity": 2},
        ]

        counts = ViolationUtils.count_by_severity(violations)
        assert counts["error"] == 2
        assert counts["warning"] == 1
        assert counts["info"] == 1

    def test_filter_by_severity(self):
        """Test filtering violations by severity"""
        violations = [
            {"severity": 0, "message": "error"},
            {"severity": 1, "message": "warning"},
            {"severity": 2, "message": "info"},
        ]

        errors = ViolationUtils.filter_by_severity(violations, 0)
        assert len(errors) == 1
        assert errors[0]["message"] == "error"

    def test_merge_violations(self):
        """Test merging violation lists"""
        list1 = [{"rule": "r1"}]
        list2 = [{"rule": "r2"}]
        list3 = [{"rule": "r3"}]

        merged = ViolationUtils.merge_violations(list1, list2, list3)
        assert len(merged) == 3

    def test_deduplicate_violations(self):
        """Test deduplicating violations"""
        violations = [
            {"rule": "r1", "file": "f1", "line": 1, "message": "m1"},
            {"rule": "r1", "file": "f1", "line": 1, "message": "m1"},
            {"rule": "r2", "file": "f2", "line": 2, "message": "m2"},
        ]

        unique = ViolationUtils.deduplicate_violations(violations)
        assert len(unique) == 2

    def test_prioritize_violations(self):
        """Test prioritizing violations (Java first)"""
        violations = [
            {"file": "spec.yaml"},
            {"file": "User.java"},
            {"file": "api.json"},
        ]

        prioritized = ViolationUtils.prioritize_violations(violations)
        assert prioritized[0]["file"].endswith(".java")


class TestReportUtils:
    """Test ReportUtils functionality"""

    def test_format_severity_icon(self):
        """Test severity icon formatting"""
        assert ReportUtils.format_severity_icon(0) == "🔴"
        assert ReportUtils.format_severity_icon(1) == "🟡"
        assert ReportUtils.format_severity_icon(2) == "🔵"

    def test_format_severity_label(self):
        """Test severity label formatting"""
        assert ReportUtils.format_severity_label(0) == "Error"
        assert ReportUtils.format_severity_label(1) == "Warning"
        assert ReportUtils.format_severity_label(2) == "Info"

    def test_format_timestamp(self):
        """Test timestamp formatting"""
        from datetime import datetime

        dt = datetime(2024, 1, 15, 10, 30, 0)
        formatted = ReportUtils.format_timestamp(dt)
        assert formatted == "2024-01-15 10:30:00"

    def test_format_violation_markdown(self):
        """Test violation markdown formatting"""
        violation = {
            "rule": "test-rule",
            "message": "Test message",
            "severity": 0,
            "file": "test.yaml",
            "line": 10,
        }

        formatted = ReportUtils.format_violation_markdown(violation)
        assert "test-rule" in formatted
        assert "Test message" in formatted
        assert "🔴" in formatted

    def test_create_summary_header(self):
        """Test summary header creation"""
        header = ReportUtils.create_summary_header("Test Report", "/path/to/project")
        assert "Test Report" in header
        assert "/path/to/project" in header


class TestProjectUtils:
    """Test ProjectUtils functionality"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up and clean up test directory"""
        self.temp_dir = tempfile.mkdtemp()
        yield
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_detect_maven_project(self):
        """Test Maven project detection"""
        pom_path = os.path.join(self.temp_dir, "pom.xml")
        with open(pom_path, "w") as f:
            f.write("<project></project>")

        is_java, tool = ProjectUtils.detect_build_tool(self.temp_dir)
        assert is_java
        assert tool == "maven"

    def test_detect_gradle_project(self):
        """Test Gradle project detection"""
        build_path = os.path.join(self.temp_dir, "build.gradle")
        with open(build_path, "w") as f:
            f.write("// Gradle build")

        is_java, tool = ProjectUtils.detect_build_tool(self.temp_dir)
        assert is_java
        assert tool == "gradle"

    def test_detect_python_project(self):
        """Test Python project detection"""
        req_path = os.path.join(self.temp_dir, "requirements.txt")
        with open(req_path, "w") as f:
            f.write("pytest\n")

        project_type = ProjectUtils.detect_project_type(self.temp_dir)
        assert project_type == "python"

    def test_get_source_directories_java(self):
        """Test getting Java source directories"""
        pom_path = os.path.join(self.temp_dir, "pom.xml")
        with open(pom_path, "w") as f:
            f.write("<project></project>")

        dirs = ProjectUtils.get_source_directories(self.temp_dir)
        assert "src/main/java" in dirs
        assert "src/test/java" in dirs

    def test_get_build_directories_maven(self):
        """Test getting Maven build directories"""
        pom_path = os.path.join(self.temp_dir, "pom.xml")
        with open(pom_path, "w") as f:
            f.write("<project></project>")

        dirs = ProjectUtils.get_build_directories(self.temp_dir)
        assert "target" in dirs

    def test_should_exclude_path(self):
        """Test path exclusion logic"""
        pom_path = os.path.join(self.temp_dir, "pom.xml")
        with open(pom_path, "w") as f:
            f.write("<project></project>")

        assert ProjectUtils.should_exclude_path(
            "target/classes/User.class", self.temp_dir
        )
        assert not ProjectUtils.should_exclude_path(
            "src/main/java/User.java", self.temp_dir
        )
