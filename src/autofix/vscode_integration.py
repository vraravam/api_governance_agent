#!/usr/bin/env python3
"""
VS Code Integration for Auto-Fix

Provides functionality to show modified files in VS Code's UI after applying fixes.
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Optional


class VSCodeIntegration:
    """Handles VS Code UI integration for showing modified files"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def show_modified_files(
        self,
        modified_files: List[str],
        original_content: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Opens modified files in VS Code for review

        Args:
            modified_files: List of file paths that were modified
            original_content: Optional dict of {file_path: original_content} for diff view

        Returns:
            True if files were successfully opened in VS Code
        """

        if not modified_files:
            return False

        print("\n📂 Opening modified files in VS Code for review...")

        # Method 1: Use `code` CLI to open files
        success = self._open_files_with_code_cli(modified_files)

        if success:
            print(f"   ✓ Opened {len(modified_files)} file(s) in editor")
            print("   ℹ️  Files are also visible in Source Control panel (Git changes)")
            return True

        # Method 2: Fallback - create a summary file that VS Code will detect
        summary_path = self._create_review_summary(modified_files)
        if summary_path:
            print(f"   ✓ Created review summary: {summary_path}")
            print("   ℹ️  Open this file to review all changes")
            return True

        return False

    def _open_files_with_code_cli(self, files: List[str]) -> bool:
        """
        Uses the `code` CLI command to open files in VS Code

        Args:
            files: List of file paths to open

        Returns:
            True if successful
        """

        try:
            # Check if `code` command is available
            result = subprocess.run(
                ["code", "--version"], capture_output=True, timeout=2
            )

            if result.returncode != 0:
                return False

            # Open each file in VS Code
            for file_path in files:
                full_path = self.project_path / file_path
                if full_path.exists():
                    subprocess.run(
                        ["code", str(full_path)], capture_output=True, timeout=5
                    )

            return True

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False

    def _create_review_summary(self, files: List[str]) -> Optional[Path]:
        """
        Creates a markdown summary file listing all modified files

        Args:
            files: List of modified file paths

        Returns:
            Path to created summary file
        """

        try:
            summary_path = self.project_path / "autofix-output" / "REVIEW_CHANGES.md"
            summary_path.parent.mkdir(parents=True, exist_ok=True)

            content = f"""# 🔍 Auto-Fix Changes Applied - Review Required

## Modified Files ({len(files)})

The following files were modified by the auto-fix system. Please review the changes:

"""

            for file_path in files:
                full_path = self.project_path / file_path
                if full_path.exists():
                    content += f"- [ ] `{file_path}`\n"
                    content += (
                        f"  - [Open file in editor](file://{full_path.absolute()})\n"
                    )

                    # Try to show a git diff
                    try:
                        diff_result = subprocess.run(
                            ["git", "diff", str(file_path)],
                            cwd=str(self.project_path),
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )

                        if diff_result.returncode == 0 and diff_result.stdout:
                            content += f"\n```diff\n{diff_result.stdout[:500]}\n```\n"
                            if len(diff_result.stdout) > 500:
                                content += "  - *(Diff truncated - open file to see full changes)*\n"
                    except:
                        pass

                    content += "\n"

            content += """
## Review Steps

1. ✅ **Check each modified file** - Click the links above or open files in Source Control panel
2. ✅ **Verify changes are correct** - Ensure the auto-fixes match your expectations
3. ✅ **Test your application** - Run tests to verify nothing broke
4. ✅ **Commit changes** - If all looks good, commit the changes to git

## View Changes in Source Control

The modified files should be visible in:
- **VS Code Source Control panel** (left sidebar, git icon)
- **Git diff view** - Click any file in Source Control to see changes
- **Timeline view** - Right-click file → "Open Timeline"

## Undo Changes

If you need to revert these changes:

```bash
# Revert specific file
git checkout -- path/to/file

# Revert all changes
git checkout -- .
```

---

**Auto-Fix Session:** {files[0].split('/')[0] if files else 'unknown'}
**Files Modified:** {len(files)}
"""

            summary_path.write_text(content, encoding="utf-8")

            # Try to open the summary file
            try:
                subprocess.run(
                    ["code", str(summary_path)], capture_output=True, timeout=5
                )
            except:
                pass

            return summary_path

        except Exception as e:
            print(f"   ⚠️  Could not create review summary: {e}")
            return None

    def show_diff_view(self, file_path: str, original_content: str) -> bool:
        """
        Shows a diff view comparing original vs modified content

        Args:
            file_path: Path to the modified file
            original_content: Original file content before modifications

        Returns:
            True if diff view was successfully opened
        """

        try:
            full_path = self.project_path / file_path
            if not full_path.exists():
                return False

            # Create a temporary file with original content
            temp_path = self.project_path / "autofix-output" / ".original" / file_path
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_text(original_content, encoding="utf-8")

            # Use `code --diff` to show comparison
            subprocess.run(
                ["code", "--diff", str(temp_path), str(full_path)],
                capture_output=True,
                timeout=5,
            )

            return True

        except Exception:
            return False

    def stage_files_in_git(self, files: List[str]) -> bool:
        """
        Stages modified files in git (makes them appear in Source Control panel)

        Args:
            files: List of file paths to stage

        Returns:
            True if files were successfully staged
        """

        try:
            for file_path in files:
                subprocess.run(
                    ["git", "add", str(file_path)],
                    cwd=str(self.project_path),
                    capture_output=True,
                    timeout=5,
                )

            print(f"   ✓ Staged {len(files)} file(s) in git")
            print("   ℹ️  View changes in Source Control panel (Ctrl+Shift+G)")
            return True

        except Exception as e:
            print(f"   ⚠️  Could not stage files in git: {e}")
            return False


def integrate_with_vscode(
    modified_files: List[str],
    project_path: str,
    original_content: Optional[Dict[str, str]] = None,
    stage_in_git: bool = True,
) -> bool:
    """
    Convenience function to integrate auto-fix changes with VS Code UI

    Args:
        modified_files: List of file paths that were modified
        project_path: Root path of the project
        original_content: Optional dict of original file contents for diff view
        stage_in_git: Whether to stage files in git (shows in Source Control)

    Returns:
        True if integration was successful
    """

    integration = VSCodeIntegration(project_path)

    # Stage files in git first (makes them appear in Source Control panel)
    if stage_in_git:
        integration.stage_files_in_git(modified_files)

    # Open files in editor
    return integration.show_modified_files(modified_files, original_content)
