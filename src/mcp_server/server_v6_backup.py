#!/usr/bin/env python3
"""
MCP Server for API Governance Tool

Exposes API governance capabilities as MCP tools for IDE-based agents.
Uses stdio transport for local development and IDE integration.
"""

import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Add parent directories to path for imports
api_governance_agent_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(api_governance_agent_path))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    print(
        f"Error: fastmcp import failed: {e}. Run: pip install fastmcp", file=sys.stderr
    )
    sys.exit(1)

from mcp_server.tool_schemas import (
    ValidateOpenAPIInput,
    ValidateOpenAPIOutput,
    ValidateArchitectureInput,
    ValidateArchitectureOutput,
    GovernanceSummaryInput,
    GovernanceSummaryOutput,
    ProposeFixesOutput,
    ProposedFixInfo,
    ReviewFixesOutput,
    CreateGovernancePROutput,
)
from mcp_server.output_normalizer import OutputNormalizer
from scanner import GovernanceScanner
from engines.arch_unit_engine import ArchUnitEngine
from scanner.project_detector import ProjectDetector

# Auto-fix imports


# ========================================
# GOVERNANCE REPORT PATHS
# ========================================
def get_governance_paths(project_path: Path) -> Dict[str, Path]:
    """
    Get standardized paths for governance reports.
    All reports go into build/governance/ directory which can be cleaned automatically.
    Only one copy of each report is maintained (overwrites on each scan).

    Args:
        project_path: Root path of the project being scanned

    Returns:
        Dict with all governance-related paths
    """
    # Use build/governance for all reports (ignored by most .gitignore files)
    governance_dir = project_path / "build" / "governance"
    governance_dir.mkdir(parents=True, exist_ok=True)

    return {
        "governance_dir": governance_dir,
        "governance_report": governance_dir / "governance-report.json",
        "api_report": governance_dir / "api-violations.json",
        "arch_report": governance_dir / "arch-violations.json",
        "arch_temp": governance_dir / "arch-violations-temp.json",
        "combined_report": governance_dir / "combined-report.md",
        "api_report_md": governance_dir / "api-governance-report.md",
        "fix_instructions_dir": governance_dir / "copilot-fixes",
        "fix_instructions_md": governance_dir
        / "copilot-fixes"
        / "copilot-fix-instructions.md",
        "fix_instructions_json": governance_dir
        / "copilot-fixes"
        / "copilot-fix-instructions.json",
    }


# ========================================
from autofix.engine import AutoFixEngine
from autofix.proposer import ProposedFix
from autofix.review_gate import ReviewState

# Initialize MCP server
mcp = FastMCP("API Governance Server")


@mcp.tool()
async def validate_openapi(spec_path: str, ruleset: str = None) -> Dict:
    """
    Validate OpenAPI specifications against Spectral rules and LLM semantic analysis.

    Args:
        spec_path: Path to OpenAPI specification file
        ruleset: Optional path to custom Spectral ruleset

    Returns:
        Validation results with violations, severity summary, and suggested fixes
    """
    try:
        # Validate input
        input_data = ValidateOpenAPIInput(spec_path=spec_path, ruleset=ruleset)

        # Resolve paths
        spec_path_obj = Path(input_data.spec_path).resolve()
        if not spec_path_obj.exists():
            return {
                "violations": [],
                "severity_summary": {"critical": 1, "warning": 0, "info": 0},
                "suggested_fixes": [f"File not found: {spec_path}"],
            }

        # Determine ruleset path
        if input_data.ruleset:
            ruleset_path = str(Path(input_data.ruleset).resolve())
        else:
            # Use default ruleset
            ruleset_path = str(
                api_governance_agent_path / "rules" / "spectral_ruleset.yaml"
            )

        # Run governance scan
        project_path = str(spec_path_obj.parent)
        scanner = GovernanceScanner(
            project_path=project_path,
            ruleset_path=ruleset_path,
            llm_endpoint="http://localhost:11434",
        )

        # Execute scan (single file target)
        result = await scanner.scan(output_path=None, target_spec=str(spec_path_obj))

        # Combine all violations
        all_violations = result.spectral_results + result.llm_results

        # Normalize violations
        normalized_violations = [
            OutputNormalizer.normalize_violation(v) for v in all_violations
        ]

        # Calculate summary
        severity_summary = OutputNormalizer.calculate_severity_summary(
            normalized_violations
        )
        suggested_fixes = OutputNormalizer.extract_suggested_fixes(
            normalized_violations
        )

        # Build output
        output = ValidateOpenAPIOutput(
            violations=normalized_violations,
            severity_summary=severity_summary,
            suggested_fixes=suggested_fixes,
        )

        return output.model_dump()

    except Exception as e:
        # Return error as a critical violation
        return {
            "violations": [
                {
                    "rule_id": "mcp-error",
                    "description": f"Error during validation: {str(e)}",
                    "severity": "critical",
                    "file": spec_path,
                    "line": None,
                    "fix_hint": "Check server logs for details",
                }
            ],
            "severity_summary": {"critical": 1, "warning": 0, "info": 0},
            "suggested_fixes": ["Fix the error and retry"],
        }


