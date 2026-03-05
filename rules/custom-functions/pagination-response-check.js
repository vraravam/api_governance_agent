module.exports = (targetVal, opts, context) => {
  const operation = targetVal;

  if (!operation || typeof operation !== "object") {
    return [];
  }

  const errors = [];

  // Check if operation has pagination parameters
  const parameters = operation.parameters || [];
  const hasPagination = parameters.some((p) => p.name === "page[size]" || p.name === "page[number]");

  if (!hasPagination) {
    return errors; // Not a paginated endpoint
  }

  // Check if 200 response includes totalItems
  const successResponse = operation.responses?.["200"];
  if (!successResponse) {
    return errors;
  }

  const schema = successResponse.content?.["application/json"]?.schema;
  if (!schema || !schema.properties?.data) {
    return errors;
  }

  const dataSchema = schema.properties.data;
  const rootProperties = schema.properties;

  // Check for totalItems at root level or in data
  if (!rootProperties.totalItems && !dataSchema.properties?.totalItems) {
    errors.push({
      message: 'Paginated response should include "totalItems" to aid client-side pagination',
      path: [...context.path, "responses", "200", "content", "application/json", "schema", "properties"],
    });
  }

  return errors;
};
