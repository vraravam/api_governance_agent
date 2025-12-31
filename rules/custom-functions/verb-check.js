module.exports = (targetVal, opts, context) => {
  const path = targetVal;

  if (typeof path !== "string") {
    return [];
  }

  const errors = [];

  // Common verbs to detect in REST APIs
  const commonVerbs = [
    "create",
    "update",
    "delete",
    "get",
    "post",
    "put",
    "patch",
    "add",
    "remove",
    "insert",
    "modify",
    "edit",
    "change",
    "activate",
    "deactivate",
    "enable",
    "disable",
    "register",
    "unregister",
    "subscribe",
    "unsubscribe",
    "calculate",
    "compute",
    "process",
    "execute",
    "run",
    "validate",
    "verify",
    "check",
    "confirm",
    "submit",
    "approve",
    "reject",
    "cancel",
    "decline",
    "send",
    "receive",
    "fetch",
    "retrieve",
    "export",
    "import",
    "upload",
    "download",
    "search",
    "find",
    "query",
    "lookup",
    "refresh",
    "reload",
    "reset",
    "clear",
    "archive",
    "restore",
    "recover",
    "backup",
  ];

  // Parse path segments
  const segments = path.split("/").filter((segment) => {
    if (/^v\d+$/.test(segment)) return false;
    if (/^\{.*\}$/.test(segment)) return false;
    if (segment === "") return false;
    return true;
  });

  // Check each segment
  segments.forEach((segment, index) => {
    const lowerSegment = segment.toLowerCase();

    // Check against common verbs
    if (commonVerbs.includes(lowerSegment)) {
      errors.push({
        message: `Path contains verb '${segment}'. Consider using a reified resource (e.g., POST /${segment}s or POST /${segment}-requests)`,
        path: [...context.path, index],
      });
      return;
    }

    // Check for verb-like patterns
    // Words ending in -ing (processing, calculating)
    if (lowerSegment.endsWith("ing")) {
      errors.push({
        message: `Path segment '${segment}' appears to be a verb (ends with -ing). Consider using a noun form`,
        path: [...context.path, index],
      });
      return;
    }

    // Words ending in -ate (activate, validate)
    if (lowerSegment.endsWith("ate") && lowerSegment.length > 4) {
      errors.push({
        message: `Path segment '${segment}' may be a verb (ends with -ate). Consider using a reified resource`,
        path: [...context.path, index],
      });
    }
  });

  return errors;
};