@mcp.tool()
async def validate_architecture(
    project_path: str, rule_profile: str = "default"
) -> Dict:
    """
    Validate Java architecture using ArchUnit rules.

    Args:
        project_path: Path to compiled Java classes directory
        rule_profile: Rule profile to use (default: 'default')

    Returns:
        Validation results with violations, impacted layers, and refactoring guidance
    """
    try:
        # Validate input
        input_data = ValidateArchitectureInput(
            project_path=project_path, rule_profile=rule_profile
        )

        # Resolve path
        project_path_obj = Path(input_data.project_path).resolve()
        if not project_path_obj.exists():
            return {
                "violations": [
                    {
                        "rule_id": "path-error",
                        "description": f"Project path not found: {project_path}",
                        "severity": "critical",
                        "file": project_path,
                        "line": None,
                        "fix_hint": "Verify the path exists and contains compiled Java classes",
                    }
                ],
                "impacted_layers": [],
                "refactoring_guidance": ["Fix the path error"],
            }

        # Run ArchUnit scan
        engine = ArchUnitEngine(str(project_path_obj))
        violations = engine.run_scan()

        # Enhance with LLM if available
        # User requested to skip LLM during scan and use it for fixes instead
        # if violations:
        #     try:
        #         llm = LLMAnalyzer(api_endpoint="http://localhost:11434")
        #         violations = await llm.enhance_arch_violations(violations)
        #     except Exception:
        #         pass  # Continue without LLM

        # Normalize violations
        normalized_violations = [
            OutputNormalizer.normalize_violation(v) for v in violations
        ]

        # Extract architectural information
        impacted_layers = OutputNormalizer.extract_impacted_layers(
            normalized_violations
        )
        refactoring_guidance = OutputNormalizer.generate_refactoring_guidance(
            normalized_violations
        )

        # Build output
        output = ValidateArchitectureOutput(
            violations=normalized_violations,
            impacted_layers=impacted_layers,
            refactoring_guidance=refactoring_guidance,
        )

        return output.model_dump()

    except Exception as e:
        return {
            "violations": [
                {
                    "rule_id": "mcp-error",
                    "description": f"Error during validation: {str(e)}",
                    "severity": "critical",
                    "file": project_path,
                    "line": None,
                    "fix_hint": "Check server logs for details",
                }
            ],
            "impacted_layers": [],
            "refactoring_guidance": ["Fix the error and retry"],
        }


@mcp.tool()
async def governance_summary(project_path: str) -> Dict:
    """
    Provide overall governance health summary for a project.

    Args:
        project_path: Path to project directory

    Returns:
        Overall health score, violation counts, and recommended next steps
    """
    try:
        # Validate input
        input_data = GovernanceSummaryInput(project_path=project_path)

        # Resolve path
        project_path_obj = Path(input_data.project_path).resolve()
        if not project_path_obj.exists():
            return {
                "overall_health_score": 0,
                "critical_violations": 1,
                "warnings": 0,
                "next_steps": [f"Project path not found: {project_path}"],
                "scan_types_detected": [],
            }

        # Detect project type
        detector = ProjectDetector(str(project_path_obj))

        scan_types = []
        all_violations = []

        # Check for OpenAPI specs
        specs = detector.find_openapi_specs()
        if specs:
            scan_types.append("api_spec")

            # Run API spec scan
            try:
                ruleset_path = str(
                    api_governance_agent_path / "rules" / "spectral_ruleset.yaml"
                )

                scanner = GovernanceScanner(
                    project_path=str(project_path_obj),
                    ruleset_path=ruleset_path,
                    llm_endpoint="http://localhost:11434",
                )
                result = await scanner.scan(output_path=None)
                # Skip LLM enhancement for now
                # all_violations.extend(result.spectral_results + result.llm_results)
                all_violations.extend(result.spectral_results)
            except Exception:
                pass  # Continue with other scans

        # Check for Java project
        is_java, build_tool = detector.is_java_project()
        if is_java:
            scan_types.append("java_architecture")

            # Run Java architecture scan
            try:
                engine = ArchUnitEngine(str(project_path_obj))
                violations = engine.run_scan()

                # Enhance with LLM if available
                # User requested to skip LLM during scan
                # if violations:
                #     try:
                #         llm = LLMAnalyzer(api_endpoint="http://localhost:11434")
                #         violations = await llm.enhance_arch_violations(violations)
                #     except Exception:
                #         pass

                all_violations.extend(violations)
            except Exception:
                pass  # Continue

        # Normalize all violations
        normalized_violations = [
            OutputNormalizer.normalize_violation(v) for v in all_violations
        ]

        # Calculate summary
        severity_summary = OutputNormalizer.calculate_severity_summary(
            normalized_violations
        )
        health_score = OutputNormalizer.calculate_health_score(
            severity_summary.critical, severity_summary.warning, severity_summary.info
        )

        # Generate next steps
        next_steps = []
        if severity_summary.critical > 0:
            next_steps.append(
                f"Address {severity_summary.critical} critical violation(s) immediately"
            )
        if severity_summary.warning > 0:
            next_steps.append(f"Review {severity_summary.warning} warning(s)")
        if not next_steps:
            next_steps.append(
                "No violations found. Maintain current quality standards."
            )

        # Build output
        output = GovernanceSummaryOutput(
            overall_health_score=health_score,
            critical_violations=severity_summary.critical,
            warnings=severity_summary.warning,
            next_steps=next_steps,
            scan_types_detected=scan_types,
        )

        return output.model_dump()

    except Exception as e:
        return {
            "overall_health_score": 0,
            "critical_violations": 1,
            "warnings": 0,
            "next_steps": [f"Error during scan: {str(e)}"],
            "scan_types_detected": [],
        }


# ============================================================================
# AUTO-FIX TOOLS
# ============================================================================

# Global storage for fix sessions (in production, use Redis or database)
_fix_sessions: Dict[str, tuple[AutoFixEngine, List[ProposedFix], ReviewState]] = {}


