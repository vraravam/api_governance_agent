# 🎯 API Governance Agent - Prompt Runsheet

**Interactive workflow using VS Code Copilot Chat**

---

## Prerequisites

✅ Complete [SETUP_GUIDE.md](SETUP_GUIDE.md) first
✅ MCP Server configured and running
✅ VS Code with GitHub Copilot extension

---

## Quick Reference Card

| What You Want       | Prompt to Use                                                              |
| ------------------- | -------------------------------------------------------------------------- |
| Scan with spec path | `Run complete governance scan with spec path: <path-to-openapi-spec-file>` |
| View violations     | `show me the governance violations`                                        |
| Fix all issues      | `apply all governance fixes` ( Skip for Higher Voilation Number)           |
| Fix by category     | `apply fix RESOURCE_NAMING violations`                                     |
| Check status        | `show governance scan status`                                              |

---

## Complete Workflow

### Step 1: Scan Your Project 🔍

**Prompt:**

```
scan the project for governance violations
```

**If OpenAPI spec is not auto-detected**, the tool will tell you. Provide the spec path like this:

```
scan with spec path: .company/spec-prod.json
```

Or use relative paths:

```
scan with spec path: src/main/resources/openapi.yaml
```

**What Happens:**

- ✅ Scans OpenAPI specs (if present or provided)
- ✅ Scans Java code with ArchUnit (if present)
- ✅ Categorizes violations by priority
- ✅ Generates detailed report

**Expected Output:**

```
📊 Scan Complete!

Found 25 violations across 3 categories:

🔴 RESOURCE_NAMING (P1): 14 violations
   - plural-resources (5 violations)
   - kebab-case-paths (4 violations)
   - no-verbs-in-url (5 violations)

🟡 HTTP_SEMANTICS (P6): 1 violation
   - http-methods-case (1 violation)

🟢 RESPONSE_STRUCTURE (P8): 10 violations
   - response-envelope-check (10 violations)
```

---

### Step 2: Review Violations 📋

**Prompt:**

```
show me the governance violations organized by category
```

**What Happens:**

- Shows violations grouped by priority
- Displays file locations
- Shows specific rule violations

**Or view specific category:**

```
show me RESOURCE_NAMING violations
```

---

### Step 3: Apply Fixes 🔧

#### Option A: Fix All Violations (Fastest)

**Prompt:**

```
apply all governance fixes
```

**What Happens:**

- Proposes fixes for all violations
- Shows preview of changes
- Applies fixes automatically
- Creates git commits per rule
- Opens files in VS Code for review

---

#### Option B: Fix by Category (Recommended)

**For highest priority first:**

**Prompt:**

```
fix RESOURCE_NAMING violations
```

**Or ask for recommendation:**

```
what category should I fix first?
```

**What Happens:**

- Fixes only violations in that category
- Smaller, focused changes
- Easier to review
- Less risk of conflicts

**Available Categories (in priority order):**

1. `RESOURCE_NAMING` (P1) - Highest priority
2. `ARCHITECTURE` (P2)
3. `CODE_QUALITY` (P3)
4. `VERSIONING` (P4)
5. `DATA_TYPES` (P5)
6. `HTTP_SEMANTICS` (P6)
7. `ERROR_HANDLING` (P7)
8. `RESPONSE_STRUCTURE` (P8)
9. `DOCUMENTATION` (P9)
10. `OTHER` (P10) - Lowest priority

---

## Troubleshooting

### OpenAPI Spec Not Auto-Detected 🔍

**Problem:** Tool says "No OpenAPI specs auto-detected"

**Solution 1: Provide Spec Path**

```
scan with spec path: .company/spec-prod.json
```

**Common OpenAPI spec locations:**

- `.company/spec-prod.json` (hidden folder)
- `src/main/resources/openapi.yaml`
- `openapi.json` (project root)
- `api/openapi.yaml`
- `docs/openapi.json`

**Solution 2: Move Spec to Standard Location**

Move your OpenAPI spec to one of these auto-detected paths:

- `src/main/resources/openapi.{json,yaml,yml}`
- `openapi.{json,yaml,yml}` (project root)
- `api/openapi.{json,yaml,yml}`
- `docs/openapi.{json,yaml,yml}`

---

### Step 4: Validate Fixes ✅

**After applying fixes, validate them:**

