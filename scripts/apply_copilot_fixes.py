#!/usr/bin/env python3
"""
Apply Copilot Fixes Automatically

This script reads the copilot-fix-instructions.json and applies fixes
directly to files, bypassing the need for manual Copilot interaction.

This is useful for:
- Batch applying SAFE fixes
- CI/CD integration
- Automated code refactoring

Safety:
- Creates backups before modifying files
- Only applies SAFE fixes by default
- Generates a detailed change report
"""

import json
import shutil
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import argparse
import sys

# Add parent directory to path for imports
script_dir = Path(__file__).parent
src_dir = script_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from utils.logger import logger


class DirectFixApplicator:
    """
    Applies fixes directly to files using predefined strategies.

    This is faster than LLM calls and doesn't require external APIs.
    """

    def __init__(self, project_path: str, backup: bool = True):
        self.project_path = Path(project_path)
        self.backup = backup
        self.backup_dir = (
            self.project_path
            / ".governance-backups"
            / datetime.now().strftime("%Y%m%d-%H%M%S")
        )

        if backup:
            self.backup_dir.mkdir(parents=True, exist_ok=True)

    def apply_fixes(
        self, instructions: List[Dict], safety_filter: str = "safe"
    ) -> Dict:
        """
        Apply fixes from instruction list

        Args:
            instructions: List of fix instructions from JSON
            safety_filter: "safe", "review_required", or "all"

        Returns:
            Summary dictionary with results
        """
        results = {
            "total": len(instructions),
            "applied": 0,
            "skipped": 0,
            "failed": 0,
            "files_modified": set(),
            "details": [],
        }

        for instruction in instructions:
            try:
                # Check safety level (handle both uppercase and lowercase)
                safety = instruction.get("safety", "unknown")
                if isinstance(safety, str):
                    safety = safety.lower()

                should_skip = False
                if safety_filter == "safe":
                    # Only apply SAFE fixes
                    should_skip = safety != "safe"
                elif safety_filter == "review_required":
                    # Apply SAFE and REVIEW_REQUIRED, skip MANUAL_ONLY
                    should_skip = safety == "manual_only"
                # elif safety_filter == "all":
                #     Apply ALL fixes including MANUAL_ONLY
                #     Let the fix applicator attempt them - some may work!

                if should_skip:
                    results["skipped"] += 1
                    results["details"].append(
                        {
                            "fix_id": instruction["fix_id"],
                            "status": "skipped",
                            "reason": f"Safety level {safety} not in filter '{safety_filter}'",
                        }
                    )
                    continue

                # Apply the fix
                success = self._apply_single_fix(instruction)

                if success:
                    results["applied"] += 1
                    results["files_modified"].add(instruction["file"])
                    results["details"].append(
                        {
                            "fix_id": instruction["fix_id"],
                            "status": "applied",
                            "file": instruction["file"],
                        }
                    )
                else:
                    results["failed"] += 1
                    results["details"].append(
                        {
                            "fix_id": instruction["fix_id"],
                            "status": "failed",
                            "reason": "Could not apply fix",
                        }
                    )

            except Exception as e:
                results["failed"] += 1
                results["details"].append(
                    {
                        "fix_id": instruction["fix_id"],
                        "status": "failed",
                        "reason": str(e),
                    }
                )

        results["files_modified"] = list(results["files_modified"])
        return results

    def _apply_single_fix(self, instruction: Dict) -> bool:
        """
        Apply a single fix using Copilot prompt or rule-specific logic.
        Returns True if successful.
        """
        rule_id = instruction["rule_id"]
        file_path_str = instruction["file"]

        # Handle absolute paths correctly
        if Path(file_path_str).is_absolute():
            file_path = Path(file_path_str)
        else:
            file_path = self.project_path / file_path_str

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return False

        # Backup file
        if self.backup:
            # For backup, use relative path from project_path
            if Path(file_path_str).is_absolute():
                try:
                    rel_backup_path = file_path.relative_to(self.project_path)
                except ValueError:
                    # File is outside project path, use full path structure
                    rel_backup_path = str(file_path).replace("/", "_")[
                        1:
                    ]  # Remove leading slash
            else:
                rel_backup_path = file_path_str

            backup_file = self.backup_dir / rel_backup_path
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_file)

        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Try Copilot prompt-based fix first (if available)
        if "prompt" in instruction:
            fixed_content = self._apply_copilot_fix(content, instruction)
            if fixed_content and fixed_content != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)
                return True

        # Fallback to rule-specific fix for hardcoded patterns
        fixed_content = self._apply_rule_fix(rule_id, content, instruction)

        if fixed_content and fixed_content != content:
            # Write fixed content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            return True

        return False

    def _apply_copilot_fix(self, content: str, instruction: Dict) -> str:
        """
        Apply fix using the copilot-fix-instructions prompt.

        Since we don't have API access, we return the content unchanged.
        The actual fix application should happen via VS Code Copilot Chat directly.

        For now, this method serves as a placeholder for future integration.
        """
        # TODO: Integrate with VS Code Language Model API when available
        # For now, return unchanged content - fixes must be applied via Copilot Chat
        return content

    def _apply_rule_fix(self, rule_id: str, content: str, instruction: Dict) -> str:
        """
        Apply rule-specific transformation to content.

        This uses simple pattern matching and replacement for SAFE rules.
        """
        # Import-based fixes (safe to apply automatically)
        if rule_id == "coding-no-std-streams":
            return self._fix_std_streams(content)

        elif rule_id == "coding-no-java-util-logging":
            return self._fix_java_util_logging(content)

        elif rule_id == "security-use-secure-random":
            return self._fix_secure_random(content)

        elif rule_id == "security-serial-version-uid":
            return self._fix_serial_version_uid(content)

        # OpenAPI fixes
        elif rule_id == "kebab-case-paths":
            return self._fix_kebab_case_paths(content)

        elif rule_id == "uuid-resource-ids":
            return self._fix_uuid_format(content)

        elif rule_id == "operation-description-required":
            return self._fix_add_descriptions(content, "description")

        elif rule_id == "operation-summary-required":
            return self._fix_add_descriptions(content, "summary")

        # For other rules, return original content (will be marked as failed)
        return content

    def _fix_std_streams(self, content: str) -> str:
        """Replace System.out/err with logger"""
        import re

        # Add logger if not present
        if "private static final Logger logger" not in content:
            # Find class declaration
            class_match = re.search(
                r"(public|private|protected)?\s*class\s+(\w+)", content
            )
            if class_match:
                class_name = class_match.group(2)
                logger_declaration = f"\n    private static final Logger logger = LoggerFactory.getLogger({class_name}.class);\n"

                # Insert after class opening brace
                content = re.sub(
                    r"(class\s+\w+[^{]*{)", r"\1" + logger_declaration, content, count=1
                )

        # Replace System.out/err
        content = re.sub(r"System\.out\.println\((.*?)\)", r"logger.info(\1)", content)
        content = re.sub(r"System\.err\.println\((.*?)\)", r"logger.error(\1)", content)

        # Add imports if not present
        if "import org.slf4j.Logger;" not in content:
            content = (
                "import org.slf4j.Logger;\nimport org.slf4j.LoggerFactory;\n" + content
            )

        return content

    def _fix_java_util_logging(self, content: str) -> str:
        """Replace java.util.logging with SLF4J"""
        import re

        content = re.sub(r"java\.util\.logging\.Logger", "org.slf4j.Logger", content)
        content = re.sub(
            r"Logger\.getLogger\((.*?)\)", r"LoggerFactory.getLogger(\1)", content
        )

        # Update imports
        content = content.replace(
            "import java.util.logging.Logger;", "import org.slf4j.Logger;"
        )
        if (
            "import org.slf4j.LoggerFactory;" not in content
            and "LoggerFactory" in content
        ):
            content = "import org.slf4j.LoggerFactory;\n" + content

        return content

    def _fix_secure_random(self, content: str) -> str:
        """Replace Random with SecureRandom"""
        import re

        content = re.sub(r"\bnew Random\(\)", "new SecureRandom()", content)
        content = re.sub(r"\bRandom\s+(\w+)", r"SecureRandom \1", content)

        # Add import
        if "import java.security.SecureRandom;" not in content:
            content = "import java.security.SecureRandom;\n" + content

        return content

    def _fix_serial_version_uid(self, content: str) -> str:
        """Add serialVersionUID to Serializable classes"""
        import re

        # Check if class implements Serializable
        if "implements" in content and "Serializable" in content:
            # Check if serialVersionUID already exists
            if "serialVersionUID" not in content:
                # Add after class opening brace
                content = re.sub(
                    r"(class\s+\w+[^{]*{)",
                    r"\1\n    private static final long serialVersionUID = 1L;\n",
                    content,
                    count=1,
                )

        return content

    def _fix_kebab_case_paths(self, content: str) -> str:
        """Convert paths to kebab-case"""
        import re

        def to_kebab_case(match):
            path = match.group(1)
            # Convert camelCase to kebab-case
            path = re.sub(r"([a-z])([A-Z])", r"\1-\2", path)
            # Convert snake_case to kebab-case
            path = path.replace("_", "-")
            return f'"{path.lower()}"'

        # Match path patterns in OpenAPI
        content = re.sub(
            r'"(/[^"]*)"',
            lambda m: (
                to_kebab_case(m)
                if "_" in m.group(1) or any(c.isupper() for c in m.group(1))
                else m.group(0)
            ),
            content,
        )

        return content

    def _fix_uuid_format(self, content: str) -> str:
        """Add format: uuid to UUID parameters"""
        import re

        # Find parameters with 'id' in name and type string
        # This is a simplified pattern - may need adjustment for complex schemas
        pattern = r"(- name: \w*[iI][dD]\w*\s+in: \w+\s+schema:\s+type: string)(\s+)"

        def add_format(match):
            if "format:" not in match.group(0):
                return match.group(1) + "\n        format: uuid" + match.group(2)
            return match.group(0)

        content = re.sub(pattern, add_format, content, flags=re.MULTILINE)

        return content

    def _fix_add_descriptions(self, content: str, field: str) -> str:
        """Add description/summary fields where missing"""
        import yaml

        try:
            # Parse YAML
            data = yaml.safe_load(content)

            # Add descriptions to operations
            if "paths" in data:
                for path, methods in data["paths"].items():
                    for method, operation in methods.items():
                        if isinstance(operation, dict) and field not in operation:
                            if field == "description":
                                operation[field] = (
                                    f"Operation for {method.upper()} {path}"
                                )
                            elif field == "summary":
                                operation[field] = (
                                    f"{method.upper()} {path.split('/')[-1]}"
                                )

            # Convert back to YAML
            return yaml.dump(data, sort_keys=False, default_flow_style=False)

        except Exception as e:
            logger.warning(f"Could not parse YAML for {field} fix: {e}")
            return content