@mcp.tool()
async def propose_fixes(
    report_path: str,
    project_path: str,
    output_dir: str = None,
    use_copilot: bool = True,
) -> Dict:
    """
    Propose fixes for governance violations from a report.

    Args:
        report_path: Path to governance report JSON file
        project_path: Path to project directory
        output_dir: Optional directory for output files
        use_copilot: Use GitHub Copilot for fast fix generation (default: True, 80-90% faster)

    Returns:
        Proposed fixes with diff previews and metadata
    """
    import time

    start_time = time.time()

    try:
        # Validate paths
        report_file = Path(report_path)
        if not report_file.exists():
            return {
                "fixes_proposed": 0,
                "fixes": [],
                "diff_preview_path": None,
                "safe_to_auto_apply_count": 0,
                "error": f"Report file not found: {report_path}",
            }

        project_dir = Path(project_path)
        if not project_dir.exists():
            return {
                "fixes_proposed": 0,
                "fixes": [],
                "diff_preview_path": None,
                "safe_to_auto_apply_count": 0,
                "error": f"Project directory not found: {project_path}",
            }

        # Initialize engine with Copilot support
        print(f"\n{'='*60}")
        print(
            f"Fix Proposal Engine: {'GitHub Copilot (Fast)' if use_copilot else 'LLM (Legacy)'}"
        )
        print(f"{'='*60}\n")

        engine = AutoFixEngine(str(project_dir), use_copilot=use_copilot)

        # Load violations
        violations = engine.load_governance_report(str(report_file))

        # Propose fixes
        fixes, diffs = await engine.propose_fixes(violations, output_dir)

        elapsed_time = time.time() - start_time
        print(f"\n✓ Fix proposal completed in {elapsed_time:.2f} seconds")

        if not fixes:
            return {
                "fixes_proposed": 0,
                "fixes": [],
                "diff_preview_path": None,
                "safe_to_auto_apply_count": 0,
                "message": "No fixable violations found",
                "execution_time_seconds": elapsed_time,
            }

        # Create session ID
        import uuid

        session_id = str(uuid.uuid4())

        # Start review session
        review_state = engine.review_gate.start_review(fixes)

        # Store session
        _fix_sessions[session_id] = (engine, fixes, review_state)

        # Convert fixes to output format
        fix_infos = []
        for fix in fixes:
            fix_infos.append(
                ProposedFixInfo(
                    fix_id=fix.fix_id,
                    rule_id=fix.rule_id,
                    file_path=fix.file_path,
                    line_number=fix.line_number,
                    complexity=fix.complexity_level,
                    is_safe_to_auto_apply=fix.is_safe_to_auto_apply,
                    explanation=fix.explanation,
                )
            )

        safe_count = sum(1 for f in fixes if f.is_safe_to_auto_apply)

        # Generate summary table
        table_rows = []
        table_rows.append("| File | Rule | Change Type | Reason |")
        table_rows.append("| :--- | :--- | :--- | :--- |")

        for fix in fixes:
            # Shorten file path for display
            display_path = (
                fix.file_path.split("/")[-1] if "/" in fix.file_path else fix.file_path
            )
            change_type = "AI-Fixed" if "ai" in fix.fix_id else "Rule-Fixed"
            # Get first sentence of explanation
            reason = fix.explanation.split(".")[0] + "."
            table_rows.append(
                f"| {display_path} | {fix.rule_id} | {change_type} | {reason} |"
            )

        summary_table = "\n".join(table_rows)

        # Determine diff preview path
        diff_path = None
        if output_dir:
            diff_path = str(Path(output_dir) / "fix-preview.md")

        output = ProposeFixesOutput(
            fixes_proposed=len(fixes),
            fixes=fix_infos,
            diff_preview_path=diff_path,
            safe_to_auto_apply_count=safe_count,
            summary_table=summary_table,
        )

        result = output.model_dump()
        result["fix_session_id"] = session_id
        result["execution_time_seconds"] = elapsed_time
        result["analyzer_type"] = "GitHub Copilot" if use_copilot else "LLM"
        return result

    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            "fixes_proposed": 0,
            "fixes": [],
            "diff_preview_path": None,
            "safe_to_auto_apply_count": 0,
            "error": f"Error proposing fixes: {str(e)}",
            "execution_time_seconds": elapsed_time,
        }


@mcp.tool()
async def review_fixes(
    fix_session_id: str,
    approved_fix_ids: List[str] = None,
    rejected_fix_ids: List[str] = None,
    comments: Dict[str, str] = None,
) -> Dict:
    """
    Review proposed fixes by approving or rejecting them.

    Args:
        fix_session_id: Fix session identifier from propose_fixes
        approved_fix_ids: List of fix IDs to approve
        rejected_fix_ids: List of fix IDs to reject
        comments: Optional comments per fix_id

    Returns:
        Review status with counts
    """
    try:
        # Get session
        if fix_session_id not in _fix_sessions:
            return {
                "approved_count": 0,
                "rejected_count": 0,
                "pending_count": 0,
                "ready_to_apply": False,
                "error": f"Invalid session ID: {fix_session_id}",
            }

        engine, fixes, review_state = _fix_sessions[fix_session_id]

        # Apply approvals
        if approved_fix_ids:
            for fix_id in approved_fix_ids:
                engine.review_gate.approve_fix(fix_id)

        # Apply rejections
        if rejected_fix_ids:
            for fix_id in rejected_fix_ids:
                engine.review_gate.reject_fix(fix_id)

        # Add comments
        if comments:
            for fix_id, comment in comments.items():
                engine.review_gate.add_comment(fix_id, comment)

        # Get summary
        summary = review_state.get_summary()

        output = ReviewFixesOutput(
            approved_count=summary["approved"],
            rejected_count=summary["rejected"],
            pending_count=summary["pending"],
            ready_to_apply=summary["approved"] > 0,
        )

        return output.model_dump()

    except Exception as e:
        return {
            "approved_count": 0,
            "rejected_count": 0,
            "pending_count": 0,
            "ready_to_apply": False,
            "error": f"Error reviewing fixes: {str(e)}",
        }


@mcp.tool()
async def create_governance_pr(
    fix_session_id: str, push_to_remote: bool = False, remote_name: str = "origin"
) -> Dict:
    """
    Create pull request information for applied fixes.

    Args:
        fix_session_id: Fix session identifier
        push_to_remote: Whether to push branch to remote
        remote_name: Git remote name

    Returns:
        PR information including title, description, and metadata
    """
    try:
        # Get session
        if fix_session_id not in _fix_sessions:
            return {"error": f"Invalid session ID: {fix_session_id}"}

        engine, fixes, review_state = _fix_sessions[fix_session_id]

        # Check if fixes were applied
        if not hasattr(engine, "pr_creator") or not engine.pr_creator:
            return {"error": "Fixes have not been applied yet. Call apply_fixes first."}

        # Get PR info from last apply_fixes call
        if not engine.last_pr_info:
            return {
                "error": "No PR information available. Ensure fixes were applied with git operations in apply_fixes."
            }

        pr_info = engine.last_pr_info

        # Push to remote if requested
        pushed = False
        if push_to_remote and pr_info.branch_name:
            try:
                engine.pr_creator.push_branch(pr_info.branch_name, remote_name)
                pushed = True
            except Exception:
                # Continue even if push fails
                pass

        # Save PR description
        pr_desc_path = (
            Path(engine.project_path) / "governance-autofix" / "pull-request.md"
        )
        pr_desc_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pr_desc_path, "w", encoding="utf-8") as f:
            f.write(f"# {pr_info.title}\n\n")
            f.write(pr_info.description)

        output = CreateGovernancePROutput(
            branch_name=pr_info.branch_name,
            pr_title=pr_info.title,
            pr_description_path=str(pr_desc_path),
            commits=len(pr_info.commits),
            files_changed=pr_info.files_changed,
            pushed_to_remote=pushed,
        )

        return output.model_dump()

    except Exception as e:
        return {"error": f"Error creating PR: {str(e)}"}


