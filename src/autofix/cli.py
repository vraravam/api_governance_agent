#!/usr/bin/env python3
"""
CLI for Governance Auto-Fix Workflow

Provides command-line interface for the auto-fix workflow.
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from autofix.engine import AutoFixEngine


async def main_async():
    parser = argparse.ArgumentParser(
        description="Governance Auto-Fix Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full interactive workflow
  python -m autofix.cli --report governance-report.json --project ./my-project

  # Auto-approve safe fixes only
  python -m autofix.cli --report report.json --project . --auto-approve-safe

  # Preview fixes without applying
  python -m autofix.cli --report report.json --project . --preview-only

  # Apply fixes without creating PR
  python -m autofix.cli --report report.json --project . --no-pr
        """,
    )

    parser.add_argument(
        "--report", required=True, help="Path to governance report JSON file"
    )

    parser.add_argument(
        "--project",
        default=".",
        help="Path to project directory (default: current directory)",
    )

    parser.add_argument(
        "--output-dir",
        default="./governance-autofix",
        help="Directory for output files (default: ./governance-autofix)",
    )

    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="Only generate fix previews without applying",
    )

    parser.add_argument(
        "--auto-approve-safe",
        action="store_true",
        help="Automatically approve safe-to-auto-apply fixes",
    )

    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Skip interactive review (use with --auto-approve-safe)",
    )

    parser.add_argument(
        "--no-pr",
        action="store_true",
        help="Apply fixes without creating git branch/commits",
    )

    parser.add_argument(
        "--branch-name", help="Custom branch name for PR (default: auto-generated)"
    )

    parser.add_argument(
        "--use-copilot",
        action="store_true",
        default=True,
        help="Use GitHub Copilot for fast fix generation (default: True, 80-90%% faster)",
    )

    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use legacy LLM analyzer instead of Copilot (slower)",
    )

    args = parser.parse_args()

    # Validate arguments
    report_path = Path(args.report)
    if not report_path.exists():
        print(f"Error: Governance report not found: {args.report}", file=sys.stderr)
        sys.exit(1)

    project_path = Path(args.project)
    if not project_path.exists():
        print(f"Error: Project directory not found: {args.project}", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine analyzer to use
    use_copilot = not args.use_llm  # Default to Copilot unless --use-llm specified

    # Initialize engine
    print(f"\n{'='*60}")
    print(f"Fix Analyzer: {'GitHub Copilot (Fast)' if use_copilot else 'LLM (Legacy)'}")
    print(f"{'='*60}\n")

    engine = AutoFixEngine(str(project_path), use_copilot=use_copilot)

    try:
        if args.preview_only:
            # Preview mode: only generate fixes and diffs
            print("Running in PREVIEW mode (no changes will be applied)\n")

            violations = engine.load_governance_report(str(report_path))
            fixes, diffs = await engine.propose_fixes(violations, str(output_dir))

            if fixes:
                print(f"\n✅ Generated {len(fixes)} fix proposals")
                print(f"📄 Preview saved to: {output_dir / 'fix-preview.md'}")
                print("\nTo apply fixes, run without --preview-only flag")
            else:
                print("\n❌ No fixable violations found")

        else:
            # Full workflow
            result = await engine.run_full_workflow(
                report_path=str(report_path),
                interactive=not args.no_interactive,
                auto_approve_safe=args.auto_approve_safe,
                create_pr=not args.no_pr,
                output_dir=str(output_dir),
            )

            # Print final summary
            print("\n📊 FINAL SUMMARY")
            print(f"   Fixes Proposed: {result.fixes_proposed}")
            print(f"   Fixes Approved: {result.fixes_approved}")
            print(f"   Fixes Rejected: {result.fixes_rejected}")
            print(f"   Fixes Applied:  {result.fixes_applied}")

            if result.branch_name:
                print(f"\n🌿 Git Branch: {result.branch_name}")

            if result.pr_info:
                print(f"📝 PR Title: {result.pr_info.title}")
                print(f"📄 PR Description: {output_dir / 'pull-request.md'}")

            print(f"\n📁 Output Directory: {output_dir}")

            # Exit code based on results
            if result.fixes_applied > 0:
                print("\n✅ Auto-fix workflow completed successfully!")
                sys.exit(0)
            elif result.fixes_proposed == 0:
                print("\n✅ No fixable violations found")
                sys.exit(0)
            else:
                print("\n⚠️  Workflow completed but no fixes were applied")
                sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main():
    """Wrapper to run async main function"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
