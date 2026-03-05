import sys
import asyncio
from pathlib import Path
import json
import pytest

# Add src directory to sys.path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from mcp_server.server import validate_openapi


@pytest.mark.asyncio
async def test_api_validation_rules():
    """Test that API validation detects required rules."""
    spec_path = str(project_root / "tests" / "data" / "bad_api_spec.yaml")

    result = await validate_openapi(spec_path)

    violations = result.get("violations", [])

    checks = {
        "verb_detected": False,
        "crud_detected": False,
        "versioning_detected": False,
    }

    for v in violations:
        rule = v.get("rule_id", "")
        if rule == "no-verbs-in-url":
            checks["verb_detected"] = True
        elif rule == "no-crud-names":
            checks["crud_detected"] = True
        elif rule == "versioning-required":
            checks["versioning_detected"] = True

    # Use pytest assertions
    assert checks["verb_detected"] is True, "Verb rule detection failed"
    assert checks["crud_detected"] is True, "CRUD rule detection failed"
    assert checks["versioning_detected"] is True, "Versioning rule detection failed"
    assert all(checks.values()) is True, f"Not all checks passed: {checks}"


async def main():
    """Legacy main function for manual testing."""
    spec_path = str(project_root / "tests" / "data" / "bad_api_spec.yaml")
    print(f"Testing validation on: {spec_path}")

    result = await validate_openapi(spec_path)

    print("\n--- Validation Result ---")
    print(json.dumps(result, indent=2))

    violations = result.get("violations", [])

    checks = {
        "verb_detected": False,
        "crud_detected": False,
        "versioning_detected": False,
    }

    for v in violations:
        rule = v.get("rule_id", "")
        if rule == "no-verbs-in-url":
            checks["verb_detected"] = True
            print(f"\n[SUCCESS] Verb Rule detected: {v.get('description')}")
        elif rule == "no-crud-names":
            checks["crud_detected"] = True
            print(f"\n[SUCCESS] CRUD Rule detected: {v.get('description')}")
        elif rule == "versioning-required":
            checks["versioning_detected"] = True
            print(f"\n[SUCCESS] Versioning Rule detected: {v.get('description')}")

    if all(checks.values()):
        print("\n[SUCCESS] All API verification checks passed!")
        sys.exit(0)
    else:
        print(f"\n[FAILURE] Checks failed: {checks}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
