"""
Process execution utilities for running external commands.
"""

import subprocess
import shutil
from typing import Optional, List
from utils.logger import logger


class ProcessResult:
    """Result of a process execution"""

    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.success = returncode == 0

    def __bool__(self):
        return self.success


class ProcessUtils:
    """Utility class for running external processes"""

    @staticmethod
    def run_command(
        cmd: List[str],
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        capture_output: bool = True,
        check: bool = False,
    ) -> ProcessResult:
        """
        Run a command and return result.

        Args:
          cmd: Command and arguments as list
          cwd: Working directory
          timeout: Timeout in seconds
          capture_output: Whether to capture stdout/stderr
          check: Whether to raise exception on non-zero exit

        Returns:
          ProcessResult object

        Raises:
          subprocess.CalledProcessError: If check=True and command fails
          subprocess.TimeoutExpired: If timeout is exceeded
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                check=check,
            )
            return ProcessResult(result.returncode, result.stdout, result.stderr)
        except subprocess.CalledProcessError as e:
            return ProcessResult(e.returncode, e.stdout, e.stderr)

    @staticmethod
    def run_command_safe(
        cmd: List[str], cwd: Optional[str] = None, timeout: Optional[int] = None
    ) -> ProcessResult:
        """
        Run command, logging errors but not raising exceptions.

        Args:
          cmd: Command and arguments as list
          cwd: Working directory
          timeout: Timeout in seconds

        Returns:
          ProcessResult object (never raises)
        """
        try:
            return ProcessUtils.run_command(cmd, cwd=cwd, timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
            return ProcessResult(1, "", "Command timed out")
        except Exception as e:
            logger.error(f"Command failed: {' '.join(cmd)}: {e}")
            return ProcessResult(1, "", str(e))

    @staticmethod
    def check_binary_exists(binary_name: str) -> bool:
        """
        Check if a binary exists in PATH.

        Args:
          binary_name: Name of binary to check

        Returns:
          True if binary exists, False otherwise
        """
        return shutil.which(binary_name) is not None

    @staticmethod
    def get_binary_path(binary_name: str) -> Optional[str]:
        """
        Get full path to binary if it exists.

        Args:
          binary_name: Name of binary

        Returns:
          Full path to binary or None if not found
        """
        return shutil.which(binary_name)

    @staticmethod
    def get_binary_version(binary_name: str) -> Optional[str]:
        """
        Get version of a binary.

        Args:
          binary_name: Name of binary

        Returns:
          Version string or None if not available
        """
        if not ProcessUtils.check_binary_exists(binary_name):
            return None

        # Try common version flags
        for flag in ["--version", "-v", "version"]:
            result = ProcessUtils.run_command_safe([binary_name, flag], timeout=5)
            if result.success:
                # Return first line of output
                output = result.stdout.strip() or result.stderr.strip()
                if output:
                    return output.split("\n")[0]

        return None

    @staticmethod
    def compile_java(
        source_file: str, classpath: str, output_dir: Optional[str] = None
    ) -> ProcessResult:
        """
        Compile a Java source file.

        Args:
          source_file: Path to Java source file
          classpath: Classpath string
          output_dir: Output directory for compiled classes

        Returns:
          ProcessResult object
        """
        cmd = ["javac", "-cp", classpath]
        if output_dir:
            cmd.extend(["-d", output_dir])
        cmd.append(source_file)

        return ProcessUtils.run_command_safe(cmd, timeout=60)

    @staticmethod
    def run_java(
        class_name: str,
        classpath: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> ProcessResult:
        """
        Run a Java class.

        Args:
          class_name: Fully qualified class name
          classpath: Classpath string
          args: Additional arguments to pass to Java program
          cwd: Working directory

        Returns:
          ProcessResult object
        """
        cmd = ["java", "-cp", classpath, class_name]
        if args:
            cmd.extend(args)

        return ProcessUtils.run_command_safe(cmd, cwd=cwd, timeout=300)
