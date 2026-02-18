"""
Unit tests for autofix modules using pytest.
Tests FixProposer, DiffGenerator, and AutoFixEngine.
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from autofix.fix_strategies import FixStrategy, FixComplexity, FixSafety
from autofix.diff_generator import DiffGenerator, FileDiff


class TestFixStrategies:
    """Test fix strategy dataclasses"""

    def test_fix_strategy_creation(self):
        """Test creating a FixStrategy"""
        strategy = FixStrategy(
            rule_id="test-rule",
            complexity=FixComplexity.SIMPLE,
            safety=FixSafety.SAFE,
            fix_function="test_fix_strategy_creation",
            description="Test strategy",
            explanation_template=(),
        )

        assert strategy.rule_id == "test-rule"
        assert strategy.complexity == FixComplexity.SIMPLE
        assert strategy.safety == FixSafety.SAFE

    def test_fix_complexity_values(self):
        """Test FixComplexity enum values"""
        assert FixComplexity.SIMPLE.value == "simple"
        assert FixComplexity.MODERATE.value == "moderate"
        assert FixComplexity.COMPLEX.value == "complex"

    def test_fix_safety_values(self):
        """Test FixSafety enum values"""
        assert FixSafety.SAFE.value == "safe"
        assert FixSafety.REVIEW_REQUIRED.value == "review_required"
        # assert FixSafety.RISKY.value == "risky"


class TestDiffGenerator:
    """Test DiffGenerator functionality"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up and tear down test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = DiffGenerator(self.temp_dir)
        yield
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init(self):
        """Test DiffGenerator initialization"""
        assert str(self.generator.project_path) == self.temp_dir

    def test_generate_summary_empty(self):
        """Test generating summary for empty diffs"""
        summary = self.generator.generate_summary([])
        assert "No fixes proposed" in summary

    def test_generate_summary_with_diffs(self):
        """Test generating summary with diffs"""
        diff1 = FileDiff(
            file_path="test.java",
            unified_diff="diff content",
            additions=5,
            deletions=3,
            explanation="Test explanation",
            rule_id="test-rule",
        )

        diff2 = FileDiff(
            file_path="test2.java",
            unified_diff="diff content 2",
            additions=2,
            deletions=1,
            explanation="Test explanation 2",
            rule_id="test-rule-2",
        )

        summary = self.generator.generate_summary([diff1, diff2])
        assert "Total Files: 2" in summary
        assert "+7" in summary  # Total additions
        assert "-4" in summary  # Total deletions

    def test_file_diff_str(self):
        """Test FileDiff string representation"""
        diff = FileDiff(
            file_path="test.java",
            unified_diff="@@ -1,3 +1,3 @@\n-old line\n+new line",
            additions=1,
            deletions=1,
            explanation="Changed line",
            rule_id="test-rule",
        )

        str_repr = str(diff)
        assert "test.java" in str_repr
        assert "test-rule" in str_repr
        assert "+1" in str_repr
        assert "-1" in str_repr


class TestProposedFix:
    """Test ProposedFix dataclass"""

    def test_proposed_fix_creation(self):
        """Test creating a ProposedFix"""
        from autofix.proposer import ProposedFix

        strategy = FixStrategy(
            rule_id="test-rule",
            complexity=FixComplexity.SIMPLE,
            safety=FixSafety.SAFE,
            fix_function="test_fix_strategy_creation",
            description="Test",
            explanation_template=(),
        )

        fix = ProposedFix(
            fix_id="fix-1",
            rule_id="rule-1",
            file_path="test.java",
            line_number=10,
            original_content="old code",
            proposed_content="new code",
            explanation="Fixed issue",
            strategy=strategy,
        )

        assert fix.fix_id == "fix-1"
        assert fix.rule_id == "rule-1"
        assert fix.original_content != fix.proposed_content

    def test_is_safe_to_auto_apply(self):
        """Test auto-apply safety check"""
        from autofix.proposer import ProposedFix

        strategy = FixStrategy(
            rule_id="test-rule",
            complexity=FixComplexity.SIMPLE,
            safety=FixSafety.SAFE,
            fix_function="test_fix_strategy_creation",
            description="Test",
            explanation_template=(),
        )

        # Fix with content change
        fix = ProposedFix(
            fix_id="fix-1",
            rule_id="rule-1",
            file_path="test.java",
            line_number=10,
            original_content="old",
            proposed_content="new",
            explanation="Fixed",
            strategy=strategy,
        )

        assert fix.is_safe_to_auto_apply

    def test_complexity_level(self):
        """Test complexity level property"""
        from autofix.proposer import ProposedFix

        strategy = FixStrategy(
            rule_id="test-rule",
            complexity=FixComplexity.MODERATE,
            safety=FixSafety.SAFE,
            fix_function="test_fix_strategy_creation",
            description="Test",
            explanation_template=(),
        )

        fix = ProposedFix(
            fix_id="fix-1",
            rule_id="rule-1",
            file_path="test.java",
            line_number=10,
            original_content="old",
            proposed_content="new",
            explanation="Fixed",
            strategy=strategy,
        )

        assert fix.complexity_level == "moderate"
