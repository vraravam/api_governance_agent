"""
Output normalizer for MCP server

Normalizes violation data from different engines (Spectral, ArchUnit, LLM)
into consistent JSON format for MCP tool responses.
"""

from typing import List, Dict
from .tool_schemas import Violation, SeveritySummary


class OutputNormalizer:
    """Normalizes governance engine outputs to MCP-compatible JSON"""

    @staticmethod
    def normalize_severity(severity_code: int) -> str:
        """
        Convert numeric severity to string format

        Args:
            severity_code: 0=critical, 1=warning, 2=info

        Returns:
            Severity string: "critical", "warning", or "info"
        """
        severity_map = {0: "critical", 1: "warning", 2: "info"}
        return severity_map.get(severity_code, "warning")

    @staticmethod
    def normalize_violation(raw_violation: Dict) -> Violation:
        """
        Normalize a single violation from any engine to standard format

        Args:
            raw_violation: Raw violation dict from Spectral/ArchUnit/LLM

        Returns:
            Normalized Violation object
        """
        # Extract common fields
        rule_id = raw_violation.get("rule", raw_violation.get("code", "unknown-rule"))
        description = raw_violation.get("message", "No description available")
        severity_code = raw_violation.get("severity")
        if severity_code is None:
            severity_code = 1  # Default to warning if missing
        else:
            try:
                severity_code = int(severity_code)
            except (ValueError, TypeError):
                severity_code = 1
        severity = OutputNormalizer.normalize_severity(severity_code)

        # Extract file path
        # Prioritize 'source' (Spectral) or 'file' (Standard). 'path' is often the JSON path (list).
        file_path = raw_violation.get("source") or raw_violation.get("file")

        if not file_path:
            candidate = raw_violation.get("path")
            if isinstance(candidate, str):
                file_path = candidate
            else:
                file_path = "unknown"

        # Extract line number
        line = raw_violation.get("line")
        if line is not None:
            try:
                line = int(line)
            except (ValueError, TypeError):
                line = None

        # Generate fix hint
        fix_hint = OutputNormalizer._generate_fix_hint(raw_violation)

        return Violation(
            rule_id=str(rule_id),
            description=str(description),
            severity=severity,
            file=str(file_path),
            line=line,
            fix_hint=fix_hint,
        )

    @staticmethod
    def _generate_fix_hint(raw_violation: Dict) -> str:
        """
        Generate a fix hint from violation data

        Args:
            raw_violation: Raw violation dict

        Returns:
            Fix hint string
        """
        # Check for existing suggestions
        if "suggestion" in raw_violation:
            return str(raw_violation["suggestion"])

        if "llm_context" in raw_violation:
            return str(raw_violation["llm_context"])

        # Generate basic hint from rule
        rule = raw_violation.get("rule", "")
        if "verb-in-path" in rule:
            return "Replace verb with a reified resource name (e.g., 'activations' instead of 'activate')"
        elif "leaky-abstraction" in rule:
            return "Use domain-specific naming instead of implementation details"
        elif "description" in rule:
            return "Add a detailed description explaining the purpose and usage"
        elif "standard-stream" in rule:
            return "Use a proper logging framework instead of System.out/System.err"
        elif "package" in rule:
            return "Move class to the correct package according to architectural rules"

        return "Review the rule documentation and apply recommended fixes"

    @staticmethod
    def calculate_severity_summary(violations: List[Violation]) -> SeveritySummary:
        """
        Calculate severity summary from violations

        Args:
            violations: List of normalized violations

        Returns:
            SeveritySummary object
        """
        critical = sum(1 for v in violations if v.severity == "critical")
        warning = sum(1 for v in violations if v.severity == "warning")
        info = sum(1 for v in violations if v.severity == "info")

        return SeveritySummary(critical=critical, warning=warning, info=info)

    @staticmethod
    def extract_suggested_fixes(violations: List[Violation]) -> List[str]:
        """
        Extract unique suggested fixes from violations

        Args:
            violations: List of normalized violations

        Returns:
            List of unique fix suggestions
        """
        fixes = set()

        for violation in violations:
            # Add the fix hint
            if violation.fix_hint:
                fixes.add(violation.fix_hint)

        # Limit to top 10 most relevant
        return sorted(list(fixes))[:10]

    @staticmethod
    def extract_impacted_layers(violations: List[Violation]) -> List[str]:
        """
        Extract impacted architectural layers from violations

        Args:
            violations: List of normalized violations

        Returns:
            List of impacted layers
        """
        layers = set()

        for violation in violations:
            file_path = violation.file

            # Extract package/layer information
            if "controller" in file_path.lower():
                layers.add("controller")
            if "service" in file_path.lower():
                layers.add("service")
            if "repository" in file_path.lower():
                layers.add("repository")
            if "model" in file_path.lower() or "entity" in file_path.lower():
                layers.add("model")
            if "util" in file_path.lower():
                layers.add("utility")

        return sorted(list(layers))

    @staticmethod
    def generate_refactoring_guidance(violations: List[Violation]) -> List[str]:
        """
        Generate refactoring guidance based on violations

        Args:
            violations: List of normalized violations

        Returns:
            List of refactoring suggestions
        """
        guidance = []

        # Count violations by type
        rule_counts = {}
        for v in violations:
            rule_counts[v.rule_id] = rule_counts.get(v.rule_id, 0) + 1

        # Generate guidance for common issues
        if any("standard-stream" in rule for rule in rule_counts):
            guidance.append(
                "Replace System.out/System.err with a logging framework (e.g., SLF4J)"
            )

        if any("package" in rule for rule in rule_counts):
            guidance.append(
                "Reorganize classes to follow layered architecture (controller/service/repository)"
            )

        if any("circular" in rule for rule in rule_counts):
            guidance.append(
                "Break circular dependencies by introducing interfaces or refactoring"
            )

        if not guidance:
            guidance.append("Review violations and apply suggested fixes")

        return guidance

    @staticmethod
    def calculate_health_score(critical: int, warnings: int, info: int) -> int:
        """
        Calculate overall health score (0-100)

        Args:
            critical: Number of critical violations
            warnings: Number of warnings
            info: Number of info issues

        Returns:
            Health score (0-100, higher is better)
        """
        # Start at 100 and deduct points
        score = 100

        # Critical violations are most severe (-5 points each)
        score -= critical * 5

        # Warnings are moderate (-2 points each)
        score -= warnings * 2

        # Info issues are minor (-0.5 points each)
        score -= int(info * 0.5)

        # Ensure score is between 0 and 100
        return max(0, min(100, score))
