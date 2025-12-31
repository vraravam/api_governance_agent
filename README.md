# 🤖 API Governance Agent

**Your AI-powered pair programmer for API standards and architectural integrity**

> Automatically scan, fix, and validate governance violations in your codebase using AI

---

## 🎯 What Is This?

The API Governance Agent is an intelligent tool that:

- 🔍 **Scans** your OpenAPI specs and Java code for violations
- 🤖 **Proposes** AI-powered fixes automatically
- ✅ **Validates** changes with build, test, and re-scan
- 💡 **Integrates** seamlessly with VS Code and CLI workflows

**No more manual violation hunting!** Let AI handle the tedious work.

---

## 🚀 All Users - Setup Path

1. **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete setup in 5 minutes (covers all platforms)
   - Windows: Use `.bat` or `.ps1` scripts
   - macOS/Linux: Use `.sh` script
   - **IMPORTANT:** Create `.vscode/mcp.json` for server config
2. **[PROMPT_RUNSHEET.md](PROMPT_RUNSHEET.md)** - IDE workflow with prompts

---

## ✨ Key Features

### 🔍 Multi-Engine Scanning

**Spectral (OpenAPI)**

- 70+ built-in governance rules
- REST API best practices
- Security checks
- Custom ruleset support

**ArchUnit (Java)**

- Architectural pattern enforcement
- Package dependency validation
- Naming convention checks
- Layer violation detection

**LLM Analysis**

- Semantic issue detection
- Context-aware suggestions
- Natural language explanations

---

### 🤖 Automated Fixing

**AI-Powered Fix Generation**

- Analyzes violations in context
- Proposes specific, targeted fixes
- Explains reasoning for each change
- Handles complex multi-file updates

**Category-Based Workflow**

- Fix by priority (P1 → P10)
- Incremental, reviewable changes
- Better git history
- Easier team reviews

---

### ✅ Comprehensive Validation

**NEW: Unified Validation Tool**

```
Phase 1: Build & Test → Phase 2: Re-Scan → Phase 3: Confidence Score
```

- Detects build system (Gradle/Maven/npm)
- Runs tests automatically
- Re-scans for violations
- Provides confidence score (0-100)
- Recommends COMMIT, REVIEW, or FIX

---

### 🎨 IDE Integration

**VS Code with MCP Server**

- Chat with Copilot to scan and fix
- Automatic file preview
- Git integration
- Real-time validation

**Simple Prompts:**

```
scan for violations
fix RESOURCE_NAMING violations
validate the fixes
```

---

