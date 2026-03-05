"""
Unit tests for MCP server tools

Tests each MCP tool with mock inputs and validates output schemas.
"""

import pytest
from pathlib import Path

# Add src directory to sys.path for imports
import sys

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from mcp_server.tool_schemas import (
    ValidateOpenAPIInput,
    Violation,
    SeveritySummary,
)
from mcp_server.output_normalizer import OutputNormalizer


class TestToolSchemas:
    """Test Pydantic schemas for validation"""

    def test_validate_openapi_input(self):
        """Test ValidateOpenAPIInput schema"""
        input_data = ValidateOpenAPIInput(
            spec_path="/path/to/spec.yaml", ruleset="/path/to/ruleset.yaml"
        )
        assert input_data.spec_path == "/path/to/spec.yaml"
        assert input_data.ruleset == "/path/to/ruleset.yaml"

    def test_validate_openapi_input_optional_ruleset(self):
        """Test ValidateOpenAPIInput with optional ruleset"""
        input_data = ValidateOpenAPIInput(spec_path="/path/to/spec.yaml")
        assert input_data.spec_path == "/path/to/spec.yaml"
        assert input_data.ruleset is None

    def test_violation_schema(self):
        """Test Violation schema"""
        violation = Violation(
            rule_id="test-rule",
            description="Test violation",
            severity="warning",
            file="test.yaml",
            line=10,
            fix_hint="Fix this",
        )
        assert violation.rule_id == "test-rule"
        assert violation.severity == "warning"
        assert violation.line == 10

    def test_severity_summary(self):
        """Test SeveritySummary schema"""
        summary = SeveritySummary(critical=1, warning=2, info=3)
        assert summary.critical == 1
        assert summary.warning == 2
        assert summary.info == 3


class TestOutputNormalizer:
    """Test output normalization logic"""

    def test_normalize_severity(self):
        """Test severity code normalization"""
        assert OutputNormalizer.normalize_severity(0) == "critical"
        assert OutputNormalizer.normalize_severity(1) == "warning"
        assert OutputNormalizer.normalize_severity(2) == "info"
        assert OutputNormalizer.normalize_severity(99) == "warning"  # default

    def test_normalize_violation_spectral(self):
        """Test normalizing Spectral violation"""
        raw = {
            "rule": "oas3-schema",
            "message": "Schema is invalid",
            "severity": 0,
            "path": ["paths", "/users", "get"],
            "line": 15,
        }

        violation = OutputNormalizer.normalize_violation(raw)
        assert violation.rule_id == "oas3-schema"
        assert violation.description == "Schema is invalid"
        assert violation.severity == "critical"
        assert violation.line == 15

    def test_normalize_violation_archunit(self):
        """Test normalizing ArchUnit violation"""
        raw = {
            "rule": "no-standard-streams",
            "message": "Class uses System.out",
            "severity": 1,
            "source": "com.example.MyClass",
            "suggestion": "Use logging framework",
        }

        violation = OutputNormalizer.normalize_violation(raw)
        assert violation.rule_id == "no-standard-streams"
        assert violation.severity == "warning"
        assert violation.fix_hint == "Use logging framework"

    def test_calculate_severity_summary(self):
        """Test severity summary calculation"""
        violations = [
            Violation(
                rule_id="r1",
                description="d1",
                severity="critical",
                file="f1",
                fix_hint="h1",
            ),
            Violation(
                rule_id="r2",
                description="d2",
                severity="warning",
                file="f2",
                fix_hint="h2",
            ),
            Violation(
                rule_id="r3",
                description="d3",
                severity="warning",
                file="f3",
                fix_hint="h3",
            ),
            Violation(
                rule_id="r4",
                description="d4",
                severity="info",
                file="f4",
                fix_hint="h4",
            ),
        ]

        summary = OutputNormalizer.calculate_severity_summary(violations)
        assert summary.critical == 1
        assert summary.warning == 2
        assert summary.info == 1

    def test_calculate_health_score(self):
        """Test health score calculation"""
        # Perfect score
        assert OutputNormalizer.calculate_health_score(0, 0, 0) == 100

        # With violations
        # Formula: 100 - (critical*5) - (warnings*2) - (info*0.5)
        score = OutputNormalizer.calculate_health_score(1, 2, 3)
        expected = 100 - (1 * 5) - (2 * 2) - int(3 * 0.5)
        assert score == expected
        assert score == 90  # 100 - 5 - 4 - 1 = 90

        # Clamped to 0
        score = OutputNormalizer.calculate_health_score(10, 10, 10)
        assert score >= 0

    def test_extract_impacted_layers(self):
        """Test extracting impacted layers"""
        violations = [
            Violation(
                rule_id="r1",
                description="d1",
                severity="warning",
                file="com.example.controller.UserController",
                fix_hint="h1",
            ),
            Violation(
                rule_id="r2",
                description="d2",
                severity="warning",
                file="com.example.service.UserService",
                fix_hint="h2",
            ),
        ]

        layers = OutputNormalizer.extract_impacted_layers(violations)
        assert "controller" in layers
        assert "service" in layers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