@mcp.tool()
async def run_complete_governance_scan(project_path: str = ".") -> Dict:
    """
    Run a complete governance scan automatically:
    1. Detects project type (API, Java, or both)
    2. Scans OpenAPI specs if found using GovernanceScanner
    3. Runs ArchUnit tests if Java project detected
    4. Automatically merges reports into governance-report.json
    5. Generates fix instructions

    This is the ONE command users need to run - no file names required!

    Args:
        project_path: Path to project directory (default: current directory)

    Returns:
        Complete scan results with all violations and generated fix instructions
    """
    try:
        import subprocess
        import json
        from pathlib import Path

        project_path_obj = Path(project_path).resolve()
        if not project_path_obj.exists():
            return {
                "error": f"Project path not found: {project_path}",
                "violations": [],
                "fix_instructions_generated": False,
            }

        # Get standardized governance paths (build/governance/)
        paths = get_governance_paths(project_path_obj)

        # Detect project type
        detector = ProjectDetector(str(project_path_obj))

        results = {
            "project_path": str(project_path_obj),
            "governance_dir": str(paths["governance_dir"]),
            "scans_performed": [],
            "violations": [],
            "total_violations": 0,
            "by_type": {},
            "by_severity": {},
            "fix_instructions_generated": False,
            "fix_instructions_path": None,
            "next_steps": [],
        }

        # Check for OpenAPI specs
        openapi_specs = detector.find_openapi_specs()

        # Check for Java files
        is_java, build_tool = detector.is_java_project()

        api_violations_file = None
        arch_violations_file = None

        # 1. Scan OpenAPI if found - USE GovernanceScanner directly
        if openapi_specs:
            results["scans_performed"].append("OpenAPI")
            try:
                # Auto-detect ruleset path
                package_root = Path(__file__).parent.parent.parent
                ruleset_path = package_root / "rules" / "spectral_ruleset.yaml"

                # Create scanner and run scan
                scanner = GovernanceScanner(
                    project_path=str(project_path_obj),
                    ruleset_path=str(ruleset_path),
                    llm_endpoint="http://localhost:11434",
                )

                # Run scan (generates reports in build/governance/)
                scan_result = await scanner.scan(
                    output_path=str(paths["api_report_md"])
                )

                # The scanner creates governance-report.json - move it to build/governance/
                old_report = project_path_obj / "governance-report.json"
                if old_report.exists():
                    import shutil

                    shutil.move(str(old_report), str(paths["governance_report"]))
                    api_violations_file = paths["governance_report"]
                else:
                    # Check if already in correct location
                    api_violations_file = paths["governance_report"]

                if api_violations_file.exists():
                    with open(api_violations_file, "r") as f:
                        api_data = json.load(f)
                        api_violation_count = api_data.get(
                            "total_violations", len(api_data.get("violations", []))
                        )
                        results["by_type"]["api"] = api_violation_count
                        results["violations"].extend(api_data.get("violations", []))
                else:
                    results["by_type"]["api"] = scan_result.total_violations

            except Exception as e:
                results["scans_performed"].append(f"OpenAPI (failed: {str(e)})")
                results["error"] = f"OpenAPI scan failed: {str(e)}"
                api_violations_file = None

        # 2. Run ArchUnit if Java project - USE ArchUnitEngine directly
        if is_java:
            results["scans_performed"].append("ArchUnit")
            try:
                # Run ArchUnit scan directly (ensures we get ALL violations, not just what's in a file)
                arch_engine = ArchUnitEngine(str(project_path_obj))
                arch_violations = arch_engine.run_scan()

                results["by_type"]["architecture"] = len(arch_violations)

                # Save arch violations to build/governance/arch-violations-temp.json
                arch_violations_file = paths["arch_temp"]
                arch_data = {
                    "violations": arch_violations,
                    "total": len(arch_violations),
                    "by_severity": {},
                }

                # Count by severity
                for v in arch_violations:
                    sev = v.get("severity", "UNKNOWN")
                    arch_data["by_severity"][sev] = (
                        arch_data["by_severity"].get(sev, 0) + 1
                    )

                with open(arch_violations_file, "w") as f:
                    json.dump(arch_data, f, indent=2)

                results["scans_performed"].append(
                    f"ArchUnit ({len(arch_violations)} violations)"
                )

            except Exception as e:
                results["scans_performed"].append(f"ArchUnit (failed: {str(e)})")
                results["error"] = f"ArchUnit scan failed: {str(e)}"
                arch_violations_file = None

        # 3. Merge reports if we have both API and ArchUnit violations
        # Reports are now in build/governance/
        governance_report = paths["governance_report"]

        if arch_violations_file:
            try:
                # If we have both, merge them
                if api_violations_file or governance_report.exists():
                    # Get the api_governance_agent package directory (where scripts/ folder is)
                    # This file is in api_governance_agent/src/mcp_server/server.py
                    package_root = Path(__file__).parent.parent.parent
                    merge_script = package_root / "scripts" / "merge_reports.py"

                    if not merge_script.exists():
                        results["error"] = f"Merge script not found: {merge_script}"
                    else:
                        # Run merge script from package root directory
                        merge_cmd = ["pipenv", "run", "python", str(merge_script)]

                        # Use build/governance/governance-report.json
                        if governance_report.exists():
                            merge_cmd.extend(["--openapi", str(governance_report)])
                        elif api_violations_file:
                            merge_cmd.extend(["--openapi", str(api_violations_file)])

                        merge_cmd.extend(["--archunit", str(arch_violations_file)])
                        merge_cmd.extend(["--output", str(governance_report)])

                        result = subprocess.run(
                            merge_cmd,
                            cwd=str(
                                package_root
                            ),  # Run from api_governance_agent package root
                            capture_output=True,
                            text=True,
                            timeout=60,
                        )

                        if result.returncode != 0:
                            results["error"] = f"Report merge failed: {result.stderr}"

            except Exception as e:
                results["error"] = f"Report merge failed: {str(e)}"

        # 4. Load the final governance report (merged or API-only)
        if governance_report.exists():
            try:
                with open(governance_report, "r") as f:
                    report_data = json.load(f)
                    results["violations"] = report_data.get("violations", [])
                    results["total_violations"] = report_data.get(
                        "total_violations", len(results["violations"])
                    )

                    # Get severity breakdown
                    if "summary" in report_data:
                        results["by_severity"] = report_data["summary"].get(
                            "by_severity", {}
                        )

                # 4.1. Generate a combined markdown report with BOTH API and Architecture violations
                try:
                    combined_md = paths["combined_report"]
                    with open(combined_md, "w", encoding="utf-8") as f:
                        f.write("# Complete Governance Scan Report\n\n")
                        f.write(
                            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        )
                        f.write(f"**Report Location:** `{paths['governance_dir']}`\n\n")

                        f.write("## Executive Summary\n\n")
                        f.write(f"- **Project Path:** `{project_path_obj}`\n")
                        f.write(
                            f"- **Total Violations:** {results['total_violations']}\n"
                        )
                        f.write(
                            f"  - API Violations: {results['by_type'].get('api', 0)}\n"
                        )
                        f.write(
                            f"  - Architecture Violations: {results['by_type'].get('architecture', 0)}\n\n"
                        )

                        # API Violations Section
                        api_violations = [
                            v for v in results["violations"] if v.get("type") == "api"
                        ]
                        if api_violations:
                            f.write(f"## API Violations ({len(api_violations)})\n\n")
                            for v in api_violations:
                                severity_icon = (
                                    "🔴" if v.get("severity", 1) == 0 else "🟡"
                                )
                                f.write(
                                    f"{severity_icon} **{v.get('rule', 'unknown')}**\n"
                                )
                                f.write(
                                    f"  - Message: {v.get('message', 'No message')}\n"
                                )
                                f.write(f"  - File: `{v.get('file', 'unknown')}`\n")
                                f.write(f"  - Line: {v.get('line', 'N/A')}\n\n")

                        # Architecture Violations Section
                        arch_violations = [
                            v
                            for v in results["violations"]
                            if v.get("type") == "architecture"
                        ]
                        if arch_violations:
                            f.write(
                                f"## Architecture Violations ({len(arch_violations)})\n\n"
                            )
                            for v in arch_violations:
                                severity_icon = (
                                    "🔴" if v.get("severity", 1) == 0 else "🟡"
                                )
                                f.write(
                                    f"{severity_icon} **{v.get('rule', 'unknown')}**\n"
                                )
                                f.write(
                                    f"  - Message: {v.get('message', 'No message')}\n"
                                )
                                f.write(f"  - File: `{v.get('file', 'unknown')}`\n")
                                f.write(f"  - Line: {v.get('line', 'N/A')}\n\n")

                        f.write("## Next Steps\n\n")
                        f.write(
                            f"1. Review fix instructions: `{paths['fix_instructions_json']}`\n"
                        )
                        f.write(
                            "2. Apply safe fixes: `@workspace Apply safe fixes automatically`\n"
                        )
                        f.write(
                            "3. Apply all fixes: `@workspace Apply all fixes automatically`\n"
                        )

                    results["combined_report_path"] = str(combined_md)

                except Exception:
                    # Non-fatal, continue
                    pass

            except Exception as e:
                results["error"] = f"Failed to load governance report: {str(e)}"

        # 5. Generate fix instructions automatically if we have violations
        if results["total_violations"] > 0 and governance_report.exists():
            try:
                # Use VSCodeCopilotEngine directly instead of subprocess
                from engines.vscode_copilot_engine import VSCodeCopilotEngine

                # Load violations from governance report in build/governance/
                with open(governance_report, "r") as f:
                    report_data = json.load(f)
                    violations = report_data.get("violations", [])

                # Generate fix instructions
                engine = VSCodeCopilotEngine(project_path=str(project_path_obj))
                instructions = engine.prepare_fix_instructions(violations)

                # Save fix instructions to build/governance/copilot-fixes/
                fix_output_dir = paths["fix_instructions_dir"]
                fix_output_dir.mkdir(parents=True, exist_ok=True)

                fix_instructions_md = paths["fix_instructions_md"]
                fix_instructions_json = paths["fix_instructions_json"]

                # Generate markdown document
                markdown_doc = engine.generate_copilot_workspace_instructions(
                    instructions
                )
                with open(fix_instructions_md, "w", encoding="utf-8") as f:
                    f.write(markdown_doc)

                # Save JSON for automation
                json_data = [
                    {
                        "fix_id": f"fix-{idx:04d}",
                        "rule_id": inst.rule_id,
                        "file": inst.file_path,
                        "lines": inst.context_lines,
                        "prompt": inst.to_copilot_prompt(),
                        "complexity": inst.fix_strategy.complexity.value,
                        "safety": inst.fix_strategy.safety.value,
                    }
                    for idx, inst in enumerate(instructions, 1)
                ]
                with open(fix_instructions_json, "w") as f:
                    json.dump(json_data, f, indent=2)

                # Calculate statistics
                safe_count = sum(
                    1
                    for inst in instructions
                    if inst.fix_strategy.safety.value == "SAFE"
                )
                review_count = sum(
                    1
                    for inst in instructions
                    if inst.fix_strategy.safety.value == "REVIEW_REQUIRED"
                )
                manual_count = sum(
                    1
                    for inst in instructions
                    if inst.fix_strategy.safety.value == "MANUAL_ONLY"
                )

                # Set results
                results["fix_instructions_generated"] = True
                results["fix_instructions_path"] = str(fix_instructions_md)
                results["fix_summary"] = {
                    "total_fixes": len(instructions),
                    "safe_fixes": safe_count,
                    "review_required": review_count,
                    "manual_only": manual_count,
                }

                results["next_steps"] = [
                    f"✅ Scan complete! Found {results['total_violations']} violations",
                    f"   - API violations: {results['by_type'].get('api', 0)}",
                    f"   - Architecture violations: {results['by_type'].get('architecture', 0)}",
                    f"✅ Generated {len(instructions)} fix instructions",
                    f"   - SAFE fixes: {safe_count}",
                    f"   - REVIEW_REQUIRED: {review_count}",
                    f"   - MANUAL_ONLY: {manual_count}",
                    f"� Project path: {project_path_obj}",
                    f"📄 Fix instructions: {fix_instructions_json}",
                    f"📄 Governance report: {governance_report}",
                    "⚡ Apply ALL fixes: @workspace Apply all fixes automatically",
                    "⚡ Apply SAFE only: @workspace Apply safe fixes automatically",
                    f"🔍 Review fixes: Open {fix_instructions_md}",
                ]

            except Exception as e:
                results["fix_instructions_generated"] = False
                results["next_steps"] = [
                    f"✅ Scan complete! Found {results['total_violations']} violations",
                    f"   - API violations: {results['by_type'].get('api', 0)}",
                    f"   - Architecture violations: {results['by_type'].get('architecture', 0)}",
                    f"❌ Fix generation failed: {str(e)}",
                    f"📄 View report: {governance_report}",
                ]
        else:
            results["next_steps"] = [
                "✅ No violations found! Your project is compliant.",
                "🎉 Great job maintaining governance standards!",
            ]

        return results

    except Exception as e:
        return {
            "error": f"Complete scan failed: {str(e)}",
            "violations": [],
            "fix_instructions_generated": False,
        }


