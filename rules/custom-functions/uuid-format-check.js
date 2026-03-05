module.exports = (targetVal, opts, context) => {
  const parameter = targetVal;

  if (!parameter || typeof parameter !== "object") {
    return [];
  }

  const errors = [];
  const paramName = parameter.name;

  // Check if parameter name ends with 'id' or 'Id'
  if (!paramName || !/id$/i.test(paramName)) {
    return errors;
  }

  // Check schema
  const schema = parameter.schema;
  if (!schema) {
    return errors;
  }

  // Validate that type is string
  if (schema.type !== "string") {
    errors.push({
      message: `ID parameter '${paramName}' should be type 'string' (UUID), not '${schema.type}'`,
      path: [...context.path, "schema", "type"],
    });
  }

  // Validate that format is uuid
  if (schema.format !== "uuid") {
    errors.push({
      message: `ID parameter '${paramName}' must use format 'uuid'. Sequential integers are not allowed for security reasons`,
      path: [...context.path, "schema", "format"],
    });
  }

  return errors;
};
