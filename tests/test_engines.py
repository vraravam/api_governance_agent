"""
Unit tests for engine modules using pytest.
Tests SpectralRunner, ArchUnitEngine, and analyzers.
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from engines.spectral_runner import SpectralRunner
from utils import ProcessResult


class TestSpectralRunner:
    """Test SpectralRunner functionality"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up and tear down test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.ruleset = Path(self.temp_dir) / "ruleset.yaml"
        self.ruleset.write_text("rules: {}")
        self.runner = SpectralRunner(str(self.ruleset))
        yield
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init(self):
        """Test SpectralRunner initialization"""
        assert self.runner.ruleset_path == str(self.ruleset)

    def test_structure_violations_empty(self):
        """Test structuring empty violations list"""
        violations = self.runner._structure_violations([])
        assert len(violations) == 0

    def test_structure_violations_single(self):
        """Test structuring single violation"""
        raw = {
            "code": "test-rule",
            "message": "Test message",
            "severity": 1,
            "path": ["paths", "/users"],
            "range": {"start": {"line": 10}},
            "source": "test.yaml",
        }

        violations = self.runner._structure_violations([raw])
        assert len(violations) == 1
        assert violations[0]["rule"] == "test-rule"
        assert violations[0]["engine"] == "spectral"

    @patch("utils.ProcessUtils.run_command")
    def test_run_spectral_no_violations(self, mock_run):
        """Test running Spectral with no violations"""
        # Mock successful Spectral run with no violations
        mock_result = ProcessResult(0, "", "")
        mock_run.return_value = mock_result

        # Create temp spec file
        spec = Path(self.temp_dir) / "spec.yaml"
        spec.write_text("openapi: 3.0.0\n")

        # Create empty output file
        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_file = MagicMock()
            mock_file.name = str(Path(self.temp_dir) / "output.json")
            mock_temp.return_value.__enter__.return_value = mock_file

            # Write empty JSON array
            with open(mock_file.name, "w") as f:
                f.write("[]")

            violations = self.runner.run_spectral(spec)
            assert len(violations) == 0

    @patch("utils.ProcessUtils.check_binary_exists")
    def test_run_spectral_binary_not_found(self, mock_check):
        """Test running Spectral when binary not found"""
        mock_check.return_value = False

        spec = Path(self.temp_dir) / "spec.yaml"
        spec.write_text("openapi: 3.0.0\n")

        # Should handle gracefully
        violations = self.runner.run_spectral(spec)
        assert len(violations) == 0


class TestArchUnitEngine:
    """Test ArchUnitEngine functionality"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up and tear down test environment"""
        self.temp_dir = tempfile.mkdtemp()
        yield
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init(self):
        """Test ArchUnitEngine initialization"""
        from engines.arch_unit_engine import ArchUnitEngine

        engine = ArchUnitEngine(self.temp_dir)
        assert str(engine.project_path) == str(Path(self.temp_dir).resolve())

    def test_get_classpath(self):
        """Test classpath construction"""
        from engines.arch_unit_engine import ArchUnitEngine

        engine = ArchUnitEngine(self.temp_dir)

        # Ensure lib dir exists
        engine.lib_dir.mkdir(parents=True, exist_ok=True)

        classpath = engine._get_classpath()
        assert isinstance(classpath, str)
        assert str(engine.resources_dir) in classpath
