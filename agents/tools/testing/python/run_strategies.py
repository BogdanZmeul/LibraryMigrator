import subprocess
import logging

logger = logging.getLogger(__name__)


class TestRunner:
    def run(self, project_path: str) -> tuple[int, str]:
        raise NotImplementedError


class RuffRunner(TestRunner):
    def run(self, project_path: str) -> tuple[int, str]:
        logger.info("Strategy: Ruff Static Analysis (Critical .py only)")

        cmd = [
            "ruff", "check", project_path,
            "--select", "E9,F63,F7",
            "--exclude", "*.ipynb",
            "--output-format", "json"
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            return res.returncode, res.stdout
        except FileNotFoundError:
            logger.error("Ruff is not installed. Please install it via 'pip install ruff'.")
            return -1, "[]"
        except Exception as e:
            logger.error(f"Ruff execution error: {e}")
            return -1, "[]"