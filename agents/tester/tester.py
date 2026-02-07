"""
Tester Agent - runs pytest and collects errors after migration
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Tester:
    """
    Agent responsible for testing migrated code using pytest
    """

    def __init__(self, repo_path: str):
        """
        Initialize Tester agent

        Args:
            repo_path: Path to the repository after migration
        """
        self.repo_path = Path(repo_path)
        self.errors = []
        self.error_id_counter = 1

        logger.info(f"Tester agent initialized for repository: {repo_path}")

    def run_tests(self) -> Dict:
        """
        Main entry point - runs pytest and returns results

        Returns:
            Dictionary with test results:
            {
                "status": "success" | "failed" | "error",
                "errors_count": int,
                "errors_file": str or None,
                "exit_code": int
            }
        """
        logger.info("=" * 60)
        logger.info("Starting test execution...")
        logger.info("=" * 60)

        # Execute pytest
        result = self._execute_pytest()
        exit_code = result['returncode']

        # Determine status based on exit code
        if exit_code == 0:
            status = "success"
            logger.info("✓ All tests passed successfully!")
        elif exit_code == -1:
            # Special case: execution error (timeout, pytest not found, etc.)
            status = "error"
            logger.error("✗ Test execution failed due to system error")
        else:
            # pytest failed (exit code 1 or higher)
            status = "failed"
            logger.warning(f"✗ Tests failed with exit code: {exit_code}")

        return {
            "status": status,
            "errors_count": 0,  # Will be updated when we parse errors
            "errors_file": None,
            "exit_code": exit_code
        }

    def _execute_pytest(self) -> Dict:
        """
        Execute pytest via subprocess

        Returns:
            Dictionary with execution results:
            {
                "returncode": int,
                "stdout": str,
                "stderr": str
            }
        """
        logger.info(f"Executing pytest in directory: {self.repo_path}")

        command = ["pytest", "tests/", "-v", "--tb=short"]

        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            logger.info(f"Pytest execution completed with exit code: {result.returncode}")

            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        except subprocess.TimeoutExpired:
            logger.error("Pytest execution timed out after 5 minutes")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "Test execution timed out after 300 seconds"
            }
        except FileNotFoundError:
            logger.error("Pytest not found. Is it installed?")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "pytest command not found. Please install pytest."
            }
        except Exception as e:
            logger.error(f"Unexpected error during pytest execution: {str(e)}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Unexpected error: {str(e)}"
            }

    def _parse_errors(self, output: str) -> List[Dict]:
        """
        Parse errors from pytest output

        Args:
            output: Combined stderr and stdout from pytest

        Returns:
            List of error dictionaries
        """
        # TODO: Implement error parsing
        pass

    def _save_errors(self, errors: List[Dict]) -> str:
        """
        Save errors to errors.json

        Args:
            errors: List of error dictionaries

        Returns:
            Path to saved errors.json file
        """
        # TODO: Implement error saving
        pass
