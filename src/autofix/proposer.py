"""
Fix Proposer - Analyzes violations and generates fix proposals

This module takes governance violations and proposes minimal, safe fixes.
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field

from .fix_strategies import FixStrategy, FixComplexity, FixSafety, get_strategy
from engines.llm_analyzer import LLMAnalyzer
from engines.copilot_analyzer import CopilotAnalyzer
from utils.logger import logger
from utils import PathUtils
import asyncio


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
    strategy: FixStrategy
    requires_imports: List[str] = field(default_factory=list)
    removes_imports: List[str] = field(default_factory=list)
    additional_files: List[Tuple[str, str]] = field(
        default_factory=list
    )  # [(path, content)]

    @property
    def is_safe_to_auto_apply(self) -> bool:
        """Check if this fix can be auto-applied"""
        # If we have a concrete proposal (content changed), we consider it applicable
        # This matches the user's request to "apply all fixes"
        return self.proposed_content != self.original_content

    @property
    def complexity_level(self) -> str:
        """Get human-readable complexity"""
        return self.strategy.complexity.value


class FixProposer:
    """Proposes fixes for governance violations"""

    def __init__(
        self,
        project_path: str,
        llm_analyzer: Optional[LLMAnalyzer] = None,
        use_copilot: bool = True,
    ):
        """
        Initialize fix proposer with configurable analyzer

        Args:
            project_path: Root path of the project
            llm_analyzer: Optional LLM analyzer (fallback/legacy)
            use_copilot: Use GitHub Copilot for fast fixes (default: True)
        """
        self.project_path = Path(project_path)
        self.use_copilot = use_copilot
        self._fix_counter = 0

        # Initialize analyzer based on configuration
        if use_copilot:
            try:
                self.analyzer = CopilotAnalyzer()
                print("✓ Using GitHub Copilot for fast fix generation (2-8s per fix)")
            except Exception as e:
                print(f"⚠ Copilot initialization failed: {e}")
                print("  Falling back to LLM analyzer (slower)")
                self.analyzer = llm_analyzer
                self.use_copilot = False
        else:
            self.analyzer = llm_analyzer
            print("⚠ Using legacy LLM analyzer (30-90s per fix)")

        # For backward compatibility
        self.llm_analyzer = self.analyzer

    def _find_test_files_for_java_class(self, java_class_path: str) -> List[str]:
        """
        Find test files (unit tests and integration tests) for ANY Java class.

        Works for:
        - Controllers (UserController.java)
        - Services (UserService.java)
        - Repositories (UserRepository.java)
        - Entities (User.java)
        - DTOs (UserDTO.java)
        - Any other Java class

        Args:
            java_class_path: Relative path to Java file (e.g., "src/main/java/com/example/service/UserService.java")

        Returns:
            List of test file paths (relative to project root)
        """
        java_path_obj = Path(java_class_path)
        class_name = java_path_obj.stem

        # Use PathUtils to find test files
        test_files = PathUtils.find_test_files_for_class(
            str(self.project_path), class_name
        )

        # Convert to relative paths
        return [
            PathUtils.get_relative_path(str(f), str(self.project_path))
            for f in test_files
        ]

    def _find_test_files_for_controller(self, controller_path: str) -> List[str]:
        """
        Legacy method name for backward compatibility.
        Delegates to _find_test_files_for_java_class.
        """
        return self._find_test_files_for_java_class(controller_path)

    def _find_related_files(self, file_path: str, rule_id: str) -> List[str]:
        """
        Find related files that might need updates when fixing violations.

        Examples:
        - OpenAPI spec change → Find corresponding Java controllers AND their tests
        - Java controller change → Find corresponding OpenAPI spec AND controller tests
        - ANY Java file change → Find its tests (Services, Repositories, Entities, etc.)
        - DTO change → Find entities/mappers

        Args:
            file_path: Path to the file being fixed
            rule_id: The governance rule that was violated

        Returns:
            List of related file paths (relative to project root)
        """
        related_files = []
        file_path_obj = Path(file_path)

        # CASE 1: OpenAPI spec change → Find Java controller AND its tests
        if (
            file_path.endswith((".yaml", ".yml", ".json"))
            and "openapi" in file_path.lower()
        ):
            # Extract resource name from spec file (e.g., "users" from "users-api.yaml")
            spec_name = (
                file_path_obj.stem.replace("-openapi", "")
                .replace("-api", "")
                .replace("_", "")
            )

            # Search for controller files
            for controller_pattern in [
                f"**/*{spec_name.capitalize()}*Controller.java",
                f"**/*{spec_name.title()}*Controller.java",
                f"**/controller/*{spec_name}*.java",
                f"**/controllers/*{spec_name}*.java",
            ]:
                for controller_file in self.project_path.rglob(controller_pattern):
                    rel_path = str(controller_file.relative_to(self.project_path))
                    if rel_path not in related_files and "/test/" not in rel_path:
                        related_files.append(rel_path)
                        print(f"  🔗 Found related controller: {rel_path}")

                        # Now find test files for this controller
                        test_files = self._find_test_files_for_java_class(rel_path)
                        for test_file in test_files:
                            if test_file not in related_files:
                                related_files.append(test_file)
                                print(f"  🧪 Found related test: {test_file}")

        # CASE 2: Java controller change → Find OpenAPI spec AND controller tests
        elif (
            file_path.endswith(".java")
            and "Controller" in file_path
            and "/test/" not in file_path
        ):
            # Extract controller name (e.g., "UserController" → "user")
            controller_name = file_path_obj.stem.replace("Controller", "").lower()

            # Search for API spec files
            for spec_pattern in [
                f"**/{controller_name}*openapi*.yaml",
                f"**/{controller_name}*api*.yaml",
                f"**/{controller_name}*.yaml",
                f"**/openapi/**/{controller_name}*.yaml",
            ]:
                for spec_file in self.project_path.rglob(spec_pattern):
                    rel_path = str(spec_file.relative_to(self.project_path))
                    if rel_path not in related_files:
                        related_files.append(rel_path)
                        print(f"  🔗 Found related API spec: {rel_path}")

            # Find test files for this controller
            test_files = self._find_test_files_for_java_class(file_path)
            for test_file in test_files:
                if test_file not in related_files:
                    related_files.append(test_file)
                    print(f"  🧪 Found related test: {test_file}")

        # CASE 3: ANY other Java file (Service, Repository, Entity, DTO, etc.) → Find its tests
        # This handles ArchUnit violations on Services, Repositories, and any other Java class
        elif file_path.endswith(".java") and "/test/" not in file_path:
            # Find test files for this Java class
            test_files = self._find_test_files_for_java_class(file_path)
            for test_file in test_files:
                if test_file not in related_files:
                    related_files.append(test_file)
                    print(f"  🧪 Found related test: {test_file}")

        # CASE 4: DTO/Entity changes → Find mappers (future enhancement)
        # Could add mapper/converter detection here

        return related_files

    async def propose_fixes(self, violations: List[Dict]) -> List[ProposedFix]:
        """
        Generate fix proposals for a list of violations with batching and parallelization.
        """
        # Group violations by file path
        file_batches: Dict[str, List[Dict]] = {}
        for violation in violations:
            api_message = violation.get("message", "")
            file_path = self._extract_file_path(violation, api_message)
            if not file_path:
                continue

            if file_path not in file_batches:
                file_batches[file_path] = []
            file_batches[file_path].append(violation)

        if not file_batches:
            return []

        # Process files in parallel with a concurrency limit
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent LLM sessions

        async def process_file(path, v_list) -> List[ProposedFix]:
            async with semaphore:
                try:
                    return await self._generate_fixes_for_file(path, v_list)
                except Exception as e:
                    print(f"Error processing fixes for {path}: {e}")
                    return []

        tasks = [process_file(path, v_list) for path, v_list in file_batches.items()]
        results = await asyncio.gather(*tasks)

        all_proposals = []
        for file_proposals in results:
            all_proposals.extend(file_proposals)

        return all_proposals

    async def _generate_fixes_for_file(
        self, file_path: str, violations: List[Dict]
    ) -> List[ProposedFix]:
        """
        Process all violations for a single file.
        Attempts to apply specific strategies first, then falls back to batch LLM fix.
        """
        full_path = self.project_path / file_path
        if not full_path.exists():
            return []

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                original_content = f.read()
        except Exception:
            return []

        current_content = original_content
        fast_proposals = []
        llm_violations = []

        # 1. Apply fast fixes first
        for violation in violations:
            rule_id = violation.get("rule") or violation.get("rule_id", "unknown")
            strategy = get_strategy(rule_id)

            # If no strategy, it's an LLM candidate
            if not strategy:
                llm_violations.append(violation)
                continue

            # If strategy has a specific function, try applying it
            fix_method = getattr(self, strategy.fix_function, None)
            if fix_method:
                try:
                    line_number = self._extract_line_number(
                        violation, violation.get("message", "")
                    )
                    result = fix_method(
                        current_content, violation.get("message", ""), line_number
                    )
                    if result:
                        current_content, _, _ = (
                            result  # We use the updated content for next steps
                        )
                        # We still create a proposal so the user knows what happened
                        # But wait, if we merge them all into one batch fix, it might be cleaner
                        fast_proposals.append(violation)
                    else:
                        llm_violations.append(violation)
                except Exception:
                    llm_violations.append(violation)
            else:
                # Manual or no function strategy -> LLM candidate
                llm_violations.append(violation)

        # 2. If we have remaining violations, use batch LLM fix
        final_content = current_content
        if llm_violations and self.analyzer:
            final_content = await self.analyzer.generate_batch_fix(
                current_content, llm_violations
            )

        if final_content == original_content:
            return []

        # 3. Create a single consolidated ProposedFix for the whole file
        self._fix_counter += 1
        fix_id = f"fix-{self._fix_counter:04d}-batch"

        # Summarize rules
        rules_fixed = list(set([v.get("rule") for v in violations if v.get("rule")]))
        explanation = (
            f"Consolidated fix for {len(violations)} violations in `{file_path}`.\n\n"
        )
        explanation += "Rules addressed: " + ", ".join(rules_fixed)

        # Special handling for cross-file fixes if the LLM suggests them?
        # For now, we just stick to this file in batch.
        # Cross-file fixes are usually 1-to-1 (path -> java controller).

        return [
            ProposedFix(
                fix_id=fix_id,
                rule_id="multiple-violations",
                file_path=file_path,
                line_number=None,
                original_content=original_content,
                proposed_content=final_content,
                explanation=explanation,
                strategy=FixStrategy(
                    rule_id="multi-fix",
                    description="Batch fix for multiple violations",
                    complexity=FixComplexity.MODERATE,
                    safety=FixSafety.REVIEW_REQUIRED,
                    fix_function="none",
                    explanation_template=explanation,
                ),
            )
        ]

    async def _generate_fix(
        self, violation: Dict, strategy: FixStrategy
    ) -> Optional[ProposedFix]:
        """Generate a specific fix for a violation"""

        # Extract violation details
        rule_id = strategy.rule_id
        message = violation.get("message", "")
        file_path = self._extract_file_path(violation, message)
        line_number = self._extract_line_number(violation, message)

        if not file_path:
            return None

        # Read file content
        try:
            full_path = self.project_path / file_path
            if not full_path.exists():
                return None

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return None

        # Generate fix based on rule type
        fix_method = getattr(self, strategy.fix_function, None)
        if not fix_method:
            # Fix function not implemented yet or manual strategy
            return await self._create_manual_fix_proposal(
                violation, strategy, file_path, line_number, content
            )

        try:
            result = fix_method(content, message, line_number)
            if not result:
                return None

            proposed_content, requires_imports, removes_imports = result

            self._fix_counter += 1
            fix_id = f"fix-{self._fix_counter:04d}"

            # Find related files that might need updates
            related_files = self._find_related_files(file_path, rule_id)

            proposed_fix = ProposedFix(
                fix_id=fix_id,
                rule_id=rule_id,
                file_path=file_path,
                line_number=line_number,
                original_content=content,
                proposed_content=proposed_content,
                explanation=strategy.explanation_template,
                strategy=strategy,
                requires_imports=requires_imports,
                removes_imports=removes_imports,
            )

            # Add related files as metadata for Copilot to consider
            if related_files:
                # Store in additional_files field for later reference
                proposed_fix.additional_files = [
                    (rel_file, "RELATED_FILE_REFERENCE") for rel_file in related_files
                ]

            return proposed_fix
        except Exception:
            # Fix generation failed
            return None

    async def _create_manual_fix_proposal(
        self,
        violation: Dict,
        strategy: FixStrategy,
        file_path: str,
        line_number: Optional[int],
        content: str,
    ) -> ProposedFix:
        """Create a manual-only fix proposal with guidance, or attempt AI fix"""

        # Try to use LLM to generate a fix if available
        proposed_content = content
        additional_files = []
        explanation = f"{strategy.explanation_template}\n\n"
        is_safe = False

        if self.analyzer:
            try:
                # Check if this is an OpenAPI violation that might affect Java code
                related_java_files = []
                if file_path.endswith((".yaml", ".yml", ".json")):
                    related_java_files = self._find_related_java_files(violation)

                if related_java_files:
                    # Multi-file fix
                    files_to_fix = {file_path: content}
                    for java_path in related_java_files:
                        try:
                            with open(
                                self.project_path / java_path, "r", encoding="utf-8"
                            ) as f:
                                files_to_fix[java_path] = f.read()
                        except Exception:
                            continue

                    fixed_files = await self.analyzer.generate_cross_file_fix(
                        files_to_fix, violation
                    )

                    if file_path in fixed_files:
                        proposed_content = fixed_files[file_path]
                        is_safe = True

                    for path, fixed_content in fixed_files.items():
                        if path != file_path:
                            additional_files.append((path, fixed_content))

                else:
                    # Single file fix
                    generated_content = await self.analyzer.generate_fix(
                        content, violation
                    )
                    if generated_content != content:
                        proposed_content = generated_content
                        is_safe = True

                if is_safe:
                    explanation += "**Auto-Generated Fix**: Copilot has proposed a fix for this violation. "
                    if additional_files:
                        explanation += f"This fix also suggests changes in {len(additional_files)} related file(s)."
                    explanation += " Please review carefully."
            except Exception as e:
                print(f"DEBUG: AI fix failed: {e}")
                pass

        if not is_safe:
            explanation += "**Manual Action Required**: This fix cannot be automated. "
            explanation += "Please review the violation and apply the fix manually."

        self._fix_counter += 1
        fix_id = (
            f"fix-{self._fix_counter:04d}-manual"
            if not is_safe
            else f"fix-{self._fix_counter:04d}-ai"
        )

        return ProposedFix(
            fix_id=fix_id,
            rule_id=strategy.rule_id,
            file_path=file_path,
            line_number=line_number,
            original_content=content,
            proposed_content=proposed_content,
            explanation=explanation,
            strategy=strategy,
            requires_imports=[],
            removes_imports=[],
            additional_files=additional_files,
        )

    # ========================================================================
    # FIX IMPLEMENTATION METHODS
    # ========================================================================

    def fix_java_util_logging(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Replace java.util.logging with SLF4J"""

        # Replace imports
        new_content = content.replace(
            "import java.util.logging.Logger;",
            "import org.slf4j.Logger;\nimport org.slf4j.LoggerFactory;",
        )

        # Replace Logger.getGlobal() calls
        new_content = re.sub(
            r"java\.util\.logging\.Logger\.getGlobal\(\)",
            "LoggerFactory.getLogger(getClass())",
            new_content,
        )

        # Replace field declarations
        new_content = re.sub(
            r"private\s+java\.util\.logging\.Logger\s+(\w+);",
            r"private static final Logger \1 = LoggerFactory.getLogger(\1.class);",
            new_content,
        )

        # Replace parameter types
        new_content = re.sub(r"java\.util\.logging\.Logger", "Logger", new_content)

        if new_content == content:
            return None

        return (
            new_content,
            ["org.slf4j.Logger", "org.slf4j.LoggerFactory"],
            ["java.util.logging.Logger"],
        )

    def fix_secure_random(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Replace Random with SecureRandom"""

        # Replace imports
        new_content = content.replace(
            "import java.util.Random;", "import java.security.SecureRandom;"
        )

        # Replace class usage
        new_content = re.sub(r"\bnew\s+Random\s*\(", "new SecureRandom(", new_content)

        new_content = re.sub(r"\bRandom\s+(\w+)\s*=", r"SecureRandom \1 =", new_content)

        if new_content == content:
            return None

        return (new_content, ["java.security.SecureRandom"], ["java.util.Random"])

    def fix_serial_version_uid(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Fix serialVersionUID to be static final"""

        # Find the incorrect serialVersionUID declaration
        pattern = r"(public|private|protected)?\s+int\s+serialVersionUID\s*=\s*(\d+);"
        match = re.search(pattern, content)

        if not match:
            return None

        # Replace with correct declaration
        new_content = re.sub(
            pattern, r"private static final long serialVersionUID = \2L;", content
        )

        if new_content == content:
            return None

        return (new_content, [], [])

    def fix_transactional_layer(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Remove @Transactional from controller"""

        # Remove @Transactional annotation from class level
        new_content = re.sub(r"@Transactional\s*\n", "", content)

        # Also remove the import if no other usage
        if "@Transactional" not in new_content:
            new_content = re.sub(
                r"import\s+org\.springframework\.transaction\.annotation\.Transactional;\s*\n",
                "",
                new_content,
            )

        if new_content == content:
            return None

        return (
            new_content,
            [],
            ["org.springframework.transaction.annotation.Transactional"],
        )

    def fix_std_streams(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Replace System.out/err with logger"""

        # Check if logger field exists
        has_logger = re.search(r"private\s+static\s+final\s+Logger\s+\w+", content)

        new_content = content

        # Add logger field if not present
        if not has_logger:
            # Find class declaration
            class_match = re.search(r"(public\s+class\s+\w+[^{]*\{)", new_content)
            if class_match:
                class_decl = class_match.group(1)
                logger_field = (
                    "\n    private static final Logger logger = LoggerFactory.getLogger("
                    + self._extract_class_name(content)
                    + ".class);\n"
                )
                new_content = new_content.replace(class_decl, class_decl + logger_field)

        # Replace System.out.println
        new_content = re.sub(
            r"System\.out\.println\((.*?)\);", r"logger.info(\1);", new_content
        )

        # Replace System.err.println
        new_content = re.sub(
            r"System\.err\.println\((.*?)\);", r"logger.error(\1);", new_content
        )

        if new_content == content:
            return None

        return (new_content, ["org.slf4j.Logger", "org.slf4j.LoggerFactory"], [])

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _extract_file_path(self, violation: Dict, message: str) -> Optional[str]:
        """Extract file path from violation"""

        # Try direct file field
        if "file" in violation:
            return violation["file"]

        # Try source field (used by Spectral)
        if "source" in violation:
            return violation["source"]

        # Try to parse from message
        # ArchUnit messages often contain class names like "Class <com.example.Foo>"
        class_match = re.search(r"Class <([^>]+)>", message)
        if class_match:
            class_name = class_match.group(1)
            # Convert to file path
            file_path = class_name.replace(".", "/") + ".java"
            return f"src/main/java/{file_path}"

        # Try to find Java class reference
        class_match = re.search(r"([a-z][a-z0-9_]*\.)+[A-Z][a-zA-Z0-9_]*", message)
        if class_match:
            class_name = class_match.group(0)
            file_path = class_name.replace(".", "/") + ".java"
            return f"src/main/java/{file_path}"

        return None

    def _extract_line_number(self, violation: Dict, message: str) -> Optional[int]:
        """Extract line number from violation"""

        # Try direct line field
        if "line" in violation and violation["line"]:
            return int(violation["line"])

        # Try to parse from message
        line_match = re.search(r"line (\d+)", message, re.IGNORECASE)
        if line_match:
            return int(line_match.group(1))

        return None

    def _extract_class_name(self, content: str) -> str:
        """Extract class name from Java content"""
        match = re.search(r"public\s+class\s+(\w+)", content)
        if match:
            return match.group(1)
        return "UnknownClass"

    def _find_related_java_files(self, violation: Dict) -> List[str]:
        """Find Java files related to an OpenAPI violation"""
        path = violation.get("path", "")
        if not path:
            return []

        # Extract the actual API path from the Spectral path (e.g. "paths./users.get")
        api_path = None
        if path.startswith("paths."):
            parts = path.split(".")
            if len(parts) > 1:
                api_path = parts[1]

        if not api_path:
            return []

        related_files = []

        # Pattern search in Java files for the API path
        # Look for @RequestMapping("/path"), @GetMapping("/path"), etc.
        try:
            # Simple heuristic: grep for the path
            # We look for files containing the path string
            import subprocess

            cmd = ["grep", "-l", "-r", api_path, str(self.project_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                files = result.stdout.strip().split("\n")
                for f in files:
                    # Include all Java files (production + test) - tests may need updates too
                    if f.endswith(".java"):
                        rel_path = os.path.relpath(f, self.project_path)
                        related_files.append(rel_path)
        except Exception:
            pass

        return list(set(related_files))

    # ========================================================================
    # API/OPENAPI FIX FUNCTIONS
    # ========================================================================

    def fix_kebab_case_paths(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Convert API paths to kebab-case in OpenAPI spec and Java controllers"""
        try:
            spec = yaml.safe_load(content)
            if "paths" not in spec:
                return None

            modified = False
            new_paths = {}
            path_changes = {}

            for path, path_item in spec["paths"].items():
                # Convert camelCase or snake_case to kebab-case
                new_path = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", path).lower()
                new_path = new_path.replace("_", "-")

                if new_path != path:
                    modified = True
                    path_changes[path] = new_path
                    new_paths[new_path] = path_item
                else:
                    new_paths[path] = path_item

            if not modified:
                return None

            spec["paths"] = new_paths
            new_content = yaml.dump(spec, default_flow_style=False, sort_keys=False)

            # Find and update Java controllers
            additional_files = []
            try:
                for old_path in path_changes.keys():
                    controllers = self._find_java_controllers_for_path(old_path)
                    for controller in controllers:
                        updated_java = self._update_java_controller_paths(
                            controller, path_changes
                        )
                        if updated_java:
                            rel_path = controller.relative_to(self.project_path)
                            additional_files.append((str(rel_path), updated_java))
                            print(f"  ✓ Will update Java controller: {rel_path}")
            except Exception as e:
                print(f"  ⚠ Warning: Could not update Java controllers: {e}")

            return (new_content, [], [])

        except Exception:
            return None

    def fix_plural_resources(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Convert singular resource names to plural in OpenAPI spec and Java controllers"""
        try:
            spec = yaml.safe_load(content)
            if "paths" not in spec:
                return None

            modified = False
            new_paths = {}
            path_changes = {}

            # Simple pluralization rules
            plurals = {
                "user": "users",
                "product": "products",
                "order": "orders",
                "customer": "customers",
                "item": "items",
                "category": "categories",
                "company": "companies",
            }

            for path, path_item in spec["paths"].items():
                new_path = path
                for singular, plural in plurals.items():
                    # Match /singular/ or /singular{param}
                    pattern = f"/{singular}(/|{{)"
                    replacement = f"/{plural}\\1"
                    updated = re.sub(pattern, replacement, new_path)
                    if updated != new_path:
                        path_changes[path] = updated
                        new_path = updated

                if new_path != path:
                    modified = True
                    new_paths[new_path] = path_item
                else:
                    new_paths[path] = path_item

            if not modified:
                return None

            spec["paths"] = new_paths
            new_content = yaml.dump(spec, default_flow_style=False, sort_keys=False)

            # Find and update Java controllers
            additional_files = []
            try:
                for old_path in path_changes.keys():
                    controllers = self._find_java_controllers_for_path(old_path)
                    for controller in controllers:
                        updated_java = self._update_java_controller_paths(
                            controller, path_changes
                        )
                        if updated_java:
                            rel_path = controller.relative_to(self.project_path)
                            additional_files.append((str(rel_path), updated_java))
                            print(f"  ✓ Will update Java controller: {rel_path}")
            except Exception as e:
                print(f"  ⚠ Warning: Could not update Java controllers: {e}")

            return (new_content, [], [])

        except Exception:
            return None

    def fix_standard_http_verbs(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Remove verbs from API paths in OpenAPI spec"""
        import yaml

        try:
            spec = yaml.safe_load(content)
            if "paths" not in spec:
                return None

            modified = False
            new_paths = {}

            # Common verbs to remove
            verbs = [
                "get",
                "create",
                "update",
                "delete",
                "fetch",
                "retrieve",
                "list",
                "add",
                "remove",
            ]

            for path, path_item in spec["paths"].items():
                new_path = path
                for verb in verbs:
                    # Remove verb from path segments
                    new_path = re.sub(
                        f"/{verb}([A-Z])", lambda m: "/" + m.group(1).lower(), new_path
                    )
                    new_path = re.sub(f"/-{verb}", "", new_path)
                    new_path = re.sub(f"/{verb}/", "/", new_path)

                # Clean up double slashes
                new_path = re.sub(r"/+", "/", new_path)

                if new_path != path:
                    modified = True
                    new_paths[new_path] = path_item
                else:
                    new_paths[path] = path_item

            if not modified:
                return None

            spec["paths"] = new_paths
            new_content = yaml.dump(spec, default_flow_style=False, sort_keys=False)
            return (new_content, [], [])

        except Exception:
            return None

    def fix_uuid_format(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Add format: uuid to UUID parameters in OpenAPI spec"""
        import yaml

        try:
            spec = yaml.safe_load(content)
            modified = False

            def add_uuid_format(obj):
                nonlocal modified
                if isinstance(obj, dict):
                    # Check if this is a UUID parameter without format
                    if "type" in obj and obj["type"] == "string":
                        name = obj.get("name", "").lower()
                        description = obj.get("description", "").lower()
                        if (
                            "id" in name or "uuid" in name or "uuid" in description
                        ) and "format" not in obj:
                            obj["format"] = "uuid"
                            modified = True

                    # Recurse through all dict values
                    for value in obj.values():
                        add_uuid_format(value)
                elif isinstance(obj, list):
                    for item in obj:
                        add_uuid_format(item)

            add_uuid_format(spec)

            if not modified:
                return None

            new_content = yaml.dump(spec, default_flow_style=False, sort_keys=False)
            return (new_content, [], [])

        except Exception:
            return None

    def fix_camelcase_properties(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Convert property names to camelCase in OpenAPI spec"""
        import yaml

        try:
            spec = yaml.safe_load(content)
            if "components" not in spec or "schemas" not in spec["components"]:
                return None

            modified = False

            def to_camel_case(snake_str):
                components = snake_str.split("_")
                return components[0] + "".join(x.title() for x in components[1:])

            def fix_properties(obj):
                nonlocal modified
                if isinstance(obj, dict):
                    if "properties" in obj:
                        new_props = {}
                        for prop_name, prop_value in obj["properties"].items():
                            if "_" in prop_name:
                                new_name = to_camel_case(prop_name)
                                new_props[new_name] = prop_value
                                modified = True
                            else:
                                new_props[prop_name] = prop_value
                        obj["properties"] = new_props

                    for value in obj.values():
                        fix_properties(value)
                elif isinstance(obj, list):
                    for item in obj:
                        fix_properties(item)

            fix_properties(spec)

            if not modified:
                return None

            new_content = yaml.dump(spec, default_flow_style=False, sort_keys=False)
            return (new_content, [], [])

        except Exception:
            return None

    def fix_response_envelope(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Wrap responses in standard envelope - requires manual review"""
        # This is complex and requires understanding of the API design
        # We'll provide guidance but mark as manual
        return None

    def fix_pagination_structure(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Add standard pagination fields to OpenAPI spec"""
        import yaml

        try:
            spec = yaml.safe_load(content)
            modified = False

            pagination_schema = {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "Current page number"},
                    "pageSize": {
                        "type": "integer",
                        "description": "Number of items per page",
                    },
                    "totalItems": {
                        "type": "integer",
                        "description": "Total number of items",
                    },
                    "totalPages": {
                        "type": "integer",
                        "description": "Total number of pages",
                    },
                },
            }

            def add_pagination(obj, path=""):
                nonlocal modified
                if isinstance(obj, dict):
                    # Check if this looks like a paginated response
                    if (
                        "type" in obj
                        and obj["type"] == "object"
                        and "properties" in obj
                    ):
                        props = obj["properties"]
                        has_items = (
                            "items" in props or "data" in props or "results" in props
                        )
                        missing_pagination = "page" not in props

                        if has_items and missing_pagination:
                            # Add pagination fields
                            obj["properties"].update(pagination_schema["properties"])
                            modified = True

                    for key, value in obj.items():
                        add_pagination(value, f"{path}.{key}")
                elif isinstance(obj, list):
                    for item in obj:
                        add_pagination(item, path)

            add_pagination(spec)

            if not modified:
                return None

            new_content = yaml.dump(spec, default_flow_style=False, sort_keys=False)
            return (new_content, [], [])

        except Exception:
            return None

    def fix_schema_depth(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Reduce schema nesting depth - requires manual review"""
        # Complex refactoring, mark as manual
        return None

    def fix_error_responses(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Add standard error responses to OpenAPI spec"""
        import yaml

        try:
            spec = yaml.safe_load(content)
            if "paths" not in spec:
                return None

            modified = False

            error_responses = {
                "400": {
                    "description": "Bad Request",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "error": {"type": "string"},
                                    "message": {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "404": {
                    "description": "Not Found",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "error": {"type": "string"},
                                    "message": {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "500": {
                    "description": "Internal Server Error",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "error": {"type": "string"},
                                    "message": {"type": "string"},
                                },
                            }
                        }
                    },
                },
            }

            for path, path_item in spec["paths"].items():
                for method, operation in path_item.items():
                    if method in [
                        "get",
                        "post",
                        "put",
                        "delete",
                        "patch",
                    ] and isinstance(operation, dict):
                        if "responses" not in operation:
                            operation["responses"] = {}

                        # Add missing error responses
                        for code, response in error_responses.items():
                            if code not in operation["responses"]:
                                operation["responses"][code] = response
                                modified = True

            if not modified:
                return None

            new_content = yaml.dump(spec, default_flow_style=False, sort_keys=False)
            return (new_content, [], [])

        except Exception:
            return None

    def fix_description_required(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Add placeholder descriptions to OpenAPI spec"""
        import yaml

        try:
            spec = yaml.safe_load(content)
            modified = False

            def add_descriptions(obj, context=""):
                nonlocal modified
                if isinstance(obj, dict):
                    # Add description if missing and this is an operation or schema
                    if "description" not in obj:
                        if "operationId" in obj:
                            obj["description"] = (
                                f"TODO: Add description for {obj['operationId']}"
                            )
                            modified = True
                        elif "type" in obj and context == "schema":
                            obj["description"] = "TODO: Add description for this schema"
                            modified = True
                        elif "name" in obj and context == "parameter":
                            obj["description"] = (
                                f"TODO: Add description for parameter {obj['name']}"
                            )
                            modified = True

                    # Add summary if missing for operations
                    if "operationId" in obj and "summary" not in obj:
                        obj["summary"] = f"TODO: Add summary for {obj['operationId']}"
                        modified = True

                    # Recurse with context
                    for key, value in obj.items():
                        new_context = context
                        if key == "schemas":
                            new_context = "schema"
                        elif key == "parameters":
                            new_context = "parameter"
                        add_descriptions(value, new_context)
                elif isinstance(obj, list):
                    for item in obj:
                        add_descriptions(item, context)

            add_descriptions(spec)

            if not modified:
                return None

            new_content = yaml.dump(spec, default_flow_style=False, sort_keys=False)
            return (new_content, [], [])

        except Exception:
            return None

    def fix_versioning_required(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Add version prefix to API paths in YAML and update Java controllers"""
        try:
            spec = yaml.safe_load(content)
            if "paths" not in spec:
                return None

            modified = False
            new_paths = {}
            path_changes = {}

            for path, path_item in spec["paths"].items():
                # Check if path already has version
                if not re.match(r"^/v\d+/", path):
                    # Add /v1/ prefix
                    new_path = "/v1" + path
                    new_paths[new_path] = path_item
                    path_changes[path] = new_path
                    modified = True
                else:
                    new_paths[path] = path_item

            if not modified:
                return None

            spec["paths"] = new_paths
            new_content = yaml.dump(spec, default_flow_style=False, sort_keys=False)

            # Find and update Java controllers
            additional_files = []
            try:
                for old_path in path_changes.keys():
                    controllers = self._find_java_controllers_for_path(old_path)
                    for controller in controllers:
                        updated_java = self._update_java_controller_paths(
                            controller, path_changes
                        )
                        if updated_java:
                            rel_path = controller.relative_to(self.project_path)
                            additional_files.append((str(rel_path), updated_java))
                            print(f"  ✓ Will update Java controller: {rel_path}")
            except Exception as e:
                print(f"  ⚠ Warning: Could not update Java controllers: {e}")

            return (new_content, [], [])

        except Exception:
            return None

    def fix_created_returns_resource(
        self, content: str, message: str, line_number: Optional[int]
    ) -> Optional[Tuple[str, List[str], List[str]]]:
        """Ensure POST operations return created resource"""
        import yaml

        try:
            spec = yaml.safe_load(content)
            if "paths" not in spec:
                return None

            modified = False

            for path, path_item in spec["paths"].items():
                if "post" in path_item:
                    post_op = path_item["post"]
                    if "responses" in post_op:
                        # Check if 201 response exists and has content
                        if "201" in post_op["responses"]:
                            response_201 = post_op["responses"]["201"]
                            if "content" not in response_201:
                                response_201["content"] = {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "description": "The created resource",
                                        }
                                    }
                                }
                                modified = True

            if not modified:
                return None

            new_content = yaml.dump(spec, default_flow_style=False, sort_keys=False)
            return (new_content, [], [])

        except Exception:
            return None

    # ========================================================================
    # JAVA CONTROLLER UPDATE FUNCTIONS
    # ========================================================================

    def _find_java_controllers_for_path(self, api_path: str) -> List[Path]:
        """Find Java controller files that define a specific API path"""
        controllers = []

        # Search for Java files with @RequestMapping, @GetMapping, etc.
        try:
            # Normalize path for search (remove version prefix, params)
            search_path = re.sub(r"/v\d+", "", api_path)  # Remove /v1/
            search_path = re.sub(r"\{[^}]+\}", "", search_path)  # Remove {id}
            search_path = search_path.strip("/")

            # Search for files containing this path (include test files - they need updates too)
            for java_file in self.project_path.rglob("**/*Controller.java"):
                try:
                    with open(java_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Check if this controller has the path
                    # Look for @GetMapping("/path"), @PostMapping("/path"), etc.
                    if search_path in content or api_path in content:
                        # More precise check
                        patterns = [
                            rf'@\w+Mapping\(["\'].*{re.escape(search_path)}',
                            rf'@RequestMapping\(["\'].*{re.escape(search_path)}',
                        ]
                        if any(re.search(p, content) for p in patterns):
                            controllers.append(java_file)
                except Exception:
                    continue
        except Exception:
            pass

        return controllers

    def _update_java_controller_paths(
        self, java_file: Path, path_changes: Dict[str, str]
    ) -> Optional[str]:
        """
        Update Java controller to match new API paths

        Args:
            java_file: Path to Java controller file
            path_changes: Dict of old_path -> new_path mappings

        Returns:
            Updated Java content or None if no changes
        """
        try:
            with open(java_file, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Process each path change
            for old_path, new_path in path_changes.items():
                # Extract version prefix if present
                version_match = re.match(r"^(/v\d+)", new_path)
                version_prefix = version_match.group(1) if version_match else None

                # Remove version from paths for mapping comparison
                old_path_no_version = re.sub(r"^/v\d+", "", old_path)
                new_path_no_version = re.sub(r"^/v\d+", "", new_path)

                # 1. Add @RequestMapping with version at class level if needed
                if (
                    version_prefix
                    and f'@RequestMapping("{version_prefix}")' not in content
                ):
                    # Find class declaration
                    class_pattern = r"(@(?:Rest)?Controller)\s*\n(public\s+class\s+\w+)"

                    def add_request_mapping(match):
                        return f'{match.group(1)}\n@RequestMapping("{version_prefix}")\n{match.group(2)}'

                    content = re.sub(class_pattern, add_request_mapping, content)

                    # Add import if not present
                    if (
                        "import org.springframework.web.bind.annotation.RequestMapping;"
                        not in content
                    ):
                        # Find last import
                        import_pattern = r"(import\s+[^;]+;)\s*\n\s*\n"
                        if re.search(import_pattern, content):
                            content = re.sub(
                                import_pattern,
                                r"\1\nimport org.springframework.web.bind.annotation.RequestMapping;\n\n",
                                content,
                                count=1,
                            )

                # 2. Update method-level mappings
                # Fix casing (e.g., /Users -> /users)
                # Note: Parsing API URL paths from OpenAPI spec (not file paths)
                old_path_segments = old_path_no_version.split("/")
                new_path_segments = new_path_no_version.split("/")

                for old_seg, new_seg in zip(old_path_segments, new_path_segments):
                    if old_seg and new_seg and old_seg != new_seg:
                        # Replace in @GetMapping, @PostMapping, etc.
                        mapping_pattern = (
                            rf'(@\w+Mapping\(["\'])([^"\']*{re.escape(old_seg)}[^"\']*)'
                        )

                        def replace_segment(match):
                            prefix = match.group(1)
                            path = match.group(2)
                            updated_path = path.replace(old_seg, new_seg)
                            return f"{prefix}{updated_path}"

                        content = re.sub(mapping_pattern, replace_segment, content)

                # 3. Convert snake_case to kebab-case in paths
                # e.g., /user_profile -> /user-profile
                snake_case_pattern = r'(@\w+Mapping\(["\'])([^"\']*_[^"\']*)'

                def convert_to_kebab(match):
                    prefix = match.group(1)
                    path = match.group(2)
                    kebab_path = path.replace("_", "-")
                    return f"{prefix}{kebab_path}"

                content = re.sub(snake_case_pattern, convert_to_kebab, content)

            # Return None if no changes made
            if content == original_content:
                return None

            return content

        except Exception as e:
            logger.warning(f"Failed to update Java controller {java_file}: {e}")
            return None

    def _get_path_changes_from_yaml(
        self, old_content: str, new_content: str
    ) -> Dict[str, str]:
        """
        Extract path changes from YAML diff

        Returns:
            Dict of old_path -> new_path
        """
        try:
            old_spec = yaml.safe_load(old_content)
            new_spec = yaml.safe_load(new_content)

            path_changes = {}

            old_paths = set(old_spec.get("paths", {}).keys())
            new_paths = set(new_spec.get("paths", {}).keys())

            # Simple approach: match by path similarity
            for old_path in old_paths:
                # Remove version and params for comparison
                old_normalized = re.sub(r"/v\d+", "", old_path)
                old_normalized = re.sub(r"\{[^}]+\}", "{id}", old_normalized)

                for new_path in new_paths:
                    new_normalized = re.sub(r"/v\d+", "", new_path)
                    new_normalized = re.sub(r"\{[^}]+\}", "{id}", new_normalized)

                    # If normalized paths are similar or match
                    if old_normalized.lower().replace("_", "-").replace(
                        " ", ""
                    ) == new_normalized.lower().replace("_", "-").replace(" ", ""):
                        if old_path != new_path:
                            path_changes[old_path] = new_path
                        break

            return path_changes

        except Exception:
            return {}
