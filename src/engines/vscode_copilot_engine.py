"""
VS Code Copilot Integration Engine

Leverages VS Code's built-in GitHub Copilot to apply governance fixes
without requiring API tokens or external LLM infrastructure.

This approach:
1. Uses VS Code's Copilot Chat API (no tokens needed)
2. Pre-defined fix strategies as structured prompts
3. Direct file editing without git operations
4. Much faster than external LLM calls
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
import json

from autofix.fix_strategies import FixStrategy, ALL_STRATEGIES
from utils.logger import logger
from engines.controller_change_generator import ControllerChangeGenerator  # ⭐ NEW


@dataclass
class SecondaryFix:
    """
    Represents a required change to a related file (e.g., controller update)
    """

    file_path: str
    change_type: str  # 'response_status', 'response_wrapper', 'add_import', etc.
    reason: str
    old_code: Optional[str] = None
    new_code: Optional[str] = None
    search_pattern: Optional[str] = None
    instruction: Optional[str] = None


@dataclass
class CopilotFixInstruction:
    """
    Structured instruction for VS Code Copilot to apply a fix.
    This is what we'll feed to Copilot Chat.
    """

    rule_id: str
    file_path: str
    violation_message: str
    fix_strategy: FixStrategy
    context_lines: Tuple[int, int]  # Start and end line numbers
    related_files: List[str] = field(
        default_factory=list
    )  # Related files that might need updates
    secondary_fixes: List[SecondaryFix] = field(
        default_factory=list
    )  # ⭐ NEW: Controller updates

    def to_copilot_prompt(self) -> str:
        """
        Generate a precise, actionable prompt for Copilot Chat

        This prompt is optimized for:
        - Clear, unambiguous instructions
        - Minimal token usage
        - Direct code generation
        - No markdown wrappers
        """
        # Build related files note
        related_files_note = ""
        if self.related_files:
            related_files_note = f"""
**⚠️ IMPORTANT - Related Files Found**:
This change affects: {self.file_path}
Please also check these related files for consistency:
{chr(10).join(f"  - {rf}" for rf in self.related_files)}

After fixing {Path(self.file_path).name}, verify the related files are still aligned.
"""

        # ⭐ NEW: Build controller update instructions
        controller_updates = ""
        if self.secondary_fixes:
            controller_updates = """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 CRITICAL: MULTI-FILE UPDATE REQUIRED 🚨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This OpenAPI fix requires corresponding controller updates to maintain consistency.
You MUST apply ALL changes below AFTER fixing the OpenAPI spec:

"""
            for idx, fix in enumerate(self.secondary_fixes, 1):
                controller_updates += f"""
**Controller Update {idx}: {Path(fix.file_path).name}**
Reason: {fix.reason}

"""
                if fix.old_code and fix.new_code:
                    controller_updates += f"""
Change Required:
```java
// OLD CODE (remove):
{fix.old_code}

// NEW CODE (replace with):
{fix.new_code}
```
"""

                if fix.instruction:
                    controller_updates += f"""
Instructions:
{fix.instruction}
"""

            controller_updates += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Apply Changes in This Order**:
1. Fix primary file (OpenAPI spec)
2. Fix each related controller file (listed above)
3. Verify all files are consistent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        return f"""Fix this code violation following the exact strategy provided.

**Rule**: {self.rule_id}
**Issue**: {self.violation_message}
**Fix Strategy**: {self.fix_strategy.description}
{related_files_note}{controller_updates}
**Required Changes**:
{self._get_specific_instructions()}

**Constraints**:
- Return ONLY the fixed code
- NO markdown code blocks
- Preserve all formatting and style
- Maintain exact indentation
- Keep all existing imports unless specified
{"- Add imports: " + ", ".join(self.fix_strategy.requires_imports) if self.fix_strategy.requires_imports else ""}

Apply the fix now."""

    def _get_specific_instructions(self) -> str:
        """Get rule-specific instructions for common patterns"""
        rule_id = self.rule_id

        # Pre-defined fix instructions for each rule type
        RULE_INSTRUCTIONS = {
            # Coding rules
            "coding-no-std-streams": """
