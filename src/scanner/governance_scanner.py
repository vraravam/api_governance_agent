from typing import Optional, NamedTuple, List, Dict
from pathlib import Path

from scanner.project_detector import ProjectDetector
from engines.spectral_runner import SpectralRunner
from engines.llm_analyzer import LLMAnalyzer
from report.report_generator import ReportGenerator
from autofix.category_manager import CategoryManager
from utils.logger import logger
from utils import FileUtils


class ScanResult(NamedTuple):
    """Result of a governance scan"""

    project_path: str
    spec_files: List[str]
    spectral_results: List[Dict]
    llm_results: List[Dict]
    scan_type: str = "API Specification"

    @property
    def total_violations(self) -> int:
        return len(self.spectral_results) + len(self.llm_results)

    @property
    def error_count(self) -> int:
        errors = 0
        for violation in self.spectral_results + self.llm_results:
            if violation.get("severity") == 0:  # 0=error
                errors += 1
        return errors


class GovernanceScanner:
    """Main orchestrator for the governance scanning process"""

    def __init__(self, project_path: str, ruleset_path: str, llm_endpoint: str):
        self.project_path = project_path
        self.detector = ProjectDetector(project_path)
        self.spectral = SpectralRunner(ruleset_path)
        self.llm = LLMAnalyzer(llm_endpoint)

    async def scan(
        self,
        output_path: Optional[str] = None,
        target_spec: Optional[str] = None,
        interactive: bool = False,
    ) -> ScanResult:
        """Execute full governance scan

        Args:
            output_path: Path to save the report
            target_spec: Specific spec file to scan
            interactive: If True, prompt user for spec path if not found
        """
        logger.info("Starting API Governance Scan...")

        # Step 1: Detect project type
        is_java, build_tool = self.detector.is_java_project()
        if not is_java:
            logger.warning(
                "Not a recognized Java project (no pom.xml or build.gradle found)"
            )
        else:
            logger.info(f"Detected {build_tool} project")

        # Step 2: Locate OpenAPI specs
        if target_spec:
            target_path = Path(target_spec)
            if target_path.is_absolute():
                spec_to_check = target_path
            else:
                # Relative path - resolve from project directory
                spec_to_check = Path(self.project_path) / target_spec

            if spec_to_check.exists():
                specs = [spec_to_check]
                logger.info(f"✓ Using specified spec: {spec_to_check}")
                logger.info(f"  File type: {spec_to_check.suffix.upper()}")
            else:
                logger.error(f"✗ Specified spec not found: {spec_to_check}")
                specs = []
        else:
            specs = self.detector.find_openapi_specs()
            if not specs:
                if interactive:
                    # Prompt user for spec path
                    logger.info("🔍 No OpenAPI specs auto-detected.")
                    print("\n" + "=" * 60)
                    print("📝 OpenAPI Specification Location")
                    print("=" * 60)
                    print("Please provide the path to your OpenAPI specification file.")
                    print("Supported formats: .yaml, .yml, .json")
                    print("You can use:")
                    print("  - Absolute path: /full/path/to/openapi.json")
                    print("  - Relative path: ./docs/api-spec.json")
                    print("  - Press Enter to skip API scanning")
                    print("=" * 60)

                    user_spec = input("Spec file path: ").strip()

                    if user_spec:
                        user_path = Path(user_spec).expanduser()
                        if not user_path.is_absolute():
                            user_path = Path(self.project_path) / user_path

                        if user_path.exists():
                            specs = [user_path]
                            logger.info(f"✓ Using provided spec: {user_path}")
                        else:
                            logger.error(f"✗ File not found: {user_path}")
                            logger.info("📝 Continuing without API spec scanning...")
                            specs = []
                    else:
                        logger.info("📝 Skipping API spec scanning (user choice)")
                        specs = []
                else:
                    logger.warning("⚠️  No OpenAPI specifications found in project.")
                    logger.info(
                        "💡 Tip: If your project has OpenAPI/Swagger specs, you can:"
                    )
                    logger.info("   - Use --spec flag: --spec path/to/openapi.json")
                    logger.info(
                        "   - Use --interactive flag to be prompted for the path"
                    )
                    logger.info("   - Place spec in standard locations:")
                    logger.info(
                        "     • src/main/resources/openapi.json or openapi.yaml"
                    )
                    logger.info("     • openapi.json or openapi.yaml (project root)")
                    logger.info("     • api/openapi.json")
                    logger.info(
                        "📝 Continuing with ArchUnit scan only (Java architecture rules)..."
                    )
                    specs = []
            else:
                logger.info(f"✓ Found {len(specs)} OpenAPI specification(s):")
                for spec in specs:
                    logger.info(f"  - {spec.name} ({spec.suffix.upper()[1:]} format)")

        # Step 3: Validate and scan each spec
        all_spectral_results = []
        all_llm_results = []
        valid_specs = []

        for spec in specs:
            logger.info(f"Validating: {spec}")
            is_valid, error = self.detector.validate_spec_syntax(spec)

            if not is_valid:
                logger.error(f"Invalid spec {spec}: {error}")
                continue

            valid_specs.append(str(spec))

            # Load spec content for analysis (support both YAML and JSON)
            try:
                spec_content, _ = FileUtils.read_spec_file(str(spec))
            except Exception as e:
                logger.warning(
                    f"Failed to parse spec content for {spec}: {e}. Proceeding with Spectral check only."
                )
                spec_content = {}

            # Run Spectral
            logger.info(f"Running Spectral analysis on {spec.name}...")
            spectral_results = self.spectral.run_spectral(spec)
            logger.info(f"Spectral found {len(spectral_results)} violations")

            # Check if Spectral failed silently (returns empty list when binary not found)
            if not spectral_results and valid_specs:
                logger.warning(
                    "⚠️  Spectral returned 0 violations - if this is unexpected, check if Spectral is installed"
                )
                logger.warning(
                    "⚠️  Install with: npm install -g @stoplight/spectral-cli"
                )

            # Enhance Spectral violations with LLM context and descriptions
            # Enhance Spectral violations with LLM context and descriptions
            # Skipped as per user request to move AI to fix phase
            # if spectral_results:
            #     logger.info(f"Enhancing Spectral violations with LLM context...")
            #     try:
            #         spectral_results = await self.llm.enhance_spectral_violations(spectral_results, spec_content)
            #         enhanced_count = len([r for r in spectral_results if r.get('enhanced')])
            #         logger.info(f"LLM enhanced {enhanced_count}/{len(spectral_results)} violations")
            #     except Exception as e:
            #         logger.warning(f"LLM enhancement failed: {str(e)}. Using original Spectral results.")

            all_spectral_results.extend(spectral_results)

            # Run LLM semantic analysis
            # Skipped to speed up scan
            # logger.info(f"Running LLM semantic analysis on {spec.name}...")
            # llm_results = await self.llm.analyze_spec(spec, spec_content)
            # all_llm_results.extend(llm_results)
            # logger.info(f"LLM found {len(llm_results)} semantic issues")

        # Step 4: Create scan result
        # Ensure we return empty results if nothing was scanned (to avoid errors in server.py)
        scan_result = ScanResult(
            project_path=self.project_path,
            spec_files=valid_specs,
            spectral_results=all_spectral_results,
            llm_results=all_llm_results,
            scan_type="API Specification",
        )

        if output_path:
            output_file = Path(output_path)
        else:
            # Default to project root
            output_file = Path(self.project_path) / "api-governance-report.md"

        if output_file:
            report_gen = ReportGenerator(scan_result)
            report_gen.generate_markdown(output_file)

            # Auto-categorize violations for incremental fixing
            all_violations = scan_result.spectral_results + scan_result.llm_results
            if all_violations:
                logger.info("Categorizing violations for incremental fixing...")
                category_manager = CategoryManager()
                categorized = category_manager.categorize_violations(all_violations)
                category_summary = category_manager.generate_category_summary(
                    all_violations
                )

                logger.info(f"Violations organized into {len(categorized)} categories:")
                for cat_name, cat_violations in categorized.items():
                    if cat_violations:
                        category_info = CategoryManager.CATEGORIES[cat_name]
                        logger.info(
                            f"  • {cat_name}: {len(cat_violations)} violations (Priority {category_info.priority}, {category_info.estimated_effort} effort)"
                        )

            # Generate JSON report for auto-fix tools with categories
            json_output = output_file.parent / "governance-report.json"

            # SAFEGUARD: Don't overwrite existing report if we got 0 violations (might indicate Spectral not installed)
            if json_output.exists() and scan_result.total_violations == 0:
                logger.warning(f"⚠️  Governance report already exists at {json_output}")
                logger.warning(
                    "⚠️  Current scan found 0 violations - NOT overwriting existing report"
                )
                logger.warning(
                    "⚠️  This might indicate Spectral is not installed or misconfigured"
                )
                logger.warning(
                    "⚠️  To force overwrite, delete the existing report first"
                )
            else:
                report_gen.generate_json(json_output, include_categories=True)
                if scan_result.total_violations == 0:
                    logger.warning(
                        "⚠️  Created report with 0 violations - if OpenAPI specs exist, check Spectral installation"
                    )

        logger.info("Scan complete!")
        logger.info(f"Total Violations: {scan_result.total_violations}")

        return scan_result
