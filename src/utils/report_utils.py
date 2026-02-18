"""
Report formatting and generation utilities.
"""

from typing import List, Dict
from datetime import datetime


class ReportUtils:
    """Utility class for report formatting"""

    @staticmethod
    def format_severity_icon(severity: int) -> str:
        """
        Get icon for severity level.

        Args:
          severity: Severity level (0=error, 1=warning, 2=info)

        Returns:
          Emoji icon string
        """
        icons = {0: "🔴", 1: "🟡", 2: "🔵"}
        return icons.get(severity, "•")

    @staticmethod
    def format_severity_label(severity: int) -> str:
        """
        Get label for severity level.

        Args:
          severity: Severity level (0=error, 1=warning, 2=info)

        Returns:
          Human-readable label
        """
        labels = {0: "Error", 1: "Warning", 2: "Info"}
        return labels.get(severity, "Unknown")

    @staticmethod
    def format_timestamp(dt: datetime = None) -> str:
        """
        Format timestamp for reports.

        Args:
          dt: Datetime object (uses current time if None)

        Returns:
          Formatted timestamp string
        """
        if dt is None:
            dt = datetime.now()
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def create_summary_table(violations: List[Dict], include_files: bool = True) -> str:
        """
        Create a markdown summary table.

        Args:
          violations: List of violations
          include_files: Whether to include file count

        Returns:
          Markdown formatted table
        """
        from utils.violation_utils import ViolationUtils

        severity_counts = ViolationUtils.count_by_severity(violations)

        lines = [
            "| Metric | Count |",
            "|--------|-------|",
            f"| Total Violations | {len(violations)} |",
            f"| Errors | {severity_counts['error']} |",
            f"| Warnings | {severity_counts['warning']} |",
            f"| Info | {severity_counts['info']} |",
        ]

        if include_files:
            files = ViolationUtils.group_by_file(violations)
            lines.append(f"| Files Affected | {len(files)} |")

        return "\n".join(lines)

    @staticmethod
    def create_rule_summary(violations: List[Dict]) -> str:
        """
        Create summary of violations by rule.

        Args:
          violations: List of violations

        Returns:
          Markdown formatted summary
        """
        from utils.violation_utils import ViolationUtils

        by_rule = ViolationUtils.group_by_rule(violations)

        lines = [
            "### Violations by Rule",
            "",
            "| Rule | Count |",
            "|------|-------|",
        ]

        # Sort by count descending
        sorted_rules = sorted(by_rule.items(), key=lambda x: len(x[1]), reverse=True)

        for rule, rule_violations in sorted_rules:
            lines.append(f"| `{rule}` | {len(rule_violations)} |")

        return "\n".join(lines)

    @staticmethod
    def format_violation_markdown(violation: Dict) -> str:
        """
        Format a single violation as markdown.

        Args:
          violation: Violation dictionary

        Returns:
          Markdown formatted violation
        """
        severity = violation.get("severity", 1)
        icon = ReportUtils.format_severity_icon(severity)
        label = ReportUtils.format_severity_label(severity)
        rule = violation.get("rule", "unknown")
        message = violation.get("message", "N/A")

        lines = [
            f"{icon} **{label}:** {rule}",
            f"  - Message: {message}",
        ]

        if violation.get("path"):
            lines.append(f"  - Path: `{violation['path']}`")

        if violation.get("file"):
            lines.append(f"  - File: `{violation['file']}`")

        if violation.get("line"):
            lines.append(f"  - Line: {violation['line']}")

        if violation.get("suggestion"):
            lines.append(f"  - Suggestion: {violation['suggestion']}")

        return "\n".join(lines)

    @staticmethod
    def create_diff_header(
        file_path: str, rule_id: str, additions: int, deletions: int
    ) -> str:
        """
        Create a formatted header for a diff.

        Args:
          file_path: Path to file
          rule_id: Rule ID
          additions: Number of added lines
          deletions: Number of deleted lines

        Returns:
          Formatted header string
        """
        lines = [
            "=" * 80,
            f"File: {file_path}",
            f"Rule: {rule_id}",
            f"Changes: +{additions} -{deletions}",
            "=" * 80,
        ]
        return "\n".join(lines)

    @staticmethod
    def create_summary_header(
        title: str, project_path: str = None, scan_type: str = None
    ) -> str:
        """
        Create a report summary header.

        Args:
          title: Report title
          project_path: Project path (optional)
          scan_type: Scan type (optional)

        Returns:
          Formatted header string
        """
        lines = [
            f"# {title}",
            "",
            f"**Generated:** {ReportUtils.format_timestamp()}",
            "",
        ]

        if project_path:
            lines.append(f"**Project:** `{project_path}`")

        if scan_type:
            lines.append(f"**Scan Type:** {scan_type}")

        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def wrap_section(title: str, content: str, level: int = 2) -> str:
        """
        Wrap content in a markdown section.

        Args:
          title: Section title
          content: Section content
          level: Heading level (1-6)

        Returns:
          Formatted section
        """
        heading = "#" * level
        return f"\n{heading} {title}\n\n{content}\n"
