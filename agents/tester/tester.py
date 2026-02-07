import os
import logging
from agents.tools.io.json_handlers import save_json_file
from agents.tools.testing.python.run_strategies import DockerRunner, LocalRunner
from agents.tools.testing.python.error_parser import parse_python_traceback

logger = logging.getLogger(__name__)


def tester_node(state):
    logger.info("Tester: Start working...")

    project_path = state.get("project_path", ".")
    errors_path = state.get("errors_path", "errors.json")

    # clean previous errors
    save_json_file(errors_path, [])

    # look for docker in the client's repository
    has_docker = os.path.exists(os.path.join(project_path, "Dockerfile")) or \
                 os.path.exists(os.path.join(project_path, "docker-compose.yml"))

    runner = None
    if has_docker:
        runner = DockerRunner()
    else:
        # Check for requirements.txt for LocalRunner
        if os.path.exists(os.path.join(project_path, "requirements.txt")):
            runner = LocalRunner()
        else:
            logger.warning("No Dockerfile or requirements.txt found. Cannot determine run strategy.")
            return {"status": "cannot_test"}

    # run code
    return_code, stderr = runner.run(project_path)

    # CASE A: Dependency Conflict (-2 code from our runner)
    if return_code == -2:
        logger.error("Dependency conflict detected during installation/build.")
        # We do NOT write to errors.json because this is not a code fixable by Analyzer
        return {
            "status": "dependency_error",
            "message": "Migration complete, but tests failed due to dependency conflicts. Manual update required."
        }

    # CASE B: Success (0)
    if return_code == 0:
        logger.info("Execution finished successfully. No runtime errors detected.")
        return {"status": "success"}

    # CASE C: Runtime Errors (Non-zero)
    logger.info(f"Runtime errors detected (RC={return_code}). Parsing logs...")

    structured_errors = parse_python_traceback(stderr, project_path)

    if not structured_errors:
        logger.warning("Tester: Execution failed, but no Python traceback found in logs.")
        # This might be a segfault or other crash. We can't fix it automatically easily.
        return {"status": "failed_unknown"}

    logger.info(f"Tester: Found {len(structured_errors)} errors. Saving to {errors_path}")
    save_json_file(errors_path, structured_errors)

    # Return 'failed' to trigger the loop back to Analyzer (Fixing Mode)
    return {
        "status": "failed",
        "errors_path": errors_path
    }