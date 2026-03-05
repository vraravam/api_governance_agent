"""
Category Manager - Organizes violations into manageable categories for incremental fixing

This module helps users tackle fixes category-by-category instead of all 43+ fixes at once.
"""

from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict
import json
from pathlib import Path


@dataclass
class ViolationCategory:
    """Represents a category of violations"""

    name: str
    display_name: str
    description: str
    rules: Set[str]
    priority: int  # Lower = higher priority
    estimated_effort: str  # "Low", "Medium", "High"


class CategoryManager:
    """
    Organizes violations into logical categories for incremental fixing.

    Categories are designed to:
    1. Group related governance rules together
    2. Allow fixing by priority (high-impact first)
    3. Stay within LLM token limits
    4. Provide clear progress tracking
    """

    # Define violation categories
    CATEGORIES = {
        "RESOURCE_NAMING": ViolationCategory(
            name="RESOURCE_NAMING",
            display_name="Resource Naming",
            description="Plural resources, kebab-case paths, no verbs in URLs",
            rules={
                "plural-resources",
                "kebab-case-paths",
                "no-verbs-in-url",
                "pluralResourceNaming",
                "noVerbsInMapping",
                "requestMappingsKebabCase",
            },
            priority=1,
            estimated_effort="Low",
        ),
        "DATA_TYPES": ViolationCategory(
            name="DATA_TYPES",
            display_name="Data Types & Formats",
            description="UUID IDs, camelCase fields, ISO8601 dates, ISO4217 currency",
            rules={
                "uuid-resource-ids",
                "request-fields-camelcase",
                "response-fields-camelcase",
                "datetime-iso8601",
                "currency-code-iso4217",
                "pathVariablesShouldBeUUID",
                "requestParamsCamelCase",
            },
            priority=5,  # MEDIUM
            estimated_effort="Medium",
        ),
        "HTTP_SEMANTICS": ViolationCategory(
            name="HTTP_SEMANTICS",
            display_name="HTTP Semantics",
            description="Correct status codes, HTTP methods, headers",
            rules={
                "post-create-returns-201",
                "put-returns-200-or-204",
                "delete-returns-204-or-200",
                "get-no-request-body",
                "delete-no-request-body",
                "postMethodsShouldReturn201",
                "getMethodsNoRequestBody",
            },
            priority=6,  # MEDIUM
            estimated_effort="Low",
        ),
        "PAGINATION": ViolationCategory(
            name="PAGINATION",
            display_name="Pagination",
            description="Page-based pagination with proper response structure",
            rules={
                "pagination-parameter-naming",
                "pagination-response-structure",
                "paginatedEndpointsUsePageable",
                "pagination-response-check",
            },
            priority=7,  # MEDIUM
            estimated_effort="Medium",
        ),
        "RESPONSE_STRUCTURE": ViolationCategory(
            name="RESPONSE_STRUCTURE",
            display_name="Response Structure",
            description="Response envelopes, array field naming, nested depth",
            rules={
                "response-envelope",
                "array-fields-plural",
                "nested-resources-depth",
                "controllerMethodsReturnProperTypes",
            },
            priority=8,  # MEDIUM
            estimated_effort="Medium",
        ),
        "DOCUMENTATION": ViolationCategory(
            name="DOCUMENTATION",
            display_name="Documentation",
            description="Required descriptions for operations, schemas, parameters",
            rules={
                "operation-description-required",
                "schema-description-required",
                "parameter-description-required",
                "tag-description-required",
            },
            priority=9,  # LOW
            estimated_effort="Low",
        ),
        "ARCHITECTURE": ViolationCategory(
            name="ARCHITECTURE",
            display_name="Architecture & Layering",
            description="Critical: Layered architecture, dependency rules, package structure",
            rules={
                # Actual ArchUnit rule names from violations:
                "architecture-layered",  # Layered architecture violations
                "architecture-persistence-no-web",  # Persistence layer shouldn't depend on web
                "dependency-controller-no-repository",  # Controllers accessing repositories directly
                "dependency-domain-independence",  # Domain layer independence
                "dependency-no-upper-packages",  # No dependencies on upper packages
                "naming-service-package",  # Service package naming conventions
                # Legacy rule names (may still be used):
                "arch-layered-architecture",
                "arch-no-cycles",
                "arch-naming-convention",
                "controllersInCorrectPackage",
                "controllerNamingConvention",
                "classLevelRequestMapping",
                "repositoryAccessThroughService",
                "domainLayerIndependence",
            },
            priority=2,  # CRITICAL - moved up from 7
            estimated_effort="High",
        ),
        "CODE_QUALITY": ViolationCategory(
            name="CODE_QUALITY",
            display_name="Code Quality & Best Practices",
            description="Important: Logging, exception handling, injection patterns",
            rules={
                # Actual ArchUnit rule names from violations:
                "coding-no-std-streams",  # No System.out/System.err
                "coding-no-generic-exceptions",  # No generic exception handling
                "coding-no-field-injection",  # No field injection (use constructor)
                "coding-no-java-util-logging",  # No java.util.logging (use SLF4J)
                # Legacy rule names (may still be used):
                "no-sysout",
                "no-generic-exceptions",
                "proper-logging",
                "no-empty-catch",
                "no-java-util-logging",
                "constructor-injection-over-field",
            },
            priority=3,  # HIGH - moved up from 9
            estimated_effort="Medium",
        ),
        "SECURITY": ViolationCategory(
            name="SECURITY",
            display_name="Security",
            description="Critical: Authentication, authorization, sensitive data",
            rules={
                "no-api-keys-in-url",
                "require-authentication",
                "security-definitions-required",
                "no-hardcoded-credentials",
            },
            priority=4,  # CRITICAL - moved up from 8
            estimated_effort="High",
        ),
        "OTHER": ViolationCategory(
            name="OTHER",
            display_name="Other",
            description="Miscellaneous violations not fitting other categories",
            rules=set(),  # Catch-all
            priority=10,
            estimated_effort="Varies",
        ),
    }

    def __init__(self):
        """Initialize category manager"""
        self.categories = self.CATEGORIES.copy()

    def categorize_violation(self, violation: Dict) -> str:
        """
        Categorize a single violation.

        Args:
            violation: Single violation dictionary

        Returns:
            Category name (e.g., 'RESOURCE_NAMING', 'ARCHITECTURE', etc.)
        """
        rule_id = violation.get("rule") or violation.get("rule_id", "unknown")

        # Find matching category
        for category in self.categories.values():
            if rule_id in category.rules:
                return category.name

        # If no category found, return OTHER
        return "OTHER"

    def categorize_violations(self, violations: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Organize violations into categories.

        Args:
            violations: List of violation dictionaries

        Returns:
            Dict mapping category name to list of violations
        """
        categorized = defaultdict(list)

        for violation in violations:
            # Use the singular method for consistency
            category_name = self.categorize_violation(violation)
            categorized[category_name].append(violation)

        return dict(categorized)

    def generate_category_summary(self, violations: List[Dict]) -> Dict[str, Dict]:
        """
        Generate summary statistics for each category.

        Returns:
            Dict with category stats: {
                'RESOURCE_NAMING': {
                    'count': 15,
                    'priority': 1,
                    'effort': 'Low',
                    'display_name': 'Resource Naming',
                    'description': '...',
                    'violations': [...]
                },
                ...
            }
        """
        categorized = self.categorize_violations(violations)
        summary = {}

        for category_name, category_violations in categorized.items():
            category_def = self.categories.get(category_name, self.categories["OTHER"])

            summary[category_name] = {
                "count": len(category_violations),
                "priority": category_def.priority,
                "effort": category_def.estimated_effort,
                "display_name": category_def.display_name,
                "description": category_def.description,
                "violations": category_violations,
            }

        # Sort by priority
        return dict(sorted(summary.items(), key=lambda x: x[1]["priority"]))

    def get_category_violations(
        self, violations: List[Dict], category_name: str
    ) -> List[Dict]:
        """
        Get violations for a specific category.

        Args:
            violations: All violations
            category_name: Category to filter by

        Returns:
            List of violations in that category
        """
        categorized = self.categorize_violations(violations)
        return categorized.get(category_name, [])

    def generate_progress_report(
        self, all_violations: List[Dict], fixed_violations: List[Dict]
    ) -> Dict:
        """
        Generate progress report showing fixes per category.

        Args:
            all_violations: All violations found
            fixed_violations: Violations that have been fixed

        Returns:
            Progress report by category
        """
        all_summary = self.generate_category_summary(all_violations)
        fixed_summary = self.generate_category_summary(fixed_violations)

        progress = {}
        for category_name, category_data in all_summary.items():
            total = category_data["count"]
            fixed = fixed_summary.get(category_name, {}).get("count", 0)
            remaining = total - fixed

            progress[category_name] = {
                "display_name": category_data["display_name"],
                "total": total,
                "fixed": fixed,
                "remaining": remaining,
                "percentage": round((fixed / total * 100) if total > 0 else 0, 1),
                "priority": category_data["priority"],
                "effort": category_data["effort"],
            }

        return progress

    def get_next_category_to_fix(
        self, all_violations: List[Dict], fixed_violations: List[Dict]
    ) -> Tuple[str, List[Dict]]:
        """
        Recommend the next category to fix based on priority and remaining count.

        Returns:
            Tuple of (category_name, violations_to_fix)
        """
        progress = self.generate_progress_report(all_violations, fixed_violations)

        # Find first category with remaining violations (by priority)
        for category_name, stats in sorted(
            progress.items(), key=lambda x: x[1]["priority"]
        ):
            if stats["remaining"] > 0:
                violations = self.get_category_violations(all_violations, category_name)
                # Filter out already fixed
                fixed_rule_ids = {
                    v.get("rule") or v.get("rule_id") for v in fixed_violations
                }
                remaining_violations = [
                    v
                    for v in violations
                    if (v.get("rule") or v.get("rule_id")) not in fixed_rule_ids
                ]
                return category_name, remaining_violations

        return None, []

    def export_category_report(self, violations: List[Dict], output_path: str):
        """
        Export categorized violations to JSON file.

        Args:
            violations: List of violations
            output_path: Path to save report
        """
        summary = self.generate_category_summary(violations)

        report = {
            "total_violations": len(violations),
            "total_categories": len([c for c in summary.values() if c["count"] > 0]),
            "categories": summary,
            "recommended_order": [
                {
                    "category": cat_name,
                    "display_name": cat_data["display_name"],
                    "count": cat_data["count"],
                    "effort": cat_data["effort"],
                    "priority": cat_data["priority"],
                }
                for cat_name, cat_data in summary.items()
                if cat_data["count"] > 0
            ],
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

    def print_category_summary(self, violations: List[Dict]):
        """
        Print a human-readable category summary to console.

        Args:
            violations: List of violations
        """
        summary = self.generate_category_summary(violations)

        print("\n" + "=" * 80)
        print(" 📊 VIOLATIONS BY CATEGORY")
        print("=" * 80)
        print(f"\n Total Violations: {len(violations)}")
        print(
            f" Active Categories: {len([c for c in summary.values() if c['count'] > 0])}"
        )
        print()

        for category_name, category_data in summary.items():
            if category_data["count"] == 0:
                continue

            priority_emoji = (
                "🔴"
                if category_data["priority"] <= 3
                else "🟡" if category_data["priority"] <= 6 else "🟢"
            )
            effort_emoji = (
                "⚡"
                if category_data["effort"] == "Low"
                else "⚙️" if category_data["effort"] == "Medium" else "🔧"
            )

            print(f"{priority_emoji} {category_data['display_name']}")
            print(
                f"   Priority: {category_data['priority']} | Effort: {effort_emoji} {category_data['effort']} | Count: {category_data['count']}"
            )
            print(f"   {category_data['description']}")
            print()

        print("=" * 80)
        print(" 💡 Recommended Workflow:")
        print("=" * 80)
        print(" 1. Start with highest priority categories (🔴)")
        print(" 2. Fix category-by-category for better focus")
        print(" 3. Review changes after each category")
        print(" 4. Commit fixes incrementally")
        print()


def main():
    """Example usage"""
    # Mock violations for testing
    violations = [
        {"rule": "plural-resources", "message": "Use plural", "file": "api.yaml"},
        {"rule": "uuid-resource-ids", "message": "Use UUID", "file": "api.yaml"},
        {
            "rule": "post-create-returns-201",
            "message": "POST should return 201",
            "file": "api.yaml",
        },
        {"rule": "no-sysout", "message": "No System.out", "file": "Controller.java"},
    ]

    manager = CategoryManager()
    manager.print_category_summary(violations)

    # Get next category to fix
    next_category, next_violations = manager.get_next_category_to_fix(violations, [])
    print(f"\n🎯 Next Category to Fix: {next_category}")
    print(f"   Violations: {len(next_violations)}")


if __name__ == "__main__":
    main()