def main():
    parser = argparse.ArgumentParser(
        description="Apply Copilot fix instructions directly to files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--instructions", required=True, help="Path to copilot-fix-instructions.json"
    )

    parser.add_argument(
        "--project",
        default=".",
        help="Path to project directory (default: current directory)",
    )

    parser.add_argument(
        "--safety",
        choices=["safe", "review_required", "all"],
        default="safe",
        help="Which fixes to apply by safety level (default: safe)",
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backups (not recommended)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    try:
        # Load instructions
        print(f"\n📖 Loading fix instructions: {args.instructions}")
        with open(args.instructions, "r") as f:
            instructions = json.load(f)

        print(f"✓ Loaded {len(instructions)} fix instruction(s)")

        if args.dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made\n")
            for inst in instructions:
                print(f"  • {inst['fix_id']}: {inst['rule_id']} in {inst['file']}")
            return

        # Apply fixes
        print(f"\n🔧 Applying fixes (safety level: {args.safety})...")
        applicator = DirectFixApplicator(args.project, backup=not args.no_backup)
        results = applicator.apply_fixes(instructions, args.safety)

        # Print results
        print(f"\n{'='*70}")
        print("📊 Results")
        print(f"{'='*70}")
        print(f"✅ Applied: {results['applied']}")
        print(f"⏭️  Skipped: {results['skipped']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"📁 Files modified: {len(results['files_modified'])}")

        if results["files_modified"]:
            print("\n📝 Modified files:")
            for file in results["files_modified"]:
                print(f"  • {file}")

        if not args.no_backup and results["applied"] > 0:
            print(f"\n💾 Backups saved to: {applicator.backup_dir}")

        print(f"\n{'='*70}\n")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
