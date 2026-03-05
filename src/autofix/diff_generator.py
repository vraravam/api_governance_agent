"""
Diff Generator - Creates unified diffs with explanations

Generates before/after diffs for proposed fixes with detailed explanations.
"""

import difflib
from typing import List
from dataclasses import dataclass
from pathlib import Path

from .proposer import ProposedFix


@dataclass
class FileDiff:
    """Represents a diff for a single file"""

    file_path: str
    unified_diff: str
    additions: int
    deletions: int
    explanation: str
    rule_id: str
    severity: str = "warning"

    def __str__(self) -> str:
        """Format diff for display"""
        output = []
        output.append(f"\n{'=' * 80}")
        output.append(f"File: {self.file_path}")
        output.append(f"Rule: {self.rule_id}")
        output.append(f"Severity: {self.severity}")
        output.append(f"Changes: +{self.additions} -{self.deletions}")
        output.append(f"{'=' * 80}\n")
        output.append(self.unified_diff)
        output.append(f"\n{'-' * 80}")
        output.append("Explanation:")
        output.append(f"{'-' * 80}")
        output.append(self.explanation)
        output.append(f"{'=' * 80}\n")
        return "\n".join(output)


class DiffGenerator:
    """Generates unified diffs for proposed fixes"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def generate_diff(self, fix: ProposedFix) -> FileDiff:
        """
        Generate a unified diff for a proposed fix

        Args:
            fix: ProposedFix object

        Returns:
            FileDiff object with unified diff and metadata
        """

        # Split content into lines
        original_lines = fix.original_content.splitlines(keepends=True)
        proposed_lines = fix.proposed_content.splitlines(keepends=True)

        # Generate unified diff
        diff_lines = list(
            difflib.unified_diff(
                original_lines,
                proposed_lines,
                fromfile=f"a/{fix.file_path}",
                tofile=f"b/{fix.file_path}",
                lineterm="",
            )
        )

        # Count additions and deletions
        additions = sum(
            1
            for line in diff_lines
            if line.startswith("+") and not line.startswith("+++")
        )
        deletions = sum(
            1
            for line in diff_lines
            if line.startswith("-") and not line.startswith("---")
        )

        # Format diff
        unified_diff = "\n".join(diff_lines) if diff_lines else "No changes"

        # Build explanation
        explanation = self._build_explanation(fix)

        return FileDiff(
            file_path=fix.file_path,
            unified_diff=unified_diff,
            additions=additions,
            deletions=deletions,
            explanation=explanation,
            rule_id=fix.rule_id,
            severity=self._get_severity(fix),
        )

    def generate_all_diffs(self, fixes: List[ProposedFix]) -> List[FileDiff]:
        """Generate diffs for all proposed fixes"""
        return [self.generate_diff(fix) for fix in fixes]

    def generate_summary(self, diffs: List[FileDiff]) -> str:
        """Generate a summary of all diffs"""

        if not diffs:
            return "No fixes proposed."

        total_files = len(diffs)
        total_additions = sum(d.additions for d in diffs)
        total_deletions = sum(d.deletions for d in diffs)

        # Group by severity
        critical = [d for d in diffs if d.severity == "critical"]
        warnings = [d for d in diffs if d.severity == "warning"]
        info = [d for d in diffs if d.severity == "info"]

        summary = []
        summary.append("\n" + "=" * 80)
        summary.append("FIX PROPOSAL SUMMARY")
        summary.append("=" * 80)
        summary.append(f"Total Files: {total_files}")
        summary.append(f"Total Changes: +{total_additions} -{total_deletions}")
        summary.append("")
        summary.append("By Severity:")
        summary.append(f"  Critical: {len(critical)}")
        summary.append(f"  Warning:  {len(warnings)}")
        summary.append(f"  Info:     {len(info)}")
        summary.append("=" * 80 + "\n")

        return "\n".join(summary)

    def _build_explanation(self, fix: ProposedFix) -> str:
        """Build detailed explanation for a fix"""

        explanation = []

        # Add strategy explanation
        explanation.append(fix.explanation)
        explanation.append("")

        # Add import changes if any
        if fix.requires_imports:
            explanation.append("**Imports Added:**")
            for imp in fix.requires_imports:
                explanation.append(f"  - {imp}")
            explanation.append("")

        if fix.removes_imports:
            explanation.append("**Imports Removed:**")
            for imp in fix.removes_imports:
                explanation.append(f"  - {imp}")
            explanation.append("")

        # Add complexity note
        complexity = fix.complexity_level
        if complexity == "simple":
            explanation.append("**Complexity:** Simple (single-line change)")
        elif complexity == "moderate":
            explanation.append("**Complexity:** Moderate (multi-line, single file)")
        else:
            explanation.append("**Complexity:** Complex (multi-file or structural)")

        explanation.append("")

        # Add safety note
        if fix.is_safe_to_auto_apply:
            explanation.append(
                "✅ **Safe to auto-apply:** This fix can be applied automatically."
            )
        else:
            explanation.append(
                "⚠️  **Review required:** Please review this fix before applying."
            )

        return "\n".join(explanation)

    def _get_severity(self, fix: ProposedFix) -> str:
        """Determine severity from rule ID"""

        # Map rule categories to severity
        if fix.rule_id.startswith("security-"):
            return "critical"
        elif fix.rule_id.startswith("dependency-"):
            return "critical"
        elif fix.rule_id.startswith("architecture-"):
            return "critical"
        elif fix.rule_id.startswith("coding-"):
            return "warning"
        elif fix.rule_id.startswith("naming-"):
            return "warning"
        elif fix.rule_id.startswith("annotation-"):
            return "warning"
        else:
            return "info"

    def export_diff_to_file(self, diffs: List[FileDiff], output_path: str):
        """Export all diffs to a file"""

        with open(output_path, "w", encoding="utf-8") as f:
            # Write summary
            f.write(self.generate_summary(diffs))
            f.write("\n\n")

            # Write individual diffs
            for diff in diffs:
                f.write(str(diff))
                f.write("\n\n")

    def export_diff_to_markdown(self, diffs: List[FileDiff], output_path: str):
        """Export diffs to a markdown file"""

        with open(output_path, "w", encoding="utf-8") as f:
            # Write header
            f.write("# Governance Auto-Fix Proposal\n\n")

            # Write summary
            total_files = len(diffs)
            total_additions = sum(d.additions for d in diffs)
            total_deletions = sum(d.deletions for d in diffs)

            f.write("## Summary\n\n")
            f.write(f"- **Total Files**: {total_files}\n")
            f.write(f"- **Total Changes**: +{total_additions} -{total_deletions}\n\n")

            # Group by severity
            critical = [d for d in diffs if d.severity == "critical"]
            warnings = [d for d in diffs if d.severity == "warning"]
            info = [d for d in diffs if d.severity == "info"]

            f.write("### By Severity\n\n")
            f.write(f"- 🔴 **Critical**: {len(critical)}\n")
            f.write(f"- 🟡 **Warning**: {len(warnings)}\n")
            f.write(f"- 🔵 **Info**: {len(info)}\n\n")

            # Write individual diffs
            f.write("## Proposed Changes\n\n")

            for i, diff in enumerate(diffs, 1):
                severity_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(
                    diff.severity, "⚪"
                )

                f.write(f"### {i}. {severity_icon} {diff.file_path}\n\n")
                f.write(f"**Rule**: `{diff.rule_id}`  \n")
                f.write(f"**Changes**: +{diff.additions} -{diff.deletions}\n\n")

                f.write("#### Diff\n\n")
                f.write("```diff\n")
                f.write(diff.unified_diff)
                f.write("\n```\n\n")

                f.write("#### Explanation\n\n")
                f.write(diff.explanation)
                f.write("\n\n---\n\n")