1. Replace System.out.println() with logger.info()
2. Replace System.out.print() with logger.debug()
3. Replace System.err.println() with logger.error()
4. Add: private static final Logger logger = LoggerFactory.getLogger(ClassName.class);
""",
            "coding-no-generic-exceptions": """
1. Replace 'throws Exception' with specific exception type (e.g., IllegalArgumentException, IOException)
2. Replace 'throw new Exception' with specific exception
3. Choose exception based on context:
   - IllegalArgumentException for invalid parameters
   - IllegalStateException for invalid state
   - UnsupportedOperationException for unsupported operations
   - IOException for I/O errors
   - RuntimeException only if truly generic error
""",
            "coding-no-field-injection": """
1. Remove @Autowired from fields
2. Create constructor with all dependency parameters
3. Add @Autowired to constructor (or omit if single constructor)
4. Assign fields in constructor
""",
            "coding-no-jodatime": """
1. Replace org.joda.time.DateTime with java.time.ZonedDateTime or LocalDateTime
2. Replace org.joda.time.LocalDate with java.time.LocalDate
3. Replace org.joda.time.LocalTime with java.time.LocalTime
4. Update all method calls to use java.time API
""",
            "coding-no-java-util-logging": """
1. Replace java.util.logging.Logger with org.slf4j.Logger
2. Replace Logger.getLogger() with LoggerFactory.getLogger()
3. Update all logging calls (info, warning -> warn, severe -> error)
""",
            # Security rules
            "security-use-secure-random": """
1. Replace 'new Random()' with 'new SecureRandom()'
2. Replace 'Random rand' with 'SecureRandom rand'
3. Update all variable declarations and usages
""",
            "security-serial-version-uid": """
1. Add after class declaration: private static final long serialVersionUID = 1L;
2. Place it as the first field in the class
""",
            "security-no-hardcoded-creds": """
1. Replace hardcoded strings containing password/secret/key with @Value annotation
2. Example: private String password = "hardcoded"; -> @Value("${app.password}") private String password;
3. Add configuration reference comment
""",
            # API/OpenAPI rules
            "kebab-case-paths": """
1. Convert all path segments to lowercase
2. Replace underscores with hyphens
3. Convert camelCase to kebab-case (e.g., userId -> user-id)
4. Example: /userProfile -> /user-profile, /user_profile -> /user-profile
""",
            "plural-resources": """
1. Convert resource names to plural
2. Example: /user/{id} -> /users/{id}
3. Example: /product/{id} -> /products/{id}
4. Keep parameter names as they are
""",
            "no-crud-names": """
1. Remove verbs (get, create, update, delete, fetch, retrieve) from paths
2. Suggest appropriate HTTP method in comment
3. Example: POST /createUser -> POST /users
4. Example: GET /fetchUser/{id} -> GET /users/{id}
""",
            "uuid-resource-ids": """
1. Find parameters with 'id' in name and type 'string'
2. Add 'format: uuid' to the parameter schema
3. Example:
   parameters:
     - name: userId
       schema:
         type: string
         format: uuid
""",
            "response-envelope": """
1. Wrap the response schema in an envelope with 'data' field
2. Add 'error' field (optional)
3. Example:
   responses:
     '200':
       content:
         application/json:
           schema:
             type: object
             properties:
               data:
                 [existing schema here]
               error:
                 type: object
                 nullable: true
""",
            "pagination-parameter-naming": """
1. Add these fields to paginated response schemas:
   - page (integer)
   - pageSize (integer)
   - totalItems (integer)
   - totalPages (integer)
2. Keep existing data array
""",
            "versioning-required": """
1. Add version prefix to all paths
2. Example: /users -> /v1/users
3. Use /v1/ unless specified otherwise
""",
            "operation-description-required": """
1. Add 'description' field to operation
2. Use clear, actionable description
3. Example: description: 'Retrieves a list of all users in the system'
""",
            "operation-summary-required": """
1. Add 'summary' field to operation
2. Keep it brief (3-7 words)
3. Example: summary: 'Get all users'
""",
            "parameter-description-required": """