@mcp.tool()
async def apply_fixes() -> Dict:
    """
    ⭐ PRIMARY TOOL: Apply ALL governance fixes automatically.

    Use this when user says: "apply fixes", "apply all fixes", "fix all violations"

    Returns ALL fix instructions for Copilot to apply using replace_string_in_file.
    Includes ULTRA-STRICT instructions to prevent Copilot from skipping fixes.

    Returns:
        - List of ALL fixes to apply
        - Ultra-strict instructions for Copilot
        - Validation happens automatically after
    """
    try:
        from pathlib import Path
        import json

        # Look for instructions file
        possible_paths = [
            Path.cwd()
            / "build"
            / "governance"
            / "copilot-fixes"
            / "copilot-fix-instructions.json",
            Path.cwd() / "copilot-fixes" / "copilot-fix-instructions.json",
        ]

        instructions_file = None
        for path in possible_paths:
            if path.exists():
                instructions_file = path
                break

        if not instructions_file:
            return {
                "error": "❌ Fix instructions not found. Run 'scan project' first.",
                "success": False,
                "total_fixes": 0,
            }

        # Load all fix instructions
        with open(instructions_file, "r") as f:
            all_instructions = json.load(f)

        total_fixes = len(all_instructions)

        # ========================================
        # DIRECT PYTHON EXECUTION - NO COPILOT JUDGMENT
        # Apply all fixes using autofix engine directly
        # ========================================

        print(f"\n{'='*80}")
        print(f"🔧 APPLYING ALL {total_fixes} FIXES DIRECTLY (NO USER PROMPTS)")
        print(f"{'='*80}\n")

        applied_fixes = []
        skipped_fixes = []
        failed_fixes = []

        for idx, instruction in enumerate(all_instructions, 1):
            fix_id = instruction.get("fix_id", f"fix-{idx}")
            file_path_str = instruction["file"]
            rule_id = instruction["rule_id"]

            print(
                f"[{idx}/{total_fixes}] Applying {fix_id} to {Path(file_path_str).name}..."
            )

            # Handle absolute paths
            if Path(file_path_str).is_absolute():
                file_path = Path(file_path_str)
            else:
                file_path = Path.cwd() / file_path_str

            if not file_path.exists():
                print(f"  ⚠️  File not found: {file_path}")
                skipped_fixes.append(
                    {
                        "fix_id": fix_id,
                        "file": str(file_path),
                        "reason": "file_not_found",
                    }
                )
                continue

            try:
                # Apply fix using replace_string_in_file directly
                old_content = instruction.get("old_string", "")
                new_content = instruction.get("new_string", "")

                # If old/new strings provided, do direct file replacement
                if old_content and new_content:
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_content = f.read()

                    if old_content in file_content:
                        # Apply the replacement
                        updated_content = file_content.replace(
                            old_content, new_content, 1
                        )

                        # Write back to file
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(updated_content)

                        applied_fixes.append(
                            {
                                "fix_id": fix_id,
                                "file": str(file_path),
                                "rule": rule_id,
                                "status": "applied",
                            }
                        )

                        print("  ✅ Applied")
                    else:
                        # Old string not found - skip this fix
                        print("  ⚠️  Old string not found in file")
                        skipped_fixes.append(
                            {
                                "fix_id": fix_id,
                                "file": str(file_path),
                                "reason": "old_string_not_found",
                            }
                        )
                else:
                    # No old/new strings - mark as needs manual review
                    print("  ⚠️  No old/new strings provided")
                    skipped_fixes.append(
                        {
                            "fix_id": fix_id,
                            "file": str(file_path),
                            "reason": "no_replacement_strings",
                        }
                    )

            except Exception as e:
                print(f"  ❌ Failed: {str(e)}")
                failed_fixes.append(
                    {"fix_id": fix_id, "file": str(file_path), "error": str(e)}
                )

        print(f"\n{'='*80}")
        print("� SUMMARY:")
        print(f"   ✅ Applied: {len(applied_fixes)}/{total_fixes}")
        print(f"   ⚠️  Skipped: {len(skipped_fixes)}")
        print(f"   ❌ Failed: {len(failed_fixes)}")
        print(f"{'='*80}\n")

        # ========================================
        # AUTOMATIC VALIDATION (TOOL CHAINING)
        # ========================================

        print("🧪 Running automatic validation...")
        validation_result = await validate_fixes()

        return {
            "success": True,
            "total_fixes": total_fixes,
            "fixes_applied": len(applied_fixes),
            "fixes_skipped": len(skipped_fixes),
            "fixes_failed": len(failed_fixes),
            "applied": applied_fixes,
            "skipped": skipped_fixes,
            "failed": failed_fixes,
            "validation": validation_result,
            "confidence_score": validation_result.get("confidence_score", 0),
            "message": f"✅ Applied {len(applied_fixes)}/{total_fixes} fixes. Confidence: {validation_result.get('confidence_score', 0)}%",
            "next_steps": validation_result.get("next_steps", []),
        }

    except Exception as e:
        return {
            "error": f"❌ Failed to apply fixes: {str(e)}",
            "success": False,
            "total_fixes": 0,
        }


