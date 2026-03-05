"""
Review Gate - Manages human approval workflow

Handles interactive review of proposed fixes with approval/rejection tracking.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
import json

from .proposer import ProposedFix
from .diff_generator import FileDiff


class ReviewDecision(Enum):
    """Review decision for a fix"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"


@dataclass
class ReviewComment:
    """Comment on a proposed fix"""

    fix_id: str
    comment: str
    timestamp: str


@dataclass
class ReviewState:
    """Tracks review state for all fixes"""

    fixes: List[ProposedFix]
    decisions: Dict[str, ReviewDecision] = field(default_factory=dict)
    comments: List[ReviewComment] = field(default_factory=list)

    def __post_init__(self):
        # Initialize all fixes as pending
        for fix in self.fixes:
            if fix.fix_id not in self.decisions:
                self.decisions[fix.fix_id] = ReviewDecision.PENDING

    @property
    def approved_fixes(self) -> List[ProposedFix]:
        """Get all approved fixes"""
        return [
            fix
            for fix in self.fixes
            if self.decisions.get(fix.fix_id) == ReviewDecision.APPROVED
        ]

    @property
    def rejected_fixes(self) -> List[ProposedFix]:
        """Get all rejected fixes"""
        return [
            fix
            for fix in self.fixes
            if self.decisions.get(fix.fix_id) == ReviewDecision.REJECTED
        ]

    @property
    def pending_fixes(self) -> List[ProposedFix]:
        """Get all pending fixes"""
        return [
            fix
            for fix in self.fixes
            if self.decisions.get(fix.fix_id) == ReviewDecision.PENDING
        ]

    def is_complete(self) -> bool:
        """Check if all fixes have been reviewed"""
        return all(
            decision != ReviewDecision.PENDING for decision in self.decisions.values()
        )

    def get_summary(self) -> Dict[str, int]:
        """Get review summary"""
        return {
            "total": len(self.fixes),
            "approved": len(self.approved_fixes),
            "rejected": len(self.rejected_fixes),
            "pending": len(self.pending_fixes),
        }


