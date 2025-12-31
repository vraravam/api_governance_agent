import sys
import asyncio
from pathlib import Path
import json
import pytest

# Add src directory to sys.path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from mcp_server.server import validate_architecture


@pytest.mark.asyncio
async def test_architecture_validation_rules():
    """Test that architecture validation detects required rules."""
    test_classes_path = str(project_root / "tests" / "data" / "java_sample" / "classes")

    result = await validate_architecture(test_classes_path)

    violations = result.get("violations", [])

    # Check for different types of violations
    checks = {
        "package_violations": False,
        "naming_violations": False,
        "dependency_violations": False,
    }

    for v in violations:
        description = v.get("description", "").lower()

        # Check for package violations
        if "does not reside in" in description or "package" in description:
            checks["package_violations"] = True

        # Check for naming violations
        if "simple name" in description or "starting with" in description:
            checks["naming_violations"] = True

        # Check for dependency violations (field access, controller-repository, etc)
        if "field" in description or "gets field" in description:
            checks["dependency_violations"] = True

    # Use pytest assertions - at least one violation type should be detected
    assert any(checks.values()) is True, f"No violations detected: {checks}"
    assert len(violations) > 0, "Expected to find violations"


async def main():
    """Legacy main function for manual testing."""
    test_classes_path = str(project_root / "tests" / "data" / "java_sample" / "classes")
    print(f"Testing validation on: {test_classes_path}")

    result = await validate_architecture(test_classes_path)

    print("\n--- Validation Result ---")
    print(json.dumps(result, indent=2))

    violations = result.get("violations", [])

    # Check for different types of violations
    checks = {
        "package_violations": False,
        "naming_violations": False,
        "dependency_violations": False,
    }

    for v in violations:
        description = v.get("description", "").lower()

        # Check for package violations
        if "does not reside in" in description or "package" in description:
            checks["package_violations"] = True
            if not checks.get("printed_package"):
                print(
                    f"\n[SUCCESS] Package violation detected: {v.get('description')[:100]}..."
                )
                checks["printed_package"] = True

        # Check for naming violations
        if "simple name" in description or "starting with" in description:
            checks["naming_violations"] = True
            if not checks.get("printed_naming"):
                print(
                    f"\n[SUCCESS] Naming violation detected: {v.get('description')[:100]}..."
                )
                checks["printed_naming"] = True

        # Check for dependency violations (field access, controller-repository, etc)
        if "field" in description or "gets field" in description:
            checks["dependency_violations"] = True
            if not checks.get("printed_dependency"):
                print(
                    f"\n[SUCCESS] Dependency violation detected: {v.get('description')[:100]}..."
                )
                checks["printed_dependency"] = True

    if any(checks.values()):
        print("\n[SUCCESS] Architecture validation test passed!")
        print(f"Found: {len(violations)} total violations")
        sys.exit(0)
    else:
        print("\n[FAILURE] No violations detected!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
