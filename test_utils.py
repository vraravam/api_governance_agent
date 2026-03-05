#!/usr/bin/env python3
"""
Test script to verify utility refactoring works correctly.
Run this to ensure all utility modules are working.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_file_utils():
    """Test FileUtils"""
    print("Testing FileUtils...")
    from utils import FileUtils

    # Test directory creation
    test_dir = FileUtils.ensure_dir("/tmp/test_utils")
    assert test_dir.exists(), "Failed to create directory"

    # Test JSON operations
    test_data = {"test": "data", "count": 42}
    FileUtils.write_json("/tmp/test_utils/test.json", test_data)
    loaded = FileUtils.read_json("/tmp/test_utils/test.json")
    assert loaded == test_data, "JSON read/write mismatch"

    # Test safe operations
    result = FileUtils.read_json_safe("/nonexistent/file.json", {"default": True})
    assert result == {"default": True}, "Safe read didn't return default"

    print("✅ FileUtils passed")


def test_process_utils():
    """Test ProcessUtils"""
    print("Testing ProcessUtils...")
    from utils import ProcessUtils

    # Test command execution
    result = ProcessUtils.run_command(["echo", "test"])
    assert result.success, "Echo command failed"
    assert "test" in result.stdout, "Output doesn't contain expected text"

    # Test binary check
    has_python = ProcessUtils.check_binary_exists("python3")
    assert has_python, "Python3 should be available"

    # Test safe execution
    result = ProcessUtils.run_command_safe(["nonexistent_command"])
    assert not result.success, "Should fail for nonexistent command"

    print("✅ ProcessUtils passed")


def test_path_utils():
    """Test PathUtils"""
    print("Testing PathUtils...")
    from utils import PathUtils

    # Test file finding
    py_files = PathUtils.find_files("src", "*.py", recursive=True)
    assert len(py_files) > 0, "Should find Python files"

    # Test FQCN extraction
    message = "Class <com.example.MyClass> violates rule"
    fqcn = PathUtils.extract_fqcn_from_message(message)
    assert fqcn == "com.example.MyClass", f"FQCN extraction failed: {fqcn}"

    # Test relative path
    rel = PathUtils.get_relative_path("src/utils/file_utils.py", "src")
    assert "utils/file_utils.py" in rel, f"Relative path wrong: {rel}"

    print("✅ PathUtils passed")


def test_violation_utils():
    """Test ViolationUtils"""
    print("Testing ViolationUtils...")
    from utils import ViolationUtils

    # Test normalization
    spectral_violation = {
        "code": "test-rule",
        "message": "Test message",
        "severity": 1,
        "path": ["paths", "/users"],
        "range": {"start": {"line": 10}},
        "source": "test.yaml",
    }

    normalized = ViolationUtils.normalize_spectral_violation(spectral_violation)
    assert normalized["rule"] == "test-rule", "Rule normalization failed"
    assert normalized["engine"] == "spectral", "Engine tag missing"

    # Test grouping
    violations = [
        {"rule": "rule1", "severity": 0},
        {"rule": "rule2", "severity": 1},
        {"rule": "rule1", "severity": 0},
    ]

    by_severity = ViolationUtils.group_by_severity(violations)
    assert len(by_severity[0]) == 2, "Severity grouping failed"

    by_rule = ViolationUtils.group_by_rule(violations)
    assert len(by_rule["rule1"]) == 2, "Rule grouping failed"

    # Test counting
    counts = ViolationUtils.count_by_severity(violations)
    assert counts["error"] == 2, "Error count wrong"
    assert counts["warning"] == 1, "Warning count wrong"

    print("✅ ViolationUtils passed")


def test_report_utils():
    """Test ReportUtils"""
    print("Testing ReportUtils...")
    from utils import ReportUtils

    # Test severity formatting
    icon = ReportUtils.format_severity_icon(0)
    assert icon == "🔴", f"Wrong icon: {icon}"

    label = ReportUtils.format_severity_label(1)
    assert label == "Warning", f"Wrong label: {label}"

    # Test violation formatting
    violation = {
        "rule": "test-rule",
        "message": "Test message",
        "severity": 0,
        "file": "test.yaml",
        "line": 10,
    }

    formatted = ReportUtils.format_violation_markdown(violation)
    assert "test-rule" in formatted, "Rule not in formatted output"
    assert "Test message" in formatted, "Message not in formatted output"

    print("✅ ReportUtils passed")


def test_project_utils():
    """Test ProjectUtils"""
    print("Testing ProjectUtils...")
    from utils import ProjectUtils

    # Test current project detection
    project_type = ProjectUtils.detect_project_type(".")
    assert project_type == "python", f"Wrong project type: {project_type}"

    # Test build directory detection
    build_dirs = ProjectUtils.get_build_directories(".")
    assert "__pycache__" in build_dirs, "Missing Python build dir"

    # Test exclusion
    should_exclude = ProjectUtils.should_exclude_path("src/__pycache__/test.pyc", ".")
    assert should_exclude, "Should exclude pycache files"

    should_include = ProjectUtils.should_exclude_path("src/utils/test.py", ".")
    assert not should_include, "Should not exclude source files"

    print("✅ ProjectUtils passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Utility Refactoring")
    print("=" * 60)
    print()

    try:
        test_file_utils()
        test_process_utils()
        test_path_utils()
        test_violation_utils()
        test_report_utils()
        test_project_utils()

        print()
        print("=" * 60)
        print("✅ All utility tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ Test failed: {e}")
        print("=" * 60)
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
