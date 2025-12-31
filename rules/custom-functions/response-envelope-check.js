module.exports = (targetVal, opts, context) => {
  const response = targetVal;

  if (!response || typeof response !== "object") {
    return [];
  }

  const errors = [];
  const statusCode = context.path[context.path.length - 1];

  // Get response schema
  const schema = response.content?.["application/json"]?.schema;
  if (!schema || !schema.properties) {
    return errors;
  }

  const properties = schema.properties;

  // Check success responses (2xx)
  if (/^2\d{2}$/.test(statusCode)) {
    if (!properties.data) {
      errors.push({
        message: `Success response (${statusCode}) must have 'data' property at root level`,
        path: [...context.path, "content", "application/json", "schema", "properties"],
      });
    }

    if (properties.errors) {
      errors.push({
        message: `Success response (${statusCode}) should not have 'errors' property`,
        path: [...context.path, "content", "application/json", "schema", "properties"],
      });
    }
  }

  // Check error responses (4xx, 5xx)
  if (/^[45]\d{2}$/.test(statusCode)) {
    if (!properties.errors) {
      errors.push({
        message: `Error response (${statusCode}) must have 'errors' property at root level`,
        path: [...context.path, "content", "application/json", "schema", "properties"],
      });
    }

    if (properties.data) {
      errors.push({
        message: `Error response (${statusCode}) should not have 'data' property`,
        path: [...context.path, "content", "application/json", "schema", "properties"],
      });
    }

    // Validate error structure
    if (properties.errors) {
      const errorsSchema = properties.errors;
      const errorProps = errorsSchema.properties;

      if (!errorProps?.type) {
        errors.push({
          message: 'Error object must have "type" property',
          path: [...context.path, "content", "application/json", "schema", "properties", "errors"],
        });
      }

      if (!errorProps?.description) {
        errors.push({
          message: 'Error object must have "description" property',
          path: [...context.path, "content", "application/json", "schema", "properties", "errors"],
        });
      }

      if (!errorProps?.details) {
        errors.push({
          message: 'Error object must have "details" array with field, code, message, developerMessage',
          path: [...context.path, "content", "application/json", "schema", "properties", "errors"],
        });
      }
    }
  }

  return errors;
};