## 🛠️ Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- Java 11+ (for ArchUnit)
- VS Code with GitHub Copilot extension (for IDE workflow)
- **[direnv](https://direnv.net/)** (recommended) - for automatic environment setup

Refer to **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Installation and configuration

## 📊 What Gets Scanned?

### OpenAPI/Swagger Files

- ✅ Resource naming (plural, kebab-case, no verbs)
- ✅ HTTP method semantics
- ✅ Response structures and envelopes
- ✅ Error handling patterns
- ✅ API versioning
- ✅ Data type definitions
- ✅ Documentation completeness
- ✅ Security schemes

### Java Code (ArchUnit)

- ✅ Package dependencies
- ✅ Layer violations
- ✅ Naming conventions
- ✅ Architectural patterns
- ✅ Code organization
- ✅ Circular dependencies

---

## 📋 Generated Reports

After scanning, the tool generates comprehensive reports in the `build/governance/` directory:

### Report Files

| File                                            | Format   | Purpose                                    |
| ----------------------------------------------- | -------- | ------------------------------------------ |
| `build/governance/governance-report.json`       | JSON     | Machine-readable report for autofix tools  |
| `build/governance/combined-report.md`           | Markdown | Human-readable summary with all violations |
| `build/governance/api-violations.json`          | JSON     | OpenAPI/Spectral violations only           |
| `build/governance/arch-violations.json`         | JSON     | Java ArchUnit violations only              |
| `build/governance/fix-proposals/fix-preview.md` | Markdown | Preview of proposed fixes before applying  |

### Report Contents

**Governance Report (`governance-report.json`)**

```json
{
  "scan_timestamp": "2026-02-09T10:30:00Z",
  "project_path": "/path/to/project",
  "total_violations": 25,
  "violations_by_category": {
    "RESOURCE_NAMING": 14,
    "HTTP_SEMANTICS": 6,
    "DATA_TYPES": 5
  },
  "violations": [
    {
      "rule_id": "plural-resources",
      "severity": "warning",
      "message": "Resource 'user' should be plural 'users'",
      "file": "openapi.yaml",
      "line": 45,
      "path": "/api/user/{id}",
      "category": "RESOURCE_NAMING"
    }
  ]
}
```

**Markdown Report (`governance-report.md`)**

- Executive summary with health score
- Violations grouped by category
- Priority recommendations
- Fix instructions with examples

### Report Locations

All reports are generated in the `build/governance/` directory (automatically gitignored):

```
project-root/
└── build/
    └── governance/              # All governance reports (gitignored)
        ├── governance-report.json    # Main scan results
        ├── api-violations.json       # API spec violations only
        ├── arch-violations.json      # Java architecture violations
        ├── combined-report.md        # Human-readable summary
        └── fix-proposals/            # Fix session files
            ├── fix-preview.md        # Proposed changes preview
            ├── fix-preview.txt       # Diff format
            └── review-state.json     # Review workflow state
```

**Why `build/governance/`?**

- ✅ Standard build output location
- ✅ Auto-cleaned with build artifacts
- ✅ Ignored by most `.gitignore` files
- ✅ Keeps project root clean

### Using Reports

```bash
# View combined markdown report
cat build/governance/combined-report.md

# Check scan results
cat build/governance/governance-report.json

# Process JSON report programmatically
jq '.violations | length' build/governance/governance-report.json

# Count violations by category
jq '.violations | group_by(.category) | map({category: .[0].category, count: length})' \
  build/governance/governance-report.json

# Use in CI/CD
if [ $(jq '.total_violations' build/governance/governance-report.json) -gt 0 ]; then
  echo "❌ Governance violations found!"
  cat build/governance/combined-report.md
  exit 1
fi

# Clean reports before new scan
rm -rf build/governance/
```

---

## 🎯 Workflow Example

```
Step 1: Scan
Result: Found 25 violations (3 categories)

Step 2: Fix Priority Category
fix RESOURCE_NAMING violations
Result: 14 fixes applied

Step 3: Validate
Build: ✅ Pass
Tests: ✅ Pass
Re-scan: ✅ 0 violations
Score: 100/100

Step 4: Commit
git commit -m "fix(governance): resolve RESOURCE_NAMING"

Step 5: Repeat for Next Category
fix HTTP_SEMANTICS violations
...

Final: ✅ All violations resolved!
```

---

## 📚 Documentation Index

### Getting Started

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Installation and configuration
- **[PROMPT_RUNSHEET.md](PROMPT_RUNSHEET.md)** - IDE prompts and workflow

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## 🆘 Support

- 🐛 Report issues on [GitHub]
- 💬 Ask questions in discussions

---

**Built with ❤️ for better API governance**

Useful for CI/CD pipelines or generating static reports.

---

## 🏗️ Technical Details

For those who want to know how the sausage is made:

### Architecture

The project follows a **Wrapper & Adapter** pattern:

1.  **Scanners**: Standalone Python classes (`SpectralRunner`, `ArchUnitRunner`) execute the raw checks.
2.  **Engines**:
    - `ArchUnitEngine`: Wraps the Java process.
    - `LLMAnalyzer`: Connects to Ollama for semantic inference.
3.  **MCP Server**: Exposes these capabilities as JSON-RPC tools (`validate_openapi`, `governance_summary`) that LLMs can invoke.
4.  **Normalizer**: Converts diverse error formats (Spectral JSON, ArchUnit Strings) into a standardized `Violation` object.

### Customization

- **Rulesets**: Edit `rules/spectral_ruleset.yaml` to change API rules.
- **ArchUnit**: Modify `ArchUnitRunner.java` to add new Java architectural constraints.

---

**Happy Coding!** 🚀
