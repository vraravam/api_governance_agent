#!/usr/bin/env python3
"""
Merge OpenAPI and ArchUnit violation reports into a comprehensive governance report.

This script combines:
- OpenAPI/Spectral violations (from API spec scans)
- Java ArchUnit violations (from architecture tests)

Into a single comprehensive governance-report.json file that can be used
by the copilot_fix command.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import FileUtils, ViolationUtils


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load JSON file, return empty dict if not found."""
    return FileUtils.read_json_safe(file_path, {})


def normalize_openapi_violations(openapi_data: Dict) -> List[Dict]:
    """
    Normalize OpenAPI violations to standard format.

    Expected input formats:
    - Spectral format: {"results": [...]}
    - Custom format: {"violations": [...]}
    """
    violations = []

    # Try Spectral format
    if "results" in openapi_data:
        for result in openapi_data.get("results", []):
            for issue in result.get("results", []):
                violations.append(
                    {
                        "rule": issue.get("code", "unknown-rule"),
                        "message": issue.get("message", ""),
                        "file": result.get("source", "unknown"),
                        "line": issue.get("range", {}).get("start", {}).get("line", 0),
                        "severity": issue.get("severity", 1),  # Spectral uses 0-3
                        "path": ".".join(str(p) for p in issue.get("path", [])),
                        "type": "api",
                    }
                )

    # Try custom violations format
    elif "violations" in openapi_data:
        for v in openapi_data["violations"]:
            violations.append(
                {
                    "rule": v.get("rule", v.get("code", "unknown-rule")),
                    "message": v.get("message", v.get("description", "")),
                    "file": v.get("file", v.get("source", "unknown")),
                    "line": v.get("line", 0),
                    "severity": v.get("severity", "error"),
                    "path": v.get("path", ""),
                    "type": "api",
                }
            )

    return violations


def normalize_archunit_violations(archunit_data: Dict) -> List[Dict]:
    """
    Normalize ArchUnit violations to standard format.

    Expected input format:
    {
      "violations": [
        {
          "rule": "...",
          "violation": "...",
          "file": "...",
          "class": "...",
          "severity": "ERROR|WARNING",
          "description": "..."
        }
      ]
    }
    """
    violations = []
    for v in archunit_data.get("violations", []):
        violations.append(ViolationUtils.normalize_archunit_violation(v))
    return violations


def merge_reports(
    openapi_file: str = None,
    archunit_file: str = None,
    output_file: str = "governance-report.json",
) -> Dict:
    """
    Merge OpenAPI and ArchUnit reports into comprehensive governance report.

    Args:
        openapi_file: Path to OpenAPI violations JSON
        archunit_file: Path to ArchUnit violations JSON
        output_file: Path for merged output

    Returns:
        Merged report dictionary
    """
    print("🔄 Merging governance reports...")

    # Load reports
    openapi_data = load_json_file(openapi_file) if openapi_file else {}
    archunit_data = load_json_file(archunit_file) if archunit_file else {}

    # Normalize violations
    api_violations = normalize_openapi_violations(openapi_data)
    arch_violations = normalize_archunit_violations(archunit_data)

    all_violations = ViolationUtils.merge_violations(api_violations, arch_violations)

    # Count by type and severity
    by_type = {"api": len(api_violations), "architecture": len(arch_violations)}
    severity_counts = ViolationUtils.count_by_severity(all_violations)

    # Create merged report
    merged_report = {
        "project_path": str(Path.cwd()),
        "scan_types": ["api", "architecture"] if arch_violations else ["api"],
        "violations": all_violations,
        "total_violations": len(all_violations),
        "summary": {
            "by_type": by_type,
            "by_severity": severity_counts,
            "api_violations": len(api_violations),
            "architecture_violations": len(arch_violations),
        },
    }

    # Save merged report
    FileUtils.write_json(output_file, merged_report)

    print(f"✅ Merged report saved to: {output_file}")
    print("\n📊 Summary:")
    print(f"   Total violations: {len(all_violations)}")
    print(f"   - API violations: {len(api_violations)}")
    print(f"   - Architecture violations: {len(arch_violations)}")
    print("\n   By severity:")
    for severity, count in sorted(severity_counts.items()):
        print(f"   - {severity}: {count}")

    return merged_report


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Merge OpenAPI and ArchUnit reports into comprehensive governance report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge both API and architecture violations
  python merge_reports.py \\
    --openapi governance-report.json \\
    --archunit arch-violations.json \\
    --output governance-report.json

  # Merge only architecture violations
  python merge_reports.py \\
    --archunit arch-violations.json \\
    --output governance-report.json

  # Use default file names
  python merge_reports.py
        """,
    )

    parser.add_argument("--openapi", help="Path to OpenAPI violations JSON file")

    parser.add_argument("--archunit", help="Path to ArchUnit violations JSON file")

    parser.add_argument(
        "--output",
        default="governance-report.json",
        help="Output path for merged report (default: governance-report.json)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Auto-detect files if not provided
    if not args.openapi and not args.archunit:
        # Look for common file names
        possible_openapi = [
            "governance-report.json",
            "api-violations.json",
            "spectral-report.json",
        ]
        possible_archunit = [
            "arch-violations.json",
            "archunit-report.json",
            "architecture-violations.json",
        ]

        for f in possible_openapi:
            if Path(f).exists():
                args.openapi = f
                print(f"📁 Auto-detected OpenAPI report: {f}")
                break

        for f in possible_archunit:
            if Path(f).exists():
                args.archunit = f
                print(f"📁 Auto-detected ArchUnit report: {f}")
                break

        if not args.openapi and not args.archunit:
            print(
                "❌ Error: No report files found. Please specify --openapi or --archunit"
            )
            sys.exit(1)

    try:
        merge_reports(
            openapi_file=args.openapi,
            archunit_file=args.archunit,
            output_file=args.output,
        )
    except Exception as e:
        print(f"❌ Error merging reports: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
