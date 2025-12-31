# 🚀 API Governance Agent - Setup Guide

**Get started in 5 minutes with automated environment setup!**

---

## Prerequisites

Before you begin, ensure you have:

- ✅ **Python 3.10+** (tested with 3.14.0)
- ✅ **Node.js 18+** (for Spectral rules)
- ✅ **Java 11+** (for ArchUnit scanning)
- ✅ **VS Code** with GitHub Copilot extension
- ✅ **direnv** (recommended for automatic environment setup)

---

## Step 1: Clone Repository

```bash
git clone <repo-url>
cd <path-to-tool-project-root>
```

---

## Step 2: Automated Setup with direnv (Recommended) ⚡

### Install direnv

**macOS:**

```bash
brew install direnv
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
source ~/.zshrc
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt install direnv
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
source ~/.bashrc
```

**Other Linux:**

```bash
# Download direnv binary
curl -sfL https://direnv.net/install.sh | bash
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc  # or ~/.zshrc for zsh
source ~/.bashrc
```

**Windows (WSL):**

```bash
# Use Linux instructions above in WSL
```

### Allow direnv in Project

```bash
direnv allow <path-to-tool-project-root>
```

**That's it!** 🎉

**Every time you `cd` into the project, the environment is automatically ready!**

```bash
# Just cd into the project
cd <path-to-tool-project-root>

# Output you'll see:
# direnv: loading <path-to-tool-project-root>/.envrc
# ✓ Virtual environment activated
# ✓ Python path configured
# ✓ Environment ready!
```

---

## Step 2 (Alternative): Manual Setup Without direnv

If you prefer manual control or can't install direnv:

### 1. Create & Activate Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it (you need to do this every time you open a new terminal)
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Node.js Dependencies (Spectral)

```bash
cd rules
npm install
cd ..
```

### 4. Set PYTHONPATH (Required Every Time)

```bash
# macOS/Linux
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# Windows (Command Prompt)
set PYTHONPATH=%CD%\src;%PYTHONPATH%

# Windows (PowerShell)
$env:PYTHONPATH="${PWD}\src;$env:PYTHONPATH"
```

### 5. Compile Java (ArchUnit)

```bash
cd resources/java
./compile.sh  # macOS/Linux
compile.bat   # Windows
cd ../..
```

⚠️ **Note:** Without direnv, you must manually activate the virtual environment and set PYTHONPATH **every time** you open a new terminal.

---

## Step 3: Configure MCP Server for the Target Project (For IDE Integration)

⚠️ **IMPORTANT:** MCP configuration goes in `.vscode/mcp.json`, NOT in `settings.json`!

Create `.vscode/mcp.json` in your workspace root:

### For Windows Users 🪟

**Option 1: Direct Python Command (Recommended - Most Reliable)**

Create `.vscode/mcp.json`:

```json
{
  "servers": {
    "api-governance": {
      "command": "<path-to-tool-project-root>\\.venv\\Scripts\\python.exe",
      "args": ["-m", "src.mcp_server.server"],
      "env": {
        "PYTHONPATH": "<path-to-tool-project-root>\\src"
      }
    }
  }
}
```

**Option 2: Using PowerShell Script**

```json
{
  "servers": {
    "api-governance": {
      "command": "powershell.exe",
      "args": ["-ExecutionPolicy", "Bypass", "-File", "<path-to-tool-project-root>\\scripts\\start_mcp_server.ps1"]
    }
  }
}
```

**Option 3: Using Batch File**

```json
{
  "servers": {
    "api-governance": {
      "command": "<path-to-tool-project-root>\\scripts\\start_mcp_server.bat",
      "args": []
    }
  }
}
```

### For macOS/Linux Users 🍎🐧

**Using Shell Script (Recommended)**

Create `.vscode/mcp.json`:

```json
{
  "servers": {
    "api-governance": {
      "command": "<path-to-tool-project-root>/scripts/start_mcp_server.sh",
      "args": [],
      "env": {
        "PYTHONPATH": "<path-to-tool-project-root>/src"
      }
    }
  }
}
```

