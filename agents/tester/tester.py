import os
import logging
import json
from agents.tools.io.json_handlers import save_json_file
from agents.tools.testing.python.run_strategies import RuffRunner
from agents.tools.testing.common import get_code_context

logger = logging.getLogger(__name__)


def tester_node(state):
    logger.info("Tester: Start working...")

    project_path = state.get("project_path", ".")
    errors_path = state.get("errors_path", "errors.json")

    # clean previous errors
    save_json_file(errors_path, [])

    runner = RuffRunner()
    return_code, output_json = runner.run(project_path)

    if return_code == 0:
        logger.info("Ruff finished successfully. No errors detected.")
        return {"status": "success", "needs_analysis": False}

    logger.info(f"Ruff found errors (RC={return_code}). Parsing JSON logs...")

    try:
        if not output_json or not output_json.strip():
            logger.warning("Ruff returned non-zero code but output is empty.")
            ruff_errors = []
        else:
            ruff_errors = json.loads(output_json)

        structured_errors = []

        for idx, err in enumerate(ruff_errors):
            file_path = err.get("filename", "")
            rel_path = os.path.relpath(file_path, project_path) if os.path.isabs(file_path) else file_path

            line_no = err["location"]["row"]
            error_code = err.get("code", "UNKNOWN")
            message = err.get("message", "Unknown error")

            context_code = get_code_context(os.path.join(project_path, rel_path), line_no)

            structured_errors.append({
                "error_id": idx + 1,
                "type": error_code,
                "message": message,
                "file": rel_path,
                "line": line_no,
                "context": context_code
            })

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Ruff JSON output: {e}")
        return {"status": "failed_unknown", "needs_analysis": False}

    if not structured_errors:
        logger.warning("Tester: Ruff failed but returned no structured errors.")
        return {"status": "failed_unknown", "needs_analysis": False}

    logger.info(f"Tester: Found {len(structured_errors)} errors via Ruff. Saving to {errors_path}")
    save_json_file(errors_path, structured_errors)

    return {
        "status": "failed",
        "errors_path": errors_path,
        "needs_analysis": True
    }