**Prompt:**

```
validate the fixes
```

**What Happens:**

- Runs build (Gradle/Maven/npm)
- Executes tests
- Re-scans for violations
- Compares before/after
- Calculates confidence score (0-100)

**Expected Output:**

```
🔨 Build: ✅ Success (4.5s)
🧪 Tests: ✅ All passing
🔍 Re-scan: 0 violations remaining
📊 Confidence Score: 100/100

🎯 Recommendation: COMMIT
```

**Confidence Score Guide:**

- **90-100**: COMMIT immediately ✅
- **70-89**: COMMIT after review 👀
- **40-69**: REVIEW carefully ⚠️
- **0-39**: FIX failures first ❌

---

### Step 5: Review Changes 👀

**Prompt:**

```
show me what files were changed
```

**Or view git diff:**

```
show me the git diff for the governance fixes
```

**Or open specific file:**

```
open the REVIEW_CHANGES.md file
```

---

### Step 6: Commit or Rollback 💾

#### If Changes Look Good:

**Prompt:**

```
commit the governance fixes
```

#### If You Need to Rollback:

**Prompt:**

```
rollback the governance fixes
```

**Or manually:**

```bash
git reset --hard HEAD
```

---

## Advanced Workflows

### Incremental Category-Based Fixing

**Fix violations category by category:**

```
fix RESOURCE_NAMING violations
# Review changes, validate, commit

fix ARCHITECTURE violations
# Review changes, validate, commit

fix CODE_QUALITY violations
# Review changes, validate, commit
```

**Benefits:**

- ✅ Smaller, focused changes
- ✅ Easier code review
- ✅ Incremental progress
- ✅ Less merge conflicts
- ✅ Better git history

---

### Re-scan After Fixing

**Verify remaining violations:**

```
re-scan the project and show remaining violations
```

---

### Generate Fix Preview Without Applying

**See what would change:**

```
generate fix proposals for RESOURCE_NAMING but don't apply them
```

---

### Check Specific File

**Scan single file:**

```
scan the file src/api/openapi.yaml for violations
```

---

## Troubleshooting

### No Violations Found

**Prompt:**

```
verify the scan configuration
```

Check:

- Are there OpenAPI specs in your project?
- Are there compiled Java classes (if Java project)?
- Is the project path correct?

---

### Fixes Not Applying

**Prompt:**

```
show me the fix proposals that failed
```

Common issues:

- Files have local changes (commit or stash first)
- Files don't match expected format
- Syntax errors in original files

---

### Build Failures After Fixes

**Prompt:**

```
validate fixes with clean build
```

This will:

- Run clean build
- Show exact error messages
- Suggest rollback if needed

---

### MCP Server Not Responding

1. Check Output panel: View → Output → "GitHub Copilot Chat"
2. Reload window: `Cmd+Shift+P` → "Developer: Reload Window"
3. Restart MCP server: Stop and restart VS Code

---

## Tips & Best Practices

### ✅ DO:

- ✅ Fix by category for complex projects
- ✅ Validate after each category
- ✅ Commit incrementally
- ✅ Review changes before committing
- ✅ Run tests after fixes

### ❌ DON'T:

- ❌ Fix all at once on large projects (use categories!)
- ❌ Skip validation step
- ❌ Commit without reviewing
- ❌ Apply fixes with uncommitted changes

---

## Example Session

```
You: @workspace scan the project for governance violations

Copilot: 📊 Found 25 violations:
         🔴 RESOURCE_NAMING (P1): 14 violations
         🟡 HTTP_SEMANTICS (P6): 1 violation
         🟢 RESPONSE_STRUCTURE (P8): 10 violations

You: @workspace fix RESOURCE_NAMING violations

Copilot: 🔧 Applying fixes for RESOURCE_NAMING...
         ✅ Generated 14 fix proposals
         ✅ Applied 14 fixes
         📂 Modified files: openapi.yaml

You: @workspace validate the fixes

Copilot: 🔨 Build: ✅ Success
         🔍 Re-scan: 0 RESOURCE_NAMING violations remaining
         📊 Confidence Score: 100/100
         🎯 Recommendation: COMMIT

You: @workspace commit the governance fixes

Copilot: ✅ Committed: "fix(governance): resolve RESOURCE_NAMING violations"
```

**Happy fixing! 🚀**