### Test MCP Server

1. Open VS Code for the project to be scanned.
2. Open `.vscode/mcp.json` in the editor then click 'Add Server' then select 'Command(stdio)' and Enter
3. Open the Command Palette (`Cmd+Shift+P` or `Ctrl+Shift+P`)
4. Type "Developer: Reload Window"
5. Open Copilot Chat
6. Click on the Gear Icon, select "Mcp Servers" option.
7. Right click on "api-governance" server and click "Start Server" to start the mcp server.
8. Click on the tools icon within the copilot chat. You should see the "MCP SERVER: api-governance" tools listed:

- `scan_project`
- `propose_fixes`
- `apply_fixes`
- `validate_fixes`
- And more...

## Step 5: RUN and test

Once setup is complete:

### 🎯 IDE Integration

→ See [PROMPT_RUNSHEET.md](PROMPT_RUNSHEET.md)

- Use Copilot Chat for interactive fixing
- AI-powered fix suggestions
- Automated workflow

---

## Troubleshooting

### Script access issue

If you are getting issue Connection state: Error spawn EACCES

Run the below command on your terminal:

```bash
xattr -l <path-to-tool-project-root>/scripts/start_mcp_server.sh
```

### direnv Issues 🔧

#### direnv not loading .envrc

```bash
# Check if direnv is installed
which direnv

# Check if hook is configured
echo $SHELL  # Should show your shell

# For zsh, verify hook in ~/.zshrc:
grep direnv ~/.zshrc

# For bash, verify hook in ~/.bashrc:
grep direnv ~/.bashrc

# Reload shell configuration
source ~/.zshrc  # or ~/.bashrc
```

#### Permission denied: .envrc is blocked

```bash
# You must explicitly allow .envrc to run
direnv allow <path-to-tool-project-root>

# Output should show:
# direnv: loading .envrc
# ✓ Virtual environment activated
```

#### Changes to .envrc not taking effect

```bash
# After editing .envrc, you must allow it again
direnv allow <path-to-tool-project-root>

# Or reload manually
direnv reload
```

#### Virtual environment not activating with direnv

```bash
# Check if .venv exists
ls -la .venv/

# If missing, create it manually then allow direnv
python3 -m venv .venv
direnv allow <path-to-tool-project-root>

# Verify activation
which python  # Should show: <path-to-tool-project-root>/.venv/bin/python
```

#### Dependencies not installing automatically

```bash
# Run setup manually first time
cd <path-to-tool-project-root>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd rules && npm install && cd ..

# Then allow direnv
direnv allow <path-to-tool-project-root>
```

---

### Windows-Specific Issues 🪟

⚠️ **Note:** direnv is primarily for macOS/Linux. Windows users should use WSL or manual setup.

#### Error: "spawn EFTYPE"

This error occurs when trying to run `.sh` shell scripts on Windows. **Solution:**

1. Use the Windows-specific configuration (see Step 3 above)
2. Use `scripts/start_mcp_server.bat` or `scripts/start_mcp_server.ps1` instead of `.sh` file
3. Or use the direct Python command option

#### PowerShell Execution Policy Error

If you see "cannot be loaded because running scripts is disabled":

```powershell
# Run PowerShell as Administrator and execute:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Path Issues on Windows

- Use backslashes `\` in paths: `<path-to-tool-project-root>\\.venv\\Scripts\\python.exe`
- Or use forward slashes (VS Code will convert): `<path-to-tool-project-root>/.venv/Scripts/python.exe`

#### Virtual Environment Not Activating

```cmd
# For Command Prompt
.venv\Scripts\activate.bat

# For PowerShell
.venv\Scripts\Activate.ps1

# Verify Python path
where python
```

### General Issues

### Python Module Not Found

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Verify import works
python3 -c "from scanner.governance_scanner import GovernanceScanner; print('OK')"
```

### Spectral Not Found

```bash
# Reinstall Node dependencies
cd rules
rm -rf node_modules package-lock.json
npm install
cd ..
```

---

**Need help?** Open an issue on GitHub Issues