class ReviewGate:
    """Manages the review workflow for proposed fixes"""

    def __init__(self):
        self.review_state: Optional[ReviewState] = None

    def start_review(self, fixes: List[ProposedFix]) -> ReviewState:
        """Start a new review session"""
        self.review_state = ReviewState(fixes=fixes)
        return self.review_state

    def approve_fix(self, fix_id: str):
        """Approve a specific fix"""
        if self.review_state and fix_id in self.review_state.decisions:
            self.review_state.decisions[fix_id] = ReviewDecision.APPROVED

    def reject_fix(self, fix_id: str):
        """Reject a specific fix"""
        if self.review_state and fix_id in self.review_state.decisions:
            self.review_state.decisions[fix_id] = ReviewDecision.REJECTED

    def skip_fix(self, fix_id: str):
        """Skip a specific fix"""
        if self.review_state and fix_id in self.review_state.decisions:
            self.review_state.decisions[fix_id] = ReviewDecision.SKIPPED

    def add_comment(self, fix_id: str, comment: str):
        """Add a comment to a fix"""
        if self.review_state:
            from datetime import datetime

            self.review_state.comments.append(
                ReviewComment(
                    fix_id=fix_id, comment=comment, timestamp=datetime.now().isoformat()
                )
            )

    def approve_all(self):
        """Approve all pending fixes"""
        if self.review_state:
            for fix_id in self.review_state.decisions:
                if self.review_state.decisions[fix_id] == ReviewDecision.PENDING:
                    self.review_state.decisions[fix_id] = ReviewDecision.APPROVED

    def approve_safe_only(self):
        """Approve only safe-to-auto-apply fixes"""
        if self.review_state:
            for fix in self.review_state.fixes:
                if fix.is_safe_to_auto_apply:
                    self.review_state.decisions[fix.fix_id] = ReviewDecision.APPROVED

    def reject_all(self):
        """Reject all pending fixes"""
        if self.review_state:
            for fix_id in self.review_state.decisions:
                if self.review_state.decisions[fix_id] == ReviewDecision.PENDING:
                    self.review_state.decisions[fix_id] = ReviewDecision.REJECTED

    def interactive_review(self, diffs: List[FileDiff]) -> ReviewState:
        """
        Conduct an interactive CLI review session

        Args:
            diffs: List of FileDiff objects to review

        Returns:
            ReviewState with user decisions
        """

        if not self.review_state:
            raise ValueError("No review session started. Call start_review() first.")

        print("\n" + "=" * 80)
        print("GOVERNANCE FIX REVIEW")
        print("=" * 80)
        print(f"Total fixes to review: {len(diffs)}")
        print("\nCommands:")
        print("  [A]pprove  - Approve this fix")
        print("  [R]eject   - Reject this fix")
        print("  [S]kip     - Skip this fix for now")
        print("  [C]omment  - Add a comment")
        print("  [Q]uit     - Quit review (remaining fixes marked as pending)")
        print("  [AA]       - Approve all remaining")
        print("  [RA]       - Reject all remaining")
        print("=" * 80 + "\n")

        for i, diff in enumerate(diffs, 1):
            # Find corresponding fix
            fix = next(
                (f for f in self.review_state.fixes if f.file_path == diff.file_path),
                None,
            )

            if not fix:
                continue

            # Skip if already decided
            if self.review_state.decisions[fix.fix_id] != ReviewDecision.PENDING:
                continue

            # Display diff
            print(f"\n[{i}/{len(diffs)}] {diff.file_path}")
            print(str(diff))

            # Get user input
            while True:
                choice = input("\nDecision [A/R/S/C/Q/AA/RA]: ").strip().upper()

                if choice == "A":
                    self.approve_fix(fix.fix_id)
                    print("✅ Approved")
                    break
                elif choice == "R":
                    self.reject_fix(fix.fix_id)
                    print("❌ Rejected")
                    break
                elif choice == "S":
                    self.skip_fix(fix.fix_id)
                    print("⏭️  Skipped")
                    break
                elif choice == "C":
                    comment = input("Enter comment: ").strip()
                    if comment:
                        self.add_comment(fix.fix_id, comment)
                        print("💬 Comment added")
                    continue
                elif choice == "Q":
                    print("\n⏸️  Review paused. Remaining fixes marked as pending.")
                    return self.review_state
                elif choice == "AA":
                    self.approve_all()
                    print("✅ All remaining fixes approved")
                    return self.review_state
                elif choice == "RA":
                    self.reject_all()
                    print("❌ All remaining fixes rejected")
                    return self.review_state
                else:
                    print("Invalid choice. Please enter A, R, S, C, Q, AA, or RA.")

        # Review complete
        print("\n" + "=" * 80)
        print("REVIEW COMPLETE")
        print("=" * 80)
        summary = self.review_state.get_summary()
        print(f"Approved: {summary['approved']}")
        print(f"Rejected: {summary['rejected']}")
        print(f"Pending:  {summary['pending']}")
        print("=" * 80 + "\n")

        return self.review_state

    def save_review_state(self, output_path: str):
        """Save review state to a JSON file"""
        if not self.review_state:
            return

        data = {
            "decisions": {
                fix_id: decision.value
                for fix_id, decision in self.review_state.decisions.items()
            },
            "comments": [
                {"fix_id": c.fix_id, "comment": c.comment, "timestamp": c.timestamp}
                for c in self.review_state.comments
            ],
            "summary": self.review_state.get_summary(),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_review_state(self, input_path: str, fixes: List[ProposedFix]):
        """Load review state from a JSON file"""

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.review_state = ReviewState(fixes=fixes)

        # Load decisions
        for fix_id, decision_str in data.get("decisions", {}).items():
            self.review_state.decisions[fix_id] = ReviewDecision(decision_str)

        # Load comments
        for comment_data in data.get("comments", []):
            self.review_state.comments.append(ReviewComment(**comment_data))

    def export_review_report(self, output_path: str):
        """Export a detailed review report"""
        if not self.review_state:
            return

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Governance Fix Review Report\n\n")

            # Summary
            summary = self.review_state.get_summary()
            f.write("## Summary\n\n")
            f.write(f"- **Total Fixes**: {summary['total']}\n")
            f.write(f"- **Approved**: {summary['approved']}\n")
            f.write(f"- **Rejected**: {summary['rejected']}\n")
            f.write(f"- **Pending**: {summary['pending']}\n\n")

            # Approved fixes
            if self.review_state.approved_fixes:
                f.write("## Approved Fixes\n\n")
                for fix in self.review_state.approved_fixes:
                    f.write(f"- `{fix.file_path}` - {fix.rule_id}\n")
                f.write("\n")

            # Rejected fixes
            if self.review_state.rejected_fixes:
                f.write("## Rejected Fixes\n\n")
                for fix in self.review_state.rejected_fixes:
                    f.write(f"- `{fix.file_path}` - {fix.rule_id}\n")
                f.write("\n")

            # Comments
            if self.review_state.comments:
                f.write("## Comments\n\n")
                for comment in self.review_state.comments:
                    fix = next(
                        (
                            f
                            for f in self.review_state.fixes
                            if f.fix_id == comment.fix_id
                        ),
                        None,
                    )
                    if fix:
                        f.write(f"### {fix.file_path}\n\n")
                        f.write(f"**Time**: {comment.timestamp}  \n")
                        f.write(f"**Comment**: {comment.comment}\n\n")
