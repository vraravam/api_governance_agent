"""
Build Validator - Automates build and re-scan workflow after applying fixes

Handles the complete validation cycle:
1. Detect build system (Maven/Gradle)
2. Run build to compile Java classes
3. Re-run governance scan for specific category
4. Compare violations before/after
5. Report validation results
"""

import subprocess
import json
from typing import Optional, Dict, List
from pathlib import Path
from dataclasses import dataclass


@dataclass
class BuildResult:
    """Result of a build operation"""

    success: bool
    build_tool: str
    output: str
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class ValidationResult:
    """Result of fix validation"""

    category: str
    violations_before: int
    violations_after: int
    violations_fixed: int
    new_violations: int
    build_result: BuildResult
    scan_result: Dict
    success: bool
    message: str


class BuildValidator:
    """
    Validates fixes by rebuilding project and re-scanning

    Workflow:
    1. Detect build system (Maven/Gradle)
    2. Run build to compile changes
    3. Re-run ArchUnit tests to detect new violations
    4. Re-run Spectral for API specs
    5. Compare violations before/after
    """

    def __init__(self, project_path: str):
        """
        Initialize build validator

        Args:
            project_path: Root path of the project
        """
        self.project_path = Path(project_path)

    def detect_build_system(self) -> Optional[str]:
        """
        Detect which build system the project uses

        Returns:
            'gradle', 'maven', or None
        """
        if (self.project_path / "build.gradle").exists() or (
            self.project_path / "build.gradle.kts"
        ).exists():
            return "gradle"
        elif (self.project_path / "pom.xml").exists():
            return "maven"
        return None

    def run_build(
        self, build_tool: Optional[str] = None, clean: bool = True
    ) -> BuildResult:
        """
        Run project build (Maven or Gradle)

        Args:
            build_tool: Explicitly specify 'gradle' or 'maven', or auto-detect
            clean: Whether to run clean before build

        Returns:
            BuildResult with build status
        """
        import time

        if not build_tool:
            build_tool = self.detect_build_system()

        if not build_tool:
            return BuildResult(
                success=False,
                build_tool="unknown",
                output="",
                error="No build system detected (pom.xml or build.gradle not found)",
            )

        print(f"\n🔨 Building project with {build_tool.upper()}...")

        # Construct build command
        # For governance validation, we only need:
        # 1. Compilation (verify code compiles)
        # 2. Unit tests (verify behavior correct)
        # 3. Skip static analysis tools (SpotBugs, PMD, OWASP Dependency-Check)
        if build_tool == "gradle":
            # Use gradlew if available, otherwise gradle
            gradle_wrapper = self.project_path / "gradlew"
            gradle_cmd = str(gradle_wrapper) if gradle_wrapper.exists() else "gradle"

            # Use 'test' task which compiles + runs tests
            # The 'test' task doesn't automatically run static analysis tools,
            # so we don't need to explicitly exclude them unless 'check' is configured
            # to depend on 'test' (which would trigger them)
            tasks = ["clean"] if clean else []
            tasks.append("test")
            cmd = [gradle_cmd] + tasks + ["--no-daemon", "--console=plain"]
        else:  # maven
            mvn_wrapper = self.project_path / "mvnw"
            mvn_cmd = str(mvn_wrapper) if mvn_wrapper.exists() else "mvn"

            # Use 'test' phase which compiles + runs tests
            # Skip static analysis plugins (these are common Maven plugins)
            phases = ["clean"] if clean else []
            phases.extend(
                [
                    "test",
                    "-Dspotbugs.skip=true",
                    "-Dpmd.skip=true",
                    "-Dcheckstyle.skip=true",
                    "-Ddependency-check.skip=true",
                ]
            )
            cmd = [mvn_cmd] + phases

        # Run build
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout (increased for large projects)
            )
            duration = time.time() - start_time

            success = result.returncode == 0

            if success:
                print(f"✅ Build successful ({duration:.1f}s)")
            else:
                print(f"❌ Build failed ({duration:.1f}s)")
                print(f"   Error: {result.stderr[:200]}")

            return BuildResult(
                success=success,
                build_tool=build_tool,
                output=result.stdout,
                error=result.stderr if not success else None,
                duration_seconds=duration,
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return BuildResult(
                success=False,
                build_tool=build_tool,
                output="",
                error=f"Build timeout after {duration:.1f}s",
                duration_seconds=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            return BuildResult(
                success=False,
                build_tool=build_tool,
                output="",
                error=str(e),
                duration_seconds=duration,
            )

    async def run_governance_scan(
        self, category: Optional[str] = None, output_dir: Optional[str] = None
    ) -> Dict:
        """
        Re-run governance scan after build

        Args:
            category: Optional category to filter violations
            output_dir: Output directory for scan results

        Returns:
            Scan result dictionary
        """
        print(
            f"\n🔍 Running governance scan{f' for category {category}' if category else ''}..."
        )

        if not output_dir:
            output_dir = str(self.project_path / "build" / "governance")

        # Import scanner directly instead of using subprocess
        try:
            import sys
            from pathlib import Path

            # Add src to path if not already there
            src_path = Path(__file__).parent.parent
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))

            # Ensure output directory exists
            output_path_obj = Path(output_dir)
            output_path_obj.mkdir(parents=True, exist_ok=True)

            from scanner.governance_scanner import GovernanceScanner
            from autofix.category_manager import CategoryManager

            # Run scanner
            scanner = GovernanceScanner(
                project_path=str(self.project_path),
                ruleset_path=str(src_path.parent / "rules" / "spectral_ruleset.yaml"),
                llm_endpoint="http://localhost:11434",
            )

            # Run async scan with file path
            report_file = output_path_obj / "governance-report.md"
            scan_result = await scanner.scan(output_path=str(report_file))

            # Load the generated report
            report_path = output_path_obj / "governance-report.json"
            if report_path.exists():
                with open(report_path, "r") as f:
                    scan_data = json.load(f)

                # Filter by category if specified
                if category and "violations" in scan_data:
                    cat_mgr = CategoryManager()

                    # Categorize all violations
                    categorized = cat_mgr.categorize_violations(scan_data["violations"])

                    # Get violations for this category
                    filtered_violations = categorized.get(category, [])

                    scan_data["violations"] = filtered_violations
                    scan_data["filtered_category"] = category

                print("✅ Scan completed successfully")
                return scan_data
            else:
                return {"success": False, "error": f"Report not found at {report_path}"}

        except Exception as e:
            import traceback

            print(f"⚠️  Scan failed: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    async def validate_fixes(
        self,
        category: str,
        violations_before: List[Dict],
        clean_build: bool = True,
        output_dir: Optional[str] = None,
    ) -> ValidationResult:
        """
        Complete validation workflow: build + scan + compare

        Args:
            category: Category that was fixed
            violations_before: Violations before fixes were applied
            clean_build: Whether to run clean before build
            output_dir: Output directory for scan results

        Returns:
            ValidationResult with comparison
        """
        print("\n" + "=" * 80)
        print(f"VALIDATING FIXES FOR CATEGORY: {category}")
        print("=" * 80)

        # Step 1: Run build
        build_result = self.run_build(clean=clean_build)

        if not build_result.success:
            return ValidationResult(
                category=category,
                violations_before=len(violations_before),
                violations_after=len(violations_before),  # Assume no change
                violations_fixed=0,
                new_violations=0,
                build_result=build_result,
                scan_result={},
                success=False,
                message=f"Build failed: {build_result.error}",
            )

        # Step 2: Re-run scan for this category
        scan_result = await self.run_governance_scan(
            category=category, output_dir=output_dir
        )

        if not scan_result or scan_result.get("success") == False:
            return ValidationResult(
                category=category,
                violations_before=len(violations_before),
                violations_after=len(violations_before),
                violations_fixed=0,
                new_violations=0,
                build_result=build_result,
                scan_result=scan_result,
                success=False,
                message=f"Scan failed: {scan_result.get('error', 'Unknown error')}",
            )

        # Step 3: Compare violations
        violations_after = scan_result.get("violations", [])

        # Calculate changes
        before_count = len(violations_before)
        after_count = len(violations_after)
        fixed_count = max(0, before_count - after_count)
        new_count = max(0, after_count - before_count)

        # Determine success
        success = (fixed_count > 0 or after_count == 0) and new_count == 0

        if success:
            if after_count == 0:
                message = f"✅ All {before_count} violations fixed!"
            else:
                message = f"✅ Fixed {fixed_count} violations ({after_count} remaining)"
        else:
            if new_count > 0:
                message = (
                    f"⚠️  Fixed {fixed_count} but introduced {new_count} new violations"
                )
            else:
                message = f"❌ No violations fixed ({after_count} remaining)"

        # Print summary
        print("\n" + "=" * 80)
        print("VALIDATION RESULTS")
        print("=" * 80)
        print(f"Category:           {category}")
        print(
            f"Build:              {'✅ Success' if build_result.success else '❌ Failed'}"
        )
        print(f"Violations Before:  {before_count}")
        print(f"Violations After:   {after_count}")
        print(f"Violations Fixed:   {fixed_count}")
        print(f"New Violations:     {new_count}")
        print(f"\n{message}")
        print("=" * 80 + "\n")

        return ValidationResult(
            category=category,
            violations_before=before_count,
            violations_after=after_count,
            violations_fixed=fixed_count,
            new_violations=new_count,
            build_result=build_result,
            scan_result=scan_result,
            success=success,
            message=message,
        )

    def save_validation_report(
        self, validation_result: ValidationResult, output_path: Optional[str] = None
    ) -> str:
        """
        Save validation results to JSON file

        Args:
            validation_result: ValidationResult to save
            output_path: Optional output path, defaults to project_path/validation-report.json

        Returns:
            Path to saved report
        """
        if not output_path:
            output_path = str(self.project_path / "validation-report.json")

        report_data = {
            "category": validation_result.category,
            "violations_before": validation_result.violations_before,
            "violations_after": validation_result.violations_after,
            "violations_fixed": validation_result.violations_fixed,
            "new_violations": validation_result.new_violations,
            "build": {
                "success": validation_result.build_result.success,
                "tool": validation_result.build_result.build_tool,
                "duration_seconds": validation_result.build_result.duration_seconds,
                "error": validation_result.build_result.error,
            },
            "scan": validation_result.scan_result,
            "success": validation_result.success,
            "message": validation_result.message,
        }

        with open(output_path, "w") as f:
            json.dump(report_data, f, indent=2)

        print(f"📄 Validation report saved to: {output_path}")
        return output_path