1. Add 'description' field to each parameter
2. Be specific about the parameter's purpose
3. Example: description: 'Unique identifier for the user'
""",
            "schema-description-required": """
1. Add 'description' field to schema
2. Describe what the schema represents
3. Example: description: 'User profile information'
""",
            "created-returns-resource": """
1. Ensure POST operations have 201 response
2. 201 response should return the created resource schema
3. Example:
   responses:
     '201':
       description: 'Resource created successfully'
       content:
         application/json:
           schema:
             $ref: '#/components/schemas/ResourceSchema'
""",
        }

        return RULE_INSTRUCTIONS.get(
            rule_id,
            f"Apply the fix according to: {self.fix_strategy.explanation_template}",
        )


class VSCodeCopilotEngine:
    """
    Engine that prepares structured fix instructions for VS Code Copilot.

    Instead of calling external APIs, this generates precise instructions
    that can be fed to VS Code's Copilot Chat interface.
    """

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.controller_generator = ControllerChangeGenerator(project_path)  # ⭐ NEW

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
        test_files = []
        java_path_obj = Path(java_class_path)

        # Extract class name (e.g., "UserService")
        class_name = java_path_obj.stem

        # For controllers, also try without "Controller" suffix
        base_name = class_name.replace("Controller", "")

        # Common test file patterns - covers all standard naming conventions
        test_patterns = [
            # Exact class name tests
            f"**/{class_name}Test.java",
            f"**/{class_name}Tests.java",
            f"**/{class_name}TestCase.java",
            # Integration tests
            f"**/{class_name}IntegrationTest.java",
            f"**/{class_name}IT.java",
            f"**/{class_name}IntegrationTests.java",
            # For controllers, also try base name patterns
            f"**/{base_name}ControllerTest.java",
            f"**/{base_name}ControllerTests.java",
            f"**/{base_name}ControllerIT.java",
            # Test directories with wildcard (catches custom naming)
            f"**/test/**/{class_name}*.java",
            f"**/tests/**/{class_name}*.java",
            f"**/src/test/**/{class_name}*.java",
        ]

        project_path = Path(self.project_path)
        for pattern in test_patterns:
            for test_file in project_path.rglob(pattern):
                # Verify it's actually in a test directory
                test_file_str = str(test_file)
                if (
                    "/test/" in test_file_str or "/tests/" in test_file_str
                ) and "Test" in test_file.stem:
                    rel_path = str(test_file.relative_to(project_path))
                    if rel_path not in test_files:
                        test_files.append(rel_path)

        return test_files

    def _find_test_files_for_controller(self, controller_path: str) -> List[str]:
        """
        Legacy method name for backward compatibility.
        Delegates to _find_test_files_for_java_class.
        """
        return self._find_test_files_for_java_class(controller_path)

    def _find_related_files(self, file_path: str, rule_id: str) -> List[str]:
        """
        Find related files by parsing actual content (endpoints, paths, mappings).

        Examples:
        - OpenAPI spec → Parse 'paths' and find controllers with matching @RequestMapping AND their tests
        - Java controller → Parse @RequestMapping and find OpenAPI specs with matching paths AND controller tests

        Args:
            file_path: Path to the file being fixed
            rule_id: The governance rule that was violated

        Returns:
            List of related file paths (relative to project root)
        """
        related_files = []
        file_path_obj = Path(file_path)

        # Make absolute if relative
        if not file_path_obj.is_absolute():
            file_path_obj = Path(self.project_path) / file_path

        # Get relative path for comparison
        try:
            file_path_rel = str(file_path_obj.relative_to(self.project_path))
        except ValueError:
            # File path is outside project
            file_path_rel = file_path

        logger.info(
            f"🔍 Parsing content to find related files for: {file_path_obj.name}"
        )

        # CASE 1: OpenAPI spec → Parse endpoints and find matching controllers AND their tests
        if file_path.endswith((".yaml", ".yml", ".json")):
            try:
                import yaml

                with open(file_path_obj, "r", encoding="utf-8") as f:
                    spec = yaml.safe_load(f)

                if spec and "paths" in spec:
                    # Extract unique resource names from all paths
                    resources = set()
                    for path in spec["paths"].keys():
                        # Extract resource from API path: "/v1/users/{id}" → "users"
                        # Note: This is an API URL path (not a file path), always uses forward slashes
                        parts = [
                            p for p in path.split("/") if p and not p.startswith("{")
                        ]
                        for part in parts:
                            # Skip version numbers (v1, v2, etc.)
                            if not (
                                part.startswith("v")
                                and len(part) > 1
                                and part[1:].isdigit()
                            ):
                                resources.add(part.lower())

                    logger.info(f"   📍 Found API endpoints for resources: {resources}")

                    # Find controllers that handle these resources
                    for controller_file in self.project_path.rglob("*Controller.java"):
                        try:
                            with open(controller_file, "r", encoding="utf-8") as f:
                                content = f.read()

                            # Check if controller handles any of our resources
                            for resource in resources:
                                # Match @RequestMapping annotations with this path
                                if (
                                    f'@RequestMapping("/{resource}"' in content
                                    or f'@RequestMapping(value = "/{resource}"'
                                    in content
                                    or f'@RequestMapping(path = "/{resource}"'
                                    in content
                                ):
                                    rel_path = str(
                                        controller_file.relative_to(self.project_path)
                                    )
                                    if (
                                        rel_path not in related_files
                                        and rel_path != file_path_rel
                                        and "/test/" not in rel_path
                                    ):
                                        related_files.append(rel_path)
                                        logger.info(
                                            f"   🔗 Matched controller: {controller_file.name} handles /{resource}"
                                        )

                                        # Now find test files for this controller
                                        test_files = (
                                            self._find_test_files_for_java_class(
                                                rel_path
                                            )
                                        )
                                        for test_file in test_files:
                                            if test_file not in related_files:
                                                related_files.append(test_file)
                                                logger.info(
                                                    f"   🧪 Matched test: {Path(test_file).name}"
                                                )
                                        break
                        except Exception:
                            continue
            except Exception as e:
                logger.debug(f"   ⚠️ Could not parse OpenAPI spec: {e}")

        # CASE 2: Java controller → Parse @RequestMapping and find matching OpenAPI specs AND controller tests
        elif (
            file_path.endswith(".java")
            and "Controller" in file_path
            and "/test/" not in file_path
        ):
            try:
                with open(file_path_obj, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract @RequestMapping paths
                import re

                paths = []
                patterns = [
                    r'@RequestMapping\s*\(\s*"([^"]+)"\s*\)',
                    r'@RequestMapping\s*\(\s*value\s*=\s*"([^"]+)"\s*\)',
                    r'@RequestMapping\s*\(\s*path\s*=\s*"([^"]+)"\s*\)',
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    paths.extend([m.strip("/").lower() for m in matches])

                if paths:
                    logger.info(f"   📍 Found controller paths: {paths}")

                    # Find OpenAPI specs that define these paths
                    for spec_file in self.project_path.rglob("*.yaml"):
                        # Look for swagger/openapi/api files
                        if any(
                            keyword in spec_file.name.lower()
                            for keyword in ["swagger", "openapi", "api"]
                        ):
                            try:
                                import yaml

                                with open(spec_file, "r", encoding="utf-8") as f:
                                    spec = yaml.safe_load(f)

                                if spec and "paths" in spec:
                                    # Check if any controller path matches spec paths
                                    for spec_path in spec["paths"].keys():
                                        normalized_spec = spec_path.strip("/").lower()
                                        for controller_path in paths:
                                            # Match if spec path contains controller path
                                            if controller_path in normalized_spec:
                                                rel_path = str(
                                                    spec_file.relative_to(
                                                        self.project_path
                                                    )
                                                )
                                                if (
                                                    rel_path not in related_files
                                                    and rel_path != file_path_rel
                                                ):
                                                    related_files.append(rel_path)
                                                    logger.info(
                                                        f"   🔗 Matched spec: {spec_file.name} defines /{controller_path}"
                                                    )
                                                    break
                            except Exception:
                                continue

                # Find test files for this controller
                test_files = self._find_test_files_for_java_class(file_path_rel)
                for test_file in test_files:
                    if test_file not in related_files:
                        related_files.append(test_file)
                        logger.info(f"   🧪 Matched test: {Path(test_file).name}")

            except Exception as e:
                logger.debug(f"   ⚠️ Could not parse controller: {e}")

        # CASE 3: ANY other Java file (Service, Repository, Entity, DTO, etc.) → Find its tests
        # This handles ArchUnit violations on Services, Repositories, and any other Java class
        elif file_path.endswith(".java") and "/test/" not in file_path:
            # Find test files for this Java class
            test_files = self._find_test_files_for_java_class(file_path_rel)
            for test_file in test_files:
                if test_file not in related_files:
                    related_files.append(test_file)
                    logger.info(f"   🧪 Matched test: {Path(test_file).name}")

        if related_files:
            logger.info(
                f"  ✅ Found {len(related_files)} related file(s) for {file_path_obj.name}"
            )
        else:
            # Only log at DEBUG level for files without relationships (reduces noise for test files, etc.)
            logger.debug(f"  ℹ️  No related files found for {file_path_obj.name}")

        return related_files

    def prepare_fix_instructions(
        self, violations: List[Dict]
    ) -> List[CopilotFixInstruction]:
        """
        Convert violations into structured Copilot fix instructions.

        Args:
            violations: List of governance violations

        Returns:
            List of CopilotFixInstruction objects ready for Copilot
        """
        instructions = []

        for violation in violations:
            rule_id = violation.get("rule") or violation.get("rule_id", "unknown")
            strategy = ALL_STRATEGIES.get(rule_id)

            if not strategy:
                logger.warning(f"No strategy found for rule: {rule_id}")
                continue

            # CHANGED: Include ALL fixes (SAFE, REVIEW_REQUIRED, and MANUAL_ONLY)
            # Copilot can help with manual fixes too!
            # The apply script will handle safety filtering based on --safety flag

            # Extract file and line information
            file_path = self._extract_file_path(violation)
            if not file_path:
                continue

            line_num = self._extract_line_number(violation)
            context_lines = self._get_context_range(file_path, line_num)

            # ⭐ Find related files that might need updates
            related_files = self._find_related_files(file_path, rule_id)

            # ⭐ NEW: Generate controller changes for OpenAPI fixes
            secondary_fixes = []
            if file_path.endswith((".yaml", ".yml", ".json")):
                # This is an OpenAPI fix - generate controller changes
                # Generate even if related_files is empty - the controller exists, we just need to find it
                should_generate = (
                    related_files  # We found specific controllers
                    or rule_id
                    in [
                        "kebab-case-paths",
                        "plural-resources",
                        "no-crud-names",
                        "proper-status-codes",
                        "response-envelope",
                        "pagination-response",
                        "uuid-resource-ids",
                    ]  # Rules that always need controller updates
                )

                if should_generate:
                    logger.info(
                        f"🔗 Generating controller changes for {Path(file_path).name}"
                    )
                    if not related_files:
                        logger.warning(
                            "⚠️  No related controllers found via content parsing"
                        )
                        logger.warning(
                            "   Generating generic fix instructions - user must find the controller"
                        )

                    controller_changes = (
                        self.controller_generator.generate_controller_fixes(
                            violation=violation,
                            openapi_file=file_path,
                            related_controllers=related_files
                            or [],  # Pass empty list if none found
                        )
                    )

                    # Convert to SecondaryFix objects
                    for change in controller_changes:
                        secondary_fixes.append(
                            SecondaryFix(
                                file_path=change["file_path"],
                                change_type=change["change_type"],
                                reason=change["reason"],
                                old_code=change.get("old_code"),
                                new_code=change.get("new_code"),
                                search_pattern=change.get("search_pattern"),
                                instruction=change.get("instruction"),
                            )
                        )

            instruction = CopilotFixInstruction(
                rule_id=rule_id,
                file_path=file_path,
                violation_message=violation.get("message", ""),
                fix_strategy=strategy,
                context_lines=context_lines,
                related_files=related_files,
                secondary_fixes=secondary_fixes,  # ⭐ NEW: Include controller updates
            )

            instructions.append(instruction)

        return instructions

    def _extract_file_path(self, violation: Dict) -> Optional[str]:
        """Extract file path from violation"""
        # Try different fields where file path might be stored
        if "file" in violation:
            return violation["file"]

        # OpenAPI violations use 'source' field
        if "source" in violation:
            return violation["source"]

        # Try to extract from message
        message = violation.get("message", "")
        if "(" in message and ")" in message:
            parts = message.split("(")
            if len(parts) > 1:
                file_part = parts[-1].split(")")[0]
                if ".java" in file_part or ".yaml" in file_part or ".yml" in file_part:
                    return file_part.split(":")[0]

        return None

    def _extract_line_number(self, violation: Dict) -> Optional[int]:
        """Extract line number from violation"""
        if "line" in violation:
            return violation["line"]

        message = violation.get("message", "")
        if ":" in message:
            parts = message.split(":")
            for part in parts:
                if part.strip().isdigit():
                    return int(part.strip())

        return None

    def _get_context_range(
        self, file_path: str, line_num: Optional[int]
    ) -> Tuple[int, int]:
        """
        Get line range for context around the violation.
        Returns (start_line, end_line) for Copilot to focus on.
        """
        if line_num is None:
            return (1, 999999)  # Whole file

        # Provide 10 lines of context before and after
        start = max(1, line_num - 10)
        end = line_num + 10

        return (start, end)

    def generate_copilot_workspace_instructions(
        self, instructions: List[CopilotFixInstruction]
    ) -> str:
        """
        Generate a comprehensive instruction document for VS Code Copilot Chat.

        This can be saved as a markdown file and referenced in Copilot Chat:
        "@workspace /fix Apply the instructions in copilot-fix-instructions.md"
        """
        doc = """# Governance Fix Instructions for Copilot