@mcp.tool()
async def apply_single_fix(fix_index: int) -> Dict:
    """
    🔧 Apply a SINGLE governance fix by index.

    This tool applies ONE fix at a time, removing Copilot's ability to judge which fixes to apply.
    You MUST call this tool repeatedly for each fix index until all fixes are applied.

    Args:
        fix_index: The index of the fix to apply (0-based, e.g., 0, 1, 2, ...)

    Returns:
        Fix application result with next fix index to call
    """
    try:
        from pathlib import Path
        import json

        # Look for instructions file
        possible_paths = [
            Path.cwd()
            / "build"
            / "governance"
            / "copilot-fixes"
            / "copilot-fix-instructions.json",
            Path.cwd() / "copilot-fixes" / "copilot-fix-instructions.json",
        ]

        instructions_file = None
        for path in possible_paths:
            if path.exists():
                instructions_file = path
                break

        if not instructions_file:
            return {
                "error": "❌ Fix instructions not found. Run 'scan project' first.",
                "success": False,
            }

        # Load all fix instructions
        with open(instructions_file, "r") as f:
            all_instructions = json.load(f)

        total_fixes = len(all_instructions)

        # Validate index
        if fix_index < 0 or fix_index >= total_fixes:
            return {
                "error": f"❌ Invalid fix_index {fix_index}. Must be between 0 and {total_fixes-1}",
                "success": False,
                "total_fixes": total_fixes,
            }

        # Get the specific fix
        instruction = all_instructions[fix_index]
        file_path_str = instruction["file"]

        # Handle absolute paths
        if Path(file_path_str).is_absolute():
            file_path = Path(file_path_str)
        else:
            file_path = Path.cwd() / file_path_str

        if not file_path.exists():
            return {
                "error": f"❌ File not found: {file_path}",
                "success": False,
                "fix_index": fix_index,
                "next_fix_index": fix_index + 1,
                "total_fixes": total_fixes,
                "message": f"⚠️ Skipping fix {fix_index+1}/{total_fixes} (file not found). Call apply_single_fix({fix_index + 1}) next.",
            }

        # Read current file content
        with open(file_path, "r", encoding="utf-8") as f:
            current_content = f.read()

        # Return fix details for Copilot to apply using replace_string_in_file
        fix_details = {
            "success": True,
            "fix_index": fix_index,
            "fix_number": fix_index + 1,
            "total_fixes": total_fixes,
            "file": str(file_path),
            "rule": instruction["rule_id"],
            "description": instruction.get("description", "Governance violation"),
            "lines": instruction.get("lines", []),
            "fix_instructions": instruction["prompt"],
            "current_content": (
                current_content[:500] + "..."
                if len(current_content) > 500
                else current_content
            ),
            "next_fix_index": fix_index + 1 if fix_index + 1 < total_fixes else None,
            "is_last_fix": (fix_index + 1) >= total_fixes,
            "progress": f"{fix_index + 1}/{total_fixes}",
            "command": (
                f"USE replace_string_in_file on {file_path} following the fix_instructions above. Then report ✅ and call apply_single_fix({fix_index + 1})."
                if fix_index + 1 < total_fixes
                else f"USE replace_string_in_file on {file_path} following the fix_instructions above. Then report ✅. This was the LAST fix - now call validate_fixes()."
            ),
        }

        return fix_details

    except Exception as e:
        return {
            "error": f"❌ Failed to get fix: {str(e)}",
            "success": False,
            "fix_index": fix_index,
        }


