import subprocess
import os
import logging
import sys

logger = logging.getLogger(__name__)


class TestRunner:
    def run(self, project_path: str) -> tuple[int, str]:
        """
        Returns (return_code, stderr_output)
        """
        raise NotImplementedError


class RuffRunner(TestRunner):
    def run(self, project_path: str) -> tuple[int, str]:
        logger.info("Strategy: Ruff Static Analysis")

        cmd = [
            "ruff", "check", project_path,
            "--select", "E9,F63,F7,F821",
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


# -----------------------

class DockerRunner(TestRunner):
    def run(self, project_path: str) -> tuple[int, str]:
        logger.info("Strategy: Docker execution")

        # 1. Build
        image_name = "ai-migration-test"
        logger.info("Building Docker image...")
        build_cmd = ["docker", "build", "-t", image_name, "."]

        try:
            build_res = subprocess.run(
                build_cmd, cwd=project_path, capture_output=True, text=True, check=False
            )
            if build_res.returncode != 0:
                logger.error(f"Docker build failed: {build_res.stderr}")
                # return a special code -2 to indicate Dependency/Build failure
                return -2, build_res.stderr
        except Exception as e:
            return -2, str(e)

        # 2. Run
        logger.info("Running Docker container...")
        run_cmd = ["docker", "run", "--rm", image_name]
        try:
            run_res = subprocess.run(
                run_cmd, capture_output=True, text=True, timeout=60
            )
            return run_res.returncode, run_res.stderr
        except subprocess.TimeoutExpired:
            logger.error("Docker execution timed out.")
            return -1, "Execution timed out."
        except Exception as e:
            return -1, str(e)


class LocalRunner(TestRunner):
    def run(self, project_path: str) -> tuple[int, str]:
        logger.info("Strategy: Local Venv execution")

        venv_path = os.path.join(project_path, ".venv_agent")

        # Determine executable based on OS
        if os.name == 'nt':
            python_exe = os.path.join(venv_path, "Scripts", "python.exe")
            pip_exe = os.path.join(venv_path, "Scripts", "pip.exe")
        else:
            python_exe = os.path.join(venv_path, "bin", "python")
            pip_exe = os.path.join(venv_path, "bin", "pip")

        # 1. Create Venv (if not exists)
        if not os.path.exists(venv_path):
            logger.info(f"Creating venv at {venv_path}")
            try:
                subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
            except Exception as e:
                logger.error(f"Failed to create venv: {e}")
                return -1, str(e)

        # 2. Install Dependencies
        req_path = os.path.join(project_path, "requirements.txt")
        if os.path.exists(req_path):
            logger.info("Installing dependencies...")
            try:
                install_res = subprocess.run(
                    [pip_exe, "install", "-r", "requirements.txt"],
                    cwd=project_path, capture_output=True, text=True
                )
                if install_res.returncode != 0:
                    # Check for dependency conflicts
                    if "ResolutionImpossible" in install_res.stderr or "conflict" in install_res.stderr.lower():
                        logger.error("Dependency conflict detected.")
                        return -2, install_res.stderr

                    logger.error(f"Pip install failed: {install_res.stderr}")
                    return -2, install_res.stderr
            except Exception as e:
                return -2, str(e)

        # 3. Execute Tests/Main
        # Priority: pytest -> main.py
        cmd = []
        # Check for tests folder
        if os.path.exists(os.path.join(project_path, "tests")) or \
                any(f.startswith("test_") for f in os.listdir(project_path)):
            logger.info("Running tests via pytest...")
            # We assume pytest is installed or we try to run it as module
            cmd = [python_exe, "-m", "pytest"]
        else:
            logger.info("Running main.py script...")
            main_script = "main.py"  # Heuristic: assume main.py exists or find entrypoint
            if not os.path.exists(os.path.join(project_path, main_script)):
                return -1, "Could not find main.py entrypoint."
            cmd = [python_exe, main_script]

        try:
            run_res = subprocess.run(
                cmd, cwd=project_path, capture_output=True, text=True, timeout=90
            )
            return run_res.returncode, run_res.stderr + "\n" + run_res.stdout
        except subprocess.TimeoutExpired:
            logger.warning("Execution timed out (90s). Assuming infinite loop or long process.")
            return 0, ""
        except Exception as e:
            return -1, str(e)