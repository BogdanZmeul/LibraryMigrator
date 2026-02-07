"""
Tester Agent - runs pytest and collects errors after migration
"""

import logging
import subprocess
import json
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
            Dictionary with test results
        """
        logger.info("=" * 60)
        logger.info("Starting test execution...")
        logger.info("=" * 60)

        # Execute pytest
        result = self._execute_pytest()
        exit_code = result['returncode']

        # Determine status and create errors
        if exit_code == 0:
            status = "success"
            logger.info("✓ All tests passed successfully!")
            errors = []
        elif exit_code == -1:
            status = "error"
            logger.error("✗ Test execution failed due to system error")
            # Create generic system error
            errors = [{
                "error_id": 1,
                "message": result['stderr'],
                "file": "unknown",
                "line": "unknown",
                "context": "System error during test execution"
            }]
        else:
            status = "failed"
            logger.warning(f"✗ Tests failed with exit code: {exit_code}")
            # Create generic error (will be replaced with real parsing later)
            errors = [{
                "error_id": 1,
                "message": "Tests failed. See pytest output for details.",
                "file": "unknown",
                "line": "unknown",
                "context": result['stderr'][:500]  # First 500 chars
            }]

        # Save errors to JSON
        errors_file = self._save_errors(errors)

        return {
            "status": status,
            "errors_count": len(errors),
            "errors_file": errors_file,
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
        output_file = self.repo_path / "errors.json"

        logger.info(f"Saving {len(errors)} errors to {output_file}")

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(errors, f, indent=2, ensure_ascii=False)

            logger.info(f"✓ Errors successfully saved to {output_file}")
            return str(output_file)

        except Exception as e:
            logger.error(f"Failed to save errors.json: {str(e)}")
            return None
