const pluralize = require("pluralize");

module.exports = (targetVal, opts, context) => {
  const path = targetVal;

  // Skip if not a path string
  if (typeof path !== "string") {
    return [];
  }

  const errors = [];

  // Parse path segments
  const segments = path.split("/").filter((segment) => {
    // Filter out version segments (v1, v2, etc.)
    if (/^v\d+$/.test(segment)) return false;
    // Filter out path parameters ({id}, {userId}, etc.)
    if (/^\{.*\}$/.test(segment)) return false;
    // Filter out empty segments
    if (segment === "") return false;
    return true;
  });

  // HEURISTIC: Only check the LAST non-parameter resource segment
  // In REST APIs, the typical pattern is:
  //   /resources/{id}/action
  //   /resources/{id}/sub-resources/{id}/action
  //
  // Strategy: Find the last "resource-like" segment before any action/operation
  //
  // Resource indicators:
  // - Typically the first 1-2 segments after version
  // - Followed by parameters or actions
  //
  // Action/operation indicators (these come AFTER resources):
  // - Common verbs: cancel, approve, activate, etc.
  // - Informational endpoints: summary, details, overview, stats, metrics
  // - Query operations: search, filter, query
  // - Non-countable operations: count, aggregate, total

  const actionPatterns = [
    // Common action verbs
    "activate",
    "deactivate",
    "enable",
    "disable",
    "start",
    "stop",
    "cancel",
    "confirm",
    "approve",
    "reject",
    "publish",
    "unpublish",
    "archive",
    "unarchive",
    "restore",
    "clone",
    "duplicate",
    "validate",
    "verify",
    "check",
    "test",
    "preview",
    "download",
    "upload",
    "export",
    "import",
    "sync",
    "refresh",
    "reset",
    "clear",
    "send",
    "receive",
    "process",
    "calculate",
    "generate",
    "lock",
    "unlock",
    "suspend",
    "resume",
    "retry",

    // Query/search operations
    "search",
    "filter",
    "query",
    "find",
    "lookup",

    // Aggregate/summary operations
    "count",
    "aggregate",
    "total",
    "sum",
    "average",
    "summary",
    "details",
    "overview",
    "report",

    // Metrics/stats
    "stats",
    "statistics",
    "metrics",
    "analytics",
    "health",
    "status",
    "info",
    "metadata",

    // Batch operations
    "batch",
    "bulk",
    "mass",

    // Special operations
    "latest",
    "current",
    "default",
    "all",

    // Status/filter adjectives (modifiers that describe resource state)
    // Pattern: /resources/status/{params}
    "pending",
    "active",
    "inactive",
    "completed",
    "failed",
    "approved",
    "rejected",
    "draft",
    "published",
    "open",
    "closed",
    "new",
    "old",
    "expired",
    "available",
    "unavailable",
    "ready",
    "processing",
  ];

  // Improved detection: Find resource segments (skip actions that come after)
  const resourceSegments = [];

  // Common API prefixes/namespaces that are NOT resources (should be skipped)
  const technicalPrefixes = [
    "api", // Common API prefix: /api/users
    "v1",
    "v2",
    "v3",
    "v4",
    "v5", // Version prefixes
    "rest", // REST API prefix
    "graphql", // GraphQL API prefix
    "internal", // Internal API marker
    "external", // External API marker
    "public", // Public API marker
    "private", // Private API marker
    "admin", // Admin namespace (when used as prefix, not resource)
  ];

  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    const segmentLower = segment.toLowerCase();

    // Skip technical prefixes (these are namespaces, not resources)
    if (technicalPrefixes.includes(segmentLower)) {
      continue;
    }

    // Check if this looks like an action/operation segment
    const isAction = actionPatterns.includes(segmentLower);

    // Check if segment contains hyphen and ends with action word
    // e.g., "batch-cancel", "bulk-delete"
    const isCompoundAction = segment.includes("-") && actionPatterns.includes(segment.split("-").pop().toLowerCase());

    if (isAction || isCompoundAction) {
      // This is an action - stop collecting resource segments
      // Everything after this is likely an operation, not a resource
      break;
    }

    // This looks like a resource segment
    resourceSegments.push({ segment, index: i });
  }

  // Legitimate singular resource patterns (resources that SHOULD be singular)
  // These are typically singleton resources representing current user, configuration, etc.
  const legitimateSingularPatterns = [
    // Current user/session context
    "me", // /me (current user)
    "current", // /current-user
    "session", // /session (current session)
    "profile", // /profile (current user's profile)
    "account", // /account (current account - when not listing accounts)

    // Configuration/settings (singletons)
    "config", // /config
    "configuration", // /configuration
    "setting", // /setting (when referring to app settings)
    "preference", // /preference (when referring to app preferences)

    // System/app-level singletons
    "health", // /health (already in actions but also singleton)
    "status", // /status (system status)
    "version", // /version (API version info)
    "schema", // /schema (API schema)

    // Aggregate/summary resources (when representing aggregated data)
    "summary", // /summary (when it's the resource itself)
    "report", // /report (when it's a specific report)
    "dashboard", // /dashboard (when it's the main dashboard)

    // Authentication/authorization
    "login", // /login
    "logout", // /logout
    "token", // /token (when requesting a token)
    "auth", // /auth
    "authentication", // /authentication
  ];

  // Check only the resource segments for plurality
  resourceSegments.forEach(({ segment, index }) => {
    const segmentLower = segment.toLowerCase();

    // Skip uncountable resources
    const uncountable = ["data", "metadata", "information", "content"];
    if (uncountable.includes(segmentLower)) {
      return;
    }

    // Skip legitimate singular resources
    if (legitimateSingularPatterns.includes(segmentLower)) {
      return;
    }

    // Special case: If segment appears in a singleton context pattern
    // e.g., /my-profile, /user-profile (possessive/descriptive compounds)
    const singletonContextPatterns = [
      /^my-/, // my-profile, my-account
      /^current-/, // current-user, current-session
      /^main-/, // main-dashboard
      /^default-/, // default-config
    ];

    if (singletonContextPatterns.some((pattern) => pattern.test(segmentLower))) {
      return;
    }

    // Check if segment is plural
    const singular = pluralize.singular(segment);
    const plural = pluralize.plural(segment);

    // If the singular and plural are different, and the segment matches singular, it's wrong
    if (singular !== plural && segment === singular) {
      errors.push({
        message: `Resource '${segment}' should be plural: '${plural}'. (Use plural for collection resources. Singular is only acceptable for singleton resources like /me, /config, or /session)`,
        path: [...context.path, index],
      });
    }
  });

  return errors;
};
