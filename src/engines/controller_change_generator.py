"""
Controller Change Generator

Generates specific controller updates based on OpenAPI changes.
Ensures spec-controller consistency by creating actionable fix instructions.
"""

from typing import Dict, List, Optional
from pathlib import Path
import re

from utils.logger import logger


class ControllerChangeGenerator:
    """
    Analyzes OpenAPI violations and generates corresponding controller changes.

    This ensures that when we fix an OpenAPI spec, we also update the
    Java controllers to maintain consistency.
    """

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def generate_controller_fixes(
        self, violation: Dict, openapi_file: str, related_controllers: List[str]
    ) -> List[Dict]:
        """
        Generate controller changes based on OpenAPI violation being fixed.

        Args:
            violation: The OpenAPI violation being fixed
            openapi_file: Path to the OpenAPI spec file
            related_controllers: List of controller files that implement these endpoints

        Returns:
            List of controller fix specifications
        """
        rule_id = violation.get("rule_id") or violation.get(
            "rule", ""
        )  # ⭐ Check both fields
        fixes = []

        logger.info(f"🔧 Generating controller fixes for rule: {rule_id}")

        # Rule-specific controller change generation
        if rule_id == "proper-status-codes" or "status" in rule_id.lower():
            fixes.extend(
                self._generate_status_code_fixes(violation, related_controllers)
            )

        elif rule_id == "response-envelope":
            fixes.extend(self._generate_envelope_fixes(violation, related_controllers))

        elif rule_id == "pagination-response" or "pagination" in rule_id.lower():
            fixes.extend(
                self._generate_pagination_fixes(violation, related_controllers)
            )

        elif rule_id == "uuid-resource-ids":
            fixes.extend(self._generate_uuid_fixes(violation, related_controllers))

        elif rule_id in ["kebab-case-paths", "plural-resources"]:
            fixes.extend(
                self._generate_path_mapping_fixes(violation, related_controllers)
            )

        logger.info(f"   Generated {len(fixes)} controller fix(es)")
        return fixes

    def _generate_status_code_fixes(
        self, violation: Dict, controllers: List[str]
    ) -> List[Dict]:
        """Generate fixes for HTTP status code changes"""
        fixes = []

        # Detect if this is about POST returning 200 instead of 201
        message = violation.get("message", "").lower()
        path = violation.get("path", "")

        if "post" in message or "create" in message:
            for controller in controllers:
                fixes.append(
                    {
                        "file_path": controller,
                        "change_type": "response_status",
                        "reason": "POST endpoint must return 201 Created, not 200 OK",
                        "search_pattern": r"@PostMapping.*\n.*return ResponseEntity\.ok\(",
                        "old_code": "return ResponseEntity.ok(entity);",
                        "new_code": "return ResponseEntity.status(HttpStatus.CREATED).body(entity);",
                        "instruction": """
Find all @PostMapping methods that return ResponseEntity.ok() and change them to:
return ResponseEntity.status(HttpStatus.CREATED).body(entity);

Also ensure the import exists:
import org.springframework.http.HttpStatus;
""",
                    }
                )

        return fixes

    def _generate_envelope_fixes(
        self, violation: Dict, controllers: List[str]
    ) -> List[Dict]:
        """Generate fixes for response envelope wrapping"""
        fixes = []

        for controller in controllers:
            fixes.append(
                {
                    "file_path": controller,
                    "change_type": "response_wrapper",
                    "reason": "Wrap response in envelope to match OpenAPI spec",
                    "instruction": """
Create a ResponseEnvelope wrapper class if it doesn't exist:

@Data
public class ResponseEnvelope<T> {
    private T data;
    private Object error;

    public static <T> ResponseEnvelope<T> success(T data) {
        ResponseEnvelope<T> envelope = new ResponseEnvelope<>();
        envelope.setData(data);
        return envelope;
    }
}

Then wrap all controller return values:
// Before: return user;
// After: return ResponseEnvelope.success(user);

// Before: return users;
// After: return ResponseEnvelope.success(users);
""",
                }
            )

        return fixes

    def _generate_pagination_fixes(
        self, violation: Dict, controllers: List[str]
    ) -> List[Dict]:
        """Generate fixes for pagination support"""
        fixes = []

        for controller in controllers:
            fixes.append(
                {
                    "file_path": controller,
                    "change_type": "pagination",
                    "reason": "Add pagination support to match OpenAPI spec",
                    "instruction": """
Change list endpoints to return paginated results:

1. Add Pageable parameter:
   @GetMapping
   public ResponseEntity<Page<User>> getUsers(Pageable pageable) {
       Page<User> users = userService.findAll(pageable);
       return ResponseEntity.ok(users);
   }

2. Add required imports:
   import org.springframework.data.domain.Page;
   import org.springframework.data.domain.Pageable;

3. Update service layer to support Pageable:
   public Page<User> findAll(Pageable pageable) {
       return userRepository.findAll(pageable);
   }
""",
                }
            )

        return fixes

    def _generate_uuid_fixes(
        self, violation: Dict, controllers: List[str]
    ) -> List[Dict]:
        """Generate fixes for UUID parameter types"""
        fixes = []

        for controller in controllers:
            fixes.append(
                {
                    "file_path": controller,
                    "change_type": "parameter_type",
                    "reason": "Change ID parameters from String/Long to UUID",
                    "instruction": """
Change path variable types from String or Long to UUID:

Before:
@GetMapping("/{id}")
public ResponseEntity<User> getUser(@PathVariable String id) {
    ...
}

After:
@GetMapping("/{id}")
public ResponseEntity<User> getUser(@PathVariable UUID id) {
    ...
}

Add import:
import java.util.UUID;
""",
                }
            )

        return fixes

    def _generate_path_mapping_fixes(
        self, violation: Dict, controllers: List[str]
    ) -> List[Dict]:
        """Generate fixes for @RequestMapping path changes"""
        fixes = []

        message = violation.get("message", "")
        path_field = violation.get("path", "")  # e.g., "paths./api/get-orders"

        logger.debug("🔍 Parsing path mapping")
        logger.debug(f"   Message: {message[:80]}...")
        logger.debug(f"   Path field: {path_field}")

        # Extract the actual API path from the violation's 'path' field
        # Format: "paths./api/get-orders" or "paths./user"
        old_path = None
        new_path = None

        if path_field and path_field.startswith("paths."):
            # Extract the API path (everything after "paths.")
            api_path = path_field[6:]  # Remove "paths." prefix
            logger.debug(f"   API path from field: {api_path}")

            # Now analyze the message to understand what change is needed
            # For plural-resources: Should change singular to plural
            # For kebab-case: Should add hyphens
            # For no-crud-names: Should remove CRUD verbs

            rule_id = violation.get("rule_id") or violation.get("rule", "")

            if rule_id == "plural-resources":
                # Need to make it plural
                # Try to extract the specific resource from the path
                # /api/get-orders -> "orders" is already plural ✓
                # /user -> should be "users"
                # /api/user -> should be "users"

                segments = [
                    s for s in api_path.split("/") if s and not s.startswith("{")
                ]
                if segments:
                    last_segment = segments[-1]

                    # Simple pluralization rules (not perfect but good enough)
                    if last_segment.endswith("s"):
                        # Already plural, might be a false positive or different issue
                        logger.debug(
                            f"   ⚠️  Resource '{last_segment}' already appears plural"
                        )
                    else:
                        # Make it plural
                        if last_segment.endswith("y"):
                            plural_form = (
                                last_segment[:-1] + "ies"
                            )  # category -> categories
                        elif last_segment.endswith(("s", "x", "z", "ch", "sh")):
                            plural_form = last_segment + "es"  # box -> boxes
                        else:
                            plural_form = last_segment + "s"  # user -> users

                        old_path = api_path
                        new_path = api_path.replace(last_segment, plural_form)
                        logger.debug(
                            f"   Pluralization: {last_segment} -> {plural_form}"
                        )

            elif rule_id == "kebab-case-paths":
                # Need to convert to kebab-case
                # /api/getOrders -> /api/get-orders
                segments = api_path.split("/")
                new_segments = []
                for seg in segments:
                    if seg and not seg.startswith("{"):
                        # Convert camelCase to kebab-case
                        kebab = re.sub(r"([a-z])([A-Z])", r"\1-\2", seg).lower()
                        new_segments.append(kebab)
                    else:
                        new_segments.append(seg)

                old_path = api_path
                new_path = "/".join(new_segments)
                logger.debug(f"   Kebab-case conversion: {api_path} -> {new_path}")

            elif rule_id == "no-crud-names":
                # Need to remove CRUD verbs (get, post, put, delete, create, update)
                # /api/getOrders -> /api/orders
                # /api/createUser -> /api/user
                crud_verbs = [
                    "get",
                    "post",
                    "put",
                    "delete",
                    "create",
                    "update",
                    "fetch",
                    "list",
                ]

                segments = api_path.split("/")
                new_segments = []
                for seg in segments:
                    if seg and not seg.startswith("{"):
                        # Remove CRUD verb prefix
                        lower_seg = seg.lower()
                        modified = seg
                        for verb in crud_verbs:
                            if lower_seg.startswith(verb):
                                # Remove the verb and lowercase the next char
                                remainder = seg[len(verb) :]
                                if remainder:
                                    modified = remainder[0].lower() + remainder[1:]
                                break
                        new_segments.append(modified)
                    else:
                        new_segments.append(seg)

                old_path = api_path
                new_path = "/".join(new_segments)
                logger.debug(f"   Remove CRUD verbs: {api_path} -> {new_path}")

        # If we couldn't extract from path field, fall back to message parsing
        if not old_path:
            logger.debug("   Falling back to message parsing...")
            # (keep existing message parsing logic as fallback)
            if "->" in message:
                parts = message.split("->")
                if len(parts) == 2:
                    old_path = parts[0].strip().split()[-1].strip("\"'")
                    new_path = parts[1].strip().strip("\"'")

        if old_path and new_path and old_path != new_path:
            logger.info(f"   ✓ Path change detected: {old_path} -> {new_path}")

            # Extract the base resource path (not path params like {id})
            # /v1/user/{id} -> /user
            # /api/products -> /products
            # /user -> /user

            # Get segments excluding parameters
            # Note: Parsing API URL paths (not file paths), always use forward slashes
            old_segments = [
                s for s in old_path.split("/") if s and not s.startswith("{")
            ]
            new_segments = [
                s for s in new_path.split("/") if s and not s.startswith("{")
            ]

            # Compare ALL segments, not just the last one
            # Example: /onBoarded/next-stores -> /on-boarded/next-stores
            # The change is in the first segment, not the last!
            changed_segments = []
            for old_seg, new_seg in zip(old_segments, new_segments):
                if old_seg != new_seg:
                    changed_segments.append((old_seg, new_seg))

            # Get the last segment as the primary resource (for logging)
            old_resource = old_segments[-1] if old_segments else None
            new_resource = new_segments[-1] if new_segments else None

            logger.debug(f"   Path segments: {old_segments} -> {new_segments}")
            logger.debug(f"   Changed segments: {changed_segments}")

            # Generate fixes if ANY segments changed
            if changed_segments or (
                old_resource and new_resource and old_resource != new_resource
            ):
                if controllers:
                    # We found specific controllers - generate targeted fixes
                    logger.info(
                        f"   Generating fixes for {len(controllers)} controller(s)"
                    )

                    # Build change description
                    if changed_segments:
                        changes_desc = ", ".join(
                            [f"{old} → {new}" for old, new in changed_segments]
                        )
                    else:
                        changes_desc = f"{old_resource} → {new_resource}"

                    for controller in controllers:
                        fixes.append(
                            {
                                "file_path": controller,
                                "change_type": "request_mapping",
                                "reason": f"Update @RequestMapping to match OpenAPI path change: {old_path} -> {new_path}",
                                "old_code": f'@RequestMapping("{old_path}")',
                                "new_code": f'@RequestMapping("{new_path}")',
                                "instruction": f"""
🔧 Update @RequestMapping annotation to match the new OpenAPI path:

PATH CHANGE: {changes_desc}

OLD: @RequestMapping("{old_path}")
NEW: @RequestMapping("{new_path}")

📝 Also update method-level mappings that reference this path:
  • @GetMapping("{old_path}/{{id}}") -> @GetMapping("{new_path}/{{id}}")
  • @PostMapping("{old_path}") -> @PostMapping("{new_path})")
  • Any other mappings using "{old_path}"

⚠️  Important: This controller change is required to maintain consistency
   with the OpenAPI specification. Without this change, the API paths
   will not match the documented spec.
""",
                            }
                        )
                        logger.debug(f"     ✓ Added fix for {Path(controller).name}")
                else:
                    # No specific controllers found - generate generic instructions
                    logger.warning(
                        "   ⚠️  No controllers found, generating generic fix instructions"
                    )

                    # Build change description
                    if changed_segments:
                        changes_desc = ", ".join(
                            [f"{old} → {new}" for old, new in changed_segments]
                        )
                    else:
                        changes_desc = f"{old_resource} → {new_resource}"

                    fixes.append(
                        {
                            "file_path": "⚠️  FIND_THE_CONTROLLER_FILE",  # Placeholder
                            "change_type": "request_mapping",
                            "reason": f"Update @RequestMapping to match OpenAPI path change: {old_path} -> {new_path}",
                            "old_code": f'@RequestMapping("{old_path}")',
                            "new_code": f'@RequestMapping("{new_path}")',
                            "instruction": f"""
🚨 MANUAL ACTION REQUIRED 🚨

The OpenAPI spec path has changed, but we couldn't automatically locate the controller.

PATH CHANGE: {changes_desc}
OLD: {old_path}
NEW: {new_path}

🔍 **STEP 1: Find the Controller**
   Search your codebase for the controller that handles this endpoint:
   - Search for: @RequestMapping("{old_path}")
   - Or search for: {old_path}
   - Or search for any of these segments: {', '.join(old_segments)}
   - Check controllers that might use partial paths (e.g., "/api" + "{old_path}")

🔧 **STEP 2: Update @RequestMapping**
   Once you find the controller, update the path mapping:

   OLD: @RequestMapping("{old_path}")
   NEW: @RequestMapping("{new_path}")

📝 **STEP 3: Update Method-Level Mappings**
   Also update all method-level mappings in that controller:
   • @GetMapping("{old_path}/{{id}}") -> @GetMapping("{new_path}/{{id}}")
   • @PostMapping("{old_path}") -> @PostMapping("{new_path})")
   • @PutMapping("{old_path}/{{id}}") -> @PutMapping("{new_path}/{{id}}")
   • @DeleteMapping("{old_path}/{{id}}") -> @DeleteMapping("{new_path}/{{id}}")

⚠️  **CRITICAL**: This controller update is REQUIRED to maintain consistency
   with the OpenAPI specification. Without it, your API paths will not match
   the documented spec, causing integration failures.

💡 **TIP**: If you can't find an exact match:
   - The controller might use a base path (e.g., @RequestMapping("/api"))
   - Method mappings might be relative (e.g., @GetMapping("{old_segments[-1]}/{{id}}"))
   - Search for any of the path segments individually
   - Check if there's path composition in application properties
""",
                        }
                    )
                    logger.info(
                        "     ✓ Added generic fix instructions (user must locate controller)"
                    )
            else:
                logger.debug(
                    "   ⚠️  No resource name change detected (same before/after)"
                )
        else:
            logger.debug("   ⚠️  Could not extract path change from message")

        logger.info(f"   Generated {len(fixes)} path mapping fix(es)")
        return fixes

    def _extract_endpoint_from_violation(self, violation: Dict) -> Optional[str]:
        """Extract the endpoint path from a violation"""
        # Try different fields
        if "path" in violation:
            return violation["path"]

        message = violation.get("message", "")
        # Try to extract path from message using regex
        path_match = re.search(r"/[a-zA-Z0-9/_-]+", message)
        if path_match:
            return path_match.group(0)

        return None

    def _find_controller_method(
        self, controller_file: str, endpoint: str, http_method: str = None
    ) -> Optional[str]:
        """
        Find the specific controller method that handles an endpoint.

        Args:
            controller_file: Path to controller file
            endpoint: Endpoint path (e.g., "/users")
            http_method: HTTP method (GET, POST, etc.)

        Returns:
            Method name if found, None otherwise
        """
        try:
            controller_path = self.project_path / controller_file
            if not controller_path.exists():
                return None

            with open(controller_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for method with matching mapping
            # Example: @GetMapping("/users") or @PostMapping
            if http_method:
                pattern = rf"@{http_method.title()}Mapping[^)]*\n\s*public[^(]+(\w+)\("
            else:
                pattern = r"@\w+Mapping[^)]*\n\s*public[^(]+(\w+)\("

            matches = re.findall(pattern, content)
            if matches:
                return matches[0]

        except Exception as e:
            logger.debug(f"Could not parse controller {controller_file}: {e}")

        return None
