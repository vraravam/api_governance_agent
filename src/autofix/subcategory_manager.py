"""
Subcategory Manager - Breaks down categories into rule-level subcategories

This module provides granular control for applying fixes at the individual rule level,
organized under their parent categories.
"""

from typing import Dict, List
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ViolationSubcategory:
    """Represents a subcategory (rule group) within a category"""

    name: str
    display_name: str
    description: str
    rule_id: str  # The actual rule ID that triggers this violation
    category: str  # Parent category
    fix_complexity: str  # "Simple", "Moderate", "Complex"
    example: str  # Example of the violation


class SubcategoryManager:
    """
    Organizes violations into rule-level subcategories within each category.

    This allows users to:
    1. Apply fixes for specific rules within a category
    2. Target exact issues (e.g., just "plural-resources" under RESOURCE_NAMING)
    3. Get better progress tracking
    4. Understand exactly what will be fixed
    """

    # Define subcategories grouped by parent category
    SUBCATEGORIES = {
        # ========================================
        # RESOURCE_NAMING SUBCATEGORIES
        # ========================================
        "plural-resources": ViolationSubcategory(
            name="plural-resources",
            display_name="Plural Resource Names",
            description="Resource paths must use plural nouns (e.g., /users not /user)",
            rule_id="plural-resources",
            category="RESOURCE_NAMING",
            fix_complexity="Simple",
            example="/user → /users",
        ),
        "pluralResourceNaming": ViolationSubcategory(
            name="pluralResourceNaming",
            display_name="Plural Resource Naming (Java)",
            description="Controller mappings must use plural resource names",
            rule_id="pluralResourceNaming",
            category="RESOURCE_NAMING",
            fix_complexity="Simple",
            example='@RequestMapping("/user") → @RequestMapping("/users")',
        ),
        "kebab-case-paths": ViolationSubcategory(
            name="kebab-case-paths",
            display_name="Kebab-Case Paths",
            description="URL paths must use kebab-case (e.g., /order-items not /orderItems)",
            rule_id="kebab-case-paths",
            category="RESOURCE_NAMING",
            fix_complexity="Simple",
            example="/orderItems → /order-items",
        ),
        "requestMappingsKebabCase": ViolationSubcategory(
            name="requestMappingsKebabCase",
            display_name="Kebab-Case Request Mappings",
            description="Request mappings should use kebab-case",
            rule_id="requestMappingsKebabCase",
            category="RESOURCE_NAMING",
            fix_complexity="Simple",
            example='@GetMapping("/orderItems") → @GetMapping("/order-items")',
        ),
        "no-verbs-in-url": ViolationSubcategory(
            name="no-verbs-in-url",
            display_name="No Verbs in URLs",
            description="REST URLs should not contain verbs (use HTTP methods instead)",
            rule_id="no-verbs-in-url",
            category="RESOURCE_NAMING",
            fix_complexity="Moderate",
            example="/getUser → /users (with GET method)",
        ),
        "noVerbsInMapping": ViolationSubcategory(
            name="noVerbsInMapping",
            display_name="No Verbs in Mappings",
            description="Controller mappings should not contain action verbs",
            rule_id="noVerbsInMapping",
            category="RESOURCE_NAMING",
            fix_complexity="Moderate",
            example='@GetMapping("/getOrders") → @GetMapping("/orders")',
        ),
        # ========================================
        # DATA_TYPES SUBCATEGORIES
        # ========================================
        "uuid-resource-ids": ViolationSubcategory(
            name="uuid-resource-ids",
            display_name="UUID Resource IDs",
            description="Resource IDs must use UUID format (not integers)",
            rule_id="uuid-resource-ids",
            category="DATA_TYPES",
            fix_complexity="Complex",
            example="/users/{id} with type: integer → type: string, format: uuid",
        ),
        "pathVariablesShouldBeUUID": ViolationSubcategory(
            name="pathVariablesShouldBeUUID",
            display_name="Path Variables Should Be UUID",
            description="Path variables for resource IDs should be UUID type",
            rule_id="pathVariablesShouldBeUUID",
            category="DATA_TYPES",
            fix_complexity="Complex",
            example="@PathVariable Long id → @PathVariable UUID id",
        ),
        "request-fields-camelcase": ViolationSubcategory(
            name="request-fields-camelcase",
            display_name="Request Fields camelCase",
            description="Request body fields must use camelCase naming",
            rule_id="request-fields-camelcase",
            category="DATA_TYPES",
            fix_complexity="Simple",
            example="user_name → userName",
        ),
        "response-fields-camelcase": ViolationSubcategory(
            name="response-fields-camelcase",
            display_name="Response Fields camelCase",
            description="Response body fields must use camelCase naming",
            rule_id="response-fields-camelcase",
            category="DATA_TYPES",
            fix_complexity="Simple",
            example="order_id → orderId",
        ),
        "requestParamsCamelCase": ViolationSubcategory(
            name="requestParamsCamelCase",
            display_name="Request Params camelCase",
            description="Request parameters should use camelCase",
            rule_id="requestParamsCamelCase",
            category="DATA_TYPES",
            fix_complexity="Simple",
            example='@RequestParam("user_id") → @RequestParam("userId")',
        ),
        "datetime-iso8601": ViolationSubcategory(
            name="datetime-iso8601",
            display_name="ISO8601 DateTime Format",
            description="Date/time fields must use ISO8601 format",
            rule_id="datetime-iso8601",
            category="DATA_TYPES",
            fix_complexity="Moderate",
            example="format: date → format: date-time (ISO8601)",
        ),
        "currency-code-iso4217": ViolationSubcategory(
            name="currency-code-iso4217",
            display_name="ISO4217 Currency Codes",
            description="Currency codes must follow ISO4217 standard",
            rule_id="currency-code-iso4217",
            category="DATA_TYPES",
            fix_complexity="Simple",
            example='currency: "Dollar" → currency: "USD"',
        ),
        # ========================================
        # HTTP_SEMANTICS SUBCATEGORIES
        # ========================================
        "post-create-returns-201": ViolationSubcategory(
            name="post-create-returns-201",
            display_name="POST Returns 201 Created",
            description="POST endpoints creating resources must return 201 Created",
            rule_id="post-create-returns-201",
            category="HTTP_SEMANTICS",
            fix_complexity="Simple",
            example="responses: 200 → responses: 201 (for POST /users)",
        ),
        "postMethodsShouldReturn201": ViolationSubcategory(
            name="postMethodsShouldReturn201",
            display_name="POST Methods Return 201",
            description="POST methods should return 201 status code",
            rule_id="postMethodsShouldReturn201",
            category="HTTP_SEMANTICS",
            fix_complexity="Simple",
            example="return ResponseEntity.ok() → return ResponseEntity.status(201)",
        ),
        "put-returns-200-or-204": ViolationSubcategory(
            name="put-returns-200-or-204",
            display_name="PUT Returns 200 or 204",
            description="PUT endpoints must return 200 OK or 204 No Content",
            rule_id="put-returns-200-or-204",
            category="HTTP_SEMANTICS",
            fix_complexity="Simple",
            example="Add 200 or 204 response to PUT endpoint",
        ),
        "delete-returns-204-or-200": ViolationSubcategory(
            name="delete-returns-204-or-200",
            display_name="DELETE Returns 204 or 200",
            description="DELETE endpoints must return 204 No Content or 200 OK",
            rule_id="delete-returns-204-or-200",
            category="HTTP_SEMANTICS",
            fix_complexity="Simple",
            example="Add 204 or 200 response to DELETE endpoint",
        ),
        "get-no-request-body": ViolationSubcategory(
            name="get-no-request-body",
            display_name="GET Has No Request Body",
            description="GET requests should not have request bodies",
            rule_id="get-no-request-body",
            category="HTTP_SEMANTICS",
            fix_complexity="Moderate",
            example="Remove requestBody from GET endpoint",
        ),
        "getMethodsNoRequestBody": ViolationSubcategory(
            name="getMethodsNoRequestBody",
            display_name="GET Methods No Request Body",
            description="GET methods should not accept request bodies",
            rule_id="getMethodsNoRequestBody",
            category="HTTP_SEMANTICS",
            fix_complexity="Moderate",
            example="Remove @RequestBody from GET method",
        ),
        "delete-no-request-body": ViolationSubcategory(
            name="delete-no-request-body",
            display_name="DELETE Has No Request Body",
            description="DELETE requests should not have request bodies",
            rule_id="delete-no-request-body",
            category="HTTP_SEMANTICS",
            fix_complexity="Moderate",
            example="Remove requestBody from DELETE endpoint",
        ),
        # ========================================
        # PAGINATION SUBCATEGORIES
        # ========================================
        "pagination-parameter-naming": ViolationSubcategory(
            name="pagination-parameter-naming",
            display_name="Pagination Parameter Naming",
            description='Pagination parameters should be named "page" and "size"',
            rule_id="pagination-parameter-naming",
            category="PAGINATION",
            fix_complexity="Simple",
            example="pageNum/pageSize → page/size",
        ),
        "pagination-response-structure": ViolationSubcategory(
            name="pagination-response-structure",
            display_name="Pagination Response Structure",
            description="Paginated responses must include totalPages, totalElements, etc.",
            rule_id="pagination-response-structure",
            category="PAGINATION",
            fix_complexity="Moderate",
            example="Add totalPages, totalElements, pageNumber, pageSize",
        ),
        "pagination-response-check": ViolationSubcategory(
            name="pagination-response-check",
            display_name="Pagination Response Check",
            description="Pagination responses must follow standard structure",
            rule_id="pagination-response-check",
            category="PAGINATION",
            fix_complexity="Moderate",
            example="Ensure response has content, totalPages, totalElements",
        ),
        "paginatedEndpointsUsePageable": ViolationSubcategory(
            name="paginatedEndpointsUsePageable",
            display_name="Use Pageable Parameter",
            description="Paginated endpoints should use Spring Pageable parameter",
            rule_id="paginatedEndpointsUsePageable",
            category="PAGINATION",
            fix_complexity="Moderate",
            example="Add Pageable parameter to method signature",
        ),
        # ========================================
        # RESPONSE_STRUCTURE SUBCATEGORIES
        # ========================================
        "response-envelope": ViolationSubcategory(
            name="response-envelope",
            display_name="Response Envelope",
            description="Responses should be wrapped in envelope with status, data, errors",
            rule_id="response-envelope",
            category="RESPONSE_STRUCTURE",
            fix_complexity="Complex",
            example="Return {status, data, errors} structure",
        ),
        "array-fields-plural": ViolationSubcategory(
            name="array-fields-plural",
            display_name="Array Fields Plural",
            description="Array/list field names must be plural",
            rule_id="array-fields-plural",
            category="RESPONSE_STRUCTURE",
            fix_complexity="Simple",
            example="item: [] → items: []",
        ),
        "nested-resources-depth": ViolationSubcategory(
            name="nested-resources-depth",
            display_name="Nested Resources Depth Limit",
            description="Nested resource paths should not exceed 2 levels deep",
            rule_id="nested-resources-depth",
            category="RESPONSE_STRUCTURE",
            fix_complexity="Complex",
            example="/users/{id}/orders/{id}/items/{id} → use query params",
        ),
        "controllerMethodsReturnProperTypes": ViolationSubcategory(
            name="controllerMethodsReturnProperTypes",
            display_name="Controller Methods Return Proper Types",
            description="Controller methods should return ResponseEntity<T>",
            rule_id="controllerMethodsReturnProperTypes",
            category="RESPONSE_STRUCTURE",
            fix_complexity="Moderate",
            example="public User getUser() → public ResponseEntity<User> getUser()",
        ),
        # ========================================
        # DOCUMENTATION SUBCATEGORIES
        # ========================================
        "operation-description-required": ViolationSubcategory(
            name="operation-description-required",
            display_name="Operation Description Required",
            description="All API operations must have descriptions",
            rule_id="operation-description-required",
            category="DOCUMENTATION",
            fix_complexity="Simple",
            example='Add description: "Retrieve user by ID"',
        ),
        "schema-description-required": ViolationSubcategory(
            name="schema-description-required",
            display_name="Schema Description Required",
            description="All schemas/models must have descriptions",
            rule_id="schema-description-required",
            category="DOCUMENTATION",
            fix_complexity="Simple",
            example="Add description to User schema",
        ),
        "parameter-description-required": ViolationSubcategory(
            name="parameter-description-required",
            display_name="Parameter Description Required",
            description="All parameters must have descriptions",
            rule_id="parameter-description-required",
            category="DOCUMENTATION",
            fix_complexity="Simple",
            example='Add description: "Unique user identifier"',
        ),
        "tag-description-required": ViolationSubcategory(
            name="tag-description-required",
            display_name="Tag Description Required",
            description="All API tags must have descriptions",
            rule_id="tag-description-required",
            category="DOCUMENTATION",
            fix_complexity="Simple",
            example='Add description to "Users" tag',
        ),
        # ========================================
        # ARCHITECTURE SUBCATEGORIES
        # ========================================
        "architecture-layered": ViolationSubcategory(
            name="architecture-layered",
            display_name="Layered Architecture Violation",
            description="Violations of layered architecture principles",
            rule_id="architecture-layered",
            category="ARCHITECTURE",
            fix_complexity="Complex",
            example="Controller accessing persistence layer directly",
        ),
        "arch-layered-architecture": ViolationSubcategory(
            name="arch-layered-architecture",
            display_name="Layered Architecture (Legacy)",
            description="Legacy layered architecture violations",
            rule_id="arch-layered-architecture",
            category="ARCHITECTURE",
            fix_complexity="Complex",
            example="Fix layer violations",
        ),
        "architecture-persistence-no-web": ViolationSubcategory(
            name="architecture-persistence-no-web",
            display_name="Persistence Layer Independence",
            description="Persistence layer should not depend on web layer",
            rule_id="architecture-persistence-no-web",
            category="ARCHITECTURE",
            fix_complexity="Complex",
            example="Remove web imports from repository classes",
        ),
        "dependency-controller-no-repository": ViolationSubcategory(
            name="dependency-controller-no-repository",
            display_name="Controller Should Not Access Repository",
            description="Controllers should access repositories through services only",
            rule_id="dependency-controller-no-repository",
            category="ARCHITECTURE",
            fix_complexity="Complex",
            example="Replace repository injection with service",
        ),
        "repositoryAccessThroughService": ViolationSubcategory(
            name="repositoryAccessThroughService",
            display_name="Repository Access Through Service",
            description="Repositories should only be accessed through service layer",
            rule_id="repositoryAccessThroughService",
            category="ARCHITECTURE",
            fix_complexity="Complex",
            example="Move repository call to service class",
        ),
        "dependency-domain-independence": ViolationSubcategory(
            name="dependency-domain-independence",
            display_name="Domain Layer Independence",
            description="Domain layer should not depend on infrastructure",
            rule_id="dependency-domain-independence",
            category="ARCHITECTURE",
            fix_complexity="Complex",
            example="Remove infrastructure imports from domain",
        ),
        "domainLayerIndependence": ViolationSubcategory(
            name="domainLayerIndependence",
            display_name="Domain Layer Independence",
            description="Domain layer must remain independent",
            rule_id="domainLayerIndependence",
            category="ARCHITECTURE",
            fix_complexity="Complex",
            example="Remove external dependencies from domain",
        ),
        "dependency-no-upper-packages": ViolationSubcategory(
            name="dependency-no-upper-packages",
            display_name="No Dependencies on Upper Packages",
            description="Lower layers should not depend on upper layers",
            rule_id="dependency-no-upper-packages",
            category="ARCHITECTURE",
            fix_complexity="Complex",
            example="Remove upward package dependencies",
        ),
        "naming-service-package": ViolationSubcategory(
            name="naming-service-package",
            display_name="Service Package Naming",
            description="Service classes must be in service package",
            rule_id="naming-service-package",
            category="ARCHITECTURE",
            fix_complexity="Moderate",
            example="Move *Service classes to .service package",
        ),
        "arch-no-cycles": ViolationSubcategory(
            name="arch-no-cycles",
            display_name="No Cyclic Dependencies",
            description="Detect and prevent cyclic dependencies",
            rule_id="arch-no-cycles",
            category="ARCHITECTURE",
            fix_complexity="Complex",
            example="Break circular dependency between ServiceA and ServiceB",
        ),
        "arch-naming-convention": ViolationSubcategory(
            name="arch-naming-convention",
            display_name="Naming Convention",
            description="Classes must follow naming conventions",
            rule_id="arch-naming-convention",
            category="ARCHITECTURE",
            fix_complexity="Simple",
            example="UserControllerImpl → UserController",
        ),
        "controllersInCorrectPackage": ViolationSubcategory(
            name="controllersInCorrectPackage",
            display_name="Controllers in Correct Package",
            description="Controllers must be in controller package",
            rule_id="controllersInCorrectPackage",
            category="ARCHITECTURE",
            fix_complexity="Moderate",
            example="Move controllers to .controller package",
        ),
        "controllerNamingConvention": ViolationSubcategory(
            name="controllerNamingConvention",
            display_name="Controller Naming Convention",
            description='Controllers must end with "Controller"',
            rule_id="controllerNamingConvention",
            category="ARCHITECTURE",
            fix_complexity="Simple",
            example="UserApi → UserController",
        ),
        "classLevelRequestMapping": ViolationSubcategory(
            name="classLevelRequestMapping",
            display_name="Class Level Request Mapping",
            description="Controllers should have class-level @RequestMapping",
            rule_id="classLevelRequestMapping",
            category="ARCHITECTURE",
            fix_complexity="Simple",
            example='Add @RequestMapping("/users") to controller class',
        ),
        # ========================================
        # CODE_QUALITY SUBCATEGORIES
        # ========================================
        "coding-no-std-streams": ViolationSubcategory(
            name="coding-no-std-streams",
            display_name="No System.out/System.err",
            description="Use proper logging instead of System.out.println()",
            rule_id="coding-no-std-streams",
            category="CODE_QUALITY",
            fix_complexity="Simple",
            example="System.out.println() → logger.info()",
        ),
        "no-sysout": ViolationSubcategory(
            name="no-sysout",
            display_name="No System.out (Legacy)",
            description="Do not use System.out or System.err",
            rule_id="no-sysout",
            category="CODE_QUALITY",
            fix_complexity="Simple",
            example='System.out.println("msg") → log.info("msg")',
        ),
        "coding-no-generic-exceptions": ViolationSubcategory(
            name="coding-no-generic-exceptions",
            display_name="No Generic Exceptions",
            description="Avoid catching generic Exception",
            rule_id="coding-no-generic-exceptions",
            category="CODE_QUALITY",
            fix_complexity="Moderate",
            example="catch (Exception e) → catch (SpecificException e)",
        ),
        "no-generic-exceptions": ViolationSubcategory(
            name="no-generic-exceptions",
            display_name="No Generic Exceptions (Legacy)",
            description="Catch specific exceptions instead of Exception",
            rule_id="no-generic-exceptions",
            category="CODE_QUALITY",
            fix_complexity="Moderate",
            example="Replace Exception with specific type",
        ),
        "coding-no-field-injection": ViolationSubcategory(
            name="coding-no-field-injection",
            display_name="No Field Injection",
            description="Use constructor injection instead of @Autowired fields",
            rule_id="coding-no-field-injection",
            category="CODE_QUALITY",
            fix_complexity="Moderate",
            example="@Autowired field → constructor parameter",
        ),
        "constructor-injection-over-field": ViolationSubcategory(
            name="constructor-injection-over-field",
            display_name="Constructor Injection Over Field",
            description="Prefer constructor injection over field injection",
            rule_id="constructor-injection-over-field",
            category="CODE_QUALITY",
            fix_complexity="Moderate",
            example="Use constructor injection",
        ),
        "coding-no-java-util-logging": ViolationSubcategory(
            name="coding-no-java-util-logging",
            display_name="No java.util.logging",
            description="Use SLF4J/Logback instead of java.util.logging",
            rule_id="coding-no-java-util-logging",
            category="CODE_QUALITY",
            fix_complexity="Simple",
            example="java.util.logging.Logger → org.slf4j.Logger",
        ),
        "no-java-util-logging": ViolationSubcategory(
            name="no-java-util-logging",
            display_name="No java.util.logging (Legacy)",
            description="Use SLF4J instead of JUL",
            rule_id="no-java-util-logging",
            category="CODE_QUALITY",
            fix_complexity="Simple",
            example="Replace JUL with SLF4J",
        ),
        "proper-logging": ViolationSubcategory(
            name="proper-logging",
            display_name="Proper Logging",
            description="Use appropriate logging framework",
            rule_id="proper-logging",
            category="CODE_QUALITY",
            fix_complexity="Simple",
            example="Ensure proper logging setup",
        ),
        "no-empty-catch": ViolationSubcategory(
            name="no-empty-catch",
            display_name="No Empty Catch Blocks",
            description="Catch blocks should not be empty",
            rule_id="no-empty-catch",
            category="CODE_QUALITY",
            fix_complexity="Simple",
            example="Add logging or proper error handling to catch block",
        ),
        # ========================================
        # SECURITY SUBCATEGORIES
        # ========================================
        "no-api-keys-in-url": ViolationSubcategory(
            name="no-api-keys-in-url",
            display_name="No API Keys in URL",
            description="API keys should not be passed in URLs",
            rule_id="no-api-keys-in-url",
            category="SECURITY",
            fix_complexity="Moderate",
            example="Move API key from query param to header",
        ),
        "require-authentication": ViolationSubcategory(
            name="require-authentication",
            display_name="Require Authentication",
            description="Endpoints must require authentication",
            rule_id="require-authentication",
            category="SECURITY",
            fix_complexity="Complex",
            example="Add security requirement to endpoint",
        ),
        "security-definitions-required": ViolationSubcategory(
            name="security-definitions-required",
            display_name="Security Definitions Required",
            description="API must define security schemes",
            rule_id="security-definitions-required",
            category="SECURITY",
            fix_complexity="Moderate",
            example="Add securitySchemes to OpenAPI spec",
        ),
        "no-hardcoded-credentials": ViolationSubcategory(
            name="no-hardcoded-credentials",
            display_name="No Hardcoded Credentials",
            description="Credentials should not be hardcoded",
            rule_id="no-hardcoded-credentials",
            category="SECURITY",
            fix_complexity="Moderate",
            example="Move credentials to environment variables",
        ),
        # ========================================
        # VERSIONING SUBCATEGORIES
        # ========================================
        "versioning-required": ViolationSubcategory(
            name="versioning-required",
            display_name="API Versioning Required",
            description="API paths must include version prefix (e.g., /v1/)",
            rule_id="versioning-required",
            category="RESOURCE_NAMING",  # Could be its own category
            fix_complexity="Moderate",
            example="/users → /v1/users",
        ),
    }

    @classmethod
    def get_subcategories_for_category(
        cls, category_name: str
    ) -> Dict[str, ViolationSubcategory]:
        """Get all subcategories belonging to a specific category"""
        return {
            name: subcat
            for name, subcat in cls.SUBCATEGORIES.items()
            if subcat.category == category_name
        }

    @classmethod
    def get_subcategory_by_rule(cls, rule_id: str) -> ViolationSubcategory:
        """Get subcategory for a specific rule ID"""
        return cls.SUBCATEGORIES.get(rule_id)

    @classmethod
    def categorize_violations_with_subcategories(
        cls, violations: List[Dict]
    ) -> Dict[str, Dict[str, List[Dict]]]:
        """
        Organize violations by category and subcategory.

        Returns:
            {
                'RESOURCE_NAMING': {
                    'plural-resources': [violation1, violation2, ...],
                    'kebab-case-paths': [violation3, ...]
                },
                'ARCHITECTURE': {
                    'architecture-layered': [...]
                }
            }
        """
        from autofix.category_manager import CategoryManager

        result = defaultdict(lambda: defaultdict(list))

        for violation in violations:
            rule_id = violation.get("rule_id") or violation.get("rule")
            if not rule_id:
                continue

            # Find which category this rule belongs to
            category_name = None
            for cat_name, category in CategoryManager.CATEGORIES.items():
                if rule_id in category.rules:
                    category_name = cat_name
                    break

            if not category_name:
                category_name = "OTHER"

            # Find subcategory (which is the rule itself)
            subcategory = cls.get_subcategory_by_rule(rule_id)
            subcategory_name = rule_id  # Use rule_id as subcategory name

            result[category_name][subcategory_name].append(violation)

        return dict(result)

    @classmethod
    def generate_subcategory_summary(cls, violations: List[Dict]) -> Dict[str, Dict]:
        """
        Generate summary with subcategory details.

        Returns detailed info about each subcategory including violation count,
        complexity, and examples.
        """
        categorized = cls.categorize_violations_with_subcategories(violations)

        summary = {}
        for category_name, subcategories in categorized.items():
            summary[category_name] = {
                "total_violations": sum(len(viols) for viols in subcategories.values()),
                "subcategories": {},
            }

            for subcat_name, subcat_violations in subcategories.items():
                subcat_info = cls.get_subcategory_by_rule(subcat_name)

                summary[category_name]["subcategories"][subcat_name] = {
                    "display_name": (
                        subcat_info.display_name if subcat_info else subcat_name
                    ),
                    "description": (
                        subcat_info.description if subcat_info else "No description"
                    ),
                    "violation_count": len(subcat_violations),
                    "fix_complexity": (
                        subcat_info.fix_complexity if subcat_info else "Unknown"
                    ),
                    "example": subcat_info.example if subcat_info else "No example",
                    "violations": subcat_violations,
                }

        return summary
