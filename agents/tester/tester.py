import os
import logging
import json
from agents.tools.io.json_handlers import save_json_file
from agents.tools.testing.python.run_strategies import DockerRunner, LocalRunner, RuffRunner
from agents.tools.testing.python.error_parser import parse_python_traceback
from agents.tools.testing.common import get_code_context

logger = logging.getLogger(__name__)


def tester_node(state):
    logger.info("Tester: Start working...")

    project_path = state.get("project_path", ".")
    errors_path = state.get("errors_path", "errors.json")

    # clean previous errors
    save_json_file(errors_path, [])

    # --- OLD LOGIC COMMENTED OUT FOR DEBUGGING ---
    # # look for docker in the client's repository
    # has_docker = os.path.exists(os.path.join(project_path, "Dockerfile")) or \
    #              os.path.exists(os.path.join(project_path, "docker-compose.yml"))
    #
    # runner = None
    # if has_docker:
    #     runner = DockerRunner()
    # else:
    #     # Check for requirements.txt for LocalRunner
    #     if os.path.exists(os.path.join(project_path, "requirements.txt")):
    #         runner = LocalRunner()
    #     else:
    #         logger.warning("No Dockerfile or requirements.txt found. Cannot determine run strategy.")
    #         return {"status": "cannot_test", "needs_analysis": False}
    #
    # # run code
    # return_code, stderr = runner.run(project_path)
    # ---------------------------------------------

    # --- NEW RUFF STRATEGY ---
    runner = RuffRunner()
    # Ruff повертає (return_code, stdout_json)
    return_code, output_json = runner.run(project_path)
    # -------------------------

    # --- OLD ERROR HANDLING COMMENTED OUT ---
    # # CASE A: Dependency Conflict (-2 code from our runner)
    # if return_code == -2:
    #     logger.error("Dependency conflict detected during installation/build.")
    #     # We do NOT write to errors.json because this is not a code fixable by Analyzer
    #     return {
    #         "status": "dependency_error",
    #         "message": "Migration complete, but tests failed due to dependency conflicts. Manual update required.",
    #         "needs_analysis": False
    #     }
    # ----------------------------------------

    # CASE B: Success (0)
    if return_code == 0:
        logger.info("Ruff finished successfully. No errors detected.")
        return {"status": "success", "needs_analysis": False}

    # CASE C: Runtime/Linting Errors (Non-zero)
    logger.info(f"Ruff found errors (RC={return_code}). Parsing JSON logs...")

    # --- CUSTOM RUFF PARSING ---
    try:
        ruff_errors = json.loads(output_json)
        structured_errors = []

        for idx, err in enumerate(ruff_errors):
            # Ruff JSON structure: {'code': 'F821', 'message': '...', 'filename': '...', 'location': {'row': 1, ...}}
            file_path = err.get("filename", "")
            # Ruff often returns absolute paths, make relative if needed
            rel_path = os.path.relpath(file_path, project_path) if os.path.isabs(file_path) else file_path

            line_no = err["location"]["row"]

            # Get code context manually
            context_code = get_code_context(os.path.join(project_path, rel_path), line_no)

            structured_errors.append({
                "error_id": idx + 1,
                "message": f"{err['code']}: {err['message']}",
                "context": context_code,
                "file": rel_path
            })

    except json.JSONDecodeError:
        logger.error("Failed to parse Ruff JSON output.")
        return {"status": "failed_unknown", "needs_analysis": False}

    if not structured_errors:
        logger.warning("Tester: Ruff failed but returned no structured errors.")
        return {"status": "failed_unknown", "needs_analysis": False}

    logger.info(f"Tester: Found {len(structured_errors)} errors via Ruff. Saving to {errors_path}")
    save_json_file(errors_path, structured_errors)

    # Return 'failed' to trigger the loop back to Analyzer (Fixing Mode)
    return {
        "status": "failed",
        "errors_path": errors_path,
        "needs_analysis": True
    }