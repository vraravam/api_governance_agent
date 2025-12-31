"""
PR Creator - Handles Git operations and pull request creation

Creates branches, commits changes, and generates pull requests for approved fixes.
"""

import subprocess
from typing import List, Optional, Dict
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from .proposer import ProposedFix
from .review_gate import ReviewState


@dataclass
class CommitInfo:
    """Information about a commit"""

    hash: str
    message: str
    files_changed: List[str]


@dataclass
class PullRequestInfo:
    """Information about a pull request"""

    branch_name: str
    commits: List[CommitInfo]
    title: str
    description: str
    files_changed: int
    additions: int
    deletions: int


class PRCreator:
    """Creates pull requests for approved governance fixes"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self._verify_git_repo()

    def _verify_git_repo(self):
        """Verify that the project is a git repository"""
        git_dir = self.project_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"Not a git repository: {self.project_path}")

    def _run_git_command(
        self, args: List[str], check=True
    ) -> subprocess.CompletedProcess:
        """Run a git command"""
        cmd = ["git"] + args
        return subprocess.run(
            cmd, cwd=self.project_path, capture_output=True, text=True, check=check
        )

    def create_branch(self, branch_name: Optional[str] = None) -> str:
        """
        Create a new git branch for fixes

        Args:
            branch_name: Optional custom branch name

        Returns:
            Name of the created branch
        """

        if not branch_name:
            # Generate branch name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_name = f"governance/auto-fix-{timestamp}"

        # Create and checkout branch
        self._run_git_command(["checkout", "-b", branch_name])

        return branch_name

    def apply_fixes(self, fixes: List[ProposedFix]) -> List[str]:
        """
        Apply approved fixes to files

        Args:
            fixes: List of ProposedFix objects to apply

        Returns:
            List of modified file paths
        """

        modified_files = []

        for fix in fixes:
            file_path = self.project_path / fix.file_path

            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write proposed content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fix.proposed_content)

            modified_files.append(fix.file_path)

        return modified_files

    def create_commit(
        self,
        files: List[str],
        rule_id: str,
        description: str,
        severity: str = "warning",
    ) -> CommitInfo:
        """
        Create a git commit for fixes

        Args:
            files: List of file paths to commit
            rule_id: Rule ID being fixed
            description: Brief description of the fix
            severity: Severity level

        Returns:
            CommitInfo object
        """

        # Stage files
        for file_path in files:
            self._run_git_command(["add", file_path])

        # Generate commit message
        commit_message = self._generate_commit_message(
            rule_id, description, files, severity
        )

        # Create commit
        self._run_git_command(["commit", "-m", commit_message])

        # Get commit hash
        result = self._run_git_command(["rev-parse", "HEAD"])
        commit_hash = result.stdout.strip()

        return CommitInfo(hash=commit_hash, message=commit_message, files_changed=files)

    def create_commits_by_rule(self, review_state: ReviewState) -> List[CommitInfo]:
        """
        Create separate commits for each rule type

        Args:
            review_state: ReviewState with approved fixes

        Returns:
            List of CommitInfo objects
        """

        approved_fixes = review_state.approved_fixes

        # Group fixes by rule_id
        fixes_by_rule: Dict[str, List[ProposedFix]] = {}
        for fix in approved_fixes:
            if fix.rule_id not in fixes_by_rule:
                fixes_by_rule[fix.rule_id] = []
            fixes_by_rule[fix.rule_id].append(fix)

        commits = []

        # Create a commit for each rule
        for rule_id, fixes in fixes_by_rule.items():
            # Apply fixes
            modified_files = self.apply_fixes(fixes)

            # Determine severity
            severity = self._determine_severity(rule_id)

            # Create commit
            description = f"Fix {len(fixes)} violation(s)"
            commit = self.create_commit(modified_files, rule_id, description, severity)
            commits.append(commit)

        return commits

    def create_single_commit(self, review_state: ReviewState) -> CommitInfo:
        """
        Create a single commit for all approved fixes

        Args:
            review_state: ReviewState with approved fixes

        Returns:
            CommitInfo object
        """

        approved_fixes = review_state.approved_fixes

        # Apply all fixes
        modified_files = self.apply_fixes(approved_fixes)

        # Count by severity
        critical = sum(
            1
            for f in approved_fixes
            if self._determine_severity(f.rule_id) == "critical"
        )
        warnings = sum(
            1
            for f in approved_fixes
            if self._determine_severity(f.rule_id) == "warning"
        )

        # Create commit
        description = f"Fix {critical} critical and {warnings} warning violations"
        commit = self.create_commit(
            modified_files, "governance-auto-fix", description, "mixed"
        )

        return commit

    def generate_pr_description(
        self,
        commits: List[CommitInfo],
        review_state: ReviewState,
        governance_report_path: Optional[str] = None,
    ) -> str:
        """
        Generate pull request description

        Args:
            commits: List of commits in the PR
            review_state: ReviewState with fix information
            governance_report_path: Optional path to governance report

        Returns:
            Formatted PR description
        """

        approved_fixes = review_state.approved_fixes

        # Count by severity
        critical = sum(
            1
            for f in approved_fixes
            if self._determine_severity(f.rule_id) == "critical"
        )
        warnings = sum(
            1
            for f in approved_fixes
            if self._determine_severity(f.rule_id) == "warning"
        )

        # Count files
        files_changed = len(set(f.file_path for f in approved_fixes))

        description = []
        description.append("## Governance Auto-Fix\n")
        description.append(
            "This PR addresses governance violations identified in the latest scan.\n"
        )

        description.append("### Summary\n")
        description.append(f"- **Critical Violations Fixed**: {critical}")
        description.append(f"- **Warnings Fixed**: {warnings}")
        description.append(f"- **Files Changed**: {files_changed}")
        description.append(f"- **Commits**: {len(commits)}\n")

        description.append("### Violations Addressed\n")
        description.append("| Rule ID | File | Description |")
        description.append("|---------|------|-------------|")

        for fix in approved_fixes:
            rule_id = fix.rule_id
            file_path = fix.file_path
            # Extract first line of explanation
            explanation = fix.explanation.split("\n")[0][:80]
            description.append(f"| `{rule_id}` | `{file_path}` | {explanation} |")

        description.append("\n### Review Notes\n")
        description.append(
            "All fixes have been reviewed and approved through the governance auto-fix workflow."
        )
        description.append(
            "Each fix is minimal and scoped to the specific rule violation.\n"
        )

        if review_state.comments:
            description.append("### Review Comments\n")
            for comment in review_state.comments:
                fix = next(
                    (f for f in approved_fixes if f.fix_id == comment.fix_id), None
                )
                if fix:
                    description.append(f"- **{fix.file_path}**: {comment.comment}")
            description.append("")

        if governance_report_path:
            description.append("### Governance Report\n")
            description.append(f"See attached: `{governance_report_path}`\n")

        description.append("### Testing\n")
        description.append("- [ ] All existing tests pass")
        description.append("- [ ] Manual verification completed")
        description.append("- [ ] No breaking changes introduced")

        return "\n".join(description)

    def create_pull_request_info(
        self,
        branch_name: str,
        commits: List[CommitInfo],
        review_state: ReviewState,
        governance_report_path: Optional[str] = None,
    ) -> PullRequestInfo:
        """
        Create pull request information

        Args:
            branch_name: Name of the branch
            commits: List of commits
            review_state: ReviewState with fix information
            governance_report_path: Optional path to governance report

        Returns:
            PullRequestInfo object
        """

        approved_fixes = review_state.approved_fixes

        # Generate title
        critical = sum(
            1
            for f in approved_fixes
            if self._determine_severity(f.rule_id) == "critical"
        )
        warnings = sum(
            1
            for f in approved_fixes
            if self._determine_severity(f.rule_id) == "warning"
        )
        title = f"fix(governance): Auto-fix {critical} critical and {warnings} warning violations"

        # Generate description
        description = self.generate_pr_description(
            commits, review_state, governance_report_path
        )

        # Count changes
        files_changed = len(set(f.file_path for f in approved_fixes))

        # Note: additions/deletions would require actual diff analysis
        # For now, we'll set placeholders
        additions = 0
        deletions = 0

        return PullRequestInfo(
            branch_name=branch_name,
            commits=commits,
            title=title,
            description=description,
            files_changed=files_changed,
            additions=additions,
            deletions=deletions,
        )

    def _generate_commit_message(
        self, rule_id: str, description: str, files: List[str], severity: str
    ) -> str:
        """Generate semantic commit message"""

        # Determine commit type
        if severity == "critical":
            commit_type = "fix"
        else:
            commit_type = "refactor"

        message = []
        message.append(f"{commit_type}(governance): [{rule_id}] {description}")
        message.append("")
        message.append(f"Fixes governance violation: {rule_id}")
        message.append(f"Severity: {severity}")
        message.append("")
        message.append("Changes:")
        for file_path in sorted(set(files)):
            message.append(f"- {file_path}")

        return "\n".join(message)

    def _determine_severity(self, rule_id: str) -> str:
        """Determine severity from rule ID"""
        if rule_id.startswith("security-"):
            return "critical"
        elif rule_id.startswith("dependency-"):
            return "critical"
        elif rule_id.startswith("architecture-"):
            return "critical"
        else:
            return "warning"

    def push_branch(self, branch_name: str, remote: str = "origin"):
        """Push branch to remote"""
        self._run_git_command(["push", "-u", remote, branch_name])

    def get_current_branch(self) -> str:
        """Get current branch name"""
        result = self._run_git_command(["branch", "--show-current"])
        return result.stdout.strip()

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes"""
        result = self._run_git_command(["status", "--porcelain"], check=False)
        return bool(result.stdout.strip())