These are pre-analyzed governance violations with specific fix strategies.
Apply each fix following the exact instructions provided.

---

"""

        for idx, instruction in enumerate(instructions, 1):
            doc += f"""
## Fix {idx}: {instruction.rule_id}

**File**: `{instruction.file_path}`
**Lines**: {instruction.context_lines[0]}-{instruction.context_lines[1]}
**Issue**: {instruction.violation_message}

**Fix Strategy**:
{instruction.fix_strategy.description}

**Complexity**: {instruction.fix_strategy.complexity.value}
**Safety**: {instruction.fix_strategy.safety.value}

**Instructions**:
```
{instruction.to_copilot_prompt()}
```

---

"""

        return doc

    def export_for_vscode(self, violations: List[Dict], output_path: str) -> str:
        """
        Export violations as Copilot-ready instructions.

        Args:
            violations: List of violations
            output_path: Where to save the instructions file

        Returns:
            Path to the generated instructions file
        """
        instructions = self.prepare_fix_instructions(violations)

        # Generate the document
        doc = self.generate_copilot_workspace_instructions(instructions)

        # Save to file
        output_file = Path(output_path) / "copilot-fix-instructions.md"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(doc)

        # Also generate a JSON version for programmatic access
        json_instructions = [
            {
                "fix_id": f"fix-{idx:04d}",
                "rule_id": inst.rule_id,
                "file": inst.file_path,
                "lines": inst.context_lines,
                "prompt": inst.to_copilot_prompt(),
                "complexity": inst.fix_strategy.complexity.value,
                "safety": inst.fix_strategy.safety.value,
                "related_files": inst.related_files,  # ⭐ NEW: Include related files
            }
            for idx, inst in enumerate(instructions, 1)
        ]

        json_file = Path(output_path) / "copilot-fix-instructions.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_instructions, f, indent=2)

        logger.info(f"✓ Generated {len(instructions)} Copilot fix instructions")
        logger.info(f"📄 Markdown: {output_file}")
        logger.info(f"📄 JSON: {json_file}")

        return str(output_file)
