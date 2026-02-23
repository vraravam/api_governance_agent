"""
Auto-Fix Engine - Main orchestrator for the auto-fix workflow

Coordinates the entire fix proposal, review, and application process.
"""

from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass

from .proposer import FixProposer, ProposedFix
from .diff_generator import DiffGenerator, FileDiff
from .review_gate import ReviewGate, ReviewState
from .pr_creator import PRCreator, PullRequestInfo
from .vscode_integration import integrate_with_vscode
from .build_validator import BuildValidator, ValidationResult
from engines.llm_analyzer import LLMAnalyzer
from engines.copilot_analyzer import CopilotAnalyzer
from utils import FileUtils


@dataclass
class AutoFixResult:
    """Result of an auto-fix workflow"""

    fixes_proposed: int
    fixes_approved: int
    fixes_rejected: int
    fixes_applied: int
    branch_name: Optional[str] = None
    pr_info: Optional[PullRequestInfo] = None
    diff_preview_path: Optional[str] = None
    review_report_path: Optional[str] = None
    validation_result: Optional[ValidationResult] = None


class AutoFixEngine:
    """
    Main engine for the auto-fix workflow

    Orchestrates:
    1. Fix proposal generation
    2. Diff creation and preview
    3. Human review workflow
    4. Fix application
    5. PR creation
    """

    def __init__(
        self,
        project_path: str,
        llm_endpoint: str = "http://localhost:11434",
        use_copilot: bool = True,
    ):
        """
        Initialize auto-fix engine

        Args:
            project_path: Root path of the project
            llm_endpoint: LLM API endpoint (legacy fallback)
            use_copilot: Use GitHub Copilot for faster fixes (default: True)
        """
        self.project_path = Path(project_path)
        self.use_copilot = use_copilot

        # Initialize analyzer
        if use_copilot:
            try:
                analyzer = CopilotAnalyzer()
                print("✓ AutoFixEngine: Using GitHub Copilot (80-90% faster)")
            except Exception as e:
                print(f"⚠ Copilot unavailable: {e}")
                print("  Falling back to LLM analyzer")
                analyzer = LLMAnalyzer(api_endpoint=llm_endpoint)
                self.use_copilot = False
        else:
            analyzer = LLMAnalyzer(api_endpoint=llm_endpoint)
            print("⚠ AutoFixEngine: Using legacy LLM analyzer")

        # For backward compatibility, keep llm_analyzer reference
        self.llm_analyzer = analyzer if isinstance(analyzer, LLMAnalyzer) else None
        self.analyzer = analyzer

        # Initialize components
        self.proposer = FixProposer(
            str(self.project_path),
            llm_analyzer=self.llm_analyzer,
            use_copilot=use_copilot,
        )
        self.diff_generator = DiffGenerator(str(self.project_path))
        self.review_gate = ReviewGate()
        self.pr_creator = None  # Initialized only when needed
        self.build_validator = BuildValidator(str(self.project_path))
        self.last_pr_info: Optional[PullRequestInfo] = None

    def load_governance_report(self, report_path: str) -> List[Dict]:
        """
        Load violations from a governance report

        Args:
            report_path: Path to governance report JSON file

        Returns:
            List of violation dictionaries
        """

        data = FileUtils.read_json(report_path)

        # Handle different report formats
        if isinstance(data, list):
            # Direct list of violations
            return data
        elif isinstance(data, dict):
            # Structured report
            violations = []
            violations.extend(data.get("spectral_results", []))
            violations.extend(data.get("llm_results", []))
            violations.extend(data.get("violations", []))
            return violations
        else:
            raise ValueError("Invalid governance report format")

    async def propose_fixes(
        self, violations: List[Dict], output_dir: Optional[str] = None
    ) -> tuple[List[ProposedFix], List[FileDiff]]:
        """
        Generate fix proposals for violations

        Args:
            violations: List of violation dictionaries
            output_dir: Optional directory to save diff previews

        Returns:
            Tuple of (proposed_fixes, diffs)
        """

        # Sort violations: Code (Java) first, then Specs
        def prioritization_key(v):
            fpath = v.get("file", "") or v.get("source", "")
            if fpath.endswith(".java"):
                return 0
            if (
                fpath.endswith(".yaml")
                or fpath.endswith(".json")
                or fpath.endswith(".yml")
            ):
                return 1
            return 2

        sorted_violations = sorted(violations, key=prioritization_key)

        # Generate fix proposals
        fixes = await self.proposer.propose_fixes(sorted_violations)

        if not fixes:
            print("No fixable violations found.")
            return [], []

        # Generate diffs
        diffs = self.diff_generator.generate_all_diffs(fixes)

        # Save diff preview if output directory provided
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Save as text
            diff_txt = output_path / "fix-preview.txt"
            self.diff_generator.export_diff_to_file(diffs, str(diff_txt))

            # Save as markdown
            diff_md = output_path / "fix-preview.md"
            self.diff_generator.export_diff_to_markdown(diffs, str(diff_md))

            print(f"Diff preview saved to: {diff_md}")

        return fixes, diffs

    def review_fixes(
        self,
        fixes: List[ProposedFix],
        diffs: List[FileDiff],
        interactive: bool = True,
        auto_approve_safe: bool = False,
    ) -> ReviewState:
        """
        Conduct review of proposed fixes

        Args:
            fixes: List of ProposedFix objects
            diffs: List of FileDiff objects
            interactive: Whether to use interactive CLI review
            auto_approve_safe: Whether to auto-approve safe fixes

        Returns:
            ReviewState with decisions
        """

        # Start review session
        review_state = self.review_gate.start_review(fixes)

        # Auto-approve safe fixes if requested
        if auto_approve_safe:
            self.review_gate.approve_safe_only()
            print(f"Auto-approved {len(review_state.approved_fixes)} safe fixes")

        # Interactive review if requested
        if interactive and review_state.pending_fixes:
            review_state = self.review_gate.interactive_review(diffs)

        return review_state

    def apply_fixes(
        self,
        review_state: ReviewState,
        create_branch: bool = True,
        branch_name: Optional[str] = None,
        commit_strategy: str = "by-rule",  # "by-rule" or "single"
        validate_fixes: bool = True,  # NEW: Enable build + scan validation
        category: Optional[str] = None,  # NEW: Category being fixed (for validation)
    ) -> AutoFixResult:
        """
        Apply approved fixes and optionally create PR

        Args:
            review_state: ReviewState with approved fixes
            create_branch: Whether to create a new git branch
            branch_name: Optional custom branch name
            commit_strategy: "by-rule" for separate commits, "single" for one commit
            validate_fixes: Whether to run build + re-scan to validate fixes
            category: Category being fixed (needed for validation)

        Returns:
            AutoFixResult with application details
        """

        approved_fixes = review_state.approved_fixes

        if not approved_fixes:
            print("No approved fixes to apply.")
            return AutoFixResult(
                fixes_proposed=len(review_state.fixes),
                fixes_approved=0,
                fixes_rejected=len(review_state.rejected_fixes),
                fixes_applied=0,
            )

        # Initialize PR creator
        try:
            self.pr_creator = PRCreator(str(self.project_path))
        except ValueError as e:
            print(f"Warning: {e}")
            print("Fixes will be applied without git operations.")
            self.pr_creator = None

        # Create branch if requested and possible
        actual_branch_name = None
        if create_branch and self.pr_creator:
            try:
                actual_branch_name = self.pr_creator.create_branch(branch_name)
                print(f"Created branch: {actual_branch_name}")
            except Exception as e:
                print(f"Failed to create branch: {e}")
                print("Continuing without branch creation.")

        # Apply fixes and create commits
        commits = []
        modified_files = []  # Track all modified files for VS Code integration

        if self.pr_creator:
            try:
                if commit_strategy == "by-rule":
                    commits = self.pr_creator.create_commits_by_rule(review_state)
                    print(f"Created {len(commits)} commits (one per rule)")
                else:
                    commit = self.pr_creator.create_single_commit(review_state)
                    commits = [commit]
                    print("Created single commit for all fixes")

                # Collect modified file paths
                for fix in approved_fixes:
                    modified_files.append(fix.file_path)
                    for add_path, _ in fix.additional_files:
                        modified_files.append(add_path)

            except Exception as e:
                print(f"Failed to create commits: {e}")
                # Still apply fixes even if commits fail
                self.pr_creator.apply_fixes(approved_fixes)
                for fix in approved_fixes:
                    modified_files.append(fix.file_path)
                    for add_path, _ in fix.additional_files:
                        modified_files.append(add_path)
        else:
            # Apply fixes without git operations
            for fix in approved_fixes:
                file_path = self.project_path / fix.file_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fix.proposed_content)
                modified_files.append(fix.file_path)

                # Apply additional files (e.g. corresponding Java code)
                for add_path, add_content in fix.additional_files:
                    add_full_path = self.project_path / add_path
                    add_full_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(add_full_path, "w", encoding="utf-8") as f:
                        f.write(add_content)
                    modified_files.append(add_path)

        # Integrate with VS Code - show modified files in UI
        if modified_files:
            print("\n🎨 Preparing files for review in VS Code...")
            try:
                integrate_with_vscode(
                    modified_files=modified_files,
                    project_path=str(self.project_path),
                    stage_in_git=(not create_branch),  # Stage if not creating branch
                )
            except Exception as e:
                print(f"   ⚠️  Could not integrate with VS Code: {e}")
                print(f"   ℹ️  Modified files: {', '.join(modified_files)}")

        # Generate PR info
        pr_info = None
        if self.pr_creator and actual_branch_name and commits:
            pr_info = self.pr_creator.create_pull_request_info(
                actual_branch_name, commits, review_state
            )

        self.last_pr_info = pr_info

        # Step 5: Validate fixes (NEW)
        validation_result = None
        if validate_fixes and category:
            print("\n" + "=" * 80)
            print("VALIDATING FIXES")
            print("=" * 80)

            # Get violations before fix (from review state)
            violations_before = []
            for fix in approved_fixes:
                violations_before.append(fix.violation)

            # Run build + scan validation
            validation_result = self.build_validator.validate_fixes(
                category=category,
                violations_before=violations_before,
                clean_build=True,
                output_dir=str(self.project_path / "build" / "governance"),
            )

            # Save validation report
            self.build_validator.save_validation_report(
                validation_result,
                output_path=str(self.project_path / "validation-report.json"),
            )

        return AutoFixResult(
            fixes_proposed=len(review_state.fixes),
            fixes_approved=len(approved_fixes),
            fixes_rejected=len(review_state.rejected_fixes),
            fixes_applied=len(approved_fixes),
            branch_name=actual_branch_name,
            pr_info=pr_info,
            validation_result=validation_result,
        )

    async def run_full_workflow(
        self,
        report_path: str,
        interactive: bool = True,
        auto_approve_safe: bool = False,
        create_pr: bool = True,
        output_dir: Optional[str] = None,
    ) -> AutoFixResult:
        """
        Run the complete auto-fix workflow

        Args:
            report_path: Path to governance report JSON
            interactive: Whether to use interactive review
            auto_approve_safe: Whether to auto-approve safe fixes
            create_pr: Whether to create PR branch and commits
            output_dir: Optional directory for output files

        Returns:
            AutoFixResult with workflow details
        """

        print("\n" + "=" * 80)
        print("GOVERNANCE AUTO-FIX WORKFLOW")
        print("=" * 80)

        # Step 1: Load violations
        print("\n[1/5] Loading governance report...")
        violations = self.load_governance_report(report_path)
        print(f"Loaded {len(violations)} violations")

        # Step 2: Propose fixes
        print("\n[2/5] Generating fix proposals...")
        fixes, diffs = await self.propose_fixes(violations, output_dir)
        print(f"Generated {len(fixes)} fix proposals")

        if not fixes:
            return AutoFixResult(
                fixes_proposed=0, fixes_approved=0, fixes_rejected=0, fixes_applied=0
            )

        # Print summary
        print("\n" + self.diff_generator.generate_summary(diffs))

        # Step 3: Review fixes
        print("\n[3/5] Reviewing fixes...")
        review_state = self.review_fixes(fixes, diffs, interactive, auto_approve_safe)

        summary = review_state.get_summary()
        print("\nReview complete:")
        print(f"  Approved: {summary['approved']}")
        print(f"  Rejected: {summary['rejected']}")
        print(f"  Pending:  {summary['pending']}")

        # Save review state
        if output_dir:
            review_file = Path(output_dir) / "review-state.json"
            self.review_gate.save_review_state(str(review_file))

            review_report = Path(output_dir) / "review-report.md"
            self.review_gate.export_review_report(str(review_report))
            print(f"\nReview state saved to: {review_file}")

        # Step 4: Apply fixes
        if summary["approved"] > 0:
            print("\n[4/5] Applying approved fixes...")
            result = self.apply_fixes(
                review_state,
                create_branch=False,  # Always disable PR/branch creation
                commit_strategy="by-rule",
            )
            print(f"Applied {result.fixes_applied} fixes")

            # Step 5: Skip PR creation
            print("\n[5/5] PR creation disabled - changes applied directly")
        else:
            print("\n[4/5] No approved fixes to apply")
            result = AutoFixResult(
                fixes_proposed=len(fixes),
                fixes_approved=0,
                fixes_rejected=summary["rejected"],
                fixes_applied=0,
            )

        print("\n" + "=" * 80)
        print("WORKFLOW COMPLETE")
        print("=" * 80 + "\n")

        return result
