# Contributing to API Governance Agent

Thank you for your interest in contributing to the API Governance Agent! This guide will help you understand our development workflow, coding standards, and best practices.

---

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Organization](#code-organization)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Tools and Frameworks](#tools-and-frameworks)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Getting Started

### Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: For Spectral CLI (npm)
- **Java**: JDK 11+ (for ArchUnit tests)
- **Git**: For version control

### First Steps

1. **Fork and Clone**

   ```bash
   git clone <repo-url>
   cd <path-to-tool-project-root>
   ```

2. **Follow Setup Guide**
   - Read [SETUP_GUIDE.md](SETUP_GUIDE.md) for complete setup instructions
   - Install dependencies: `pip install -r requirements.txt`
   - Install Spectral: `npm install -g @stoplight/spectral-cli`

3. **Verify Installation**

   ```bash
   # Run tests to ensure everything works
   python -m pytest tests/

   # Check linting and autofix (Note: this will not report any unfixable errors)
   ruff check --fix-only -q src/

   # Check formatting
   black --check src/
   ```

---

## 🛠️ Development Setup

### Python Virtual Environment

**Always use a virtual environment:**

```bash
# Create virtual environment
python -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

### Required Dependencies

Install all dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

### Development Tools

The project uses these tools (all included in requirements.txt):

- **black** (≥23.12.0): Code formatting
- **ruff** (≥0.1.8): Linting and import checking
- **pytest** (≥7.4.3): Testing framework
- **pytest-json-report**: Test reporting
- **mypy** (recommended): Type checking

---

## 📁 Code Organization

### Project Structure

```
tmp_gov_agent/
├── src/                      # Main source code
│   ├── autofix/             # Auto-fix engine and strategies
│   ├── engines/             # Scanning engines (Spectral, ArchUnit, LLM)
│   ├── mcp_server/          # MCP server for IDE integration
│   ├── report/              # Report generation
│   ├── scanner/             # Governance scanning orchestration
│   ├── sync/                # Spec-controller sync validation
│   └── utils/               # Shared utilities
├── tests/                   # Test suite
│   ├── data/               # Test fixtures
│   └── test_*.py           # Test modules
├── scripts/                 # Utility scripts
├── rules/                   # Spectral ruleset and custom functions
└── resources/              # Java resources (ArchUnit runner)
```

### Module Responsibilities

- **autofix/**: Proposes and applies fixes for governance violations
- **engines/**: Different scanning engines (Spectral, ArchUnit, LLM)
- **mcp_server/**: FastMCP server exposing tools for IDE integration
- **report/**: Generates HTML, Markdown, and JSON reports
- **scanner/**: Orchestrates scanning across different engines
- **utils/**: Shared utility classes (FileUtils, ProcessUtils, etc.)

---

## 📝 Coding Standards

### Python Style Guide

We follow **PEP 8** with these specific conventions:

#### 1. **Formatting**

- **Line Length**: 200 characters max (see `.editorconfig`)
- **Indentation**: 2 spaces (not 4!) - see `.editorconfig`
- **Quotes**: Use double quotes `"` for strings
- **Trailing Commas**: Use in multi-line collections

**Use Black for automatic formatting:**

```bash
# Format all code
black src/ tests/ scripts/

# Check formatting without changes
black --check src/
```

#### 2. **Import Organization**

Imports must be organized in this order:

```python
# Standard library imports
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Third-party imports
import pytest
from pydantic import BaseModel

# Local imports
from utils import FileUtils, ProcessUtils
from scanner.project_detector import ProjectDetector
```

**Use ruff to check and fix imports:**

```bash
# Check for issues
ruff check src/

# Auto-fix issues (including unused imports)
ruff check --fix src/
```

#### 3. **Type Hints**

**Always use type hints** for function parameters and return values:

```python
# ✅ Good
def process_violations(violations: List[Dict], output_path: str) -> bool:
    """Process and save violations."""
    ...

# ❌ Bad
def process_violations(violations, output_path):
    ...
```

**Use Optional for nullable values:**

```python
def find_file(pattern: str) -> Optional[Path]:
    """Find file matching pattern, or None if not found."""
    ...
```

#### 4. **Docstrings**

Use **Google-style docstrings**:

```python
def analyze_spec(spec_path: Path, ruleset: str) -> List[Dict]:
  """
  Analyze OpenAPI specification for violations.

  Args:
    spec_path: Path to OpenAPI spec file
    ruleset: Path to Spectral ruleset

  Returns:
    List of violation dictionaries

  Raises:
    FileNotFoundError: If spec file doesn't exist
    ValueError: If spec is invalid
  """
  ...
```

#### 5. **Naming Conventions**

- **Classes**: `PascalCase` (e.g., `GovernanceScanner`, `FileUtils`)
- **Functions/Methods**: `snake_case` (e.g., `run_scan`, `generate_report`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private**: Prefix with `_` (e.g., `_internal_method`)

#### 6. **Async/Await**

Use async/await for I/O operations:

```python
# ✅ Good - Async for I/O
async def scan(self, spec_path: str) -> ScanResult:
  violations = await self._analyze_spec(spec_path)
  return violations

# ❌ Bad - Blocking I/O in async function
async def scan(self, spec_path: str) -> ScanResult:
  violations = self._blocking_call()  # Don't do this!
  return violations
```

---

## 🧪 Testing Guidelines

### Test Organization

Tests are organized by module:

```
tests/
├── test_autofix.py         # Tests for autofix module
├── test_engines.py          # Tests for scanning engines
├── test_mcp_server.py       # Tests for MCP server
├── test_scanner.py          # Tests for scanner module
├── test_utils_all.py        # Tests for utilities
└── data/                    # Test fixtures
```

### Writing Tests

Follow these patterns:

#### 1. **Test Class Structure**

```python
import pytest
from pathlib import Path

class TestGovernanceScanner:
  """Test GovernanceScanner functionality"""

  @pytest.fixture(autouse=True)
  def setup_teardown(self):
    """Setup and cleanup for each test"""
    self.temp_dir = tempfile.mkdtemp()
    yield
    if os.path.exists(self.temp_dir):
      shutil.rmtree(self.temp_dir)

  def test_scan_valid_spec(self):
    """Test scanning a valid OpenAPI spec"""
    # Arrange
    spec_path = Path(self.temp_dir) / "spec.yaml"
    spec_path.write_text("openapi: 3.0.0\n...")

    # Act
    result = self.scanner.scan(spec_path)

    # Assert
    assert result is not None
    assert len(result.violations) >= 0
```

#### 2. **Use pytest Markers**

```python
@pytest.mark.unit
def test_simple_function():
  """Unit test example"""
  assert add(2, 2) == 4

@pytest.mark.integration
def test_full_workflow():
  """Integration test example"""
  ...

@pytest.mark.slow
def test_heavy_operation():
  """Slow test that takes time"""
  ...
```

#### 3. **Mock External Dependencies**

```python
from unittest.mock import Mock, patch, AsyncMock

@patch('utils.ProcessUtils.run_command')
def test_spectral_execution(mock_run):
  """Test Spectral execution with mocked subprocess"""
  mock_run.return_value = ProcessResult(0, "[]", "")

  runner = SpectralRunner("ruleset.yaml")
  violations = runner.run_spectral(Path("spec.yaml"))

  assert len(violations) == 0
  mock_run.assert_called_once()
```

#### 4. **Test Async Functions**

```python
@pytest.mark.asyncio
async def test_async_scan():
  """Test async scanning function"""
  scanner = GovernanceScanner(".", "rules.yaml", "http://localhost")
  result = await scanner.scan()
  assert result is not None
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_scanner.py

# Run tests matching pattern
pytest -k "test_scan"

# Run with coverage
pytest --cov=src --cov-report=html
```

### Test Configuration

See `pytest.ini` for test configuration:

- Test discovery patterns: `test_*.py`
- Test markers: `unit`, `integration`, `slow`
- Output options: verbose, short traceback

---

## 🔧 Common Patterns

### 1. **Utility Classes Pattern**

The codebase uses static utility classes:

```python
class FileUtils:
  """Utility class for file operations"""

  @staticmethod
  def read_json(file_path: str) -> Dict[str, Any]:
    """Read JSON file."""
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
      return json.load(f)

  @staticmethod
  def write_json(file_path: str, data: Dict[str, Any]):
    """Write JSON file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
      json.dump(data, f, indent=2)
```

**When to create a utility class:**

- Group related helper functions
- No instance state needed
- Pure functions that operate on inputs

### 2. **NamedTuple for Data Classes**

Use NamedTuple for simple immutable data structures:

```python
from typing import NamedTuple, List

class ScanResult(NamedTuple):
  """Result of a governance scan"""

  project_path: str
  spec_files: List[str]
  spectral_results: List[Dict]
  llm_results: List[Dict]
  scan_type: str = "API Specification"

  @property
  def total_violations(self) -> int:
    return len(self.spectral_results) + len(self.llm_results)
```

### 3. **Dataclass for Mutable Data**

Use @dataclass for mutable data structures:

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class ProposedFix:
  """Represents a proposed fix for a violation"""

  fix_id: str
  rule_id: str
  file_path: str
  line_number: Optional[int]
  original_content: str
  proposed_content: str
  explanation: str
  requires_imports: List[str] = field(default_factory=list)
```

### 4. **Pydantic Models for Validation**

Use Pydantic for API schemas and validation:

```python
from pydantic import BaseModel, Field

class Violation(BaseModel):
  """Normalized violation structure"""

  rule_id: str = Field(..., description="Unique identifier for the rule")
  description: str = Field(..., description="Human-readable description")
  severity: Literal["critical", "warning", "info"]
  file: str
  line: Optional[int] = None
```

### 5. **Logging Pattern**

Use the shared logger from utils:

```python
from utils.logger import logger

class MyClass:
  def process(self):
    logger.info("Starting process...")
    try:
      result = self._do_work()
      logger.info("✓ Process completed successfully")
      return result
    except Exception as e:
      logger.error(f"✗ Process failed: {e}")
      raise
```

**Logging levels:**

- `logger.info()`: Normal operations, progress updates
- `logger.warning()`: Recoverable issues, deprecations
- `logger.error()`: Errors that prevent operation
- `logger.debug()`: Detailed debugging information

### 6. **Error Handling**

Be specific with exceptions:

```python
# ✅ Good - Specific exception handling
try:
  data = FileUtils.read_json(path)
except FileNotFoundError:
  logger.error(f"File not found: {path}")
  return default_value
except json.JSONDecodeError as e:
  logger.error(f"Invalid JSON in {path}: {e}")
  raise ValueError(f"Invalid JSON format") from e

# ❌ Bad - Catch-all exception
try:
  data = FileUtils.read_json(path)
except Exception:
  return None
```

### 7. **Path Handling**

Always use `pathlib.Path`:

```python
from pathlib import Path

# ✅ Good
project_path = Path(project_dir)
spec_file = project_path / "api" / "openapi.yaml"
if spec_file.exists():
  content = spec_file.read_text()

# ❌ Bad
spec_file = os.path.join(project_dir, "api", "openapi.yaml")
if os.path.exists(spec_file):
  with open(spec_file) as f:
    content = f.read()
```

---

## 🛠️ Tools and Frameworks

### Core Dependencies

| Tool         | Version  | Purpose                  |
| ------------ | -------- | ------------------------ |
| **Python**   | 3.10+    | Runtime                  |
| **black**    | ≥23.12.0 | Code formatting          |
| **ruff**     | ≥0.1.8   | Linting, import checking |
| **pytest**   | ≥7.4.3   | Testing framework        |
| **pydantic** | ≥2.8.0   | Data validation          |
| **fastmcp**  | ≥0.1.0   | MCP server framework     |
| **aiohttp**  | ≥3.9.1   | Async HTTP client        |
| **pyyaml**   | ≥6.0.1   | YAML parsing             |

### External Tools

- **Spectral CLI**: OpenAPI linting (`npm install -g @stoplight/spectral-cli`)
- **ArchUnit**: Java architecture testing (managed via JAR downloads)

### Editor Configuration

The project includes `.editorconfig` for consistent editor settings:

- **Indentation**: 2 spaces
- **Line endings**: LF (Unix)
- **Encoding**: UTF-8
- **Max line length**: 200 characters
- **Trailing whitespace**: Trimmed (except Markdown)

Most modern editors respect `.editorconfig` automatically.

---

## 📤 Pull Request Process

### Before Submitting

1. **Run Tests**

   ```bash
   pytest
   ```

2. **Check Code Quality**

   ```bash
   # Format code
   black .

   # Check linting
   ruff check .

   # Fix auto-fixable issues
   ruff check --fix .
   ```

3. **Update Documentation**
   - Update docstrings for new/changed functions
   - Update README.md if adding features
   - Add examples if appropriate

4. **Test Your Changes**
   - Add tests for new functionality
   - Ensure all tests pass
   - Test manually if applicable

### PR Guidelines

1. **Branch Naming**
   - Feature: `feature/description`
   - Bug fix: `fix/description`
   - Documentation: `docs/description`

2. **Commit Messages**
   - Use clear, descriptive messages
   - Start with verb: "Add", "Fix", "Update", "Remove"
   - Reference issues: "Fix #123: Description"

3. **PR Description**
   - Describe what changed and why
   - List any breaking changes
   - Include testing notes
   - Add screenshots for UI changes

4. **Code Review**
   - Respond to feedback promptly
   - Make requested changes
   - Keep discussions focused

### PR Checklist

```markdown
- [ ] Tests added/updated and passing
- [ ] Code formatted with black
- [ ] Linting passes (ruff)
- [ ] Type hints added for new functions
- [ ] Docstrings updated
- [ ] No unused imports (checked with ruff)
- [ ] README.md updated (if needed)
- [ ] Breaking changes documented
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem**: `ModuleNotFoundError` when running tests

**Solution**: Ensure you're in the virtual environment and have installed dependencies:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

#### 2. Spectral Not Found

**Problem**: `Spectral CLI not found` error

**Solution**: Install Spectral globally:

```bash
npm install -g @stoplight/spectral-cli
spectral --version  # Verify installation
```

#### 3. Test Failures

**Problem**: Tests fail with path issues

**Solution**: Tests may depend on project structure. Ensure you're running from project root:

```bash
cd <path-to-tool-project-root>
pytest
```

#### 4. Formatting Issues

**Problem**: CI fails on formatting checks

**Solution**: Run black before committing:

```bash
black src/ tests/ scripts/
```

#### 5. UTF-8 Encoding Errors (Windows)

**Problem**: `UnicodeEncodeError` with emojis in output

**Solution**: The code handles this automatically. If issues persist, set environment variable:

```bash
# Windows PowerShell
$env:PYTHONIOENCODING = "utf-8"

# Windows CMD
set PYTHONIOENCODING=utf-8
```

---

## 📚 Additional Resources

- **[README.md](README.md)**: Project overview and features
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)**: Detailed setup instructions
- **[PROMPT_RUNSHEET.md](PROMPT_RUNSHEET.md)**: IDE integration workflow
- **[rules/rules-docs.md](rules/rules-docs.md)**: Governance rules documentation

---

## 🤝 Getting Help

- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check existing docs before asking

---

## 📜 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

---

Thank you for contributing to the API Governance Agent! 🎉

Your contributions help make API governance easier for everyone.
