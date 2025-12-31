module.exports = (targetVal, opts, context) => {
  const path = targetVal;

  if (typeof path !== "string") {
    return [];
  }

  const errors = [];

  // Count resource nesting (non-parameter segments)
  const segments = path.split("/").filter((segment) => {
    if (/^v\d+$/.test(segment)) return false;
    if (segment === "") return false;
    return true;
  });

  // Count actual resource levels (not including path parameters)
  let resourceLevels = 0;
  for (const segment of segments) {
    if (!/^\{.*\}$/.test(segment)) {
      resourceLevels++;
    }
  }

  const maxLevels = opts?.maxLevels || 2;

  if (resourceLevels > maxLevels) {
    errors.push({
      message: `Path has ${resourceLevels} resource levels. Maximum recommended is ${maxLevels}. Consider flattening: use top-level resources with filters instead of deep nesting`,
      path: context.path,
    });
  }

  return errors;
};
