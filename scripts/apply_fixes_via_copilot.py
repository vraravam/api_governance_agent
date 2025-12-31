#!/usr/bin/env python3
"""
Apply Fixes via VS Code Copilot

This script reads copilot-fix-instructions.json and applies fixes by
invoking VS Code Copilot directly through workspace edit API.

This approach uses the VS Code extension API to make edits programmatically.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict


def generate_copilot_commands(instructions: List[Dict], project_path: Path) -> str:
    """
    Generate a series of prompts that can be sent to @workspace to apply fixes.

    Returns a formatted string with all the fix requests.
    """
    commands = []
    commands.append("# Copilot Fix Commands")
    commands.append("# Copy each command below and send to @workspace in VS Code\n")

    for idx, instruction in enumerate(instructions, 1):
        file_path = instruction["file"]
        rule_id = instruction["rule_id"]
        prompt = instruction.get("prompt", "")

        # Make path relative to project if it's absolute
        if Path(file_path).is_absolute():
            try:
                file_path = str(Path(file_path).relative_to(project_path))
            except ValueError:
                pass  # Keep absolute path if it's outside project

        commands.append(f"## Fix {idx}/{len(instructions)}: {rule_id}")
        commands.append(f"File: `{file_path}`")
        commands.append("```")
        commands.append(f"@workspace {prompt}")
        commands.append(f"File: {file_path}")
        commands.append("```\n")

    return "\n".join(commands)


def apply_fixes_batch(
    instructions_file: str, project_path: str, output_file: str = None
):
    """
    Load fix instructions and apply them via Copilot programmatically.
    """
    # Load instructions
    with open(instructions_file, "r") as f:
        instructions = json.load(f)

    project_path = Path(project_path).resolve()

    print(f"📖 Loaded {len(instructions)} fix instructions")
    print(f"📁 Project path: {project_path}")

    # For now, generate commands that can be used manually
    # In the future, this could use VS Code extension API directly
    commands = generate_copilot_commands(instructions, project_path)

    if output_file:
        with open(output_file, "w") as f:
            f.write(commands)
        print(f"✓ Commands saved to: {output_file}")
    else:
        print("\n" + commands)

    print("\n💡 To apply fixes:")
    print("   1. Open VS Code Copilot Chat")
    print("   2. Send each command to @workspace")
    print("   3. Review and accept the changes")


def apply_fix_inline(instruction: Dict, project_path: Path) -> bool:
    """
    Apply a single fix by directly editing the file with the fix content.

    This reads the file, extracts the relevant section, and replaces it
    with the fixed version (if the instruction contains the full fix).
    """
    file_path_str = instruction["file"]

    # Handle absolute paths
    if Path(file_path_str).is_absolute():
        file_path = Path(file_path_str)
    else:
        file_path = project_path / file_path_str

    if not file_path.exists():
        print(f"✗ File not found: {file_path}")
        return False

    # Read current content
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if instruction has a direct fix
    if "fix_content" in instruction:
        # Direct replacement
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(instruction["fix_content"])
        return True

    # Otherwise, we need Copilot to generate the fix
    return False


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Apply fixes via VS Code Copilot",
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
        "--output", help="Output file for commands (default: print to stdout)"
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Attempt to apply fixes automatically (experimental)",
    )

    args = parser.parse_args()

    try:
        if args.auto:
            print("⚠️  Auto mode is experimental and may not work for all fixes")
            # TODO: Implement auto-apply using VS Code extension API
            print("❌ Auto mode not yet implemented")
            sys.exit(1)
        else:
            apply_fixes_batch(args.instructions, args.project, args.output)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
