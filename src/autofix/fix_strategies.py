"""
Fix Strategies for Java Architecture Violations

Defines fix templates and strategies for each rule category.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class FixComplexity(Enum):
    """Complexity level of a fix"""

    SIMPLE = "simple"  # Single-line change
    MODERATE = "moderate"  # Multi-line, single file
    COMPLEX = "complex"  # Multi-file or structural change


class FixSafety(Enum):
    """Safety level of auto-applying a fix"""

    SAFE = "safe"  # Can auto-apply with confidence
    REVIEW_REQUIRED = "review_required"  # Needs human review
    MANUAL_ONLY = "manual_only"  # DEPRECATED - Use REVIEW_REQUIRED instead


@dataclass
class FixStrategy:
    """Defines how to fix a specific rule violation"""

    rule_id: str
    description: str
    complexity: FixComplexity
    safety: FixSafety
    fix_function: str  # Name of the function that implements the fix
    explanation_template: str
    requires_imports: List[str] = None

    def __post_init__(self):
        if self.requires_imports is None:
            self.requires_imports = []


# ============================================================================
# CODING RULES STRATEGIES
# ============================================================================

CODING_STRATEGIES = {
    "coding-no-std-streams": FixStrategy(
        rule_id="coding-no-std-streams",
        description="Replace System.out/err with proper logging",
        complexity=FixComplexity.MODERATE,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_std_streams",
        explanation_template=(
            "System.out and System.err should not be used in production code. "
            "This fix replaces them with SLF4J logger calls. "
            "A logger field has been added to the class."
        ),
        requires_imports=["org.slf4j.Logger", "org.slf4j.LoggerFactory"],
    ),
    "coding-no-generic-exceptions": FixStrategy(
        rule_id="coding-no-generic-exceptions",
        description="Replace generic exceptions with specific types",
        complexity=FixComplexity.MODERATE,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_generic_exceptions",
        explanation_template=(
            "Generic exceptions (Exception, RuntimeException, Throwable) should not be thrown. "
            "This fix replaces them with more specific exception types based on context. "
            "Review the exception type to ensure it matches your use case."
        ),
        requires_imports=[],
    ),
    "coding-no-field-injection": FixStrategy(
        rule_id="coding-no-field-injection",
        description="Convert field injection to constructor injection",
        complexity=FixComplexity.MODERATE,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_field_injection",
        explanation_template=(
            "Field injection is discouraged in favor of constructor injection. "
            "This fix moves @Inject annotations from fields to a constructor. "
            "Constructor injection makes dependencies explicit and improves testability."
        ),
        requires_imports=[],
    ),
    "coding-no-jodatime": FixStrategy(
        rule_id="coding-no-jodatime",
        description="Replace Joda-Time with java.time API",
        complexity=FixComplexity.MODERATE,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_jodatime",
        explanation_template=(
            "Joda-Time is deprecated in favor of java.time (JSR-310). "
            "This fix replaces Joda-Time classes with their java.time equivalents. "
            "Review the conversion to ensure date/time semantics are preserved."
        ),
        requires_imports=["java.time.LocalDateTime", "java.time.ZonedDateTime"],
    ),
    "coding-no-java-util-logging": FixStrategy(
        rule_id="coding-no-java-util-logging",
        description="Replace java.util.logging with SLF4J",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.SAFE,
        fix_function="fix_java_util_logging",
        explanation_template=(
            "java.util.logging should be replaced with SLF4J for better flexibility. "
            "This fix replaces java.util.logging.Logger with org.slf4j.Logger. "
            "No behavioral changes are introduced."
        ),
        requires_imports=["org.slf4j.Logger", "org.slf4j.LoggerFactory"],
    ),
}

# ============================================================================
# NAMING CONVENTION STRATEGIES
# ============================================================================

NAMING_STRATEGIES = {
    "naming-service-package": FixStrategy(
        rule_id="naming-service-package",
        description="Move service class to ..service.. package",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_service_package",
        explanation_template=(
            "Classes ending with 'Service' should reside in a '..service..' package. "
            "This requires moving the file and updating all imports. "
            "The LLM will propose the necessary changes with detailed explanations.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "naming-controller-package": FixStrategy(
        rule_id="naming-controller-package",
        description="Move controller class to ..controller.. package",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_controller_package",
        explanation_template=(
            "Classes ending with 'Controller' should reside in a '..controller..' package. "
            "This requires moving the file and updating all imports. "
            "The LLM will propose the necessary changes with detailed explanations.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "naming-repository-package": FixStrategy(
        rule_id="naming-repository-package",
        description="Move repository class to ..repository.. package",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_repository_package",
        explanation_template=(
            "Classes ending with 'Repository' or 'DAO' should reside in a '..repository..' or '..dao..' package. "
            "This requires moving the file and updating all imports. "
            "The LLM will propose the necessary changes with detailed explanations.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "naming-entity-package": FixStrategy(
        rule_id="naming-entity-package",
        description="Move entity class to ..domain.. package",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_entity_package",
        explanation_template=(
            "Classes ending with 'Entity' or 'Model' should reside in a '..domain..', '..entity..', or '..model..' package. "
            "This requires moving the file and updating all imports. "
            "The LLM will propose the necessary changes with detailed explanations.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "naming-config-package": FixStrategy(
        rule_id="naming-config-package",
        description="Move config class to ..config.. package",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_config_package",
        explanation_template=(
            "Classes ending with 'Config' or 'Configuration' should reside in a '..config..' package. "
            "This requires moving the file and updating all imports. "
            "The LLM will propose the necessary changes with detailed explanations.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "naming-exception-suffix": FixStrategy(
        rule_id="naming-exception-suffix",
        description="Rename exception class to end with 'Exception'",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_exception_suffix",
        explanation_template=(
            "Exception classes should have names ending with 'Exception'. "
            "This requires renaming the class and updating all references. "
            "The LLM will propose the necessary changes with detailed explanations.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "naming-no-interface-prefix": FixStrategy(
        rule_id="naming-no-interface-prefix",
        description="Remove 'I' prefix from interface name",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_interface_prefix",
        explanation_template=(
            "Interface names should not start with 'I' prefix. Use descriptive names instead. "
            "This requires renaming the interface and updating all references. "
            "The LLM will propose the necessary changes with detailed explanations.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
}

# ============================================================================
# DEPENDENCY MANAGEMENT STRATEGIES
# ============================================================================

DEPENDENCY_STRATEGIES = {
    "dependency-no-cycles": FixStrategy(
        rule_id="dependency-no-cycles",
        description="Break circular package dependencies",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_circular_dependencies",
        explanation_template=(
            "Circular dependencies between packages should be eliminated. "
            "This typically requires architectural refactoring such as: "
            "1) Extracting common interfaces, 2) Introducing a mediator, or 3) Restructuring packages. "
            "The LLM will analyze the codebase and propose architectural refactorings with detailed rationale.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "dependency-controller-no-repository": FixStrategy(
        rule_id="dependency-controller-no-repository",
        description="Introduce service layer between controller and repository",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_controller_repository_dependency",
        explanation_template=(
            "Controllers should not access repositories directly. A service layer should mediate. "
            "This fix requires creating a new service class and updating the controller. "
            "The LLM will propose the necessary changes with detailed explanations.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "dependency-no-upper-packages": FixStrategy(
        rule_id="dependency-no-upper-packages",
        description="Remove dependencies on upper packages",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_upper_package_dependency",
        explanation_template=(
            "Classes should not depend on classes in parent packages. "
            "This violates the acyclic dependencies principle. "
            "Refactor by moving shared code to a common package or restructuring the hierarchy. "
            "The LLM will analyze the codebase and propose architectural refactorings with detailed rationale.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "dependency-domain-independence": FixStrategy(
        rule_id="dependency-domain-independence",
        description="Remove infrastructure dependencies from domain layer",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_domain_independence",
        explanation_template=(
            "Domain/entity classes should not depend on infrastructure layers (service, repository, controller). "
            "This violates clean architecture principles. "
            "Refactor by inverting dependencies or moving logic to appropriate layers. "
            "The LLM will analyze the codebase and propose architectural refactorings with detailed rationale.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
}

# ============================================================================
# ANNOTATION-BASED STRATEGIES
# ============================================================================

ANNOTATION_STRATEGIES = {
    "annotation-service-package": FixStrategy(
        rule_id="annotation-service-package",
        description="Move @Service annotated class to ..service.. package",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_service_annotation_package",
        explanation_template=(
            "Classes annotated with @Service should reside in a '..service..' package. "
            "This requires moving the file and updating all imports. "
            "The LLM will propose the necessary changes with detailed explanations.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "annotation-repository-package": FixStrategy(
        rule_id="annotation-repository-package",
        description="Move @Repository annotated class to ..repository.. package",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_repository_annotation_package",
        explanation_template=(
            "Classes annotated with @Repository should reside in a '..repository..' or '..dao..' package. "
            "This requires moving the file and updating all imports. "
            "The LLM will propose the necessary changes with detailed explanations.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "annotation-controller-package": FixStrategy(
        rule_id="annotation-controller-package",
        description="Move @Controller annotated class to ..controller.. package",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_controller_annotation_package",
        explanation_template=(
            "Classes annotated with @Controller or @RestController should reside in a '..controller..' package. "
            "This requires moving the file and updating all imports. "
            "The LLM will propose the necessary changes with detailed explanations.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "annotation-transactional-layer": FixStrategy(
        rule_id="annotation-transactional-layer",
        description="Move @Transactional to service or repository layer",
        complexity=FixComplexity.MODERATE,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_transactional_layer",
        explanation_template=(
            "@Transactional should only be used in service or repository layers, not controllers. "
            "This fix removes the annotation from the controller. "
            "You should add it to the appropriate service method instead."
        ),
        requires_imports=[],
    ),
}

# ============================================================================
# ARCHITECTURE STRATEGIES
# ============================================================================

ARCHITECTURE_STRATEGIES = {
    "architecture-layered": FixStrategy(
        rule_id="architecture-layered",
        description="Enforce layered architecture pattern",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_layered_architecture",
        explanation_template=(
            "The layered architecture pattern requires: Controller -> Service -> Repository. "
            "This violation indicates a layer is being skipped or accessed incorrectly. "
            "Refactor to introduce missing layers or fix incorrect dependencies. "
            "The LLM will analyze the codebase and propose architectural refactorings with detailed rationale.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
    "architecture-persistence-no-web": FixStrategy(
        rule_id="architecture-persistence-no-web",
        description="Remove web layer dependencies from persistence layer",
        complexity=FixComplexity.COMPLEX,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_persistence_web_dependency",
        explanation_template=(
            "Persistence layer (repository, dao, entity) should not depend on web layer (controller). "
            "This violates separation of concerns. "
            "Refactor by inverting dependencies or moving logic to appropriate layers. "
            "The LLM will analyze the codebase and propose architectural refactorings with detailed rationale.\n\n"
            "⚠️ IMPORTANT: This is a complex architectural fix. The LLM will propose changes, but you MUST carefully review and test all modifications before committing."
        ),
        requires_imports=[],
    ),
}

# ============================================================================
# SECURITY STRATEGIES
# ============================================================================

SECURITY_STRATEGIES = {
    "security-use-secure-random": FixStrategy(
        rule_id="security-use-secure-random",
        description="Replace Random with SecureRandom",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.SAFE,
        fix_function="fix_secure_random",
        explanation_template=(
            "java.util.Random should not be used for security-sensitive operations. "
            "This fix replaces it with java.security.SecureRandom. "
            "No behavioral changes for non-security code, but provides cryptographically strong randomness."
        ),
        requires_imports=["java.security.SecureRandom"],
    ),
    "security-serial-version-uid": FixStrategy(
        rule_id="security-serial-version-uid",
        description="Add static final serialVersionUID",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.SAFE,
        fix_function="fix_serial_version_uid",
        explanation_template=(
            "Serializable classes should declare a static final serialVersionUID. "
            "This fix adds the field with a generated value. "
            "This ensures serialization compatibility across JVM versions."
        ),
        requires_imports=[],
    ),
    "security-no-hardcoded-creds": FixStrategy(
        rule_id="security-no-hardcoded-creds",
        description="Move hardcoded credentials to configuration",
        complexity=FixComplexity.MODERATE,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_hardcoded_credentials",
        explanation_template=(
            "Hardcoded credentials (password, secret, api_key) should not be in source code. "
            "This fix replaces hardcoded values with configuration placeholders. "
            "You must configure the actual values in your configuration management system."
        ),
        requires_imports=[],
    ),
}

# ============================================================================
# API/OPENAPI RULES STRATEGIES
# ============================================================================

API_STRATEGIES = {
    "kebab-case-paths": FixStrategy(
        rule_id="kebab-case-paths",
        description="Convert API paths to kebab-case",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.SAFE,
        fix_function="fix_kebab_case_paths",
        explanation_template=(
            "API paths should use kebab-case (lowercase with hyphens).\n\n"
            "This fix converts camelCase or snake_case paths to kebab-case.\n"
            "Examples:\n"
            "- /userProfile → /user-profile\n"
            "- /orderItems → /order-items\n"
            "- /user_profile → /user-profile\n\n"
            "⚠️ IMPORTANT: Update your Java controllers to match the new paths:\n"
            "- Find @GetMapping/@PostMapping with camelCase or snake_case paths\n"
            "- Replace with kebab-case paths\n"
            "- Update controller tests (MockMvc, RestTemplate, etc.)\n\n"
            "Example controller update:\n"
            "```java\n"
            "// BEFORE:\n"
            '@GetMapping("/userProfile")\n'
            "public ResponseEntity<?> getUserProfile() { ... }\n\n"
            "// AFTER:\n"
            '@GetMapping("/user-profile")\n'
            "public ResponseEntity<?> getUserProfile() { ... }\n"
            "```\n\n"
            "Example test update:\n"
            "```java\n"
            "// BEFORE:\n"
            'mockMvc.perform(get("/userProfile"))\n\n'
            "// AFTER:\n"
            'mockMvc.perform(get("/user-profile"))\n'
            "```"
        ),
        requires_imports=[],
    ),
    "plural-resources": FixStrategy(
        rule_id="plural-resources",
        description="Use plural nouns for collection resources",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_plural_resources",
        explanation_template=(
            "Collection resource names should be plural nouns.\n\n"
            "This fix converts singular resource names to plural.\n"
            "Examples:\n"
            "- /user/{id} → /users/{id}\n"
            "- /order → /orders\n"
            "- /product/{id} → /products/{id}\n\n"
            "⚠️ IMPORTANT: Update your Java controllers to match the new paths:\n"
            "- Find @GetMapping/@PostMapping with singular resource names\n"
            "- Replace with plural resource names\n"
            "- Update controller tests (MockMvc, RestTemplate, etc.)\n\n"
            "Example controller update:\n"
            "```java\n"
            "// BEFORE:\n"
            '@GetMapping("/user/{id}")\n'
            "public ResponseEntity<?> getUser(@PathVariable Long id) { ... }\n\n"
            "// AFTER:\n"
            '@GetMapping("/users/{id}")\n'
            "public ResponseEntity<?> getUser(@PathVariable Long id) { ... }\n"
            "```\n\n"
            "Example test update:\n"
            "```java\n"
            "// BEFORE:\n"
            'mockMvc.perform(get("/user/123"))\n\n'
            "// AFTER:\n"
            'mockMvc.perform(get("/users/123"))\n'
            "```"
        ),
        requires_imports=[],
    ),
    "no-verbs-in-url": FixStrategy(
        rule_id="no-verbs-in-url",
        description="Remove verbs from API paths, use resource nouns instead",
        complexity=FixComplexity.MODERATE,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_standard_http_verbs",
        explanation_template=(
            "REST API paths should not contain verbs. Use HTTP methods (GET, POST, PUT, DELETE) instead.\n\n"
            "This fix updates the OpenAPI spec by:\n"
            "- Converting verbs to plural nouns (search → searches)\n"
            "- Removing verb prefixes (search/suggestions → suggestions)\n"
            "- Creating compound nouns (dealers/search → dealer-searches)\n\n"
            "⚠️ IMPORTANT: Update your Java controllers to match the new paths:\n"
            "- Find @GetMapping/@PostMapping annotations with old paths\n"
            "- Replace with new resource-based paths\n"
            "- Update controller tests (MockMvc, RestTemplate, etc.)\n\n"
            "Example controller update:\n"
            "```java\n"
            "// BEFORE:\n"
            '@GetMapping("/v1/search")\n'
            "public ResponseEntity<?> search() { ... }\n\n"
            "// AFTER:\n"
            '@GetMapping("/v1/searches")\n'
            "public ResponseEntity<?> search() { ... }\n"
            "```\n\n"
            "Example test update:\n"
            "```java\n"
            "// BEFORE:\n"
            'mockMvc.perform(get("/v1/search"))\n\n'
            "// AFTER:\n"
            'mockMvc.perform(get("/v1/searches"))\n'
            "```"
        ),
        requires_imports=[],
    ),
    "no-crud-names": FixStrategy(
        rule_id="no-crud-names",
        description="Remove CRUD verbs from API paths, use HTTP methods instead",
        complexity=FixComplexity.MODERATE,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_standard_http_verbs",
        explanation_template=(
            "API paths should not contain CRUD operation names (get/create/update/delete/post/put).\n"
            "Use HTTP methods instead.\n\n"
            "Examples:\n"
            "- POST /createUser → POST /users\n"
            "- GET /getUser/{id} → GET /users/{id}\n"
            "- PUT /updateUser/{id} → PUT /users/{id}\n"
            "- DELETE /deleteUser/{id} → DELETE /users/{id}\n\n"
            "⚠️ IMPORTANT: Update your Java controllers to match the new paths:\n"
            "- Find @GetMapping/@PostMapping with CRUD verbs\n"
            "- Replace with resource-based paths\n"
            "- Update HTTP method if needed\n"
            "- Update controller tests (MockMvc, RestTemplate, etc.)\n\n"
            "Example controller update:\n"
            "```java\n"
            "// BEFORE:\n"
            '@PostMapping("/createUser")\n'
            "public ResponseEntity<?> createUser(@RequestBody UserDTO user) { ... }\n\n"
            "// AFTER:\n"
            '@PostMapping("/users")\n'
            "public ResponseEntity<?> createUser(@RequestBody UserDTO user) { ... }\n"
            "```\n\n"
            "Example test update:\n"
            "```java\n"
            "// BEFORE:\n"
            'mockMvc.perform(post("/createUser"))\n\n'
            "// AFTER:\n"
            'mockMvc.perform(post("/users"))\n'
            "```"
        ),
        requires_imports=[],
    ),
    "uuid-resource-ids": FixStrategy(
        rule_id="uuid-resource-ids",
        description="Add format: uuid for UUID parameters",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.SAFE,
        fix_function="fix_uuid_format",
        explanation_template=(
            "UUID parameters should specify 'format: uuid' for proper validation. "
            "This fix adds the format constraint to UUID parameters. "
            "This helps with API validation and documentation."
        ),
        requires_imports=[],
    ),
    "array-fields-plural": FixStrategy(
        rule_id="array-fields-plural",
        description="Use plural names for array fields",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.SAFE,
        fix_function="fix_camelcase_properties",
        explanation_template=(
            "Array field names should use plural nouns. "
            "This fix converts singular array field names to plural. "
            "Example: item -> items"
        ),
        requires_imports=[],
    ),
    "response-envelope": FixStrategy(
        rule_id="response-envelope",
        description="Wrap responses in standard envelope",
        complexity=FixComplexity.MODERATE,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_response_envelope",
        explanation_template=(
            "API responses should use a consistent envelope structure with 'data', 'error', etc. "
            "This fix wraps the response schema in a standard envelope. "
            "Review the envelope structure to match your API standards."
        ),
        requires_imports=[],
    ),
    "pagination-parameter-naming": FixStrategy(
        rule_id="pagination-parameter-naming",
        description="Add standard pagination fields",
        complexity=FixComplexity.MODERATE,
        safety=FixSafety.SAFE,
        fix_function="fix_pagination_structure",
        explanation_template=(
            "Paginated responses should include 'page', 'pageSize', 'totalItems', and 'totalPages'. "
            "This fix adds missing pagination fields to the response schema. "
            "This provides a consistent pagination experience."
        ),
        requires_imports=[],
    ),
    "operation-description-required": FixStrategy(
        rule_id="operation-description-required",
        description="Add descriptions to operations",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.SAFE,
        fix_function="fix_description_required",
        explanation_template=(
            "API operations should have descriptions. "
            "This fix adds placeholder descriptions that should be filled with meaningful content. "
            "Good descriptions improve API documentation and developer experience."
        ),
        requires_imports=[],
    ),
    "operation-summary-required": FixStrategy(
        rule_id="operation-summary-required",
        description="Add summaries to operations",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.SAFE,
        fix_function="fix_description_required",
        explanation_template=(
            "API operations should have summaries. "
            "This fix adds placeholder summaries that should be filled with meaningful content."
        ),
        requires_imports=[],
    ),
    "parameter-description-required": FixStrategy(
        rule_id="parameter-description-required",
        description="Add descriptions to parameters",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.SAFE,
        fix_function="fix_description_required",
        explanation_template=(
            "API parameters should have descriptions. "
            "This fix adds placeholder descriptions."
        ),
        requires_imports=[],
    ),
    "schema-description-required": FixStrategy(
        rule_id="schema-description-required",
        description="Add descriptions to schemas",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.SAFE,
        fix_function="fix_description_required",
        explanation_template=(
            "API schemas should have descriptions. "
            "This fix adds placeholder descriptions."
        ),
        requires_imports=[],
    ),
    "versioning-required": FixStrategy(
        rule_id="versioning-required",
        description="Add version prefix to API paths",
        complexity=FixComplexity.MODERATE,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_versioning_required",
        explanation_template=(
            "API paths should include version prefix (e.g., /v1/). "
            "This fix adds the version prefix to all paths. "
            "Review to ensure the version number is correct."
        ),
        requires_imports=[],
    ),
    "created-returns-resource": FixStrategy(
        rule_id="created-returns-resource",
        description="POST operations should return created resource",
        complexity=FixComplexity.MODERATE,
        safety=FixSafety.REVIEW_REQUIRED,
        fix_function="fix_created_returns_resource",
        explanation_template=(
            "POST operations that create resources should return the created resource. "
            "This fix ensures 201 responses include the resource schema."
        ),
        requires_imports=[],
    ),
    "post-create-returns-201": FixStrategy(
        rule_id="post-create-returns-201",
        description="POST create operations should return 201 status code",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.SAFE,
        fix_function="fix_post_returns_201",
        explanation_template=(
            "POST operations that create resources should return 201 Created, not 200 OK. "
            "This fix changes the response status code to 201 and ensures proper Location header is documented. "
            "HTTP 201 indicates successful resource creation."
        ),
        requires_imports=[],
    ),
    "response-fields-camelcase": FixStrategy(
        rule_id="response-fields-camelcase",
        description="Convert response field names to camelCase",
        complexity=FixComplexity.SIMPLE,
        safety=FixSafety.SAFE,
        fix_function="fix_response_fields_camelcase",
        explanation_template=(
            "Response field names should use camelCase (e.g., userId, firstName). "
            "This fix converts snake_case fields (user_id, first_name) to camelCase. "
            "This ensures consistent API naming conventions."
        ),
        requires_imports=[],
    ),
}

# ============================================================================
# MASTER STRATEGY REGISTRY
# ============================================================================

ALL_STRATEGIES: Dict[str, FixStrategy] = {
    **CODING_STRATEGIES,
    **NAMING_STRATEGIES,
    **DEPENDENCY_STRATEGIES,
    **ANNOTATION_STRATEGIES,
    **ARCHITECTURE_STRATEGIES,
    **SECURITY_STRATEGIES,
    **API_STRATEGIES,
}


def get_strategy(rule_id: str) -> Optional[FixStrategy]:
    """Get fix strategy for a rule ID"""
    return ALL_STRATEGIES.get(rule_id)


def get_strategies_by_safety(safety: FixSafety) -> List[FixStrategy]:
    """Get all strategies matching a safety level"""
    return [s for s in ALL_STRATEGIES.values() if s.safety == safety]


def get_strategies_by_complexity(complexity: FixComplexity) -> List[FixStrategy]:
    """Get all strategies matching a complexity level"""
    return [s for s in ALL_STRATEGIES.values() if s.complexity == complexity]
