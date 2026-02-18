#!/usr/bin/env python3
"""
Master test runner - Run all tests with pytest
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Run all tests with detailed output using pytest"""

    # Get tests directory
    tests_dir = Path(__file__).parent.parent / "tests"

    # Run pytest with verbose output
    cmd = [sys.executable, "-m", "pytest", str(tests_dir)]

    result = subprocess.run(cmd)

    print()

    # Exit with pytest's exit code
    if result.returncode == 0:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
