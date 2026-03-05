"""
Utilities for normalizing and processing violation data.
"""

from typing import Dict, List


class ViolationUtils:
    """Utility class for violation data operations"""

    @staticmethod
    def normalize_spectral_violation(violation: Dict) -> Dict:
        """
        Normalize a Spectral violation to standard format.

        Args:
          violation: Raw Spectral violation

        Returns:
          Normalized violation dictionary
        """
        return {
            "rule": violation.get("code", "unknown"),
            "severity": violation.get("severity", 1),
            "message": violation.get("message", ""),
            "path": ".".join(str(p) for p in violation.get("path", [])),
            "line": violation.get("range", {}).get("start", {}).get("line", 0),
            "source": violation.get("source", ""),
            "engine": "spectral",
            "type": "api",
        }

    @staticmethod
    def normalize_archunit_violation(violation: Dict) -> Dict:
        """
        Normalize an ArchUnit violation to standard format.

        Args:
          violation: Raw ArchUnit violation

        Returns:
          Normalized violation dictionary
        """
        normalized = {
            "rule": violation.get("rule", "unknown-rule"),
            "message": violation.get(
                "violation", violation.get("message", violation.get("description", ""))
            ),
            "file": violation.get("file", "unknown"),
            "class": violation.get("class", ""),
            "severity": violation.get("severity", "ERROR"),
            "description": violation.get("description", ""),
            "type": "architecture",
            "engine": "archunit",
        }

        # Only include line number if it's meaningful
        if (
            "line" in violation
            and violation["line"] is not None
            and violation["line"] != 0
        ):
            normalized["line"] = violation["line"]

        return normalized

    @staticmethod
    def group_by_severity(violations: List[Dict]) -> Dict[int, List[Dict]]:
        """
        Group violations by severity level.

        Args:
          violations: List of violations

        Returns:
          Dictionary mapping severity to violations
        """
        groups = {0: [], 1: [], 2: []}  # error, warning, info

        for v in violations:
            severity = v.get("severity", 1)
            if severity in groups:
                groups[severity].append(v)

        return groups

    @staticmethod
    def group_by_rule(violations: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group violations by rule ID.

        Args:
          violations: List of violations

        Returns:
          Dictionary mapping rule ID to violations
        """
        groups = {}

        for v in violations:
            rule = v.get("rule", "unknown")
            if rule not in groups:
                groups[rule] = []
            groups[rule].append(v)

        return groups

    @staticmethod
    def group_by_file(violations: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group violations by file path.

        Args:
          violations: List of violations

        Returns:
          Dictionary mapping file path to violations
        """
        groups = {}

        for v in violations:
            file_path = v.get("file", v.get("source", "unknown"))
            if file_path not in groups:
                groups[file_path] = []
            groups[file_path].append(v)

        return groups

    @staticmethod
    def count_by_severity(violations: List[Dict]) -> Dict[str, int]:
        """
        Count violations by severity.

        Args:
          violations: List of violations

        Returns:
          Dictionary with counts for each severity level
        """
        counts = {"error": 0, "warning": 0, "info": 0}
        numeric_severity_map = {0: "error", 1: "warning", 2: "info"}
        string_severity_map = {"error": "error", "warning": "warning", "info": "info"}

        for v in violations:
            severity = v.get("severity", 1)
            if isinstance(severity, str):
                severity_name = string_severity_map.get(severity.lower(), "warning")
            else:
                severity_name = numeric_severity_map.get(severity, "warning")
            counts[severity_name] += 1

        return counts

    @staticmethod
    def filter_by_severity(violations: List[Dict], min_severity: int) -> List[Dict]:
        """
        Filter violations by minimum severity.

        Args:
          violations: List of violations
          min_severity: Minimum severity (0=error, 1=warning, 2=info)

        Returns:
          Filtered list of violations
        """
        return [v for v in violations if v.get("severity", 1) <= min_severity]

    @staticmethod
    def filter_by_rules(violations: List[Dict], rules: List[str]) -> List[Dict]:
        """
        Filter violations by rule IDs.

        Args:
          violations: List of violations
          rules: List of rule IDs to include

        Returns:
          Filtered list of violations
        """
        rule_set = set(rules)
        return [v for v in violations if v.get("rule") in rule_set]

    @staticmethod
    def merge_violations(*violation_lists: List[Dict]) -> List[Dict]:
        """
        Merge multiple violation lists.

        Args:
          *violation_lists: Variable number of violation lists

        Returns:
          Merged list of all violations
        """
        merged = []
        for vlist in violation_lists:
            if vlist:
                merged.extend(vlist)
        return merged

    @staticmethod
    def deduplicate_violations(violations: List[Dict]) -> List[Dict]:
        """
        Remove duplicate violations based on rule, file, and line.

        Args:
          violations: List of violations

        Returns:
          Deduplicated list of violations
        """
        seen = set()
        unique = []

        for v in violations:
            key = (
                v.get("rule", ""),
                v.get("file", v.get("source", "")),
                v.get("line", 0),
                v.get("message", ""),
            )
            if key not in seen:
                seen.add(key)
                unique.append(v)

        return unique

    @staticmethod
    def sort_violations(violations: List[Dict], by: str = "severity") -> List[Dict]:
        """
        Sort violations by specified key.

        Args:
          violations: List of violations
          by: Sort key ("severity", "file", "rule", "line")

        Returns:
          Sorted list of violations
        """
        if by == "severity":
            return sorted(violations, key=lambda v: v.get("severity", 1))
        elif by == "file":
            return sorted(violations, key=lambda v: v.get("file", v.get("source", "")))
        elif by == "rule":
            return sorted(violations, key=lambda v: v.get("rule", ""))
        elif by == "line":
            return sorted(violations, key=lambda v: v.get("line", 0))
        else:
            return violations

    @staticmethod
    def prioritize_violations(violations: List[Dict]) -> List[Dict]:
        """
        Sort violations by priority: Code files first, then specs.

        Args:
          violations: List of violations

        Returns:
          Prioritized list of violations
        """

        def priority_key(v):
            file_path = v.get("file", v.get("source", ""))
            if file_path.endswith(".java"):
                return 0
            elif file_path.endswith((".yaml", ".yml", ".json")):
                return 1
            else:
                return 2

        return sorted(violations, key=priority_key)
