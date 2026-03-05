from pathlib import Path
from typing import List, Dict
from utils.logger import logger
from utils import ProcessUtils, FileUtils
import tempfile
import os


class SpectralRunner:
    """Executes Spectral CLI with custom ruleset"""

    def __init__(self, ruleset_path: str):
        self.ruleset_path = ruleset_path

    def run_spectral(self, spec_path: Path) -> List[Dict]:
        """Execute Spectral and return structured results"""
        try:
            # Use output file to avoid stdout buffer issues with large JSON
            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".json", delete=False
            ) as tmp:
                output_file = tmp.name

            try:
                cmd = [
                    "spectral",
                    "lint",
                    str(spec_path),
                    "--ruleset",
                    self.ruleset_path,
                    "--format",
                    "json",
                    "--output",
                    output_file,
                ]

                result = ProcessUtils.run_command(cmd, timeout=60)

                # Check for Spectral configuration errors in stderr
                if result.stderr:
                    error_message = result.stderr
                    # If it's a ruleset validation error, log it but continue
                    if (
                        "the value has to be one of" in error_message
                        or "RulesetValidationError" in error_message
                    ):
                        logger.warning(
                            f"Spectral ruleset validation error: {error_message.split('Error')[0] if 'Error' in error_message else error_message[:200]}"
                        )
                        return []
                    # Don't treat stderr as fatal - Spectral writes warnings there
                    elif result.returncode != 0:
                        logger.warning(f"Spectral stderr: {error_message[:200]}")

                # Read JSON from output file (more reliable for large outputs)
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    try:
                        violations = FileUtils.read_json(output_file)

                        # Handle case where violations is an empty list or has results
                        if isinstance(violations, list):
                            logger.info(
                                f"Spectral found {len(violations)} violations in {spec_path.name}"
                            )
                            return self._structure_violations(violations)
                        else:
                            logger.warning("Spectral returned unexpected JSON format")
                            return []
                    except Exception as e:
                        logger.error(f"Failed to parse Spectral JSON output: {str(e)}")
                        # Try to read and show a sample of the problematic content
                        try:
                            content = FileUtils.read_text(output_file)
                            logger.debug(f"Output file size: {len(content)} chars")
                            logger.debug(f"First 200 chars: {content[:200]}")
                            logger.debug(f"Last 200 chars: {content[-200:]}")
                        except:
                            pass
                        return []
                    except Exception as e:
                        logger.error(f"Error reading Spectral output file: {str(e)}")
                        return []
                else:
                    logger.info(f"No violations found in {spec_path.name}")
                    return []

            finally:
                # Clean up temp file
                try:
                    if os.path.exists(output_file):
                        os.unlink(output_file)
                except:
                    pass

            return []

        except Exception as e:
            if "timed out" in str(e).lower():
                logger.error("Spectral execution timed out")
            elif not ProcessUtils.check_binary_exists("spectral"):
                logger.error(
                    "Spectral CLI not found. Install with: npm install -g @stoplight/spectral-cli"
                )
                logger.error("Or ensure 'spectral' is in your PATH")
            else:
                logger.error(f"Spectral execution failed: {str(e)}")
                logger.error(
                    "💡 Hint: Install Spectral with: npm install -g @stoplight/spectral-cli"
                )
            return []

    def _structure_violations(self, violations: List[Dict]) -> List[Dict]:
        """Convert Spectral output to structured format"""
        from utils import ViolationUtils

        return [ViolationUtils.normalize_spectral_violation(v) for v in violations]
