import argparse
import asyncio
import platform
import subprocess
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from report.report_generator import ReportGenerator
from scanner import GovernanceScanner

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="API Governance Scanner")
    parser.add_argument("--project", default=".", help="Project directory path")
    parser.add_argument(
        "--type",
        default="api",
        choices=["api", "java"],
        help="Type of scan: api (OpenAPI) or java (ArchUnit)",
    )
    parser.add_argument(
        "--spec",
        help="Specific OpenAPI spec file path to scan (supports .yaml, .yml, .json)",
    )
    parser.add_argument(
        "--output", default="api-governance-report.md", help="Output report path"
    )
    parser.add_argument(
        "--ruleset", help="Spectral ruleset path (default: auto-detected from package)"
    )
    parser.add_argument(
        "--llm-endpoint", default="http://localhost:11434", help="LLM API endpoint"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Prompt for OpenAPI spec path if not auto-detected",
    )

    args = parser.parse_args()

    # Auto-detect ruleset path if not provided
    if not args.ruleset:
        # Determine ruleset path relative to project root
        args.ruleset = str(project_root / "rules" / "spectral_ruleset.yaml")

    scanner = GovernanceScanner(
        project_path=args.project,
        ruleset_path=args.ruleset,
        llm_endpoint=args.llm_endpoint,
    )

    # Check if Java scan is requested
    if args.type == "java":
        from engines.arch_unit_engine import ArchUnitEngine
        from engines.llm_analyzer import LLMAnalyzer

        async def run_java_scan():
            print(f"Starting Java ArchUnit scan on: {args.project}")
            engine = ArchUnitEngine(args.project)
            violations = engine.run_scan()

            # Enhance with LLM
            if violations:
                print("Enhancing violations with LLM analysis...")
                llm = LLMAnalyzer(api_endpoint=args.llm_endpoint)
                for v in violations:
                    try:
                        prompt = (
                            f"Explain this Java architectural violation and suggest a fix:\n"
                            f"Rule: {v.get('rule')}\n"
                            f"Message: {v.get('message')}\n"
                            f"Context: ArchUnit test failure."
                        )
                        suggestion = await llm._call_llm(prompt)
                        v["llm_context"] = suggestion
                        v["suggestion"] = "See explanation above."
                    except Exception as e:
                        print(f"LLM enhancement failed: {e}")
            return violations

        violations = asyncio.run(run_java_scan())

        # Create a result object compatible with ReportGenerator
        from scanner.governance_scanner import ScanResult

        result = ScanResult(
            project_path=str(Path(args.project)),
            spec_files=[],
            spectral_results=violations,
            llm_results=[],
            scan_type="Java Architecture",
        )

        # Generate reports for Java scan
        output_path = Path(args.output)
        if output_path.is_dir():
            # Use directory with default filename
            md_report_path = output_path / "arch-governance-report.md"
            json_report_path = output_path / "arch-violations.json"
        else:
            # Use provided filename
            md_report_path = output_path
            json_report_path = output_path.with_suffix(".json")

        # Ensure output directory exists
        md_report_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate markdown report
        ReportGenerator(result).generate_markdown(md_report_path)
        print(f"Markdown report generated at: {md_report_path}")

        # Generate JSON report for fix tools
        ReportGenerator(result).generate_json(json_report_path, include_categories=True)
        print(f"JSON report generated at: {json_report_path}")

        print(f"\n📊 Summary: {len(violations)} Java architecture violations found")
        if violations:
            print("💡 To generate fix instructions, run:")
            print(f"   python -m autofix.proposer {json_report_path}")
    else:
        # Auto-enable interactive mode if running in a terminal and not explicitly disabled
        # This provides better UX by prompting for spec path when not found
        interactive_mode = args.interactive
        if not interactive_mode and sys.stdin.isatty() and sys.stdout.isatty():
            # Running in terminal - enable interactive mode automatically
            interactive_mode = True
            print("📋 Interactive mode enabled (terminal detected)")

        result = asyncio.run(
            scanner.scan(
                output_path=args.output,
                target_spec=args.spec,
                interactive=interactive_mode,
            )
        )

    # Handle output path - if it's a directory, create filename
    output_path = Path(args.output)
    if output_path.is_dir():
        # Use directory with default filename
        html_report_path = output_path / "governance-report.html"
        md_report_path = output_path / "governance-report.md"
    else:
        # Use provided filename
        html_report_path = output_path.with_suffix(".html")
        md_report_path = output_path

    # Ensure output directory exists
    html_report_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate reports
    ReportGenerator(result).generate_html(html_report_path)
    print(f"HTML report generated at: {html_report_path}")

    # Also generate markdown report if not already generated
    if not md_report_path.exists() or md_report_path != Path(args.output):
        ReportGenerator(result).generate_markdown(md_report_path)
        print(f"Markdown report generated at: {md_report_path}")

    if platform.system() == "Darwin":  # macOS
        try:
            subprocess.run(["open", str(html_report_path)], check=False)
        except Exception as e:
            print(f"Could not open HTML report automatically: {e}")

    # Exit with error code if critical issues found
    exit(0 if result.error_count == 0 else 1)
