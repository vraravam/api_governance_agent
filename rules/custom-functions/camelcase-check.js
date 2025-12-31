module.exports = (targetVal, opts, context) => {
  const fieldName = targetVal;

  if (typeof fieldName !== "string") {
    return [];
  }

  const errors = [];

  // Check if it's lowerCamelCase
  // Should start with lowercase, no underscores, no hyphens
  const camelCasePattern = /^[a-z][a-zA-Z0-9]*$/;

  if (!camelCasePattern.test(fieldName)) {
    let suggestion = fieldName;

    // Convert snake_case to camelCase
    if (fieldName.includes("_")) {
      suggestion = fieldName.replace(/_([a-z])/g, (match, letter) => letter.toUpperCase());
    }

    // Convert kebab-case to camelCase
    if (fieldName.includes("-")) {
      suggestion = fieldName.replace(/-([a-z])/g, (match, letter) => letter.toUpperCase());
    }

    // Convert PascalCase to camelCase
    if (/^[A-Z]/.test(fieldName)) {
      suggestion = fieldName.charAt(0).toLowerCase() + fieldName.slice(1);
    }

    errors.push({
      message: `Field '${fieldName}' must be lowerCamelCase. Suggested: '${suggestion}'`,
      path: context.path,
    });
  }

  return errors;
};
