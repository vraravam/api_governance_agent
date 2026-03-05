"""
Spec-Controller Synchronization Validator

This module coordinates between Spectral (OpenAPI) and ArchUnit (Java Controllers)
to detect drift and ensure both layers follow the same governance rules.
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class SpecControllerSyncValidator:
    """
    Validates synchronization between OpenAPI specs and Java controllers.

    Compares Spectral violations (OpenAPI) with ArchUnit violations (Controllers)
    to detect drift patterns and coordinate fixes.
    """

    # Map ArchUnit rule names to Spectral rule names
    RULE_MAPPING = {
        "pluralResourceNaming": "plural-resources",
        "noVerbsInMapping": "no-verbs-in-url",
        "pathVariablesShouldBeUUID": "uuid-resource-ids",
        "postMethodsShouldReturn201": "post-create-returns-201",
        "paginatedEndpointsUsePageable": "pagination-parameter-naming",
        "getMethodsNoRequestBody": "get-no-request-body",
        "requestMappingsKebabCase": "kebab-case-paths",
        "requestParamsCamelCase": "request-fields-camelcase",
        "controllerMethodsReturnProperTypes": "response-envelope",
        "noTrailingSlashes": "no-trailing-slash",
        "classLevelRequestMapping": None,  # Controller-only rule
        "controllerNamingConvention": None,  # Controller-only rule
        "controllersInCorrectPackage": None,  # Controller-only rule
    }

    # Reverse mapping
    SPECTRAL_TO_ARCHUNIT = {v: k for k, v in RULE_MAPPING.items() if v is not None}

    def __init__(
        self,
        spectral_results: List[Dict],
        archunit_results: Optional[List[Dict]] = None,
    ):
        """
        Initialize validator with results from both tools.

        Args:
            spectral_results: List of Spectral violations
            archunit_results: List of ArchUnit violations (optional)
        """
        self.spectral_results = spectral_results
        self.archunit_results = archunit_results or []

    def validate_sync(self) -> Dict:
        """
        Validate synchronization between spec and controllers.

        Returns:
            Dict with sync analysis:
            {
                'in_sync': [...],          # No drift
                'spec_only': [...],        # OpenAPI wrong, controller OK
                'controller_only': [...],  # Controller wrong, OpenAPI OK
                'both_wrong': [...],       # Both have violations
                'conflicts': [...],        # Violations contradict
                'summary': {...}
            }
        """
        logger.info("🔍 Validating spec-controller synchronization...")

        sync_report = {
            "in_sync": [],
            "spec_only": [],
            "controller_only": [],
            "both_wrong": [],
            "conflicts": [],
            "summary": {},
        }

        # Group violations by file
        spec_by_file = self._group_spectral_by_file()
        controller_by_file = self._group_archunit_by_file()

        # Find all OpenAPI files that have violations
        for spec_file, spec_violations in spec_by_file.items():
            # Find related controllers
            related_controllers = self._find_related_controllers(spec_file)

            if not related_controllers:
                logger.warning(f"No controllers found for {spec_file}")
                sync_report["spec_only"].append(
                    {
                        "spec_file": spec_file,
                        "controllers": [],
                        "violations": spec_violations,
                        "reason": "No related controllers found",
                    }
                )
                continue

            for controller in related_controllers:
                controller_violations = controller_by_file.get(controller, [])

                # Analyze sync status
                sync_status = self._analyze_sync_status(
                    spec_violations, controller_violations, spec_file, controller
                )

                sync_report[sync_status["category"]].append(sync_status["data"])

        # Check for controller-only violations (no matching spec violations)
        for controller, controller_violations in controller_by_file.items():
            # Only process if not already handled
            if not any(
                controller in item.get("controller", "")
                for category in ["in_sync", "spec_only", "both_wrong", "conflicts"]
                for item in sync_report[category]
            ):

                # Find related spec file
                related_spec = self._find_spec_for_controller(controller)

                sync_report["controller_only"].append(
                    {
                        "spec_file": related_spec,
                        "controller": controller,
                        "violations": controller_violations,
                        "reason": "Controller has violations but spec is clean",
                    }
                )

        # Generate summary
        sync_report["summary"] = self._generate_summary(sync_report)

        logger.info(f"✅ Sync validation complete: {sync_report['summary']}")

        return sync_report

    def _analyze_sync_status(
        self,
        spec_violations: List[Dict],
        controller_violations: List[Dict],
        spec_file: str,
        controller: str,
    ) -> Dict:
        """
        Analyze sync status between spec and controller violations.

        Returns:
            {
                'category': 'in_sync'|'spec_only'|'controller_only'|'both_wrong'|'conflicts',
                'data': {...}
            }
        """
        # Case 1: Both have no violations
        if not spec_violations and not controller_violations:
            return {
                "category": "in_sync",
                "data": {
                    "spec_file": spec_file,
                    "controller": controller,
                    "status": "clean",
                },
            }

        # Case 2: Only spec has violations
        if spec_violations and not controller_violations:
            return {
                "category": "spec_only",
                "data": {
                    "spec_file": spec_file,
                    "controller": controller,
                    "violations": spec_violations,
                    "reason": "OpenAPI spec has violations but controller is clean",
                },
            }

        # Case 3: Only controller has violations
        if controller_violations and not spec_violations:
            return {
                "category": "controller_only",
                "data": {
                    "spec_file": spec_file,
                    "controller": controller,
                    "violations": controller_violations,
                    "reason": "Controller has violations but spec is clean",
                },
            }

        # Case 4: Both have violations - check if they're compatible
        compatible, reason = self._are_violations_compatible(
            spec_violations, controller_violations
        )

        if compatible:
            return {
                "category": "both_wrong",
                "data": {
                    "spec_file": spec_file,
                    "controller": controller,
                    "spec_violations": spec_violations,
                    "controller_violations": controller_violations,
                    "reason": reason,
                    "fix_strategy": "atomic_multi_file",
                },
            }
        else:
            return {
                "category": "conflicts",
                "data": {
                    "spec_file": spec_file,
                    "controller": controller,
                    "spec_violations": spec_violations,
                    "controller_violations": controller_violations,
                    "reason": reason,
                    "fix_strategy": "manual_review",
                },
            }

    def _are_violations_compatible(
        self, spec_violations: List[Dict], controller_violations: List[Dict]
    ) -> Tuple[bool, str]:
        """
        Check if violations are compatible (same issue in both layers).

        Returns:
            (compatible: bool, reason: str)
        """
        # Extract rule names
        spec_rules = {v.get("rule") or v.get("code") for v in spec_violations}

        # Map controller rules to Spectral equivalents
        controller_rules_mapped = set()
        for v in controller_violations:
            archunit_rule = v.get("rule") or v.get("code")
            spectral_rule = self.RULE_MAPPING.get(archunit_rule)
            if spectral_rule:
                controller_rules_mapped.add(spectral_rule)

        # Check for intersection
        common_rules = spec_rules.intersection(controller_rules_mapped)

        if common_rules:
            return (
                True,
                f"Both layers have violations for same rules: {', '.join(common_rules)}",
            )
        else:
            return (
                False,
                f"Violations are for different rules: Spec={spec_rules}, Controller={controller_rules_mapped}",
            )

    def _group_spectral_by_file(self) -> Dict[str, List[Dict]]:
        """Group Spectral violations by file path."""
        grouped = {}
        for violation in self.spectral_results:
            file_path = violation.get("file") or violation.get("source", "unknown")
            if file_path not in grouped:
                grouped[file_path] = []
            grouped[file_path].append(violation)
        return grouped

    def _group_archunit_by_file(self) -> Dict[str, List[Dict]]:
        """Group ArchUnit violations by file path."""
        grouped = {}
        for violation in self.archunit_results:
            file_path = violation.get("file") or violation.get("class", "unknown")
            if file_path not in grouped:
                grouped[file_path] = []
            grouped[file_path].append(violation)
        return grouped

    def _find_related_controllers(self, spec_file: str) -> List[str]:
        """
        Find Java controllers related to an OpenAPI spec file.

        Uses content-based detection (parsing OpenAPI paths and matching
        to @RequestMapping annotations).
        """
        # This would use the existing RelatedFileDetector
        # For now, return placeholder
        # TODO: Integrate with existing detection logic
        return []

    def _find_spec_for_controller(self, controller: str) -> Optional[str]:
        """Find OpenAPI spec file for a controller."""
        # TODO: Implement reverse lookup
        return None

    def _generate_summary(self, sync_report: Dict) -> Dict:
        """Generate summary statistics."""
        return {
            "total_spec_files": len(
                set(
                    item["spec_file"]
                    for category in [
                        "in_sync",
                        "spec_only",
                        "controller_only",
                        "both_wrong",
                        "conflicts",
                    ]
                    for item in sync_report[category]
                )
            ),
            "total_controllers": len(
                set(
                    item["controller"]
                    for category in [
                        "in_sync",
                        "spec_only",
                        "controller_only",
                        "both_wrong",
                        "conflicts",
                    ]
                    for item in sync_report[category]
                    if "controller" in item
                )
            ),
            "in_sync_count": len(sync_report["in_sync"]),
            "spec_only_count": len(sync_report["spec_only"]),
            "controller_only_count": len(sync_report["controller_only"]),
            "both_wrong_count": len(sync_report["both_wrong"]),
            "conflicts_count": len(sync_report["conflicts"]),
            "requires_fixes": len(sync_report["spec_only"])
            + len(sync_report["controller_only"])
            + len(sync_report["both_wrong"]),
            "requires_manual_review": len(sync_report["conflicts"]),
        }

    def generate_fix_recommendations(self, sync_report: Dict) -> List[Dict]:
        """
        Generate fix recommendations based on sync report.

        Returns:
            List of fix recommendations with strategies
        """
        recommendations = []

        # Case 1: Spec only - fix spec and update controller
        for item in sync_report["spec_only"]:
            recommendations.append(
                {
                    "priority": "high",
                    "strategy": "fix_spec_with_controller_update",
                    "spec_file": item["spec_file"],
                    "controller": item["controller"],
                    "violations": item["violations"],
                    "action": "Fix OpenAPI spec and generate corresponding controller updates",
                }
            )

        # Case 2: Controller only - fix controller to match spec
        for item in sync_report["controller_only"]:
            recommendations.append(
                {
                    "priority": "medium",
                    "strategy": "fix_controller_to_match_spec",
                    "spec_file": item["spec_file"],
                    "controller": item["controller"],
                    "violations": item["violations"],
                    "action": "Fix controller to match OpenAPI spec",
                }
            )

        # Case 3: Both wrong - atomic multi-file fix
        for item in sync_report["both_wrong"]:
            recommendations.append(
                {
                    "priority": "high",
                    "strategy": "atomic_multi_file_fix",
                    "spec_file": item["spec_file"],
                    "controller": item["controller"],
                    "spec_violations": item["spec_violations"],
                    "controller_violations": item["controller_violations"],
                    "action": "Generate atomic fix for both spec and controller",
                }
            )

        # Case 4: Conflicts - manual review
        for item in sync_report["conflicts"]:
            recommendations.append(
                {
                    "priority": "critical",
                    "strategy": "manual_review_required",
                    "spec_file": item["spec_file"],
                    "controller": item["controller"],
                    "spec_violations": item["spec_violations"],
                    "controller_violations": item["controller_violations"],
                    "reason": item["reason"],
                    "action": "Manual review required - violations contradict each other",
                }
            )

        return recommendations

    def export_sync_report(self, sync_report: Dict, output_path: str):
        """Export sync report to JSON file."""
        with open(output_path, "w") as f:
            json.dump(sync_report, f, indent=2)
        logger.info(f"📄 Sync report exported to {output_path}")


def main():
    """Example usage"""
    # Load Spectral results
    with open("governance-report.json", "r") as f:
        spectral_results = json.load(f).get("violations", [])

    # Load ArchUnit results (if available)
    archunit_results = []
    archunit_file = Path("archunit-violations.json")
    if archunit_file.exists():
        with open(archunit_file, "r") as f:
            archunit_results = json.load(f)

    # Validate sync
    validator = SpecControllerSyncValidator(spectral_results, archunit_results)
    sync_report = validator.validate_sync()

    # Export report
    validator.export_sync_report(sync_report, "sync-report.json")

    # Generate recommendations
    recommendations = validator.generate_fix_recommendations(sync_report)

    print("\n" + "=" * 80)
    print(" SPEC-CONTROLLER SYNC VALIDATION REPORT")
    print("=" * 80)
    print("\n📊 Summary:")
    print(f"   In Sync:          {sync_report['summary']['in_sync_count']}")
    print(f"   Spec Only:        {sync_report['summary']['spec_only_count']}")
    print(f"   Controller Only:  {sync_report['summary']['controller_only_count']}")
    print(f"   Both Wrong:       {sync_report['summary']['both_wrong_count']}")
    print(f"   Conflicts:        {sync_report['summary']['conflicts_count']}")
    print(f"\n🔧 Requires Fixes:  {sync_report['summary']['requires_fixes']}")
    print(f"⚠️  Manual Review:   {sync_report['summary']['requires_manual_review']}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