@mcp.tool()
async def validate_fixes() -> Dict:
    """
    🧪 Validate applied fixes by running all project tests.

    Use this after applying fixes to verify code changes don't break functionality.

    This tool:
    - Detects build system (Gradle/Maven/npm/etc.)
    - Runs 'check' or 'test' tasks automatically
    - Runs unit tests for modified files
    - Provides comprehensive test report
    - Gives confidence score on changes

    Returns:
        Test results with pass/fail status, coverage, and confidence report
    """
    try:
        import subprocess
        import json
        from pathlib import Path

        project_path = Path.cwd()

        results = {
            "project_path": str(project_path),
            "build_system": None,
            "tests_run": [],
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "failures": [],
            "confidence_score": 0,
            "summary": "",
            "next_steps": [],
        }

        # Detect build system
        detector = ProjectDetector(str(project_path))
        is_java, build_tool = detector.is_java_project()

        # Check for other build systems
        has_package_json = (project_path / "package.json").exists()
        has_requirements = (project_path / "requirements.txt").exists()
        has_poetry = (project_path / "pyproject.toml").exists()

        # ========================================
        # 1. JAVA PROJECTS (Gradle/Maven)
        # ========================================
        if is_java and build_tool:
            results["build_system"] = build_tool
            results["tests_run"].append(f"{build_tool} check/test")

            try:
                if build_tool == "gradle":
                    # Run Gradle check (includes test, compileJava, etc.)
                    gradle_cmd = [
                        "./gradlew",
                        "check",
                        "--no-daemon",
                        "--console=plain",
                    ]

                    # Check if gradlew exists
                    if not (project_path / "gradlew").exists():
                        gradle_cmd = ["gradle", "check", "--console=plain"]

                    result = subprocess.run(
                        gradle_cmd,
                        cwd=str(project_path),
                        capture_output=True,
                        text=True,
                        timeout=300,  # 5 minutes
                    )

                    # Parse Gradle output
                    output = result.stdout + result.stderr

                    # Look for test results
                    if "BUILD SUCCESSFUL" in output:
                        results["tests_passed"] += 1
                        results["confidence_score"] = 100
                        results["summary"] = "✅ All Gradle checks passed!"
                    else:
                        # Parse failures
                        if "BUILD FAILED" in output:
                            results["tests_failed"] += 1
                            results["confidence_score"] = 0

                            # Extract failure details
                            for line in output.split("\n"):
                                if "FAILED" in line or "error" in line.lower():
                                    results["failures"].append(line.strip())

                            results["summary"] = (
                                f"❌ Gradle check failed. {len(results['failures'])} errors found."
                            )

                elif build_tool == "maven":
                    # Run Maven verify (includes test + integration tests)
                    mvn_cmd = ["./mvnw", "verify", "-B"]

                    # Check if mvnw exists
                    if not (project_path / "mvnw").exists():
                        mvn_cmd = ["mvn", "verify", "-B"]

                    result = subprocess.run(
                        mvn_cmd,
                        cwd=str(project_path),
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )

                    output = result.stdout + result.stderr

                    # Parse Maven output
                    if "BUILD SUCCESS" in output:
                        results["tests_passed"] += 1
                        results["confidence_score"] = 100
                        results["summary"] = "✅ All Maven tests passed!"
                    else:
                        results["tests_failed"] += 1
                        results["confidence_score"] = 0

                        # Extract failure details
                        for line in output.split("\n"):
                            if "FAILURE" in line or "ERROR" in line:
                                results["failures"].append(line.strip())

                        results["summary"] = (
                            f"❌ Maven verify failed. {len(results['failures'])} errors found."
                        )

            except subprocess.TimeoutExpired:
                results["summary"] = "⏱️ Tests timed out after 5 minutes"
                results["confidence_score"] = 0
            except Exception as e:
                results["summary"] = f"❌ Test execution failed: {str(e)}"
                results["confidence_score"] = 0

        # ========================================
        # 2. JAVASCRIPT/NODE PROJECTS
        # ========================================
        elif has_package_json:
            results["build_system"] = "npm"
            results["tests_run"].append("npm test")

            try:
                # Check if test script exists
                with open(project_path / "package.json", "r") as f:
                    package_data = json.load(f)
                    if "scripts" in package_data and "test" in package_data["scripts"]:
                        result = subprocess.run(
                            ["npm", "test"],
                            cwd=str(project_path),
                            capture_output=True,
                            text=True,
                            timeout=180,
                        )

                        if result.returncode == 0:
                            results["tests_passed"] += 1
                            results["confidence_score"] = 100
                            results["summary"] = "✅ All npm tests passed!"
                        else:
                            results["tests_failed"] += 1
                            results["confidence_score"] = 0
                            results["summary"] = "❌ npm tests failed"
                            results["failures"].append(result.stderr)
                    else:
                        results["summary"] = "⚠️ No test script found in package.json"
                        results["confidence_score"] = 50

            except Exception as e:
                results["summary"] = f"❌ npm test failed: {str(e)}"
                results["confidence_score"] = 0

        # ========================================
        # 3. PYTHON PROJECTS
        # ========================================
        elif has_requirements or has_poetry:
            results["build_system"] = "pytest" if has_poetry else "python"
            results["tests_run"].append("pytest")

            try:
                # Try pytest first
                result = subprocess.run(
                    ["pytest", "-v", "--tb=short"],
                    cwd=str(project_path),
                    capture_output=True,
                    text=True,
                    timeout=180,
                )

                if result.returncode == 0:
                    results["tests_passed"] += 1
                    results["confidence_score"] = 100
                    results["summary"] = "✅ All pytest tests passed!"
                else:
                    results["tests_failed"] += 1
                    results["confidence_score"] = 30
                    results["summary"] = "⚠️ Some pytest tests failed"

                    # Parse pytest output for failures
                    for line in result.stdout.split("\n"):
                        if "FAILED" in line:
                            results["failures"].append(line.strip())

            except FileNotFoundError:
                results["summary"] = "⚠️ pytest not found, skipping Python tests"
                results["confidence_score"] = 50
            except Exception as e:
                results["summary"] = f"❌ pytest failed: {str(e)}"
                results["confidence_score"] = 0

        else:
            results["summary"] = "⚠️ No recognized build system found"
            results["confidence_score"] = 50
            results["next_steps"].append(
                "Unable to detect build system (Gradle/Maven/npm/pytest)"
            )
            results["next_steps"].append("Please run tests manually to verify changes")

        # ========================================
        # GENERATE CONFIDENCE REPORT
        # ========================================
        if results["confidence_score"] == 100:
            results["next_steps"] = [
                "✅ All tests passed! Changes are safe to commit.",
                "📊 Confidence: HIGH - No test failures detected",
                "🎯 Next: Review changes with 'git diff'",
                "✅ Commit: 'git add . && git commit -m \"Applied governance fixes\"'",
            ]
        elif results["confidence_score"] >= 50:
            results["next_steps"] = [
                "⚠️ Tests could not be fully validated",
                "📊 Confidence: MEDIUM - Manual verification recommended",
                "🔍 Review: Check modified files for correctness",
                "🧪 Test: Run tests manually to verify",
            ]
        else:
            results["next_steps"] = [
                "❌ Test failures detected!",
                "📊 Confidence: LOW - Do not commit yet",
                f"🔍 Review: {len(results['failures'])} test failures found",
                "🔧 Fix: Address test failures before committing",
                "💡 Tip: Review changes with 'git diff' and fix failing tests",
            ]

        return results

    except Exception as e:
        return {
            "error": f"❌ Validation failed: {str(e)}",
            "confidence_score": 0,
            "summary": "Unable to run tests",
        }


if __name__ == "__main__":
    # Run MCP server with stdio transport
    mcp.run(transport="stdio")
